# scripts/import_names.py
import sys
import os
from sqlalchemy import create_engine, text

# 加入專案路徑以便匯入 app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.system import NameLibrary

# 設定舊資料庫的連線字串 (請確認密碼是否正確)
# 假設舊資料庫名稱為 'asbl_data'
OLD_DB_URL = "mysql+pymysql://root:123456@localhost/asbl_data"

def import_data():
    app = create_app()
    
    # 建立舊資料庫的連線引擎
    old_engine = create_engine(OLD_DB_URL)

    with app.app_context():
        print("🚀 開始匯入姓名資料...")
        
        try:
            # 1. 清空現有的姓名庫 (避免重複匯入)
            deleted = db.session.query(NameLibrary).delete()
            print(f"🧹 已清空現有資料: {deleted} 筆")
            
            conn = old_engine.connect()
            
            # 2. 匯入姓氏 (原本的 players_first_name -> category='last')
            # 注意：根據你的註解，first_name table 存的是 '姓氏'
            print("📥 正在讀取姓氏資料 (players_first_name)...")
            result_last = conn.execute(text("SELECT text FROM players_first_name"))
            
            count_last = 0
            for row in result_last:
                name_entry = NameLibrary(category='last', text=row[0])
                db.session.add(name_entry)
                count_last += 1
            
            print(f"✅ 已加入 {count_last} 個姓氏")

            # 3. 匯入名字 (原本的 players_last_name -> category='first')
            # 注意：根據你的註解，last_name table 存的是 '名字'
            print("📥 正在讀取名字資料 (players_last_name)...")
            result_first = conn.execute(text("SELECT text FROM players_last_name"))
            
            count_first = 0
            for row in result_first:
                name_entry = NameLibrary(category='first', text=row[0])
                db.session.add(name_entry)
                count_first += 1

            print(f"✅ 已加入 {count_first} 個名字")

            # 4. 提交變更
            db.session.commit()
            print(f"🎉 全部完成！總共匯入 {count_last + count_first} 筆資料。")

        except Exception as e:
            print(f"❌ 發生錯誤: {e}")
            db.session.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    # 請確認 .env 裡的密碼跟這裡 OLD_DB_URL 的密碼是一樣的，或者手動修改上面的 OLD_DB_URL
    import_data()