# app/models/league.py
from app import db
from datetime import datetime

class Season(db.Model):
    """
    賽季狀態表 (Singleton)
    """
    __tablename__ = 'seasons'
    
    id = db.Column(db.Integer, primary_key=True)
    season_number = db.Column(db.Integer, default=1, comment='第幾賽季')
    current_day = db.Column(db.Integer, default=0, comment='當前賽季天數 (0-91)')
    phase = db.Column(db.String(20), default='PRE_SEASON', comment='階段: PRE_SEASON, REGULAR, PLAYOFFS, OFF_SEASON')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Season {self.season_number} Day {self.current_day}>'

class League(db.Model):
    """
    [新增] 聯賽分組表 (T0, T1, T2...)
    """
    __tablename__ = 'leagues'
    __table_args__ = {'comment': '賽季聯賽分組'}

    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=False)
    
    # 層級: 0=T0 (頂級), 1=T1, 2=T2...
    tier = db.Column(db.Integer, nullable=False, comment='聯賽層級')
    name = db.Column(db.String(64), comment='聯賽名稱')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 關聯
    participants = db.relationship('LeagueParticipant', backref='league', lazy='dynamic')

    def __repr__(self):
        return f'<League S{self.season_id}-T{self.tier}>'

class LeagueParticipant(db.Model):
    """
    [新增] 聯賽參賽隊伍關聯表
    """
    __tablename__ = 'league_participants'
    __table_args__ = {'comment': '聯賽參賽名單'}

    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    
    start_reputation = db.Column(db.Integer, comment='季初分組時的聲望快照')
    final_rank = db.Column(db.Integer, nullable=True, comment='季末結算排名')

    def __repr__(self):
        return f'<Participant L{self.league_id}-T{self.team_id}>'

class Schedule(db.Model):
    """
    賽程表
    """
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False, comment='賽季第幾天')
    
    # 1: 正式聯賽, 2: 過渡聯賽(Provisional/Expansion), 3: 季後賽
    game_type = db.Column(db.Integer, default=1, comment='比賽類型')
    
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    
    # 狀態: PENDING(未開賽), PUBLISHED(已公布), FINISHED(已完賽), CANCELLED(已取消/季後賽提前結束)
    status = db.Column(db.String(20), default='PENDING')
    
    # 關聯到比賽結果
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=True)
    
    # [新增] 季後賽相關資訊 (用於系列賽追蹤)
    series_id = db.Column(db.String(32), nullable=True, comment='系列賽代碼 e.g. R1_A_vs_B')
    game_number = db.Column(db.Integer, nullable=True, comment='系列賽第幾戰')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Schedule S{self.season_id}-D{self.day} {self.status}>'
