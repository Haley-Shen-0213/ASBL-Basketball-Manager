# app/models/contract.py
from app import db

class Contract(db.Model):
    __tablename__ = 'contracts'
    __table_args__ = {'comment': '球員合約資料表'}

    id = db.Column(db.Integer, primary_key=True)
    
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, unique=True, comment='球員ID')
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, comment='球隊ID(冗餘)')
    
    salary = db.Column(db.Integer, nullable=False, comment='賽季薪資')
    years = db.Column(db.Integer, default=1, comment='總合約年限')
    years_left = db.Column(db.Integer, default=1, comment='剩餘年限')
    
    # 角色定位 (Star, Starter, Rotation, Role, Bench)
    role = db.Column(db.String(20), nullable=False, default='Bench', comment='角色定位')

    # 球隊/球員選項 (Team/Player Option)
    option_type = db.Column(db.String(10), nullable=True, comment='選項類型(PO/TO)') 

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<Contract Player:{self.player_id} ${self.salary} ({self.role})>'
