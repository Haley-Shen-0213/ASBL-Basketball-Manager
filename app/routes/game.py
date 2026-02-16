# app/routes/game.py
from flask import Blueprint, jsonify, request
# [修正] Team 定義在 app.models.team
from app.models.team import Team 
from app.services.match_engine.core import MatchEngine
from app.services.match_engine.service import DBToEngineAdapter
from app.utils.game_config_loader import GameConfigLoader
import dataclasses

game_bp = Blueprint('game', __name__, url_prefix='/api/game')

@game_bp.route('/simulate', methods=['POST'])
def simulate_match():
    """
    執行單場比賽模擬
    Payload: { "home_team_id": 1, "away_team_id": 2 }
    """
    data = request.get_json()
    home_id = data.get('home_team_id')
    away_id = data.get('away_team_id')

    if not home_id or not away_id:
        return jsonify({'error': '需要提供主客隊 ID'}), 400

    # 1. 撈取資料
    home_db = Team.query.get_or_404(home_id)
    away_db = Team.query.get_or_404(away_id)

    # 2. 轉換模型
    home_engine = DBToEngineAdapter.convert_team(home_db)
    away_engine = DBToEngineAdapter.convert_team(away_db)

    # 3. 載入設定
    config = GameConfigLoader.load()

    # 4. 執行模擬
    import time
    game_id = f"SIM_{int(time.time())}"
    
    engine = MatchEngine(home_engine, away_engine, config, game_id=game_id)
    result = engine.simulate()

    # 5. 回傳結果
    response = {
        "game_id": result.game_id,
        "home_team": home_db.name,
        "away_team": away_db.name,
        "home_score": result.home_score,
        "away_score": result.away_score,
        "is_ot": result.is_ot,
        "pace": result.pace,
        "logs": result.pbp_log,
        "box_score": []
    }
    
    for p in home_engine.roster + away_engine.roster:
        if p.seconds_played > 0:
            response['box_score'].append({
                "id": p.id,
                "name": p.name,
                "team_id": home_id if p in home_engine.roster else away_id,
                "pts": p.stat_pts,
                "reb": p.stat_reb,
                "ast": p.stat_ast,
                "stl": p.stat_stl,
                "blk": p.stat_blk,
                "min": round(p.seconds_played / 60, 1)
            })

    return jsonify(response)
