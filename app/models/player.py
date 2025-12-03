# app/models/player.py
from app import db
from datetime import datetime

class Player(db.Model):
    __tablename__ = 'players'
    __table_args__ = {'comment': '球員基本資料表'}

    id = db.Column(db.Integer, primary_key=True, comment='球員 ID (主鍵)')
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True, comment='所屬球隊 ID (NULL為自由球員)')
    
    # 基本資料
    name = db.Column(db.String(64), nullable=False, comment='球員姓名')
    age = db.Column(db.Integer, default=18, comment='年齡')
    position = db.Column(db.String(10), comment='守備位置 (PG/SG/SF/PF/C)')
    rarity = db.Column(db.String(5), comment='稀有度 (SSR/SS/S/A/B/C/G)')
    
    # 五大屬性
    attr_athleticism = db.Column(db.Integer, default=0, comment='屬性: 運動能力')
    attr_shooting = db.Column(db.Integer, default=0, comment='屬性: 投籃技巧')
    attr_defense = db.Column(db.Integer, default=0, comment='屬性: 防守能力')
    attr_offense = db.Column(db.Integer, default=0, comment='屬性: 進攻意識')
    attr_talent = db.Column(db.Integer, default=0, comment='屬性: 天賦潛力 (固定值)')
    
    # 詳細屬性
    detailed_stats = db.Column(db.JSON, nullable=True, comment='詳細數據 (JSON格式: 包含細項數值)')

    # 成長數據
    training_points = db.Column(db.Integer, default=0, comment='現有訓練點數')
    minutes_played_total = db.Column(db.Integer, default=0, comment='生涯總上場時間 (分鐘)')

    # 關聯
    contract = db.relationship('Contract', backref='player', uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Player {self.name} ({self.rarity})>'

class Contract(db.Model):
    __tablename__ = 'contracts'
    __table_args__ = {'comment': '球員合約資料表'}

    id = db.Column(db.Integer, primary_key=True, comment='合約 ID')
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), unique=True, nullable=False, comment='球員 ID')
    
    salary = db.Column(db.Integer, nullable=False, comment='薪資金額')
    years_left = db.Column(db.Integer, default=1, comment='剩餘合約年限')
    
    # 角色定位
    role = db.Column(db.String(20), nullable=False, comment='球隊定位 (Star/Starter/Rotation...)')
    
    # 簽約類型
    contract_type = db.Column(db.String(20), default='Regular', comment='合約類型 (Rookie/Max/Min...)')

    def __repr__(self):
        return f'<Contract {self.role} ${self.salary}>'