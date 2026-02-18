# app/models/match.py
# 專案路徑: app/models/match.py
# 模組名稱: 比賽數據資料庫模型 (Auto Increment ID 版)
# 描述: 定義 Match, MatchTeamStat, MatchPlayerStat 資料表。

from app import db
from sqlalchemy import JSON
from datetime import datetime

class Match(db.Model):
    """
    [比賽主表]
    記錄單場比賽的基礎資訊、比分與文字轉播紀錄。
    """
    __tablename__ = 'matches'
    __table_args__ = {'comment': '比賽主表'}

    # [修改] 改為 Integer Auto Increment
    id = db.Column(db.Integer, primary_key=True, comment='比賽ID (自動遞增)')
    
    # 關聯資訊
    season_id = db.Column(db.Integer, default=1, comment='賽季編號')
    date = db.Column(db.DateTime, default=datetime.utcnow, comment='比賽日期')
    
    # 對戰組合
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, comment='主隊ID')
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, comment='客隊ID')
    
    # 比賽結果
    home_score = db.Column(db.Integer, nullable=False, default=0, comment='主隊得分')
    away_score = db.Column(db.Integer, nullable=False, default=0, comment='客隊得分')
    is_ot = db.Column(db.Boolean, default=False, comment='是否延長賽')
    total_quarters = db.Column(db.Integer, default=4, comment='總節數')
    
    # 整體數據
    pace = db.Column(db.Float, default=0.0, comment='比賽節奏 (Pace)')
    
    # 文字轉播 (Play-by-Play)
    pbp_logs = db.Column(JSON, nullable=True, comment='文字轉播紀錄')

    # 關聯屬性
    home_team = db.relationship('Team', foreign_keys=[home_team_id], backref='home_matches')
    away_team = db.relationship('Team', foreign_keys=[away_team_id], backref='away_matches')
    
    # 數據關聯
    team_stats = db.relationship('MatchTeamStat', backref='match', cascade="all, delete-orphan")
    player_stats = db.relationship('MatchPlayerStat', backref='match', cascade="all, delete-orphan")

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Match {self.id} H:{self.home_score} vs A:{self.away_score}>'


class MatchTeamStat(db.Model):
    """
    [球隊比賽數據表]
    """
    __tablename__ = 'match_team_stats'
    __table_args__ = {'comment': '球隊單場比賽數據'}

    id = db.Column(db.Integer, primary_key=True)
    
    # [修改] 外鍵改為 Integer
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    
    is_home = db.Column(db.Boolean, nullable=False, comment='是否為主隊')
    
    # 進階數據
    possessions = db.Column(db.Integer, default=0, comment='總回合數')
    avg_seconds_per_poss = db.Column(db.Float, default=0.0, comment='平均每回合秒數')
    
    # 快攻
    fb_made = db.Column(db.Integer, default=0, comment='快攻進球')
    fb_attempt = db.Column(db.Integer, default=0, comment='快攻嘗試')
    
    # 違例
    violation_8s = db.Column(db.Integer, default=0, comment='8秒違例次數')
    violation_24s = db.Column(db.Integer, default=0, comment='24秒違例次數')
    
    # 詳細歷史
    possession_history = db.Column(JSON, nullable=True, comment='每回合時間歷程')

    def __repr__(self):
        return f'<MatchTeamStat M:{self.match_id} T:{self.team_id}>'


class MatchPlayerStat(db.Model):
    """
    [球員比賽數據表] (Box Score)
    """
    __tablename__ = 'match_player_stats'
    __table_args__ = (
        db.Index('idx_match_player', 'match_id', 'player_id'),
        {'comment': '球員單場比賽數據 (Box Score)'}
    )

    id = db.Column(db.Integer, primary_key=True)
    
    # [修改] 外鍵改為 Integer
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    
    # 狀態快照
    grade = db.Column(db.String(5), comment='當時等級')
    position = db.Column(db.String(10), comment='當時位置')
    role = db.Column(db.String(20), comment='當時角色')
    
    # 上場時間
    seconds_played = db.Column(db.Float, default=0.0, comment='上場秒數')
    is_starter = db.Column(db.Boolean, default=False, comment='是否先發')
    is_played = db.Column(db.Boolean, default=False, comment='是否出賽')
    
    # 基礎數據
    pts = db.Column(db.Integer, default=0, comment='得分')
    reb = db.Column(db.Integer, default=0, comment='籃板')
    ast = db.Column(db.Integer, default=0, comment='助攻')
    stl = db.Column(db.Integer, default=0, comment='抄截')
    blk = db.Column(db.Integer, default=0, comment='阻攻')
    tov = db.Column(db.Integer, default=0, comment='失誤')
    fouls = db.Column(db.Integer, default=0, comment='犯規')
    plus_minus = db.Column(db.Integer, default=0, comment='正負值 (+/-)')
    
    # 投籃細項
    fgm = db.Column(db.Integer, default=0, comment='投籃命中')
    fga = db.Column(db.Integer, default=0, comment='投籃出手')
    m3pm = db.Column(db.Integer, default=0, comment='三分命中')
    m3pa = db.Column(db.Integer, default=0, comment='三分出手')
    ftm = db.Column(db.Integer, default=0, comment='罰球命中')
    fta = db.Column(db.Integer, default=0, comment='罰球出手')
    
    # 進階細項
    orb = db.Column(db.Integer, default=0, comment='進攻籃板')
    drb = db.Column(db.Integer, default=0, comment='防守籃板')
    fb_made = db.Column(db.Integer, default=0, comment='快攻進球')
    fb_attempt = db.Column(db.Integer, default=0, comment='快攻嘗試')
    
    # 體力監控
    remaining_stamina = db.Column(db.Float, default=0.0, comment='賽後剩餘體力')
    is_fouled_out = db.Column(db.Boolean, default=False, comment='是否犯滿離場')

    # 關聯
    player = db.relationship('Player', backref='match_stats')

    def __repr__(self):
        return f'<BoxScore M:{self.match_id} P:{self.player_id} PTS:{self.pts}>'