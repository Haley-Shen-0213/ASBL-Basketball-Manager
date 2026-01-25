# tests/team_bigdata_test/run_simulation.py
# Project: ASBL (Advanced Simulation Basketball League)
# Author: System Architect
# Date: 2025-12-29
# Description: 1000萬支隊伍生成壓力測試 (即時進度顯示版)

import os
import sys
import time
import shutil
import logging
import multiprocessing
import psutil
import statistics
import traceback
import threading
from collections import Counter
from datetime import datetime
from typing import Dict, List, Any
import ctypes

# 引入 Pandas 用於數據儲存
try:
    import pandas as pd
except ImportError:
    print("錯誤: 缺少 pandas 套件。請執行 pip install pandas pyarrow")
    sys.exit(1)

# 假設專案根目錄在兩層之上
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from app.services.team_creator import TeamCreator
    from app.utils.game_config_loader import GameConfigLoader
    from app import create_app, db 
except ImportError as e:
    print(f"嚴重錯誤: 無法匯入專案模組。 {e}")
    sys.exit(1)

# ==========================================
# 配置常數
# ==========================================
TARGET_TEAMS = 20_000_000     # 測試總數量
BATCH_SIZE = 50000            # 批次大小 (保持 50 以平衡效能)
MAX_WORKERS = 30           # 工作進程數
SAVE_THRESHOLD = 10000      # 每累積多少筆資料就寫入硬碟一次

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(BASE_DIR, 'data')
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, '../../config/game_config.yaml'))

STAT_WEIGHTS = {
    'talent_offiq': 1.08, 'talent_defiq': 1.07, 'ath_speed': 1.07,
    'off_move': 1.05, 'ath_strength': 1.05, 'ath_jump': 1.05,
    'off_pass': 1.04, 'def_contest': 1.04, 'off_handle': 1.04,
    'off_dribble': 1.04, 'def_disrupt': 1.04, 'shot_touch': 1.03,
    'shot_release': 1.03, 'def_boxout': 1.03, 'shot_range': 1.02,
    'def_rebound': 1.02, 'shot_accuracy': 1.02,
}

# ==========================================
# 全域變數 (Worker 內部使用)
# ==========================================
shared_counter = None # 用於跨進程計數

# ==========================================
# 工具函數
# ==========================================

def setup_environment():
    """建立帶有時間戳記的獨立執行目錄與暫存目錄"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(DATA_ROOT, timestamp)
    temp_dir = os.path.join(run_dir, "temp_parts")
    
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    log_file = os.path.join(run_dir, f"simulation.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            # logging.StreamHandler() # 關閉 StreamHandler，避免與進度條衝突
        ]
    )
    
    if os.path.exists(CONFIG_PATH):
        shutil.copy(CONFIG_PATH, os.path.join(run_dir, "game_config.yaml"))
    
    return run_dir, temp_dir

def calculate_team_weighted_score(roster: List[Dict[str, Any]]) -> float:
    total_score = 0.0
    for player in roster:
        stats = player.get('raw_stats', {})
        if not stats and 'detailed_stats' in player:
            stats = {}
            for cat in player['detailed_stats'].values():
                stats.update(cat)
        
        player_score = 0.0
        for attr, weight in STAT_WEIGHTS.items():
            val = stats.get(attr, 0)
            player_score += val * weight
        total_score += player_score
    return total_score

def init_worker(counter_val):
    """Worker 初始化，接收共享計數器"""
    global shared_counter
    shared_counter = counter_val # 綁定到 Worker 的全域變數
    
    try:
        time.sleep(os.getpid() % 5 * 0.1) 
        app = create_app()
        app.app_context().push()
        GameConfigLoader.load()
        from app.services.player_generator import PlayerGenerator
        PlayerGenerator.initialize_class()
    except Exception as e:
        print(f"[Worker Error] Init failed: {e}")

def simulation_task(batch_count: int) -> Dict[str, Any]:
    """單一 Worker 的執行任務"""
    local_records = [] 
    local_name_counter = Counter()
    error_count = 0
    
    for _ in range(batch_count):
        start_time = time.perf_counter()
        try:
            roster = TeamCreator.create_valid_roster(max_attempts=100000)
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            # === [關鍵修改] 即時更新共享計數器 ===
            with shared_counter.get_lock():
                shared_counter.value += 1
            # ===================================

            w_score = calculate_team_weighted_score(roster)
            names = [p['name'] for p in roster]
            
            local_records.append({
                'weighted_score': w_score,
                'generation_time': duration,
                'player_names': names, 
                'roster_size': len(roster)
            })
            
            local_name_counter.update(names)
            
        except Exception as e:
            error_count += 1
            if error_count == 1:
                # 使用 logging 而不是 print，避免打斷進度條
                logging.warning(f"生成失敗 (PID {os.getpid()}): {e}")
            continue
            
    return {
        'records': local_records,
        'names': local_name_counter,
        'errors': error_count
    }

def save_chunk(data: List[Dict], temp_dir: str, chunk_id: int):
    """將目前的緩衝區資料寫入暫存 Parquet 檔"""
    if not data:
        return
    try:
        df = pd.DataFrame(data)
        file_path = os.path.join(temp_dir, f"part_{chunk_id:05d}.parquet")
        df.to_parquet(file_path, engine='pyarrow')
        logging.info(f"已寫入分塊檔案: {os.path.basename(file_path)} ({len(data)} 筆)")
    except Exception as e:
        logging.error(f"寫入分塊檔案失敗: {e}")

def monitor_progress(counter, total, start_time, stop_event):
    """獨立的監控執行緒，負責更新 UI"""
    while not stop_event.is_set():
        current = counter.value
        if current > 0:
            elapsed = time.time() - start_time
            rate = current / elapsed
            mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            
            # 使用 \r 覆蓋同一行，顯示即時進度
            sys.stdout.write(
                f"\r進度: {current:,}/{total:,} ({current/total:.1%}) | "
                f"速度: {rate:.1f} 隊/秒 | "
                f"RAM: {mem:.0f} MB"
            )
            sys.stdout.flush()
        
        if current >= total:
            break
            
        time.sleep(0.2) # 每 0.2 秒更新一次 UI

# ==========================================
# 主程式
# ==========================================

def main():
    run_dir, temp_dir = setup_environment()
    print(f"開始執行 {TARGET_TEAMS:,} 支隊伍的模擬生成")
    print(f"輸出目錄: {run_dir}")
    print(f"設定: Batch={BATCH_SIZE}, Workers={MAX_WORKERS}")
    print("-" * 60)

    total_batches = TARGET_TEAMS // BATCH_SIZE
    tasks = [BATCH_SIZE] * total_batches
    if TARGET_TEAMS % BATCH_SIZE > 0:
        tasks.append(TARGET_TEAMS % BATCH_SIZE)

    # 建立共享計數器
    global_counter = multiprocessing.Value('i', 0)
    
    # 啟動監控執行緒
    stop_monitor = threading.Event()
    start_global = time.time()
    monitor_thread = threading.Thread(
        target=monitor_progress, 
        args=(global_counter, TARGET_TEAMS, start_global, stop_monitor)
    )
    monitor_thread.start()
    
    # 數據收集容器
    buffer_records = []
    global_name_counter = Counter()
    total_errors = 0
    chunk_counter = 0
    
    logging.info("正在啟動 Worker Pool...")
    
    # 傳遞 global_counter 給每個 Worker
    with multiprocessing.Pool(processes=MAX_WORKERS, initializer=init_worker, initargs=(global_counter,)) as pool:
        results = pool.imap_unordered(simulation_task, tasks)
        
        for res in results:
            # 1. 收集數據
            buffer_records.extend(res['records'])
            global_name_counter.update(res['names'])
            total_errors += res.get('errors', 0)
            
            # 2. 檢查存檔門檻
            if len(buffer_records) >= SAVE_THRESHOLD:
                save_chunk(buffer_records, temp_dir, chunk_counter)
                buffer_records = []
                chunk_counter += 1
    
    # 停止監控
    stop_monitor.set()
    monitor_thread.join()
    
    # 寫入剩餘資料
    if buffer_records:
        save_chunk(buffer_records, temp_dir, chunk_counter)
        
    print("\n" + "-" * 60)
    total_duration = time.time() - start_global
    print(f"模擬完成。總耗時 {total_duration:.2f} 秒。開始合併數據...")
    logging.info(f"模擬完成。總耗時 {total_duration:.2f} 秒。")

    # ==========================================
    # 合併 Parquet 數據
    # ==========================================
    final_parquet_path = os.path.join(run_dir, 'teams_data.parquet')
    
    try:
        df_all = pd.read_parquet(temp_dir)
        df_all.to_parquet(final_parquet_path, engine='pyarrow')
        logging.info(f"所有分塊已合併至: {final_parquet_path}")
        
        shutil.rmtree(temp_dir)
        logging.info("暫存目錄已清理。")
        
    except Exception as e:
        logging.error(f"合併 Parquet 失敗: {e}")
        traceback.print_exc()
        return

    # ==========================================
    # 報告生成
    # ==========================================
    logging.info("正在分析數據並生成報告...")
    
    scores = df_all['weighted_score']
    times = df_all['generation_time']
    
    avg_score = scores.mean()
    stdev_score = scores.std()
    min_score = scores.min()
    max_score = scores.max()
    avg_time = times.mean()
    
    total_players = sum(global_name_counter.values())
    unique_names = len(global_name_counter)
    duplicate_ratio = ((total_players - unique_names) / total_players) * 100 if total_players > 0 else 0
    top_duplicates = global_name_counter.most_common(10)

    report_file = os.path.join(run_dir, "report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# ASBL 隊伍生成大數據壓力測試報告\n")
        f.write(f"**執行時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**資料路徑**: `{run_dir}`\n")
        f.write(f"**目標/實際**: {TARGET_TEAMS:,} / {len(df_all):,}\n")
        f.write(f"**失敗次數**: {total_errors}\n\n")
        
        f.write(f"## 1. 統計數據\n")
        f.write(f"- **平均加權分**: {avg_score:.4f}\n")
        f.write(f"- **標準差**: {stdev_score:.4f}\n")
        f.write(f"- **最小/最大分**: {min_score:.4f} / {max_score:.4f}\n")
        f.write(f"- **平均生成時間**: {avg_time:.6f} 秒/隊\n")
        f.write(f"- **名字重複率**: {duplicate_ratio:.4f}%\n")
        
        f.write(f"## 2. 前 10 名重複名字\n")
        f.write(f"| 名字 | 次數 |\n|---|---|\n")
        for name, count in top_duplicates:
            f.write(f"| {name} | {count} |\n")
            
    print(f"報告已生成於：{report_file}")
    logging.info(f"報告已生成於：{report_file}")

if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()