# app/models/system.py
from app import db

class NameLibrary(db.Model):
    __tablename__ = 'name_library'
    __table_args__ = {'comment': '球員姓名生成字庫'}

    id = db.Column(db.Integer, primary_key=True)
    # 類型: 'last' (姓氏) 或 'first' (名字)
    category = db.Column(db.String(10), index=True, nullable=False, comment='類型(last=姓/first=名)')
    # 文字: 例如 '陳', '林', '志傑', '信安'
    text = db.Column(db.String(64), nullable=False, comment='文字內容')
    # 權重: 預設為 1
    weight = db.Column(db.Integer, default=1, comment='出現權重')

    def __repr__(self):
        return f'<Name ({self.category}): {self.text}>'