# app/models/system.py
from app import db
from sqlalchemy import Computed

class NameLibrary(db.Model):
    __tablename__ = 'system_name_library'
    __table_args__ = (
        db.UniqueConstraint('language', 'content', name='uq_lang_content'),
        db.Index('idx_lang_cat_weight', 'language', 'category', 'weight'),
        {'comment': '[系統] 多國語系姓名詞庫'}
    )

    id = db.Column(db.Integer, primary_key=True, comment='唯一識別碼')
    
    # 語系代碼 (en, zh, ja, tw_aboriginal...)
    language = db.Column(db.String(16), nullable=False, comment='語系代碼')
    
    # 類別 (surname, given_name, template) - 雖然策略A不分，但資料庫結構仍需保留
    category = db.Column(db.String(16), nullable=False, comment='類別')
    
    # 內容 (中文音譯或原文)
    content = db.Column(db.String(64), nullable=False, comment='內容')
    
    # 內容字數 (對應 SQL 的 GENERATED ALWAYS AS)
    # SQLAlchemy 可用 Computed 映射，或單純視為由 DB 管理的欄位
    length = db.Column(db.Integer, Computed('char_length(content)'), comment='內容字數')
    
    # 權重
    weight = db.Column(db.Integer, nullable=False, default=10, comment='出現權重')

    def __repr__(self):
        return f'<NameLib {self.language}.{self.category}: {self.content}>'
