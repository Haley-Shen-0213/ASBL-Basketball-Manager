# app/routes/team.py
from flask import Blueprint, jsonify, request
# [修正] 分開匯入正確的模組位置
from app.models.team import Team
from app.models.user import User
from app.services.match_engine.service import DBToEngineAdapter

team_bp = Blueprint('team', __name__, url_prefix='/api/team')

@team_bp.route('/<int:team_id>', methods=['GET'])
def get_team_info(team_id):
    """取得特定球隊的基本資訊"""
    team = Team.query.get_or_404(team_id)
    return jsonify({
        'id': team.id,
        'name': team.name,
        'reputation': team.reputation,
        'funds': team.funds,
        'owner': team.owner.username
    })

@team_bp.route('/<int:team_id>/roster', methods=['GET'])
def get_team_roster(team_id):
    """取得球隊的完整球員名單 (包含詳細屬性)"""
    team = Team.query.get_or_404(team_id)
    
    engine_team = DBToEngineAdapter.convert_team(team)
    
    roster_data = []
    for p in engine_team.roster:
        player_dict = {
            'id': p.id,
            'name': p.name,
            'nationality': p.nationality,
            'position': p.position,
            'role': p.role,
            'grade': p.grade,
            'height': p.height,
            'age': p.age,
            'rating': p.attr_sum,
            'stats': {
                'physical': {
                    'stamina': p.ath_stamina,
                    'strength': p.ath_strength,
                    'speed': p.ath_speed,
                    'jump': p.ath_jump,
                    'health': p.talent_health
                },
                'offense': {
                    'touch': p.shot_touch,
                    'release': p.shot_release,
                    'accuracy': p.shot_accuracy,
                    'range': p.shot_range,
                    'pass': p.off_pass,
                    'dribble': p.off_dribble,
                    'handle': p.off_handle,
                    'move': p.off_move
                },
                'defense': {
                    'rebound': p.def_rebound,
                    'boxout': p.def_boxout,
                    'contest': p.def_contest,
                    'disrupt': p.def_disrupt
                },
                'mental': {
                    'off_iq': p.talent_offiq,
                    'def_iq': p.talent_defiq,
                    'luck': p.talent_luck
                }
            }
        }
        roster_data.append(player_dict)

    return jsonify(roster_data)

@team_bp.route('/my', methods=['POST'])
def get_my_team():
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
        
    user = User.query.get(user_id)
    if not user or not user.team:
        return jsonify({'error': 'Team not found'}), 404
        
    return jsonify({
        'team_id': user.team.id,
        'team_name': user.team.name
    })
