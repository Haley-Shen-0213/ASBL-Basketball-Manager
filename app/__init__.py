# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# 初始化 SQLAlchemy
db = SQLAlchemy()
# 初始化 Migrate
migrate = Migrate()

def create_app(config_class=Config):
    """
    建立 Flask 應用程式實例 (Factory Pattern)
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化擴充套件
    db.init_app(app)
    migrate.init_app(app, db)

    # 註冊 Blueprints (路由)
    # 1. 主路由 (通用入口)
    from app.routes import main
    app.register_blueprint(main)
    
    # 2. 功能模組路由
    from app.routes.auth import auth_bp
    from app.routes.team import team_bp
    from app.routes.game import game_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(game_bp)

    # 導入 Models 以便 SQLAlchemy (和 Migrate) 能追蹤到
    from app import models

    return app