# tests/big_data/verify_generator_integration.py
import multiprocessing
import time
import os
import sys
import pandas as pd
import yaml
import psutil
import shutil
from datetime import datetime

# ==========================================
# 環境設定 (Environment Setup)
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.append(project_root)

try:
    from app import create_app
    from app.services.player_generator import PlayerGenerator
    import config
    print(f"成功匯入專案模組。")
except ImportError as e:
    print(f"錯誤: 無法匯入應用程式模組。\n{e}")
    sys.exit(1)

# ==========================================
# 輔助函數
# ==========================================
def load_config():
    config_path = os.path.join(current_dir, 'test_config.yaml')
    if not os.path.exists(config_path):
        print(f"錯誤: 找不到設定檔 {config_path}")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def show_config_summary(conf):
    """顯示當前設定檔摘要"""
    exec_conf = conf['execution']
    out_conf = conf['output']
    log_conf = conf.get('logging', {'enabled': False})
    
    # 計算實際將使用的 Worker 數量
    configured_workers = exec_conf['max_workers']
    if configured_workers == 0:
        actual_workers = max(1, multiprocessing.cpu_count() - 2)
        worker_msg = f"自動偵測 ({actual_workers} 核心)"
    else:
        worker_msg = f"{configured_workers} 核心"

    print(f"\n=== 目前測試設定 (Current Configuration) ===")
    print(f"• 試跑次數 (Dry Run):    {exec_conf['dry_run_count']:,}")
    print(f"• 切片大小 (Batch Size): {exec_conf['batch_size_per_task']:,}")
    print(f"• 並行運算 (Workers):    {worker_msg}")
    print(f"• 輸出目錄 (Output):     {out_conf['directory_name']}")
    print(f"• 壓縮格式 (Compression): {out_conf['compression']}")
    print(f"• 執行紀錄 (Logging):    {'開啟' if log_conf.get('enabled') else '關閉'} ({log_conf.get('filename', '')})")
    print(f"==========================================\n")

def get_system_stats():
    """回傳系統狀態: (CPU使用率%, RAM使用率%, RAM使用量GB)"""
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    return cpu_pct, mem.percent, mem.used / (1024 ** 3)

def format_time(seconds):
    """將秒數轉換為 MM:SS 格式"""
    if seconds is None or seconds < 0: return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def log_file_write(conf, step_name, elapsed_seconds, file_name, record_count):
    """
    寫入執行紀錄到 Log 檔
    格式: [時間] [步驟] 耗時 | CPU | RAM | 檔案 | 筆數
    """
    log_conf = conf.get('logging', {})
    if not log_conf.get('enabled', False):
        return

    log_dir = os.path.join(current_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, log_conf.get('filename', 'execution.log'))
    
    cpu_pct, mem_pct, mem_gb = get_system_stats()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_msg = (
        f"[{now_str}] [{step_name:<10}] "
        f"Elapsed: {format_time(elapsed_seconds):<8} | "
        f"CPU: {cpu_pct:4.1f}% | "
        f"RAM: {mem_gb:4.1f}GB ({mem_pct}%) | "
        f"Count: {record_count:<8} | "
        f"File: {file_name}\n"
    )
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_msg)
    except Exception as e:
        print(f"\n[Warning] 無法寫入 Log: {e}")

def print_progress_bar(current, total, start_time, cpu_pct, mem_gb, mem_pct):
    """
    繪製控制台進度條
    """
    if total == 0: return
    bar_length = 25
    percent = min(1.0, float(current) / total)
    arrow = '█' * int(round(percent * bar_length))
    spaces = '░' * (bar_length - len(arrow))
    
    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    remaining_count = total - current
    eta = remaining_count / rate if rate > 0 else 0
    
    total_str = f"{total/1000:.0f}k" if total < 1000000 else f"{total/1000000:.1f}m"
    
    sys.stdout.write(
        f"\r[{arrow}{spaces}] {percent*100:5.1f}% "
        f"| 總數: {total_str} "
        f"| 速度: {rate:5.0f} 筆/秒 "
        f"| CPU: {cpu_pct:4.1f}% "
        f"| RAM: {mem_gb:4.1f}G ({mem_pct}%) "
        f"| ETA: {format_time(eta)} "
    )
    sys.stdout.flush()

# ==========================================
# Worker 函數
# ==========================================
def worker_task(batch_size):
    """
    Worker 負責生成指定數量的資料並回傳 List[Dict]
    """
    if hasattr(config, 'TestingConfig'):
        conf = config.TestingConfig
    else:
        conf = config.Config
        
    app = create_app(conf)
    
    data_batch = []
    with app.app_context():
        try:
            for _ in range(batch_size):
                payload = PlayerGenerator.generate_payload()
                flat_data = PlayerGenerator.to_flat_dict(payload)
                data_batch.append(flat_data)
        except Exception as e:
            print(f"[Worker Error] {e}")
            
    return data_batch

# ==========================================
# 流程步驟
# ==========================================

def run_dry_run(conf):
    """步驟 1: 試跑與驗證"""
    count = conf['execution']['dry_run_count']
    batch_size_config = conf['execution']['batch_size_per_task']
    
    chunk_size = min(batch_size_config, count)
    
    out_dir = os.path.join(current_dir, 'output', 'dry_run')
    if os.path.exists(out_dir): shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"--- [步驟 1] 試跑 (Dry Run) ---")
    print("正在初始化並生成樣本數據...")
    
    start_time = time.time()
    
    total_chunks = (count + chunk_size - 1) // chunk_size
    data = []
    
    psutil.cpu_percent(interval=None) 
    cpu_pct, mem_pct, mem_gb = get_system_stats()
    print_progress_bar(0, count, start_time, cpu_pct, mem_gb, mem_pct)

    for i in range(total_chunks):
        current_batch_size = min(chunk_size, count - len(data))
        
        batch_data = worker_task(current_batch_size)
        data.extend(batch_data)
        
        cpu_pct, mem_pct, mem_gb = get_system_stats()
        print_progress_bar(len(data), count, start_time, cpu_pct, mem_gb, mem_pct)
    
    print() # 換行
    
    df = pd.DataFrame(data)
    filename = os.path.join(out_dir, "dry_run.parquet")
    df.to_parquet(filename, engine='pyarrow', compression=conf['output']['compression'])
    
    end_time = time.time()
    duration = end_time - start_time
    file_size = os.path.getsize(filename)
    
    # [Log] 記錄試跑
    log_file_write(conf, "DRY_RUN", duration, "dry_run.parquet", len(df))
    
    print(f"試跑完成。耗時: {duration:.4f} 秒")
    
    print(f"\n--- [驗證] 檢查試跑檔案內容 ---")
    try:
        verify_df = pd.read_parquet(filename)
        print(f"欄位列表: {list(verify_df.columns)[:10]} ... (共 {len(verify_df.columns)} 欄)")
        print(f"\n前 3 筆資料預覽:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(verify_df.head(3))
    except Exception as e:
        print(f"驗證失敗: {e}")
        sys.exit(1)
        
    return duration, file_size

def estimate_and_confirm(dry_time, dry_size, dry_count, conf):
    """步驟 2 & 3: 使用者輸入與預估"""
    print("\n請檢查上方的資料預覽。")
    if input("資料欄位與內容是否符合預期? (y/n): ").lower() != 'y':
        sys.exit(0)

    while True:
        while True:
            user_input = input("\n請輸入預計完整執行的次數 (例如 1000000)，或輸入 'q' 離開: ")
            if user_input.lower() == 'q': sys.exit(0)
            try:
                target_count = int(user_input)
                if target_count > 0: break
            except ValueError: pass
        
        max_workers = conf['execution']['max_workers']
        if max_workers == 0:
            max_workers = max(1, multiprocessing.cpu_count() - 2)
            
        time_per_item = dry_time / dry_count
        size_per_item = dry_size / dry_count
        
        est_total_time_serial = time_per_item * target_count
        efficiency = 0.85 
        est_total_time_parallel = est_total_time_serial / (max_workers * efficiency)
        est_total_size = size_per_item * target_count
        
        print(f"\n--- [步驟 2] 資源預估 ({target_count:,} 筆) ---")
        print(f"Worker 數:       {max_workers}")
        print(f"預估耗時 (Wall): {est_total_time_parallel:.2f} 秒 ({est_total_time_parallel/60:.2f} 分鐘)")
        print(f"預估硬碟空間:    {est_total_size / 1024 / 1024:.2f} MB ({est_total_size / 1024 / 1024 / 1024:.2f} GB)")
        
        confirm = input("是否開始進行測試? (y/n): ").lower()
        if confirm == 'y':
            # [Log] 記錄開始
            log_file_write(conf, "START", 0, f"Target: {target_count}", 0)
            return target_count, max_workers
        elif confirm == 'n':
            print("\n--- 重新設定目標 ---")
            continue
        else:
            sys.exit(0)

def run_streaming_test(target_count, max_workers, conf):
    """步驟 4: 正式執行 (串流模式)"""
    batch_size = conf['execution']['batch_size_per_task']
    out_dir_name = conf['output']['directory_name']
    output_dir = os.path.join(current_dir, 'output', out_dir_name)
    
    if os.path.exists(output_dir): shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n--- [步驟 3] 正式測試 (Streaming Mode) ---")
    print(f"目標: {target_count:,} | Batch: {batch_size:,} | Output: {output_dir}")
    
    total_tasks = (target_count + batch_size - 1) // batch_size
    tasks = [batch_size] * total_tasks
    if target_count % batch_size != 0:
        tasks[-1] = target_count % batch_size
        
    print(f"總任務數: {total_tasks} 批")
    print("啟動 Worker Pool 與即時監控...\n")
    
    start_time = time.time()
    processed_count = 0
    file_index = 0
    
    ctx = multiprocessing.get_context('spawn')
    
    with ctx.Pool(processes=max_workers) as pool:
        result_iterator = pool.imap_unordered(worker_task, tasks)
        
        psutil.cpu_percent(interval=None)
        cpu_pct, mem_pct, mem_gb = get_system_stats()
        print_progress_bar(0, target_count, start_time, cpu_pct, mem_gb, mem_pct)
        
        for batch_data in result_iterator:
            if not batch_data: continue
            
            df = pd.DataFrame(batch_data)
            filename = f"part_{file_index:05d}.parquet"
            filepath = os.path.join(output_dir, filename)
            df.to_parquet(filepath, engine='pyarrow', compression=conf['output']['compression'])
            
            processed_count += len(batch_data)
            file_index += 1
            
            # [Log] 記錄每個批次寫入
            elapsed_now = time.time() - start_time
            log_file_write(conf, "BATCH_SAVE", elapsed_now, filename, len(batch_data))
            
            cpu_pct, mem_pct, mem_gb = get_system_stats()
            print_progress_bar(processed_count, target_count, start_time, cpu_pct, mem_gb, mem_pct)

    total_duration = time.time() - start_time
    
    # [Log] 記錄結束
    log_file_write(conf, "COMPLETE", total_duration, "ALL_FILES", processed_count)
    
    print(f"\n\n=== 測試完成 ===")
    print(f"總耗時: {total_duration:.2f} 秒")
    
    total_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in os.listdir(output_dir) if f.endswith('.parquet'))
    print(f"總檔案大小: {total_size / 1024 / 1024:.2f} MB")

# ==========================================
# 主程式
# ==========================================
if __name__ == "__main__":
    try:
        from scripts.terminal import clear_terminal
        clear_terminal()
    except ImportError:
        pass
    except Exception:
        pass
        
    conf = load_config()
    
    # 0. 顯示設定
    show_config_summary(conf)
    
    # 1. 試跑
    d_time, d_size = run_dry_run(conf)
    
    # 2. 預估與確認
    target, workers = estimate_and_confirm(d_time, d_size, conf['execution']['dry_run_count'], conf)
    
    # 3. 執行
    run_streaming_test(target, workers, conf)