# app/models/team.py
from app import db

class Team(db.Model):
    __tablename__ = 'teams'
    __table_args__ = {'comment': '球隊資料表'}

    id = db.Column(db.Integer, primary_key=True, comment='球隊 ID (主鍵)')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, comment='所屬使用者 ID')
    name = db.Column(db.String(64), nullable=False, comment='球隊名稱')
    
    # 經營資訊
    funds = db.Column(db.BigInteger, default=300000, comment='球隊資金')
    reputation = db.Column(db.Integer, default=0, comment='球隊聲望')
    
    # [新增] 場館與粉絲團
    arena_name = db.Column(db.String(64), nullable=True, comment='場館名稱')
    fanpage_name = db.Column(db.String(64), nullable=True, comment='粉絲團名稱')
    
    # [新增] 球探
    scout_chances = db.Column(db.Integer, default=100, nullable=False, comment='剩餘球探次數')
    
    # [新增] 戰績快取 (用於 Dashboard 快速顯示)
    season_wins = db.Column(db.Integer, default=0, comment='本季勝場')
    season_losses = db.Column(db.Integer, default=0, comment='本季敗場')
    
    # 關聯
    players = db.relationship('Player', backref='team', lazy='dynamic')
    contracts = db.relationship('Contract', backref='team', lazy='dynamic')

    def __repr__(self):
        return f'<Team {self.name}>'