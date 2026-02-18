# app/services/league_service.py
import random
from datetime import datetime
from sqlalchemy import or_
from app import db
from app.models.league import Season, Schedule
from app.models.team import Team
from app.models.match import Match, MatchTeamStat, MatchPlayerStat
from app.services.match_engine.core import MatchEngine
from app.services.match_engine.service import DBToEngineAdapter
from app.utils.game_config_loader import GameConfigLoader

class LeagueService:
    
    @staticmethod
    def process_league_entry(new_team):
        """
        [核心邏輯] 處理新球隊進入聯賽的流程
        
        邏輯:
        1. 檢查正式聯賽 (is_official=True) 中是否有 BOT 球隊。
        2. [有 BOT -> 取代模式]:
           - 選定一支 BOT 球隊。
           - 將該 BOT 的「戰績」複製給 New Team。
           - 將該 BOT 在「賽程表 (Schedule)」中的 ID 全部置換為 New Team ID。
           - 將該 BOT 在「歷史比賽 (Match)」中的 ID 全部置換為 New Team ID (歷史繼承)。
           - 將該 BOT 移出正式聯賽 (is_official=False)，狀態改為 'EXPANSION_BOT'。
           - New Team 晉升為正式聯賽 (is_official=True)。
        3. [無 BOT -> 擴充模式]:
           - New Team 維持 is_official=False。
           - 安排擴充賽程 (若有需要)。
        """
        
        # 1. 尋找目標 BOT (正式聯賽中的 BOT)
        target_bot = Team.query.filter_by(is_official=True, status='BOT').first()
        
        if target_bot:
            print(f"🔄 [League] Team {new_team.name} (ID:{new_team.id}) is REPLACING Bot {target_bot.name} (ID:{target_bot.id})")
            
            # === 執行取代 (Replacement) ===
            
            # A. 繼承戰績 (Inherit Records - Wins/Losses)
            new_team.season_wins = target_bot.season_wins
            new_team.season_losses = target_bot.season_losses
            
            # B. 繼承席位 (Swap Schedule Slots)
            Schedule.query.filter_by(home_team_id=target_bot.id).update({'home_team_id': new_team.id})
            Schedule.query.filter_by(away_team_id=target_bot.id).update({'away_team_id': new_team.id})
            
            # C. 繼承歷史比賽 (Inherit Match History)
            Match.query.filter_by(home_team_id=target_bot.id).update({'home_team_id': new_team.id})
            Match.query.filter_by(away_team_id=target_bot.id).update({'away_team_id': new_team.id})
            
            # 同步更新 MatchTeamStat (數據統計歸屬)
            MatchTeamStat.query.filter_by(team_id=target_bot.id).update({'team_id': new_team.id})
            
            # D. 狀態交換 (Status Swap)
            new_team.is_official = True
            new_team.status = 'PLAYER'
            
            target_bot.is_official = False
            target_bot.status = 'EXPANSION_BOT' 
            
            # 重置 BOT 戰績
            target_bot.season_wins = 0
            target_bot.season_losses = 0
            
            # E. 強制同步數據
            db.session.flush()
            new_team.update_season_stats()
            target_bot.update_season_stats()
            
        else:
            print(f"🆕 [League] Team {new_team.name} joins Expansion League")
            # === 進入擴充聯賽 ===
            new_team.is_official = False
            new_team.status = 'PLAYER'
            
            LeagueService._arrange_expansion_match(new_team)

    @staticmethod
    def _arrange_expansion_match(new_team):
        """
        為新加入的擴充球隊安排一場比賽
        """
        season = Season.query.filter_by(is_active=True).first()
        if not season: return

        opponent = Team.query.filter(
            Team.id != new_team.id,
            Team.is_official == False,
            or_(Team.status == 'BOT', Team.status == 'EXPANSION_BOT')
        ).first()
        
        if opponent:
            sched = Schedule(
                season_id=season.id,
                day=season.current_day,
                game_type=2, # 擴充賽
                home_team_id=new_team.id,
                away_team_id=opponent.id,
                status='PUBLISHED'
            )
            db.session.add(sched)
            print(f"📅 [Schedule] Created expansion match: {new_team.name} vs {opponent.name}")
    
    @staticmethod
    def get_current_season():
        season = Season.query.filter_by(is_active=True).first()
        if not season:
            season = Season(season_number=1, current_day=0, phase='PRE_SEASON')
            db.session.add(season)
            db.session.commit()
        return season

    # =====================================================
    # 每日排程系統 (Daily Schedule System)
    # =====================================================

    @staticmethod
    def process_day_change_0000():
        season = LeagueService.get_current_season()
        season.current_day += 1
        
        if season.current_day <= 70:
            season.phase = 'REGULAR'
        elif season.current_day <= 84:
            season.phase = 'PLAYOFFS'
        else:
            season.phase = 'OFF_SEASON'
            
        print(f"📅 [League] Entering Season {season.season_number} Day {season.current_day} ({season.phase})")

        if season.phase == 'REGULAR':
            LeagueService._generate_daily_official_schedule(season)

        LeagueService._matchmake_expansion_league(season)
        
        db.session.commit()

    @staticmethod
    def _generate_daily_official_schedule(season):
        teams = Team.query.filter_by(is_official=True).order_by(Team.id).all()
        n = len(teams)
        
        if n < 2 or n % 2 != 0:
            print(f"⚠️ [Warning] Official teams count ({n}) is invalid for scheduling.")
            return

        day_idx = season.current_day - 1
        round_idx = day_idx % (n - 1)
        
        fixed_team = teams[0]
        moving_teams = teams[1:]
        rotated_teams = moving_teams[round_idx:] + moving_teams[:round_idx]
        daily_roster = [fixed_team] + rotated_teams
        
        matchups = []
        for i in range(n // 2):
            t1 = daily_roster[i]
            t2 = daily_roster[n - 1 - i]
            matchups.append((t1, t2))
            
        is_second_half = day_idx >= (n - 1)
        created_count = 0
        for t1, t2 in matchups:
            if is_second_half:
                home, away = t2, t1
            else:
                home, away = t1, t2
                
            sched = Schedule(
                season_id=season.id,
                day=season.current_day,
                game_type=1,
                home_team_id=home.id,
                away_team_id=away.id,
                status='PUBLISHED'
            )
            db.session.add(sched)
            created_count += 1
            
        print(f"✅ [Schedule] Generated {created_count} official games for Day {season.current_day}")

    @staticmethod
    def process_match_execution_1900():
        """
        [19:00] 比賽執行作業
        """
        season = LeagueService.get_current_season()
        
        games = Schedule.query.filter_by(
            season_id=season.id, 
            day=season.current_day, 
            status='PUBLISHED'
        ).all()
        
        if not games:
            print(f"💤 [League] No games to simulate for Day {season.current_day}")
            return

        print(f"🏀 [League] Starting simulation for {len(games)} games...")
        
        config = GameConfigLoader.load()
        
        for game in games:
            try:
                home = Team.query.get(game.home_team_id)
                away = Team.query.get(game.away_team_id)
                
                home_engine = DBToEngineAdapter.convert_team(home)
                away_engine = DBToEngineAdapter.convert_team(away)
                
                engine = MatchEngine(home_engine, away_engine, config, game_id=f"S{season.season_number}D{season.current_day}G{game.id}")
                result = engine.simulate()
                
                match_record = Match(
                    season_id=season.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    home_score=result.home_score,
                    away_score=result.away_score,
                    is_ot=result.is_ot,
                    pace=result.pace,
                    pbp_logs=result.pbp_log
                )
                db.session.add(match_record)
                db.session.flush()
                
                for is_home_team, team_id, stats_source in [
                    (True, home.id, result), 
                    (False, away.id, result)
                ]:
                    team_stat = MatchTeamStat(
                        match_id=match_record.id,
                        team_id=team_id,
                        is_home=is_home_team,
                        possessions=stats_source.home_possessions if is_home_team else stats_source.away_possessions,
                        avg_seconds_per_poss=stats_source.home_avg_seconds_per_poss if is_home_team else stats_source.away_avg_seconds_per_poss,
                        fb_made=stats_source.home_fb_made if is_home_team else stats_source.away_fb_made,
                        fb_attempt=stats_source.home_fb_attempt if is_home_team else stats_source.away_fb_attempt,
                        violation_8s=stats_source.home_violation_8s if is_home_team else stats_source.away_violation_8s,
                        violation_24s=stats_source.home_violation_24s if is_home_team else stats_source.away_violation_24s,
                        possession_history=stats_source.home_possession_history if is_home_team else stats_source.away_possession_history
                    )
                    db.session.add(team_stat)

                for engine_team, db_team_id in [(home_engine, home.id), (away_engine, away.id)]:
                    for p in engine_team.roster:
                        p_stat = MatchPlayerStat(
                            match_id=match_record.id,
                            team_id=db_team_id,
                            player_id=int(p.id),
                            grade=p.grade,
                            position=p.position,
                            role=p.role,
                            seconds_played=p.seconds_played,
                            is_starter=p.is_starter, 
                            is_played=p.is_played, 
                            pts=p.stat_pts,
                            reb=p.stat_reb,
                            ast=p.stat_ast,
                            stl=p.stat_stl,
                            blk=p.stat_blk,
                            tov=p.stat_tov,
                            fouls=p.fouls,
                            plus_minus=p.stat_plus_minus,
                            fgm=p.stat_fgm,
                            fga=p.stat_fga,
                            m3pm=p.stat_3pm,
                            m3pa=p.stat_3pa,
                            ftm=p.stat_ftm,
                            fta=p.stat_fta,
                            orb=p.stat_orb,
                            drb=p.stat_drb,
                            fb_made=p.stat_fb_made,
                            fb_attempt=p.stat_fb_attempt,
                            remaining_stamina=p.current_stamina,
                            is_fouled_out=p.is_fouled_out
                        )
                        db.session.add(p_stat)

                game.status = 'FINISHED'
                game.match_id = match_record.id
                
                # [關鍵修改] 呼叫 Team.update_season_stats 進行校正
                db.session.flush() 
                home.update_season_stats()
                away.update_season_stats()
                
                # [關鍵修改] 呼叫 _update_reputation (原 _update_standings 拆分)
                LeagueService._update_reputation(home, away, result.home_score, result.away_score)
                
            except Exception as e:
                print(f"❌ Error simulating game {game.id}: {e}")
                db.session.rollback()
                continue
        
        db.session.commit()
        print(f"✅ [League] Day {season.current_day} Simulation Completed.")

    @staticmethod
    def _matchmake_expansion_league(season):
        expansion_teams = Team.query.filter_by(is_official=False).all()
        if not expansion_teams: return
        expansion_teams.sort(key=lambda x: x.reputation, reverse=True)
        for i in range(0, len(expansion_teams), 2):
            team_a = expansion_teams[i]
            if i + 1 >= len(expansion_teams):
                bot_opponent = LeagueService._get_or_create_ghost_bot()
                LeagueService._create_schedule(season, team_a, bot_opponent, is_expansion=True)
                break
            team_b = expansion_teams[i+1]
            if team_a.home_games_played > team_a.away_games_played:
                home, away = team_b, team_a
            else:
                home, away = team_a, team_b
            LeagueService._create_schedule(season, home, away, is_expansion=True)

    @staticmethod
    def _create_schedule(season, home, away, is_expansion=False):
        sched = Schedule(
            season_id=season.id,
            day=season.current_day,
            game_type=2 if is_expansion else 1,
            home_team_id=home.id,
            away_team_id=away.id,
            status='PUBLISHED'
        )
        db.session.add(sched)

    @staticmethod
    def _get_or_create_ghost_bot():
        bot = Team.query.filter_by(status='BOT').first()
        return bot

    @staticmethod
    def _update_reputation(home, away, home_score, away_score):
        """
        [拆分] 僅處理聲望變更
        """
        if home_score > away_score:
            winner, loser = home, away
        else:
            winner, loser = away, home
            
        rep_change_win = 1
        rep_change_lose = -1
        rep_diff = loser.reputation - winner.reputation
        if rep_diff > 500:
            rep_change_win += 3
            rep_change_lose -= 2
        winner.reputation += rep_change_win
        loser.reputation += rep_change_lose

    @staticmethod
    def _update_standings(home, away, home_score, away_score):
        """
        [已棄用] 請改用 update_season_stats + _update_reputation
        保留此函式僅為兼容舊代碼，但不建議使用
        """
        pass

    @staticmethod
    def handle_new_player_team(user, team):
        """
        處理新玩家註冊時的球隊分配
        """
        target_bot = Team.query.filter_by(is_official=True, status='BOT').first()
        
        if target_bot:
            print(f"🔄 User {user.username} taking over Bot Team {target_bot.name} (ID: {target_bot.id})")
            
            team.user_id = None 
            db.session.flush() 

            for p in target_bot.players: 
                p.team_id = None
            
            for p in team.players: 
                p.team_id = target_bot.id
            
            target_bot.user_id = user.id
            target_bot.name = team.name
            target_bot.arena_name = team.arena_name
            target_bot.fanpage_name = team.fanpage_name
            target_bot.funds = team.funds
            target_bot.reputation = 0
            target_bot.status = 'PLAYER'
            target_bot.is_bot = False
            
            # 重算一次確保數據正確
            target_bot.update_season_stats()
            
            db.session.delete(team)
            user.is_bot = False
        else:
            print(f"🆕 User {user.username} joined Expansion League")
            team.is_official = False
            team.status = 'PLAYER'
            team.is_bot = False
            team.update_season_stats() # 初始化為 0
        
        db.session.commit()