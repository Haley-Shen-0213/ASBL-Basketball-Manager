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

    # 註冊 Blueprints (之後會用到)
    # from app.routes import main
    # app.register_blueprint(main)

    return app