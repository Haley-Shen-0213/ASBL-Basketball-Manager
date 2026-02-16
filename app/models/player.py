# app/models/player.py
from app import db
from sqlalchemy import JSON

class Player(db.Model):
    __tablename__ = 'players'
    __table_args__ = {'comment': '球員核心資料表'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    
    # 國籍/語系
    nationality = db.Column(db.String(16), nullable=False, default='zh', comment='球員國籍/語系')

    age = db.Column(db.Integer, default=18)
    height = db.Column(db.Integer, nullable=False, comment='身高(cm)')
    position = db.Column(db.String(10), nullable=False, comment='註冊位置')
    
    # 訓練點數
    training_points = db.Column(db.Integer, default=0, nullable=False, comment='可用訓練點數')

    # [新增] 在這裡加入 grade 欄位
    grade = db.Column(db.String(5), nullable=False, default='G', comment='球員等級 (SSR/SS/S...)')
    
    # 綜合評價 (Rating)
    rating = db.Column(db.Integer, comment='綜合評價分數')

    # [Schema 2.3] 數據欄位
    detailed_stats = db.Column(JSON, nullable=False, comment='當前能力值') 
    initial_stats = db.Column(JSON, nullable=True, comment='初始/巔峰能力值(老化參考)')

    # 關聯
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # 關聯設定
    contract = db.relationship('Contract', backref='player', uselist=False, cascade="all, delete-orphan")
    growth_logs = db.relationship('PlayerGrowthLog', backref='player', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Player {self.name} ({self.nationality})>'

class PlayerGrowthLog(db.Model):
    """
    [Schema 2.5] 球員成長/老化紀錄
    記錄每一季或每次訓練的數值變動。
    """
    __tablename__ = 'player_growth_logs'
    __table_args__ = {'comment': '球員成長與老化歷程'}

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    
    season_id = db.Column(db.Integer, nullable=False, comment='發生賽季')
    event_type = db.Column(db.String(20), nullable=False, comment='類型: AGE_DECLINE, TRAINING')
    
    # 記錄變動量，例如 {"speed": -2, "strength": -1}
    change_delta = db.Column(JSON, nullable=False, comment='數值變化量')
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<GrowthLog P:{self.player_id} {self.event_type}>'
