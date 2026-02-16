# app/models/team.py
from app import db

class Team(db.Model):
    __tablename__ = 'teams'
    __table_args__ = {'comment': '球隊資料表'}

    id = db.Column(db.Integer, primary_key=True, comment='球隊 ID (主鍵)')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, comment='所屬使用者 ID')
    name = db.Column(db.String(64), nullable=False, comment='球隊名稱')
    
    # 經濟與聲望
    funds = db.Column(db.BigInteger, default=10000000, comment='球隊資金 (預設一千萬)')
    reputation = db.Column(db.Integer, default=100, comment='球隊聲望')
    
    # 關聯：使用字串 'Player' 和 'Contract'
    players = db.relationship('Player', backref='team', lazy='dynamic')
    contracts = db.relationship('Contract', backref='team', lazy='dynamic')

    def __repr__(self):
        return f'<Team {self.name}>'
