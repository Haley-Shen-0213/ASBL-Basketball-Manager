# app/models/scout.py (新增球探紀錄模型)
from app import db
from datetime import datetime, timedelta

class ScoutingRecord(db.Model):
    __tablename__ = 'scouting_records'
    __table_args__ = {'comment': '球探待簽名單紀錄'}

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, comment='球隊ID')
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, unique=True, comment='球員ID')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='發現時間')
    expire_at = db.Column(db.DateTime, nullable=False, comment='過期時間')
    
    # 關聯 (方便直接存取球員資料)
    player = db.relationship('Player', backref=db.backref('scout_record', uselist=False), lazy=True)

    def __repr__(self):
        return f'<ScoutRecord Team:{self.team_id} Player:{self.player_id}>'
