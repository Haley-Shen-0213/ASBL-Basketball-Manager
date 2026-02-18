# app/scheduler.py
import os
import atexit
import logging
import socket
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 設置 logger
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

# 全域變數，用於持有 Socket 鎖，防止被垃圾回收關閉
_scheduler_lock_socket = None

def init_scheduler(app):
    """
    初始化排程器
    使用 Socket Bind 機制確保在多進程環境 (如 Flask Debug Mode) 下，
    只有一個進程能啟動排程器 (Singleton)。
    """
    global _scheduler_lock_socket

    # 定義一個專用的 Port 用於鎖定
    # 選擇一個不常用的高位 Port
    LOCK_PORT = 49500 

    try:
        # 1. 嘗試建立並綁定 Socket
        _scheduler_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # 綁定到 localhost 的指定 Port
        # 如果這個 Port 已經被綁定 (代表另一個進程已經啟動了排程器)，這裡會拋出異常
        _scheduler_lock_socket.bind(('127.0.0.1', LOCK_PORT))
        
    except socket.error:
        # 2. 綁定失敗，代表排程器已經在另一個進程運行中
        # 靜默跳過，不啟動排程器
        # print(f"🔒 [Scheduler] Process {os.getpid()} skipped (Lock exists).")
        return

    # 3. 綁定成功，我是唯一的執行者 (The Chosen One)
    # 繼續執行排程器啟動邏輯
    
    # [設定] 設定預設的執行器與任務參數
    # misfire_grace_time: 允許任務延遲執行的寬限時間 (秒)
    # coalesce: 如果錯過多次執行，是否合併為一次 (True=合併, False=全部補跑)
    job_defaults = {
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 3600  # [修正關鍵] 設定全域寬限期為 1 小時
    }

    scheduler = BackgroundScheduler(job_defaults=job_defaults)
    
    # 定義需要 App Context 的包裝函式
    def run_job_with_app_context(func):
        with app.app_context():
            try:
                func()
            except Exception as e:
                print(f"❌ [Scheduler Error] {e}")

    # 延遲 import 避免循環引用
    from app.services.league_service import LeagueService

    # --- Job 1: 每日 00:00 換日與配對 ---
    scheduler.add_job(
        func=lambda: run_job_with_app_context(LeagueService.process_day_change_0000),
        trigger=CronTrigger(hour=0, minute=0),
        id='daily_change',
        name='Daily Day Change & Matchmaking',
        replace_existing=True,
        misfire_grace_time=3600 # [雙重保險] 針對個別任務設定寬限期
    )

    # --- Job 2: 每日 19:00 比賽執行 ---
    scheduler.add_job(
        func=lambda: run_job_with_app_context(LeagueService.process_match_execution_1900),
        trigger=CronTrigger(hour=20, minute=5),
        id='daily_match',
        name='Daily Match Execution',
        replace_existing=True,
        misfire_grace_time=3600 # [雙重保險] 針對個別任務設定寬限期
    )

    scheduler.start()
    print(f"⏰ [Scheduler] League Scheduler Started (PID: {os.getpid()}) on Port {LOCK_PORT}")

    # 註冊關閉事件
    atexit.register(lambda: scheduler.shutdown())