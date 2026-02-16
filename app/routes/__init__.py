# app/routes/__init__.py
from flask import Blueprint, jsonify

# 定義 'main' Blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """API 健康檢查端點"""
    return jsonify({
        "status": "online",
        "message": "ASBL Basketball Manager API is running",
        "version": "v1.0"
    })