# tests/schedule_bigdata_test/run_schedule_optimization.py
# -*- coding: utf-8 -*-
"""
專案名稱：ASBL-Basketball-Manager
模組名稱：賽程積分大數據分析工具 (V2 - Parquet Recorder)
功能描述：
    1. 執行蒙地卡羅模擬分析賽程積分。
    2. 支援多進程 (Multiprocessing) 並行運算。
    3. 實作 tqdm 進度條顯示。
    4. 將所有隨機生成的「賽程組合(Indices)」與「積分(Score)」分批寫入 Parquet 檔案。
"""

import os
import sys
import time
import psutil
import multiprocessing
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from datetime import datetime
from tqdm import tqdm  # 進度條套件

# 設定中文字型
import platform
system_name = platform.system()
if system_name == "Windows":
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei']
elif system_name == "Darwin":
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC']
else:
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 配置參數
# ==========================================
TOTAL_ITERATIONS = 100_000_000  # 目標：一億次
BATCH_SIZE = 100_000            # Worker 單次運算量
FLUSH_THRESHOLD = 2_000_000     # 每累積多少筆資料寫入一次硬碟 (控制記憶體)

NUM_TEAMS = 36
NUM_DAYS = 70

# 輸出目錄設定
OUTPUT_DIR = "tests/schedule_bigdata_test/data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 自動偵測 CPU 核心數 (保留 2 核心給系統與 I/O)
WORKER_COUNT = max(1, os.cpu_count() - 2)

# ==========================================
# 核心邏輯 (Core Logic)
# ==========================================

def generate_round_robin(num_teams=36, num_days=70):
    """產生標準圓桌法賽程"""
    schedule = []
    teams = list(range(1, num_teams + 1))
    fixed_team = teams[0]
    rotating_teams = teams[1:]
    
    for day in range(num_days):
        daily_matches = []
        if day % 2 == 0:
            daily_matches.append((fixed_team, rotating_teams[0]))
        else:
            daily_matches.append((rotating_teams[0], fixed_team))
            
        for i in range(1, len(teams) // 2):
            t1 = rotating_teams[i]
            t2 = rotating_teams[-i]
            if day % 2 == 0:
                daily_matches.append((t1, t2))
            else:
                daily_matches.append((t2, t1))
        
        schedule.append(daily_matches)
        rotating_teams = [rotating_teams[-1]] + rotating_teams[:-1]
        print("圓桌算法已完成")
    return schedule

# 預先生成賽程 (Global)
BASE_SCHEDULE = generate_round_robin(NUM_TEAMS, NUM_DAYS)

def worker_task(iterations):
    """
    Worker 執行緒：
    回傳: (scores_array, indices_matrix)
    """
    # 1. 重建查找表 (Day -> Team -> Venue 0/1)
    venues_matrix = np.zeros((NUM_DAYS, NUM_TEAMS + 1), dtype=np.int8)
    for d, matches in enumerate(BASE_SCHEDULE):
        for home, away in matches:
            venues_matrix[d][home] = 0 # Home
            venues_matrix[d][away] = 1 # Away
            
    # 準備容器
    # scores: int16 (積分通常不會超過 32767)
    # indices: int8 (天數 0-69)
    local_scores = np.zeros(iterations, dtype=np.int16)
    local_indices = np.zeros((iterations, NUM_DAYS), dtype=np.int8)
    
    day_indices = np.arange(NUM_DAYS, dtype=np.int8)
    
    for i in range(iterations):
        # 2. 隨機打亂
        np.random.shuffle(day_indices)
        
        # 存入 indices (這是我們要紀錄的賽程組合)
        local_indices[i] = day_indices
        
        # 3. 計算積分
        shuffled_venues = venues_matrix[day_indices]
        
        # 轉置矩陣 (Team, Day)
        team_matrix = shuffled_venues.T
        total_score = 0
        
        # 針對 36 隊計算
        for t in range(1, NUM_TEAMS + 1):
            venues = team_matrix[t]
            # 找出變化點
            change_indices = np.where(venues[:-1] != venues[1:])[0] + 1
            boundaries = np.concatenate(([0], change_indices, [NUM_DAYS]))
            lengths = np.diff(boundaries)
            
            # 向量化計分
            score = 0
            score += np.sum(lengths == 2) * 1
            score += np.sum(lengths == 3) * 3
            score += np.sum(lengths == 4) * 5
            score += np.sum(lengths == 5) * 10
            score += np.sum(lengths >= 6) * 30
            
            total_score += score
        
        local_scores[i] = total_score
        
    return local_scores, local_indices

# ==========================================
# 主程式 (Main)
# ==========================================

def save_chunk_to_parquet(scores, indices, chunk_id):
    """將數據寫入 Parquet"""
    # 建立 DataFrame
    # Columns: score, d0, d1, ..., d69
    cols = ['score'] + [f'd{i}' for i in range(NUM_DAYS)]
    
    # 組合數據: 先將 score 轉為 (N, 1)，再與 indices (N, 70) 合併
    # 注意：scores 是 int16, indices 是 int8，合併時會變成 int16
    data = np.hstack((scores.reshape(-1, 1), indices))
    
    df = pd.DataFrame(data, columns=cols)
    
    # 為了節省空間，強制轉型
    # score -> int16, d0~d69 -> int8
    convert_dict = {'score': 'int16'}
    for c in cols[1:]:
        convert_dict[c] = 'int8'
    
    df = df.astype(convert_dict)
    
    filename = os.path.join(OUTPUT_DIR, f"schedule_sim_part_{chunk_id:04d}.parquet")
    df.to_parquet(filename, engine='pyarrow', compression='snappy')
    return filename

def main():
    print("="*60)
    print(f"🚀 ASBL 賽程優化大數據分析 (V2 - Parquet Recorder)")
    print(f"🎯 目標: {TOTAL_ITERATIONS:,} 次模擬")
    print(f"💾 輸出: {OUTPUT_DIR}/*.parquet")
    print(f"💻 硬體: {WORKER_COUNT} Workers")
    print("="*60)
    
    # 準備任務
    num_tasks = TOTAL_ITERATIONS // BATCH_SIZE
    tasks = [BATCH_SIZE] * num_tasks
    remainder = TOTAL_ITERATIONS % BATCH_SIZE
    if remainder > 0:
        tasks.append(remainder)
    
    # 數據緩衝區
    score_buffer = []
    indices_buffer = []
    
    # 統計用 (只存分數，不存 Indices 以節省記憶體)
    all_scores_history = [] 
    
    chunk_counter = 1
    start_time = time.time()
    
    # 啟動多進程池
    with multiprocessing.Pool(processes=WORKER_COUNT) as pool:
        # 使用 tqdm 顯示進度條
        with tqdm(total=TOTAL_ITERATIONS, unit="sim", desc="模擬進度") as pbar:
            
            for scores, indices in pool.imap_unordered(worker_task, tasks):
                # 1. 收集數據
                score_buffer.append(scores)
                indices_buffer.append(indices)
                all_scores_history.append(scores) # 僅用於最後繪圖
                
                batch_len = len(scores)
                pbar.update(batch_len)
                
                # 2. 檢查緩衝區是否達到寫入門檻
                current_buffer_size = sum(len(x) for x in score_buffer)
                
                if current_buffer_size >= FLUSH_THRESHOLD:
                    # 合併緩衝區
                    flush_scores = np.concatenate(score_buffer)
                    flush_indices = np.concatenate(indices_buffer)
                    
                    # 寫入磁碟
                    save_chunk_to_parquet(flush_scores, flush_indices, chunk_counter)
                    
                    # 更新狀態
                    pbar.set_postfix_str(f"Saved Part {chunk_counter}")
                    chunk_counter += 1
                    
                    # 清空緩衝區
                    score_buffer = []
                    indices_buffer = []
                    
                    # 記憶體監控 (可選)
                    # mem = psutil.virtual_memory()
                    # if mem.percent > 90: ...

    # 寫入剩餘的數據
    if score_buffer:
        flush_scores = np.concatenate(score_buffer)
        flush_indices = np.concatenate(indices_buffer)
        save_chunk_to_parquet(flush_scores, flush_indices, chunk_counter)
        print(f"✅ 已寫入最後區塊 Part {chunk_counter}")

    total_time = time.time() - start_time
    print(f"\n✨ 模擬全部完成！總耗時: {total_time:.2f} 秒")
    
    # --- 數據分析與繪圖 ---
    print("\n📊 正在進行數據統計分析...")
    
    # 將歷史分數合併為一個大陣列 (注意記憶體，若 1 億個 int16 約 200MB，非常安全)
    final_scores = np.concatenate(all_scores_history)
    
    stats = {
        "min": np.min(final_scores),
        "max": np.max(final_scores),
        "mean": np.mean(final_scores),
        "std": np.std(final_scores),
        "p0.1": np.percentile(final_scores, 0.1),
        "p1": np.percentile(final_scores, 1),
        "p5": np.percentile(final_scores, 5),
        "p50": np.median(final_scores)
    }
    
    print("-" * 40)
    print(f"最低積分 (Best): {stats['min']}")
    print(f"最高積分 (Worst): {stats['max']}")
    print(f"平均積分:       {stats['mean']:.2f} (σ={stats['std']:.2f})")
    print(f"Top 0.1% 門檻:  <{stats['p0.1']:.1f}")
    print(f"Top 1% 門檻:    <{stats['p1']:.1f}")
    print("-" * 40)
    
    # --- 繪圖 ---
    print("🎨 正在繪製圖表...")
    plt.figure(figsize=(12, 6))
    
    # 直方圖
    plt.hist(final_scores, bins=100, density=True, alpha=0.6, color='skyblue', edgecolor='black', label='模擬分佈')
    
    # KDE 曲線 (取樣繪製)
    sample_size = min(100000, len(final_scores))
    sample = np.random.choice(final_scores, sample_size, replace=False)
    kde = gaussian_kde(sample)
    x_grid = np.linspace(stats['min'], stats['max'], 200)
    plt.plot(x_grid, kde(x_grid), 'r-', linewidth=2, label='KDE 密度曲線')
    
    # 標記線
    plt.axvline(stats['p1'], color='green', linestyle='--', linewidth=2, label=f'Top 1% (<{stats["p1"]:.0f})')
    plt.axvline(stats['mean'], color='orange', linestyle='--', linewidth=2, label=f'平均 ({stats["mean"]:.0f})')
    
    plt.title(f'賽程積分常態分佈 (N={TOTAL_ITERATIONS:,})\n耗時: {total_time:.1f}s', fontsize=14)
    plt.xlabel('積分 (越低越好)', fontsize=12)
    plt.ylabel('機率密度', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    output_img = f'schedule_analysis_{datetime.now().strftime("%Y%m%d_%H%M")}.png'
    plt.savefig(output_img)
    print(f"💾 圖表已儲存至: {output_img}")
    plt.show()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()