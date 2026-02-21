# app/routes/league.py
from flask import Blueprint, jsonify, request
from sqlalchemy import or_, and_
from app.models.league import Season, Schedule
from app.models.team import Team
from app.models.match import Match, MatchPlayerStat
from app import db

league_bp = Blueprint('league', __name__, url_prefix='/api/league')

@league_bp.route('/season/info', methods=['GET'])
def get_season_info():
    """取得當前活躍賽季資訊"""
    season = Season.query.filter_by(is_active=True).first()
    if not season:
        return jsonify({
            'id': None,
            'season_number': 0,
            'current_day': 0,
            'phase': 'OFF_SEASON'
        })
    return jsonify({
        'id': season.id,
        'season_number': season.season_number,
        'current_day': season.current_day,
        'phase': season.phase
    })

@league_bp.route('/schedule', methods=['GET'])
def get_schedule():
    season_id = request.args.get('season_id')
    day = request.args.get('day')
    
    if not season_id or not day:
        return jsonify({'error': 'Missing params'}), 400
    
    target_day = int(day)
    schedules = Schedule.query.filter_by(season_id=season_id, day=target_day).all()
    
    result = []
    
    # 為了優化效能，這裡可以預先撈取 Team 資料，但為了邏輯清晰先保持逐筆處理
    # 若有效能問題，應改為 Batch Query

    for s in schedules:
        home = Team.query.get(s.home_team_id)
        away = Team.query.get(s.away_team_id)
        match = Match.query.get(s.match_id) if s.match_id else None
        
        # [修正 5] 計算「該日之前」的歷史戰績 (Historical Record)
        # 僅針對正式聯賽 (game_type=1) 計算例行賽戰績
        home_wins = 0
        home_losses = 0
        away_wins = 0
        away_losses = 0
        
        if s.game_type == 1:
            # 計算主隊在 target_day 之前的戰績
            # 邏輯: 找出所有該隊參與且已完賽，並且 day < target_day 的比賽
            home_stats = db.session.query(Schedule, Match)\
                .join(Match, Schedule.match_id == Match.id)\
                .filter(
                    Schedule.season_id == season_id,
                    Schedule.day < target_day,
                    Schedule.game_type == 1,
                    Schedule.status == 'FINISHED',
                    or_(Schedule.home_team_id == home.id, Schedule.away_team_id == home.id)
                ).all()
            
            for sched, m in home_stats:
                winner_id = m.home_team_id if m.home_score > m.away_score else m.away_team_id
                if winner_id == home.id:
                    home_wins += 1
                else:
                    home_losses += 1

            # 計算客隊在 target_day 之前的戰績
            away_stats = db.session.query(Schedule, Match)\
                .join(Match, Schedule.match_id == Match.id)\
                .filter(
                    Schedule.season_id == season_id,
                    Schedule.day < target_day,
                    Schedule.game_type == 1,
                    Schedule.status == 'FINISHED',
                    or_(Schedule.home_team_id == away.id, Schedule.away_team_id == away.id)
                ).all()
                
            for sched, m in away_stats:
                winner_id = m.home_team_id if m.home_score > m.away_score else m.away_team_id
                if winner_id == away.id:
                    away_wins += 1
                else:
                    away_losses += 1
        
        item = {
            'id': s.id,
            'day': s.day,
            'game_type': s.game_type,
            'status': s.status,
            'match_id': s.match_id,
            'home_team': {
                'id': home.id, 
                'name': home.name,
                'wins': home_wins,     # 使用歷史戰績
                'losses': home_losses
            },
            'away_team': {
                'id': away.id, 
                'name': away.name,
                'wins': away_wins,     # 使用歷史戰績
                'losses': away_losses
            },
            'match': {
                'home_score': match.home_score,
                'away_score': match.away_score,
                'is_ot': match.is_ot
            } if match else None
        }

        # [修正 1] 季後賽系列賽資訊處理
        if s.game_type == 3 and s.series_id:
            parts = s.series_id.split('_')
            round_label = "Playoffs"
            if "R1" in s.series_id: round_label = "Round 1"
            elif "R2" in s.series_id: round_label = "Conf. Semis"
            elif "R3" in s.series_id: round_label = "Conf. Finals"
            elif "Finals" in s.series_id: round_label = "Finals"
            elif "3rdPlace" in s.series_id: round_label = "3rd Place"

            # 計算系列賽目前比分 (只計算「本場比賽之前」的場次)
            # 關鍵修正: 增加 Schedule.game_number < s.game_number 條件
            series_games = db.session.query(Schedule, Match)\
                .join(Match, Schedule.match_id == Match.id)\
                .filter(
                    Schedule.series_id == s.series_id, 
                    Schedule.status == 'FINISHED',
                    Schedule.game_number < s.game_number # <--- 修正點：只看這場之前的
                ).all()
            
            series_home_wins = 0
            series_away_wins = 0
            
            for sched, m in series_games:
                winner_id = m.home_team_id if m.home_score > m.away_score else m.away_team_id
                
                # 注意：Schedule 的 home/away 在系列賽中會互換 (主客場輪替)
                # 但我們在前端顯示時，通常固定顯示該場比賽的主客隊視角
                # 這裡我們回傳的是「該場比賽(s)的主隊」在系列賽贏了幾場
                
                if winner_id == s.home_team_id:
                    series_home_wins += 1
                elif winner_id == s.away_team_id:
                    series_away_wins += 1

            item['series_info'] = {
                'round_label': round_label,
                'game_number': s.game_number,
                'home_wins': series_home_wins,
                'away_wins': series_away_wins
            }

        result.append(item)
        
    return jsonify(result)

@league_bp.route('/match/<int:match_id>', methods=['GET'])
def get_match_detail(match_id):
    """
    取得單場比賽詳細數據 (Box Score & PBP)
    """
    match = Match.query.get_or_404(match_id)
    home_team = Team.query.get(match.home_team_id)
    away_team = Team.query.get(match.away_team_id)

    # 撈取球員數據
    player_stats = MatchPlayerStat.query.filter_by(match_id=match.id).all()
    
    box_score = {'home': [], 'away': []}
    
    for stat in player_stats:
        p_data = {
            'id': stat.player_id,
            'name': stat.player.name,
            'pos': stat.position,
            'grade': stat.grade,
            'min': round(stat.seconds_played / 60, 1),
            'pts': stat.pts,
            'reb': stat.reb,
            'ast': stat.ast,
            'stl': stat.stl,
            'blk': stat.blk,
            'tov': stat.tov,
            'pf': stat.fouls,
            'pm': stat.plus_minus,
            'fg': f"{stat.fgm}/{stat.fga}",
            'fg_pct': round(stat.fgm / stat.fga * 100, 1) if stat.fga > 0 else 0,
            '3pt': f"{stat.m3pm}/{stat.m3pa}",
            'ft': f"{stat.ftm}/{stat.fta}",
            'is_starter': stat.is_starter,
            'is_played': stat.is_played
        }
        
        if stat.team_id == match.home_team_id:
            box_score['home'].append(p_data)
        else:
            box_score['away'].append(p_data)

    # 排序：先發優先，然後按上場時間
    for team_key in ['home', 'away']:
        box_score[team_key].sort(key=lambda x: (not x['is_starter'], -x['min']))

    return jsonify({
        'id': match.id,
        'date': match.date,
        'home_team': {'id': home_team.id, 'name': home_team.name, 'score': match.home_score},
        'away_team': {'id': away_team.id, 'name': away_team.name, 'score': match.away_score},
        'is_ot': match.is_ot,
        'pace': match.pace,
        'box_score': box_score,
        'pbp_logs': match.pbp_logs or []
    })