# app/routes/__init__.py
# 專案路徑: app/routes/__init__.py
# 模組名稱: 主路由與系統 API
# 描述: 提供系統層級的 API，包含健康檢查、統計數據與系統設定。

from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from app.models.user import User
from app.utils.game_config_loader import GameConfigLoader

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
    取得系統統計數據 (活躍人數等)
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
            "active_threshold_days": active_days
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "total_users": 0,
            "active_users": 0
        }), 500

@main.route('/api/system/config/tactics', methods=['GET'])
def get_tactics_config():
    """
    [新增] 取得戰術系統相關設定
    用途: 供前端動態載入規則，確保前後端邏輯一致 (Single Source of Truth)。
    """
    try:
        # 直接從 YAML 讀取 tactics_system 區塊
        tactics_config = GameConfigLoader.get('tactics_system')
        
        if not tactics_config:
            return jsonify({'error': 'Tactics config not found'}), 500
            
        return jsonify(tactics_config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500