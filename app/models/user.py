# app/models/user.py
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'comment': '使用者帳號資料表'}

    id = db.Column(db.Integer, primary_key=True, comment='使用者 ID (主鍵)')
    username = db.Column(db.String(64), index=True, unique=True, nullable=False, comment='使用者名稱')
    email = db.Column(db.String(120), index=True, unique=True, nullable=False, comment='電子信箱')
    password_hash = db.Column(db.String(256), comment='密碼雜湊值')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='帳號建立時間')
    
    # [新增] 記錄最後登入時間，用於計算活躍人數
    last_login = db.Column(db.DateTime, default=datetime.utcnow, comment='最後登入時間')
    
    # --- [新增] 機器人標記 ---
    is_bot = db.Column(db.Boolean, default=False, comment='是否為電腦球隊管理者')
    # -----------------------
    
    # 關聯：使用字串 'Team' 避免循環引用
    team = db.relationship('Team', backref='owner', uselist=False)

    def set_password(self, password):
        """將明文密碼加密後存入"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """驗證密碼是否正確"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
