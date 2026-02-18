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
    
    # 場館與粉絲團
    arena_name = db.Column(db.String(64), nullable=True, comment='場館名稱')
    fanpage_name = db.Column(db.String(64), nullable=True, comment='粉絲團名稱')
    
    # 球探
    scout_chances = db.Column(db.Integer, default=100, nullable=False, comment='剩餘球探次數')
    daily_scout_level = db.Column(db.Integer, default=0, nullable=False, comment='每日球探投入等級(0-10)')
    
    # --- [新增] 聯賽系統欄位 ---
    status = db.Column(db.String(20), default='BOT', comment='狀態: BOT, PLAYER, PROVISIONAL')
    is_official = db.Column(db.Boolean, default=True, comment='True: 正式聯賽, False: 擴充聯賽')
    
    # 戰績快取
    season_wins = db.Column(db.Integer, default=0, comment='本季勝場')
    season_losses = db.Column(db.Integer, default=0, comment='本季敗場')
    home_games_played = db.Column(db.Integer, default=0, comment='已進行主場數')
    away_games_played = db.Column(db.Integer, default=0, comment='已進行客場數')
    
    # 關聯
    players = db.relationship('Player', backref='team', lazy='dynamic')
    contracts = db.relationship('Contract', backref='team', lazy='dynamic')
    # 待簽球員關聯
    scouting_records = db.relationship('ScoutingRecord', backref='team', lazy='dynamic', cascade="all, delete-orphan")

    def update_season_stats(self):
        """
        [同步校正] 重新計算並更新賽季數據
        說明: 查詢 Matches 資料表，重新統計勝敗與出賽數，確保資料一致性。
        時機: 比賽結束後、球隊替換後呼叫。
        """
        from app.models.match import Match
        
        # 1. 計算出賽數
        self.home_games_played = Match.query.filter_by(home_team_id=self.id).count()
        self.away_games_played = Match.query.filter_by(away_team_id=self.id).count()
        
        # 2. 計算勝敗場 (Home Win + Away Win)
        # 主場勝: 我是主隊 且 主分 > 客分
        home_wins = Match.query.filter(
            Match.home_team_id == self.id, 
            Match.home_score > Match.away_score
        ).count()
        
        # 客場勝: 我是客隊 且 客分 > 主分
        away_wins = Match.query.filter(
            Match.away_team_id == self.id, 
            Match.away_score > Match.home_score
        ).count()
        
        self.season_wins = home_wins + away_wins
        
        # 3. 計算敗場 (總場次 - 勝場)
        total_games = self.home_games_played + self.away_games_played
        self.season_losses = total_games - self.season_wins
        
        # 注意: 這裡不執行 commit，由呼叫端統一提交，避免頻繁 IO

    def __repr__(self):
        return f'<Team {self.name}>'