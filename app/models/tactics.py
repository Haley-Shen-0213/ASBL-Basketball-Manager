# app/models/tactics.py
# 專案路徑: app/models/tactics.py
# 模組名稱: 戰術配置資料庫模型
# 描述: 定義 TeamTactics 表，用於儲存登錄名單與戰術參數。

from app import db
from sqlalchemy import JSON

class TeamTactics(db.Model):
    __tablename__ = 'team_tactics'
    __table_args__ = {'comment': '球隊戰術與登錄名單配置表'}

    id = db.Column(db.Integer, primary_key=True)
    
    # 與球隊的一對一關聯
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, unique=True, comment='球隊ID')
    
    # 登錄名單 (儲存 Player ID 的 List)
    # 範例: [1, 5, 8, 12, ...]
    roster_list = db.Column(JSON, nullable=False, default=list, comment='登錄名單ID列表')
    
    # (預留) 戰術細節設定
    strategy_settings = db.Column(JSON, nullable=True, comment='戰術參數設定')

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # 關聯屬性 (方便從 Team 存取)
    team = db.relationship('Team', backref=db.backref('tactics', uselist=False), lazy=True)

    def __repr__(self):
        return f'<TeamTactics Team:{self.team_id} Count:{len(self.roster_list) if self.roster_list else 0}>'