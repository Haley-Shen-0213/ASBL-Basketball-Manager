# app/models/player.py
from app import db
from sqlalchemy import JSON

class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    age = db.Column(db.Integer, default=18)
    
    # 身高與位置
    height = db.Column(db.Integer, nullable=False)
    position = db.Column(db.String(10), nullable=False)
    
    # 1. 已移除 weight 欄位
    # 2. 新增 training_points 欄位
    training_points = db.Column(db.Integer, default=0, nullable=False)

    # 綜合評價 (Rating)
    rating = db.Column(db.Integer)

    # 詳細數據 (使用通用 JSON 型態，支援 MySQL)
    detailed_stats = db.Column(JSON) 

    # 關聯
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # 建立與 Contract 的關聯
    contract = db.relationship('Contract', backref='player', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Player {self.name} ({self.position})>'

class Contract(db.Model):
    __tablename__ = 'contracts'

    id = db.Column(db.Integer, primary_key=True)
    
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, unique=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    
    salary = db.Column(db.Integer, nullable=False)
    years = db.Column(db.Integer, default=1)
    years_left = db.Column(db.Integer, default=1)
    
    # 新增角色定位 (Spec v2.4)
    # Values: Star, Starter, Rotation, Role, Bench
    role = db.Column(db.String(20), nullable=False, default='Bench')

    # 球隊/球員選項 (Team/Player Option)
    option_type = db.Column(db.String(10), nullable=True) 

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<Contract Player:{self.player_id} ${self.salary} ({self.role})>'