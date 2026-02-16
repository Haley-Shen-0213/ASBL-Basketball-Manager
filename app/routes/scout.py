# app/routes/scout.py (球探 API)
from datetime import datetime
from flask import Blueprint, jsonify, request
from app import db
from app.models.team import Team
from app.models.scout import ScoutingRecord
from app.services.scout_service import ScoutService
from app.utils.game_config_loader import GameConfigLoader

scout_bp = Blueprint('scout', __name__, url_prefix='/api/scout')

@scout_bp.route('/settings', methods=['GET'])
def get_settings():
    user_id = request.args.get('user_id') # 假設前端會傳 user_id
    if not user_id: return jsonify({'error': 'Missing user_id'}), 400
    
    team = Team.query.filter_by(user_id=user_id).first_or_404()
    config = GameConfigLoader.get('scout_system')
    
    return jsonify({
        'daily_level': team.daily_scout_level,
        'scout_chances': team.scout_chances,
        'cost_per_level': config.get('cost_per_level', 1000),
        'max_level': config.get('max_level', 10)
    })

@scout_bp.route('/settings', methods=['POST'])
def update_settings():
    data = request.get_json()
    user_id = data.get('user_id')
    level = data.get('level')
    
    team = Team.query.filter_by(user_id=user_id).first_or_404()
    config = GameConfigLoader.get('scout_system')
    max_lvl = config.get('max_level', 10)
    
    if not isinstance(level, int) or level < 0 or level > max_lvl:
        return jsonify({'error': f'Level must be between 0 and {max_lvl}'}), 400
        
    team.daily_scout_level = level
    db.session.commit()
    
    return jsonify({'message': 'Settings updated', 'daily_level': level})

@scout_bp.route('/use', methods=['POST'])
def use_chance():
    """
    使用球探次數 (支援單次或多次)
    Payload: { "user_id": 1, "count": 10 }
    """
    data = request.get_json()
    user_id = data.get('user_id')
    count = data.get('count', 1) # 預設為 1 次
    
    if count < 1:
        return jsonify({'error': '次數必須大於 0'}), 400

    team = Team.query.filter_by(user_id=user_id).first_or_404()
    
    if team.scout_chances < count:
        return jsonify({'error': f'剩餘次數不足 (剩餘 {team.scout_chances} 次)'}), 400
        
    generated_players = []
    try:
        # 執行多次生成
        for _ in range(count):
            # 1. 扣除次數
            team.scout_chances -= 1
            
            # 2. 生成球員並寫入 ScoutingRecord (Service 內部會 add session)
            player = ScoutService.generate_scouted_player(team.id, source="MANUAL")
            generated_players.append(player.name)
            
            # 3. 每次生成都提交，確保數據一致性 (避免生成了球員卻沒扣次數，或反之)
            # 雖然效能稍差，但對於幾十次的操作來說安全性更重要
            db.session.commit()
        
        # 構建回傳訊息
        if count == 1:
            msg = f"發現新球員：{generated_players[0]}"
        else:
            msg = f"成功使用 {count} 次機會，發現 {len(generated_players)} 名新球員！"

        return jsonify({
            'message': msg,
            'new_players': generated_players,
            'remaining_chances': team.scout_chances
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@scout_bp.route('/pending', methods=['GET'])
def get_pending_players():
    user_id = request.args.get('user_id')
    team = Team.query.filter_by(user_id=user_id).first_or_404()
    
    records = ScoutingRecord.query.filter_by(team_id=team.id).all()
    result = []
    
    for r in records:
        p = r.player
        # 計算剩餘時間
        remaining = r.expire_at - datetime.utcnow()
        hours_left = int(remaining.total_seconds() / 3600)
        
        result.append({
            'player_id': p.id,
            'name': p.name,
            'grade': p.grade,
            'position': p.position,
            'height': p.height,
            'age': p.age,
            'rating': p.rating,
            'nationality': p.nationality,
            'expire_in_hours': max(0, hours_left),
            'stats': p.detailed_stats # 簡單顯示用
        })
        
    return jsonify(result)

@scout_bp.route('/sign', methods=['POST'])
def sign_player():
    data = request.get_json()
    user_id = data.get('user_id')
    player_id = data.get('player_id')
    
    team = Team.query.filter_by(user_id=user_id).first_or_404()
    
    try:
        player = ScoutService.sign_player(team.id, player_id)
        return jsonify({'message': f'成功簽下 {player.name}'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 測試用：手動觸發每日結算
@scout_bp.route('/debug/daily_tick', methods=['POST'])
def debug_daily_tick():
    logs = ScoutService.process_daily_scout_event()
    return jsonify({'logs': logs})
