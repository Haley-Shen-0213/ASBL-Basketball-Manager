# app/routes/team.py
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app import db
from app.models.team import Team
from app.models.user import User
from app.models.player import Player
from app.models.tactics import TeamTactics
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
    """
    取得球隊完整名單
    [方案 B 實作]
    1. 讀取 TeamTactics 取得 active_ids 列表
    2. 遍歷球員，動態標記 is_active 狀態
    """
    team = Team.query.get_or_404(team_id)
    
    # 1. 嘗試取得戰術設定
    tactics = TeamTactics.query.filter_by(team_id=team_id).first()
    
    # 將 JSON list 轉為 Set 以加速比對 (O(1) lookup)
    # 若無設定則為空集合
    active_ids_set = set(tactics.roster_list) if tactics and tactics.roster_list else set()
    
    roster_data = []
    for p in team.players:
        role = p.contract.role if p.contract else 'Bench'
        stats = p.detailed_stats or {}
        
        # 2. 動態判斷是否登錄
        is_active = p.id in active_ids_set
        
        player_dict = {
            'id': p.id,
            'name': p.name,
            'nationality': p.nationality,
            'position': p.position,
            'role': role,
            'grade': p.grade,
            'height': p.height,
            'age': p.age,
            'rating': p.rating,
            'is_active': is_active, # 這裡回傳動態計算的結果
            'stats': stats
        }
        roster_data.append(player_dict)

    return jsonify(roster_data)

@team_bp.route('/<int:team_id>/roster/active', methods=['POST'])
def update_active_roster(team_id):
    """
    [方案 B 實作] 更新球隊登錄名單
    Payload: { "player_ids": [1, 2, 3, ...] }
    邏輯: 更新或建立 TeamTactics 紀錄
    """
    team = Team.query.get_or_404(team_id)
    data = request.get_json()
    
    if not data or 'player_ids' not in data:
        return jsonify({'error': 'Missing player_ids list'}), 400
        
    # 確保 ID 列表為整數 (前端可能傳字串)
    try:
        new_active_ids = [int(pid) for pid in data['player_ids']]
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    
    # 讀取設定檔進行驗證 (人數上限)
    config = GameConfigLoader.get('tactics_system')
    limit = config.get('roster_size', 15)
    
    if len(new_active_ids) > limit:
        return jsonify({'error': f'Roster size exceeds limit of {limit}'}), 400

    try:
        # 1. 查詢是否已有戰術紀錄
        tactics = TeamTactics.query.filter_by(team_id=team_id).first()
        
        if tactics:
            # 2a. 更新現有紀錄
            tactics.roster_list = new_active_ids
        else:
            # 2b. 建立新紀錄
            tactics = TeamTactics(
                team_id=team_id,
                roster_list=new_active_ids
            )
            db.session.add(tactics)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Roster updated successfully',
            'active_count': len(new_active_ids)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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

@team_bp.route('/list', methods=['GET'])
def get_all_teams():
    """
    取得所有球隊列表，包含排名、總評分等資訊
    """
    teams = Team.query.all()
    result = []
    
    for t in teams:
        # 計算球隊總評分 (加總所有球員的 rating)
        # 注意：這裡簡單加總，若有效能問題可改為 SQL Sum
        total_rating = db.session.query(func.sum(Player.rating)).filter_by(team_id=t.id).scalar() or 0
        
        result.append({
            'id': t.id,
            'name': t.name,
            'reputation': t.reputation,
            'season_wins': t.season_wins,
            'season_losses': t.season_losses,
            'total_rating': int(total_rating),
            'player_count': t.players.count()
        })
    
    # 排序邏輯： 聲望 > 勝場 > 總評分
    result.sort(key=lambda x: (x['reputation'], x['season_wins'], x['total_rating']), reverse=True)
    
    # 補上排名
    for idx, data in enumerate(result):
        data['rank'] = idx + 1
        
    return jsonify(result)