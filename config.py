# config.py
import os
from dotenv import load_dotenv

# 取得目前檔案的目錄
basedir = os.path.abspath(os.path.dirname(__file__))

# 載入 .env 檔案
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # 1. 安全密鑰
    # 現在會優先從 .env 讀取，讀不到才會用後面的預設值
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback-key'

    # 2. 資料庫連線設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db') # 預設改為 SQLite 避免報錯

    # 3. 效能設定
    SQLALCHEMY_TRACK_MODIFICATIONS = False