# tests/player_generator_big_data/run_test.py
import os
import sys
import time
import yaml
import shutil
import multiprocessing
import random
import psutil
import json
from datetime import datetime, timedelta

# ==========================================
# 環境設定
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.append(project_root)

# 延遲匯入 pandas，避免在主進程初始化時造成底層衝突
pd = None 

try:
    from app import create_app
    from app.services.player_generator import PlayerGenerator
    import config
    from analyzer import BigDataAnalyzer
except ImportError as e:
    print(f"[Error] 無法匯入專案模組，請檢查路徑。\n{e}")
    sys.exit(1)

# ==========================================
# 工具函式
# ==========================================
def load_config():
    path = os.path.join(current_dir, 'test_config.yaml')
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_system_stats():
    mem = psutil.virtual_memory()
    return psutil.cpu_percent(), mem.percent, mem.used / (1024**3)

def get_latest_run_dir(base_dir):
    """搜尋 base_dir 下最新的時間戳資料夾"""
    if not os.path.exists(base_dir):
        return None
    
    subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not subdirs:
        return None
    
    # 假設資料夾名稱格式為 YYYYMMDD_HHMM，排序後最後一個即為最新
    subdirs.sort()
    return os.path.join(base_dir, subdirs[-1])

class ResourceMonitor:
    """用於追蹤整個執行過程中的資源峰值"""
    def __init__(self):
        self.peak_cpu = 0.0
        self.peak_ram_gb = 0.0
        self.start_time = None
        self.end_time = None
        self.total_rows = 0

    def update(self):
        cpu, _, mem_gb = get_system_stats()
        if cpu > self.peak_cpu: self.peak_cpu = cpu
        if mem_gb > self.peak_ram_gb: self.peak_ram_gb = mem_gb
        return cpu, mem_gb

def print_progress(current, total, start_time, monitor):
    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / rate if rate > 0 else 0
    
    cpu, mem_gb = monitor.update()
    
    bar_len = 30
    filled = int(bar_len * current / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    
    sys.stdout.write(
        f"\r[{bar}] {current/total*100:5.1f}% | "
        f"Cnt: {current/1000:.0f}k | "
        f"Spd: {rate:.0f}/s | "
        f"CPU: {cpu:4.0f}% | "
        f"RAM: {mem_gb:4.1f}G | "
        f"ETA: {int(eta//60)}:{int(eta%60):02d}   "
    )
    sys.stdout.flush()

# ==========================================
# Worker (多進程生成任務)
# ==========================================
def worker_task(batch_size):
    """單一 Worker 的生成任務"""
    # 強制重置隨機種子
    random.seed(os.getpid() + time.time())
    
    app = create_app(config.Config)
    data = []
    
    with app.app_context():
        PlayerGenerator.initialize_class()
        try:
            for _ in range(batch_size):
                payload = PlayerGenerator.generate_payload()
                data.append(PlayerGenerator.to_flat_dict(payload))
        except Exception as e:
            print(f"[Worker Error PID {os.getpid()}]: {e}")
            return []
    return data

# ==========================================
# 流程控制
# ==========================================
def run_dry_run(conf):
    global pd
    import pandas as pd
    
    count = conf['execution']['dry_run_count']
    batch_size = conf['execution']['batch_size_per_task']
    workers = conf['execution']['max_workers']
    
    print(f"\n=== [步驟 1] 試跑 (Dry Run: {count:,} 筆) ===")
    print(f"Worker 數: {workers}")
    
    start_time = time.time()
    monitor = ResourceMonitor()
    
    tasks = [batch_size] * (count // batch_size)
    if count % batch_size != 0: tasks.append(count % batch_size)
    
    results = []
    ctx = multiprocessing.get_context('spawn')
    
    with ctx.Pool(processes=workers) as pool:
        for res in pool.imap_unordered(worker_task, tasks):
            results.extend(res)
            print_progress(len(results), count, start_time, monitor)
            
    duration = time.time() - start_time
    print(f"\n\n試跑完成！耗時: {duration:.2f} 秒 (速度: {count/duration:.0f} 筆/秒)")
    
    print("-" * 60)
    print("樣本數據預覽:")
    df = pd.DataFrame(results[:3])
    print(df[['name', 'grade', 'position', 'height', 'rating', 'salary']].to_string(index=False))
    print("-" * 60)
    
    return count / duration

def execute_production_run(target_count, speed, conf):
    global pd
    if pd is None: import pandas as pd
    
    print(f"\n=== [步驟 3] 正式執行 (Target: {target_count:,} 筆) ===")
    
    # 1. 建立時間戳記資料夾
    run_id = datetime.now().strftime('%Y%m%d_%H%M')
    base_data_dir = os.path.join(current_dir, conf['output']['data_dir'])
    current_run_dir = os.path.join(base_data_dir, run_id)
    
    os.makedirs(current_run_dir, exist_ok=True)
    
    batch_size = conf['execution']['batch_size_per_task']
    workers = conf['execution']['max_workers']
    
    tasks = [batch_size] * (target_count // batch_size)
    if target_count % batch_size != 0: tasks.append(target_count % batch_size)
    
    print(f"輸出目錄: {current_run_dir}")
    
    monitor = ResourceMonitor()
    monitor.start_time = datetime.now()
    start_time = time.time()
    
    processed = 0
    file_idx = 0
    
    ctx = multiprocessing.get_context('spawn')
    
    with ctx.Pool(processes=workers) as pool:
        for batch_data in pool.imap_unordered(worker_task, tasks):
            if not batch_data: continue
            
            df = pd.DataFrame(batch_data)
            fname = f"part_{file_idx:05d}.parquet"
            fpath = os.path.join(current_run_dir, fname)
            
            df.to_parquet(fpath, engine='pyarrow', compression=conf['output']['compression'])
            
            processed += len(batch_data)
            file_idx += 1
            print_progress(processed, target_count, start_time, monitor)
            
    monitor.end_time = datetime.now()
    monitor.total_rows = processed
    total_time = time.time() - start_time
    
    print(f"\n\n執行完成！總耗時: {total_time:.2f} 秒")
    
    # 儲存執行摘要 (Metadata) 供 Analyzer 使用
    meta_path = os.path.join(current_run_dir, "execution_meta.json")
    meta_data = {
        "run_id": run_id,
        "start_time": monitor.start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": monitor.end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": total_time,
        "total_rows": processed,
        "peak_cpu": monitor.peak_cpu,
        "peak_ram_gb": monitor.peak_ram_gb,
        "avg_speed": processed / total_time if total_time > 0 else 0
    }
    with open(meta_path, 'w') as f:
        json.dump(meta_data, f)
        
    return current_run_dir

def generate_report(data_dir, conf):
    print(f"\n=== [步驟 4] 數據分析與報告生成 ===")
    print(f"分析目標目錄: {data_dir}")
    
    # 取得 Run ID (從資料夾名稱)
    run_id = os.path.basename(os.path.normpath(data_dir))
    
    # 建立對應的報告目錄
    base_report_dir = os.path.join(current_dir, conf['output']['report_dir'])
    current_report_dir = os.path.join(base_report_dir, run_id)
    os.makedirs(current_report_dir, exist_ok=True)
    
    analyzer = BigDataAnalyzer(conf, data_dir)
    report_content = analyzer.run_analysis()
    
    report_file = os.path.join(current_report_dir, f"Validation_Report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"\n報告已生成: {report_file}")
    print("-" * 60)

if __name__ == "__main__":
    try:
        from scripts.terminal import clear_terminal
        clear_terminal()
    except ImportError:
        pass
    except Exception:
        pass
    multiprocessing.freeze_support()
    os.environ['PYTHON_JIT'] = '0'
    
    conf = load_config()
    
    print("\n==========================================")
    print("   ASBL Big Data Generator & Analyzer     ")
    print("==========================================")
    print("1. 完整流程 (試跑 -> 生成 -> 報告)")
    print("2. 僅生成報告 (Report Only - 分析最新結果)")
    print("q. 離開")
    
    mode = input("\n請選擇模式 [1/2]: ").strip().lower()
    
    if mode == 'q':
        sys.exit(0)
        
    elif mode == '2':
        base_data_dir = os.path.join(current_dir, conf['output']['data_dir'])
        latest_dir = get_latest_run_dir(base_data_dir)
        
        if not latest_dir:
            print(f"\n[Error] 在 {base_data_dir} 找不到任何測試數據資料夾。")
            sys.exit(1)
            
        print(f"\n[System] 偵測到最新測試數據: {latest_dir}")
        generate_report(latest_dir, conf)
        
    else:
        speed = run_dry_run(conf)
        while True:
            try:
                val = input("\n請輸入正式執行的總筆數 (例如 1000000) [輸入 q 離開]: ")
                if val.lower() == 'q': sys.exit(0)
                target_count = int(val)
                est_sec = target_count / speed
                print(f"預估耗時: {est_sec:.0f} 秒 ({est_sec/60:.1f} 分)")
                if input("確認執行? (y/n): ").lower() == 'y': break
            except ValueError: pass
        
        data_dir = execute_production_run(target_count, speed, conf)
        generate_report(data_dir, conf)