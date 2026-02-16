# app/routes/team.py
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app import db
from app.models.team import Team
from app.models.user import User
from app.models.player import Player
from app.services.match_engine.service import DBToEngineAdapter
from app.utils.game_config_loader import GameConfigLoader

team_bp = Blueprint('team', __name__, url_prefix='/api/team')

@team_bp.route('/<int:team_id>/dashboard', methods=['GET'])
def get_team_dashboard(team_id):
    """
    [新增] 取得 Dashboard 所需的完整資訊
    包含: 基本資訊、球員人數、戰績排名
    """
    team = Team.query.get_or_404(team_id)
    
    # 1. 讀取 Config
    roster_limit = GameConfigLoader.get('system.initial_team_settings.roster_limit', 40)
    
    # 2. 計算球員人數
    player_count = team.players.count()
    
    # 3. 計算排名 (簡易版：依勝場數 > 聲望 排序)
    # 實際專案應有 League Table，此處使用即時查詢模擬
    # 查詢有多少隊伍的 (wins, reputation) 比我高
    better_teams = Team.query.filter(
        (Team.season_wins > team.season_wins) | 
        ((Team.season_wins == team.season_wins) & (Team.reputation > team.reputation))
    ).count()
    rank = better_teams + 1
    total_teams = Team.query.count()
    
    return jsonify({
        'id': team.id,
        'name': team.name,
        'funds': team.funds,
        'reputation': team.reputation,
        'arena_name': team.arena_name,
        'fanpage_name': team.fanpage_name,
        'scout_chances': team.scout_chances,
        'player_count': player_count,
        'roster_limit': roster_limit,
        'season_wins': team.season_wins,
        'season_losses': team.season_losses,
        'rank': rank,
        'total_teams': total_teams,
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