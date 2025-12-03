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
    
    # 關聯
    team = db.relationship('Team', backref='owner', uselist=False)

    def set_password(self, password):
        """將明文密碼加密後存入"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """驗證密碼是否正確"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Team(db.Model):
    __tablename__ = 'teams'
    __table_args__ = {'comment': '球隊資料表'}

    id = db.Column(db.Integer, primary_key=True, comment='球隊 ID (主鍵)')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, comment='所屬使用者 ID')
    name = db.Column(db.String(64), nullable=False, comment='球隊名稱')
    
    # 經濟與聲望
    funds = db.Column(db.BigInteger, default=10000000, comment='球隊資金 (預設一千萬)')
    reputation = db.Column(db.Integer, default=100, comment='球隊聲望')
    
    # 關聯
    players = db.relationship('Player', backref='team', lazy='dynamic')

    def __repr__(self):
        return f'<Team {self.name}>'