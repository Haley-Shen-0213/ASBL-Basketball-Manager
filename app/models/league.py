# app/models/league.py
from app import db
from datetime import datetime

class Season(db.Model):
    """
    賽季狀態表 (Singleton，通常只有一筆 active 的資料)
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

class Schedule(db.Model):
    """
    賽程表
    """
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False, comment='賽季第幾天')
    
    # 1: 正式聯賽, 2: 擴充聯賽, 3: 季後賽
    game_type = db.Column(db.Integer, default=1, comment='比賽類型')
    
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    
    # 狀態: PENDING(未開賽), PUBLISHED(已公布/可備戰), FINISHED(已完賽)
    status = db.Column(db.String(20), default='PENDING')
    
    # 關聯到比賽結果 (Match 表)，完賽後填入
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Schedule S{self.season_id}-D{self.day} T{self.home_team_id}vsT{self.away_team_id}>'
