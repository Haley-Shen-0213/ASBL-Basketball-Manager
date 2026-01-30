# tests/team_bigdata_test/run_simulation.py
# Project: ASBL (Advanced Simulation Basketball League)
# Author: System Architect
# Date: 2026-01-26
# Description: 1000萬支隊伍生成壓力測試 (修正 Python 3.13 多進程崩潰版)

import os
import sys

# ==========================================
# [CRITICAL FIX] 環境變數設定
# 必須在匯入 numpy/pandas 之前設定，強制數值運算庫在每個子進程中只使用單一執行緒。
# 這能避免 30 個 workers x N 核心導致的執行緒爆炸 (Thread Oversubscription) 和解釋器崩潰。
# ==========================================
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import time
import shutil
import logging
import multiprocessing
import psutil
import traceback
import threading
from collections import Counter
from datetime import datetime
from typing import Dict, List, Any

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
    from app import create_app 
except ImportError as e:
    print(f"嚴重錯誤: 無法匯入專案模組。 {e}")
    sys.exit(1)

# ==========================================
# 配置常數
# ==========================================
TARGET_TEAMS = 10000     # 測試總數量
BATCH_SIZE = 1000          # 批次大小
# [建議] Windows 下建議不要超過 CPU 核心數，這裡動態調整
MAX_WORKERS = min(30, os.cpu_count() or 4) 
SAVE_THRESHOLD = 1000     # 每累積多少筆資料就寫入硬碟一次

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
# 工具類別 (Static Methods Pattern)
# ==========================================
class SimulationUtils:
    
    @staticmethod
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
            ]
        )
        
        if os.path.exists(CONFIG_PATH):
            shutil.copy(CONFIG_PATH, os.path.join(run_dir, "game_config.yaml"))
        
        return run_dir, temp_dir

    @staticmethod
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

    @staticmethod
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

# ==========================================
# Worker 邏輯
# ==========================================

def init_worker(counter_val):
    """Worker 初始化，接收共享計數器"""
    global shared_counter
    shared_counter = counter_val 
    
    try:
        # 錯開啟動時間，減少同時讀取檔案的 IO 競爭
        time.sleep(os.getpid() % 5 * 0.1) 
        
        app = create_app()
        app.app_context().push()
        GameConfigLoader.load()
        
        from app.services.player_generator import PlayerGenerator
        PlayerGenerator.initialize_class()
    except Exception as e:
        # 使用 logging 而不是 print，避免 stdout 競爭
        logging.error(f"[Worker Error] Init failed (PID {os.getpid()}): {e}")

def simulation_task(batch_count: int) -> Dict[str, Any]:
    """單一 Worker 的執行任務"""
    local_records = [] 
    local_name_counter = Counter()
    error_count = 0
    
    for _ in range(batch_count):
        start_time = time.perf_counter()
        try:
            # 增加遞迴深度限制保護，雖然 Python 預設有，但明確設定可避免某些 C-stack overflow
            # sys.setrecursionlimit(2000) 
            
            roster = TeamCreator.create_valid_roster(max_attempts=100000)
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            # 更新共享計數器
            if shared_counter:
                with shared_counter.get_lock():
                    shared_counter.value += 1

            w_score = SimulationUtils.calculate_team_weighted_score(roster)
            names = [p['name'] for p in roster]
            
            local_records.append({
                'weighted_score': w_score,
                'generation_time': duration,
                'player_names': names, 
                'roster_size': len(roster)
            })
            
            local_name_counter.update(names)
            
        except RecursionError:
            logging.warning(f"生成失敗 (RecursionError) PID {os.getpid()}")
            error_count += 1
        except Exception as e:
            error_count += 1
            # 降低錯誤日誌頻率，避免磁碟 I/O 導致更嚴重的延遲
            if error_count <= 5: 
                logging.warning(f"生成失敗 (PID {os.getpid()}): {e}")
            continue
            
    return {
        'records': local_records,
        'names': local_name_counter,
        'errors': error_count
    }

def monitor_progress(counter, total, start_time, stop_event):
    """獨立的監控執行緒，負責更新 UI"""
    while not stop_event.is_set():
        current = counter.value
        if current > 0:
            elapsed = time.time() - start_time
            rate = current / elapsed if elapsed > 0 else 0
            
            try:
                proc = psutil.Process(os.getpid())
                mem = proc.memory_info().rss / 1024 / 1024
            except:
                mem = 0
            
            sys.stdout.write(
                f"\r進度: {current:,}/{total:,} ({current/total:.1%}) | "
                f"速度: {rate:.1f} 隊/秒 | "
                f"RAM: {mem:.0f} MB"
            )
            sys.stdout.flush()
        
        if current >= total:
            break
            
        time.sleep(0.5) # 降低更新頻率以減少資源消耗

# ==========================================
# 主程式
# ==========================================

def main():
    # 確保 Windows 下 multiprocessing 正常運作
    multiprocessing.freeze_support()
    
    run_dir, temp_dir = SimulationUtils.setup_environment()
    print(f"開始執行 {TARGET_TEAMS:,} 支隊伍的模擬生成")
    print(f"輸出目錄: {run_dir}")
    print(f"設定: Batch={BATCH_SIZE}, Workers={MAX_WORKERS}")
    print(f"Python 版本: {sys.version.split()[0]}")
    print("-" * 60)

    total_batches = TARGET_TEAMS // BATCH_SIZE
    tasks = [BATCH_SIZE] * total_batches
    if TARGET_TEAMS % BATCH_SIZE > 0:
        tasks.append(TARGET_TEAMS % BATCH_SIZE)

    global_counter = multiprocessing.Value('i', 0)
    stop_monitor = threading.Event()
    start_global = time.time()
    
    monitor_thread = threading.Thread(
        target=monitor_progress, 
        args=(global_counter, TARGET_TEAMS, start_global, stop_monitor)
    )
    monitor_thread.start()
    
    buffer_records = []
    global_name_counter = Counter()
    total_errors = 0
    chunk_counter = 0
    
    logging.info("正在啟動 Worker Pool...")
    
    try:
        # 使用 spawn (Windows 預設)
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(processes=MAX_WORKERS, initializer=init_worker, initargs=(global_counter,)) as pool:
            results = pool.imap_unordered(simulation_task, tasks)
            
            for res in results:
                buffer_records.extend(res['records'])
                global_name_counter.update(res['names'])
                total_errors += res.get('errors', 0)
                
                if len(buffer_records) >= SAVE_THRESHOLD:
                    SimulationUtils.save_chunk(buffer_records, temp_dir, chunk_counter)
                    buffer_records = []
                    chunk_counter += 1
    except KeyboardInterrupt:
        print("\n使用者中斷執行，正在保存現有進度...")
        logging.warning("使用者中斷執行")
    except Exception as e:
        print(f"\n主進程發生錯誤: {e}")
        logging.error(f"主進程發生錯誤: {e}")
        traceback.print_exc()
    finally:
        stop_monitor.set()
        monitor_thread.join()
    
    # 寫入剩餘資料
    if buffer_records:
        SimulationUtils.save_chunk(buffer_records, temp_dir, chunk_counter)
        
    print("\n" + "-" * 60)
    total_duration = time.time() - start_global
    print(f"模擬結束。總耗時 {total_duration:.2f} 秒。開始合併數據...")
    logging.info(f"模擬結束。總耗時 {total_duration:.2f} 秒。")

    # ==========================================
    # 合併 Parquet 數據
    # ==========================================
    final_parquet_path = os.path.join(run_dir, 'teams_data.parquet')
    
    try:
        # 檢查是否有生成的檔案
        if not os.listdir(temp_dir):
            print("警告: 沒有生成任何數據檔案。")
            return

        df_all = pd.read_parquet(temp_dir)
        df_all.to_parquet(final_parquet_path, engine='pyarrow')
        logging.info(f"所有分塊已合併至: {final_parquet_path}")
        
        shutil.rmtree(temp_dir)
        logging.info("暫存目錄已清理。")
        
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
            f.write(f"**Python 版本**: {sys.version}\n")
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

    except Exception as e:
        logging.error(f"合併 Parquet 或生成報告失敗: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()
