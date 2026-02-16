# app/routes/__init__.py
from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from app.models.user import User
from app.utils.game_config_loader import GameConfigLoader # [新增]

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

@main.route('/api/system/stats', methods=['GET'])
def system_stats():
    """
    [新增] 取得系統統計數據
    回傳:
        total_users: 總註冊人數
        active_users: 過去 N 天內有登入的使用者 (N 由 config 定義)
    """
    try:
        # 從 Config 讀取活躍判定天數，預設 7 天
        active_days = GameConfigLoader.get('system.active_user_threshold_days', 7)
        
        # 計算 N 天前的時間點
        threshold_date = datetime.utcnow() - timedelta(days=active_days)
        
        # 查詢總人數
        total_count = User.query.count()
        
        # 查詢活躍人數 (last_login >= N天前)
        active_count = User.query.filter(User.last_login >= threshold_date).count()
        
        return jsonify({
            "total_users": total_count,
            "active_users": active_count,
            "active_threshold_days": active_days # 可選：回傳判定標準供前端參考
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "total_users": 0,
            "active_users": 0
        }), 500