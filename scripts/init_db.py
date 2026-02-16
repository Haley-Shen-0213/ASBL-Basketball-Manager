# scripts/init_db.py
import sys
import os

# 將專案根目錄加入 Python 路徑，這樣才能 import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Team, Player, Contract

app = create_app()

def init_database():
    with app.app_context():
        # 1. 刪除舊表 (開發初期用，正式上線後要小心！)

        # 2. 建立新表
        db.create_all()
        print("✅ 資料表建立成功！")
        
        # 3. 檢查是否成功
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📊 目前資料庫中的資料表: {tables}")

if __name__ == '__main__':
    print("🚀 開始初始化資料庫...")
    init_database()