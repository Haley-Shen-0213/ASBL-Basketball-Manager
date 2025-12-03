# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# 初始化套件
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 綁定資料庫
    db.init_app(app)
    migrate.init_app(app, db)

    # 註冊 Blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app