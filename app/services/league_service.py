# app/services/league_service.py
import random
import math
import heapq
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from sqlalchemy import or_, and_, func, desc
from app import db
from app.models.league import Season, Schedule, League, LeagueParticipant
from app.models.team import Team
from app.models.user import User
from app.models.match import Match, MatchTeamStat, MatchPlayerStat
from app.models.tactics import TeamTactics
from app.services.match_engine.core import MatchEngine
from app.services.match_engine.service import DBToEngineAdapter
from app.services.team_creator import TeamCreator
from app.services.player_generator import PlayerGenerator
from app.utils.game_config_loader import GameConfigLoader

# =====================================================
# 獨立 Worker 函數 (必須放在 Class 外部以支援 Multiprocessing)
# =====================================================

def _get_streak_score_static(streak, weights):
    """靜態輔助方法，供 Worker 使用"""
    if streak < 2: return 0
    if streak == 2: return weights.get('streak_2', 1)
    if streak == 3: return weights.get('streak_3', 3)
    if streak == 4: return weights.get('streak_4', 5)
    if streak == 5: return weights.get('streak_5', 10)
    return weights.get('streak_6_plus', 30)

def _calculate_penalty_static(schedule, team_ids, penalty_weights):
    """靜態計算方法，供 Worker 使用"""
    total_score = 0
    team_venues = {tid: [] for tid in team_ids}
    
    for daily_matches in schedule:
        for home, away in daily_matches:
            team_venues[home].append(0)
            team_venues[away].append(1)
    
    for tid, venues in team_venues.items():
        current_streak = 1
        for i in range(1, len(venues)):
            if venues[i] == venues[i-1]:
                current_streak += 1
            else:
                total_score += _get_streak_score_static(current_streak, penalty_weights)
                current_streak = 1
        total_score += _get_streak_score_static(current_streak, penalty_weights)
    return total_score

def run_simulation_batch(batch_iterations, base_schedule, team_ids, penalty_weights, elite_pool_size):
    """
    多進程 Worker 執行的任務
    回傳: 該 Batch 找到的前 N 個最佳解 (List of (-score, indices))
    """
    local_elite_pool = [] # Min-Heap 存 (-score, indices)
    day_indices = list(range(len(base_schedule)))
    
    # 若 batch 很小，不需要每次都 copy list，直接 shuffle 即可
    # 但為了避免影響原始數據 (雖然是傳值)，這裡我們在 loop 內 shuffle
    
    for _ in range(batch_iterations):
        random.shuffle(day_indices)
        current_schedule_view = [base_schedule[i] for i in day_indices]
        score = _calculate_penalty_static(current_schedule_view, team_ids, penalty_weights)
        
        # 維護 Local Heap
        # 我們存 (-score)，所以 heap 頂端是 (-score) 最小的 => 即 score 最大的 (最爛的)
        # 目標是保留 score 最小的 (即 -score 最大的)
        
        if len(local_elite_pool) < elite_pool_size:
            heapq.heappush(local_elite_pool, (-score, day_indices[:]))
        else:
            # 如果當前 score 比池中最爛的還好 (數值更小 => -score 更大)
            # local_elite_pool[0][0] 是目前池中最小的負數 (例如 -1100)
            # 如果 -score > -1100 (例如 -1000)，代表 score 1000 < 1100，更好
            if -score > local_elite_pool[0][0]:
                heapq.heappushpop(local_elite_pool, (-score, day_indices[:]))
    
    return local_elite_pool

class LeagueService:
    """
    ASBL 聯賽營運服務 (League System Service)
    負責賽季推進、賽程排定、聯賽重組與比賽模擬。
    對應規格書: ASBL League System Specification v1.3
    """

    # =====================================================
    # 1. 聯賽進場與球隊狀態管理 (Entry & Status)
    # =====================================================

    @staticmethod
    def process_league_entry(new_team):
        """
        [核心邏輯] 處理新球隊進入聯賽的流程 (Spec 1.2)
        情境 A: 核心聯賽填充 (Core Filling) -> 接管 BOT
        情境 B/C: 擴充/過渡 -> 設為 PROVISIONAL
        """
        # 1. 尋找目標 BOT (正式聯賽中的 BOT)
        target_bot = Team.query.filter_by(is_official=True, status='BOT').first()
        
        if target_bot:
            print(f"🔄 [聯盟] 球隊 {new_team.name} (ID:{new_team.id}) 正在接管電腦球隊 {target_bot.name} (ID:{target_bot.id})")
            
            # === 執行接管 (Takeover) ===
            # A. 繼承戰績與排名數據
            new_team.season_wins = target_bot.season_wins
            new_team.season_losses = target_bot.season_losses
            new_team.reputation = 0 # 重置聲望 (新經營者)
            
            # B. 繼承席位 (更新 Schedule)
            Schedule.query.filter_by(home_team_id=target_bot.id).update({'home_team_id': new_team.id})
            Schedule.query.filter_by(away_team_id=target_bot.id).update({'away_team_id': new_team.id})
            
            # C. 繼承歷史比賽 (更新 Match)
            Match.query.filter_by(home_team_id=target_bot.id).update({'home_team_id': new_team.id})
            Match.query.filter_by(away_team_id=target_bot.id).update({'away_team_id': new_team.id})
            
            # D. 繼承聯賽參賽權 (LeagueParticipant)
            LeagueParticipant.query.filter_by(team_id=target_bot.id).update({'team_id': new_team.id})

            # E. 狀態交換
            new_team.is_official = True
            new_team.status = 'PLAYER'
            
            # 舊 BOT 降級為非正式並重置
            target_bot.is_official = False
            target_bot.status = 'BOT' 
            target_bot.season_wins = 0
            target_bot.season_losses = 0
            
            # F. 強制同步數據
            db.session.flush()
            new_team.update_season_stats()
            target_bot.update_season_stats()
            
        else:
            print(f"🆕 [聯盟] 球隊 {new_team.name} 加入過渡聯賽 (Provisional)")
            # === 進入過渡狀態 ===
            new_team.is_official = False
            new_team.status = 'PROVISIONAL'
            
            # 安排一場即時的熱身賽
            LeagueService._arrange_provisional_match(new_team)

    @staticmethod
    def _arrange_provisional_match(new_team):
        """
        為過渡球隊安排一場即時熱身賽 (Spec 1.2 情境 C)
        """
        season = LeagueService.get_current_season()
        if not season: return

        # 優先尋找其他 PROVISIONAL 球隊，其次找閒置 BOT
        opponent = Team.query.filter(
            Team.id != new_team.id,
            Team.is_official == False,
            or_(Team.status == 'PROVISIONAL', Team.status == 'BOT')
        ).order_by(func.random()).first()
        
        # 若無對手，生成 Ghost Bot
        if not opponent:
            opponent = LeagueService._get_or_create_ghost_bot()

        if opponent:
            sched = Schedule(
                season_id=season.id,
                day=season.current_day,
                game_type=2, # 過渡/熱身賽
                home_team_id=new_team.id,
                away_team_id=opponent.id,
                status='PUBLISHED'
            )
            db.session.add(sched)
            print(f"📅 [賽程] 已建立過渡熱身賽: {new_team.name} vs {opponent.name}")

    @staticmethod
    def get_current_season():
        season = Season.query.filter_by(is_active=True).first()
        if not season:
            season = Season(season_number=1, current_day=0, phase='PRE_SEASON')
            db.session.add(season)
            db.session.commit()
        return season

    # =====================================================
    # 2. 每日排程系統 (Daily Schedule System) - Spec 4
    # =====================================================

    @staticmethod
    def process_day_change_0000():
        """
        [00:00] 換日與行政作業
        """
        season = LeagueService.get_current_season()
        season.current_day += 1
        
        # 更新賽季階段
        if season.current_day == 1:
            season.phase = 'REGULAR' # 準備開始
            print(f"🔄 [賽季] 第 {season.season_number} 季 Day 1: 執行聯賽重組與賽程生成...")
            LeagueService._reset_season_and_reseed(season)
            # 重要：先存檔，讓使用者能看到分組結果
            db.session.commit()
            print("   💾 [系統] 聯賽分組資料已存檔，開始生成賽程...")
            LeagueService._generate_full_season_schedule(season)
            
        elif 2 <= season.current_day <= 71:
            season.phase = 'REGULAR'
            
        elif season.current_day == 72:
            season.phase = 'PLAYOFFS'
            print("📅 [季後賽] 例行賽結束，產生季後賽對戰組合 (R1)...")
            LeagueService._generate_playoff_bracket(season, round_num=1)
            
        elif 73 <= season.current_day <= 89:
            season.phase = 'PLAYOFFS'
            # 檢查是否需要產生下一輪對戰
            if season.current_day == 76:
                LeagueService._generate_playoff_bracket(season, round_num=2)
            elif season.current_day == 80:
                LeagueService._generate_playoff_bracket(season, round_num=3)
            elif season.current_day == 84:
                LeagueService._generate_playoff_bracket(season, round_num=4) # Finals
                
            # 清理已結束的系列賽 (例如 2-0 橫掃，移除第3戰)
            LeagueService._cleanup_finished_series(season)
            
        else:
            season.phase = 'OFF_SEASON'

        # 產生過渡聯賽的每日隨機賽程
        LeagueService._generate_daily_provisional_matches(season)
        
        print(f"📅 [聯盟] 進入第 {season.season_number} 季 第 {season.current_day} 天 ({season.phase})")
        db.session.commit()

    @staticmethod
    def _reset_season_and_reseed(season):
        """
        [Day 1] 賽季重組機制 (修正版)
        邏輯:
        1. 計算「真人玩家」數量，決定需要幾個聯賽層級 (每層36隊)。
        2. 優先放入真人玩家。
        3. 剩餘空位由「現有 BOT」依聲望填補。
        4. 若 BOT 不夠則生成新 BOT；若 BOT 太多則將多餘的設為非正式(Inactive)。
        """
        teams_per_tier = GameConfigLoader.get('league_system.structure.teams_per_tier', 36)
        
        # 1. 撈取所有真人球隊 (Player & Provisional)
        human_teams = Team.query.filter(
            or_(Team.status == 'PLAYER', Team.status == 'PROVISIONAL')
        ).all()
        
        # 2. 撈取所有現存 BOT
        bot_teams = Team.query.filter_by(status='BOT').order_by(desc(Team.reputation)).all()
        
        num_humans = len(human_teams)
        
        # 計算所需層級數 (至少 1 層)
        # 例如: 4 人 -> 1 層; 40 人 -> 2 層
        num_tiers = math.ceil(num_humans / teams_per_tier)
        if num_tiers < 1: num_tiers = 1
        
        total_capacity = num_tiers * teams_per_tier
        spots_for_bots = total_capacity - num_humans
        
        print(f"📊 [重組] 真人球隊: {num_humans} 隊 | 現有 BOT: {len(bot_teams)} 隊")
        print(f"   -> 預計開設 {num_tiers} 個聯賽層級 (共 {total_capacity} 席位)")
        
        # 3. 準備參賽名單
        active_teams = []
        active_teams.extend(human_teams)
        
        # 填補 BOT
        if len(bot_teams) >= spots_for_bots:
            # BOT 太多，取強的，剩下的設為非正式
            selected_bots = bot_teams[:spots_for_bots]
            excess_bots = bot_teams[spots_for_bots:]
            
            active_teams.extend(selected_bots)
            
            # 處理多餘 BOT (避免它們觸發新聯賽)
            for b in excess_bots:
                b.is_official = False
                # b.status 保持 'BOT'，但 is_official = False 代表沒參賽
                # 清除戰績
                b.season_wins = 0
                b.season_losses = 0
            print(f"   ✂️ 已剔除 {len(excess_bots)} 支多餘的 BOT 球隊。")
        else:
            # BOT 不夠，全上，後面再補新的
            active_teams.extend(bot_teams)
        
        # 依聲望排序 (S-shape 分組或單純排序，這裡簡化為依聲望高低填入 T0, T1...)
        # 混合後重新排序
        active_teams.sort(key=lambda x: x.reputation, reverse=True)
        
        current_idx = 0
        for tier in range(num_tiers):
            league_name = f"Tier {tier} League"
            if tier == 0: league_name = "ASBL Premier League"
            
            new_league = League(season_id=season.id, tier=tier, name=league_name)
            db.session.add(new_league)
            db.session.flush()
            
            # 取出該層級球隊
            tier_teams = active_teams[current_idx : current_idx + teams_per_tier]
            
            # 若還不夠 (因為上面 BOT 不夠)，補新 BOT
            while len(tier_teams) < teams_per_tier:
                new_bot = LeagueService._create_new_bot_team(f"Bot_T{tier}_{len(tier_teams)+1}")
                tier_teams.append(new_bot)
                # 注意: 新建立的 BOT 不用加回 active_teams，直接進 DB 即可
            
            for team in tier_teams:
                team.is_official = True
                # 確保狀態正確 (Provisional 轉正)
                if team.status == 'PROVISIONAL':
                    team.status = 'PLAYER'
                elif team.user_id is None: # 防呆
                    team.status = 'BOT'
                    
                team.season_wins = 0
                team.season_losses = 0
                team.home_games_played = 0
                team.away_games_played = 0
                
                participant = LeagueParticipant(
                    league_id=new_league.id,
                    team_id=team.id,
                    start_reputation=team.reputation
                )
                db.session.add(participant)
            
            current_idx += teams_per_tier
            print(f"   ✅ {league_name} 分組完成 ({len(tier_teams)} 隊)")

    @staticmethod
    def _create_new_bot_team(bot_name):
        """
        建立一支全新的電腦球隊 (包含 User, Team, Players, Tactics)
        """
        # 1. 建立 User
        user = User(username=bot_name, email=f"{bot_name.lower()}@cpu.asbl", is_bot=True)
        user.set_password("bot_password")
        db.session.add(user)
        db.session.flush()
        
        # 2. 建立 Team
        init_settings = GameConfigLoader.get('system.initial_team_settings', {})
        team = Team(
            name=bot_name,
            owner=user,
            funds=init_settings.get('funds', 300000),
            reputation=init_settings.get('reputation', 0),
            arena_name=f"{bot_name} Arena",
            status='BOT',
            is_official=True
        )
        db.session.add(team)
        db.session.flush()
        
        # 3. 生成球員
        PlayerGenerator.initialize_class()
        roster_payloads = TeamCreator.create_valid_roster()
        player_ids = []
        for p_data in roster_payloads:
            player, _ = PlayerGenerator.save_to_db(p_data, user_id=user.id, team_id=team.id)
            player_ids.append(player.id)
            
        # 4. 建立戰術
        tactics = TeamTactics(team_id=team.id, roster_list=player_ids)
        db.session.add(tactics)
        
        return team

    @staticmethod
    def _generate_full_season_schedule(season):
        """
        [Day 1] 產生整季賽程 (多核心並行版)
        """
        leagues = League.query.filter_by(season_id=season.id).all()
        
        # 讀取優化參數
        sched_config = GameConfigLoader.get('league_system.schedule.optimization')
        total_iterations = sched_config.get('iterations', 100000)
        elite_pool_size = sched_config.get('elite_pool_size', 1000)
        penalty_weights = GameConfigLoader.get('league_system.schedule.optimization.penalty_weights')
        
        # 設定並行參數
        cpu_count = os.cpu_count() or 4
        # 將總次數切分為多個小批次，以便更新進度條
        # 例如: 3000萬次，切成 100 個 Task，每個 Task 跑 30萬次
        num_batches = 100 
        batch_size = max(1, total_iterations // num_batches)
        
        print(f"🖥️ [系統] 偵測到 {cpu_count} 核心，準備啟動並行運算 (總運算: {total_iterations:,} 次)")

        for league in leagues:
            print(f"🔄 [賽程] 正在為 {league.name} 生成賽程...")
            
            participants = LeagueParticipant.query.filter_by(league_id=league.id).all()
            team_ids = [p.team_id for p in participants]
            
            if len(team_ids) % 2 != 0:
                print(f"⚠️ [警告] 聯賽 {league.name} 球隊數為奇數，無法生成圓桌賽程。")
                continue

            # 1. 生成基礎圓桌賽程
            base_schedule = LeagueService._create_round_robin(team_ids)
            
            # 2. 多核心蒙地卡羅模擬
            global_elite_pool = [] # 存放 (-score, schedule_indices)
            completed_iterations = 0
            start_time = time.time()

            with ProcessPoolExecutor(max_workers=cpu_count) as executor:
                futures = []
                for _ in range(num_batches):
                    # 提交任務給 Worker
                    futures.append(executor.submit(
                        run_simulation_batch, 
                        batch_size, 
                        base_schedule, 
                        team_ids, 
                        penalty_weights, 
                        elite_pool_size
                    ))
                
                # 處理結果與進度顯示
                for f in as_completed(futures):
                    try:
                        local_pool = f.result()
                        completed_iterations += batch_size
                        
                        # 合併 Local Pool 到 Global Pool
                        for score_neg, indices in local_pool:
                            if len(global_elite_pool) < elite_pool_size:
                                heapq.heappush(global_elite_pool, (score_neg, indices))
                            else:
                                if score_neg > global_elite_pool[0][0]:
                                    heapq.heappushpop(global_elite_pool, (score_neg, indices))
                        
                        # 計算統計數據
                        # Heap 存的是 -score。
                        # min(heap) 得到的是 (-score) 最小的 => score 最大的 (最差的菁英)
                        # max(heap) 得到的是 (-score) 最大的 => score 最小的 (最好的菁英)
                        worst_elite_score = -global_elite_pool[0][0] if global_elite_pool else 0
                        best_elite_score = -max(global_elite_pool)[0] if global_elite_pool else 0
                        
                        # 進度條顯示
                        progress = (completed_iterations / total_iterations) * 100
                        elapsed = time.time() - start_time
                        
                        sys.stdout.write(
                            f"\r   ⏳ 進度: {progress:5.1f}% | "
                            f"最佳積分: {best_elite_score} ~ {worst_elite_score} (Top {elite_pool_size}) | "
                            f"耗時: {elapsed:.1f}s"
                        )
                        sys.stdout.flush()
                        
                    except Exception as e:
                        print(f"\n❌ Worker 發生錯誤: {e}")

            print() # 換行
            
            # 3. 決策階段
            selected_entry = random.choice(global_elite_pool)
            final_score = -selected_entry[0]
            final_indices = selected_entry[1]
            best_schedule = [base_schedule[i] for i in final_indices]
            
            print(f"   ✅ {league.name} 賽程生成完畢。最終積分: {final_score}")
            
            # 4. 寫入資料庫
            start_day = 2
            for day_idx, daily_matches in enumerate(best_schedule):
                game_day = start_day + day_idx
                if game_day > 71: break 
                for home_id, away_id in daily_matches:
                    sched = Schedule(season_id=season.id, day=game_day, game_type=1, home_team_id=home_id, away_team_id=away_id, status='PUBLISHED')
                    db.session.add(sched)

    @staticmethod
    def _create_round_robin(team_ids):
        """標準雙循環圓桌法演算法"""
        schedule = []
        n = len(team_ids)
        if n % 2 == 1: team_ids.append(None) 
        
        fixed = team_ids[0]
        rotating = team_ids[1:]
        
        # 第一輪 (35 天)
        for i in range(n - 1):
            round_matches = []
            if i % 2 == 0:
                round_matches.append((fixed, rotating[0]))
            else:
                round_matches.append((rotating[0], fixed))
            
            for j in range(1, len(rotating) // 2 + 1):
                t1 = rotating[j]
                t2 = rotating[-(j)]
                if i % 2 == 0:
                    round_matches.append((t1, t2))
                else:
                    round_matches.append((t2, t1))
            
            schedule.append(round_matches)
            rotating.insert(0, rotating.pop())

        # 第二輪 (35 天) - 交換主客場
        second_half = []
        for day_matches in schedule:
            swapped = [(away, home) for home, away in day_matches]
            second_half.append(swapped)
        
        return schedule + second_half

    @staticmethod
    def _calculate_schedule_penalty(schedule, team_ids, penalty_weights):
        """計算賽程懲罰積分 (Spec v1.0)"""
        total_score = 0
        
        # 建立每個球隊的場地序列 (0=Home, 1=Away)
        team_venues = {tid: [] for tid in team_ids}
        
        for daily_matches in schedule:
            for home, away in daily_matches:
                team_venues[home].append(0)
                team_venues[away].append(1)
        
        for tid, venues in team_venues.items():
            current_streak = 1
            for i in range(1, len(venues)):
                if venues[i] == venues[i-1]:
                    current_streak += 1
                else:
                    total_score += LeagueService._get_streak_score(current_streak, penalty_weights)
                    current_streak = 1
            total_score += LeagueService._get_streak_score(current_streak, penalty_weights)
            
        return total_score

    @staticmethod
    def _get_streak_score(streak, weights):
        if streak < 2: return 0
        if streak == 2: return weights.get('streak_2', 1)
        if streak == 3: return weights.get('streak_3', 3)
        if streak == 4: return weights.get('streak_4', 5)
        if streak == 5: return weights.get('streak_5', 10)
        return weights.get('streak_6_plus', 30)

    @staticmethod
    def _generate_daily_provisional_matches(season):
        """
        [每日] 為過渡球隊產生隨機對戰 (Spec 1.2 C)
        """
        provisional_teams = Team.query.filter_by(status='PROVISIONAL').all()
        if not provisional_teams: return
        
        random.shuffle(provisional_teams)
        while len(provisional_teams) >= 2:
            t1 = provisional_teams.pop()
            t2 = provisional_teams.pop()
            
            sched = Schedule(
                season_id=season.id,
                day=season.current_day,
                game_type=2, # 過渡賽
                home_team_id=t1.id,
                away_team_id=t2.id,
                status='PUBLISHED'
            )
            db.session.add(sched)
        
        if provisional_teams:
            t1 = provisional_teams.pop()
            bot = LeagueService._get_or_create_ghost_bot()
            sched = Schedule(
                season_id=season.id,
                day=season.current_day,
                game_type=2,
                home_team_id=t1.id,
                away_team_id=bot.id,
                status='PUBLISHED'
            )
            db.session.add(sched)

    # =====================================================
    # 3. 季後賽系統 (Playoffs) - Spec 3
    # =====================================================
    
    @staticmethod
    def _generate_playoff_bracket(season, round_num):
        """
        產生季後賽對戰組合
        [修正] 遍歷所有聯賽層級 (T0, T1, T2...)，為每個聯賽產生獨立的季後賽樹狀圖。
        """
        leagues = League.query.filter_by(season_id=season.id).all()
        config = GameConfigLoader.get('system.playoff.series_length')
        
        for league in leagues:
            print(f"🏆 [季後賽] 正在為 {league.name} (Tier {league.tier}) 產生 R{round_num} 對戰組合...")
            
            # 依據輪次執行
            if round_num == 1:
                # R1: 取前 16 名 (Seed 1 vs 16, 2 vs 15...)
                participants = LeagueParticipant.query.filter_by(league_id=league.id).all()
                
                # 排序邏輯: 勝場 > 聲望
                ranked_teams = sorted(participants, key=lambda p: (
                    Team.query.get(p.team_id).season_wins, 
                    Team.query.get(p.team_id).reputation
                ), reverse=True)
                
                seeds = [p.team_id for p in ranked_teams[:16]]
                if len(seeds) < 16:
                    print(f"⚠️ [季後賽] {league.name} 隊伍不足 16 隊，跳過。")
                    continue

                # 對戰組合: (1,16), (8,9), (4,13), (5,12), (2,15), (7,10), (3,14), (6,11)
                # 這裡使用 series_prefix 加上 tier 區分不同聯賽的系列賽 ID (e.g., T0_R1_1)
                prefix = f"T{league.tier}_R1"
                
                matchups = [
                    (seeds[0], seeds[15]), (seeds[7], seeds[8]),
                    (seeds[3], seeds[12]), (seeds[4], seeds[11]),
                    (seeds[1], seeds[14]), (seeds[6], seeds[9]),
                    (seeds[2], seeds[13]), (seeds[5], seeds[10])
                ]
                
                series_len = config.get('round_1', 3)
                start_day = 73
                
                LeagueService._create_series_schedule(season, matchups, start_day, series_len, prefix)

            elif round_num == 2:
                # R2: 8強 (R1 勝者)
                prefix_prev = f"T{league.tier}_R1"
                prefix_curr = f"T{league.tier}_R2"
                
                winners = LeagueService._get_series_winners(season, prefix_prev)
                if len(winners) < 8: continue
                
                matchups = [
                    (winners[0], winners[1]), (winners[2], winners[3]),
                    (winners[4], winners[5]), (winners[6], winners[7])
                ]
                series_len = config.get('round_2', 3)
                start_day = 77
                LeagueService._create_series_schedule(season, matchups, start_day, series_len, prefix_curr)

            elif round_num == 3:
                # R3: 4強
                prefix_prev = f"T{league.tier}_R2"
                prefix_curr = f"T{league.tier}_R3"
                
                winners = LeagueService._get_series_winners(season, prefix_prev)
                if len(winners) < 4: continue
                
                matchups = [(winners[0], winners[1]), (winners[2], winners[3])]
                series_len = config.get('round_3', 3)
                start_day = 81
                LeagueService._create_series_schedule(season, matchups, start_day, series_len, prefix_curr)

            elif round_num == 4:
                # Finals & 3rd Place
                prefix_prev = f"T{league.tier}_R3"
                
                winners = LeagueService._get_series_winners(season, prefix_prev)
                losers = LeagueService._get_series_losers(season, prefix_prev)
                if len(winners) < 2: continue
                
                # 冠軍賽
                finals_matchup = [(winners[0], winners[1])]
                series_len = config.get('finals', 5)
                start_day = 85
                LeagueService._create_series_schedule(season, finals_matchup, start_day, series_len, f"T{league.tier}_Finals")
                
                # 季軍賽
                third_matchup = [(losers[0], losers[1])]
                LeagueService._create_series_schedule(season, third_matchup, start_day, series_len, f"T{league.tier}_3rdPlace")

    @staticmethod
    def _create_series_schedule(season, matchups, start_day, length, series_prefix):
        """建立系列賽賽程"""
        for idx, (home_id, away_id) in enumerate(matchups):
            series_id = f"{series_prefix}_{idx+1}"
            
            # 高種子 (home_id) 在 BO3/BO5 的主場優勢
            # BO3: H-H-A (簡化版) 或 H-A-H
            # BO5: H-H-A-A-H
            
            for i in range(length):
                game_num = i + 1
                day = start_day + i
                
                # 決定主場
                is_home_game = True
                if length == 3:
                    if game_num == 2: is_home_game = False # Game 2 客場
                elif length == 5:
                    if game_num in [3, 4]: is_home_game = False # Game 3,4 客場
                
                h, a = (home_id, away_id) if is_home_game else (away_id, home_id)
                
                sched = Schedule(
                    season_id=season.id,
                    day=day,
                    game_type=3, # 季後賽
                    home_team_id=h,
                    away_team_id=a,
                    status='PUBLISHED',
                    series_id=series_id,
                    game_number=game_num
                )
                db.session.add(sched)
        
        print(f"   ✅ 已建立 {series_prefix} 賽程 ({len(matchups)} 組)")

    @staticmethod
    def _get_series_winners(season, series_prefix):
        """取得某輪系列賽的勝者列表 (按 series_id 排序)"""
        # 邏輯: 查詢該輪所有已結束比賽，統計勝場
        matches = db.session.query(Schedule, Match).join(Match, Schedule.match_id == Match.id)\
            .filter(Schedule.season_id == season.id, Schedule.series_id.like(f"{series_prefix}%"))\
            .all()
        
        series_wins = {} # {series_id: {team_id: wins}}
        
        for sched, match in matches:
            sid = sched.series_id
            if sid not in series_wins: 
                series_wins[sid] = {}
            
            winner_id = match.home_team_id if match.home_score > match.away_score else match.away_team_id
            series_wins[sid][winner_id] = series_wins[sid].get(winner_id, 0) + 1
            
        # 判定勝者
        winners = []
        # 確保按照 series_id 順序 (T0_R1_1, T0_R1_2...) 回傳，這樣下一輪配對才正確
        sorted_sids = sorted(series_wins.keys(), key=lambda x: int(x.split('_')[-1]))
        
        for sid in sorted_sids:
            wins_map = series_wins[sid]
            # 取勝場最多者
            w = max(wins_map, key=wins_map.get)
            winners.append(w)
            
        return winners

    @staticmethod
    def _get_series_losers(season, series_prefix):
        """取得某輪系列賽的敗者列表"""
        # 類似 winners，只是取輸的一方
        matches = db.session.query(Schedule, Match).join(Match, Schedule.match_id == Match.id)\
            .filter(Schedule.season_id == season.id, Schedule.series_id.like(f"{series_prefix}%"))\
            .all()
        
        series_wins = {}
        series_teams = {}
        
        for sched, match in matches:
            sid = sched.series_id
            if sid not in series_wins: 
                series_wins[sid] = {}
                if sched.game_number == 1:
                    series_teams[sid] = {sched.home_team_id, sched.away_team_id}
            
            winner_id = match.home_team_id if match.home_score > match.away_score else match.away_team_id
            series_wins[sid][winner_id] = series_wins[sid].get(winner_id, 0) + 1
        
        losers = []
        sorted_sids = sorted(series_wins.keys(), key=lambda x: int(x.split('_')[-1]))
        
        for sid in sorted_sids:
            wins_map = series_wins[sid]
            winner = max(wins_map, key=wins_map.get)
            # 敗者 = 參與者集合 - 勝者
            teams = series_teams.get(sid, set(wins_map.keys())) # Fallback
            loser = list(teams - {winner})[0]
            losers.append(loser)
            
        return losers

    @staticmethod
    def _cleanup_finished_series(season):
        """
        [每日] 清理已分出勝負的系列賽 (Spec 4)
        若 BO3 已經 2-0，則取消第 3 戰。
        
        [修正] 邏輯變更：
        不要只檢查「今天」完賽的系列賽，而是檢查「未來還有賽程」的系列賽。
        若該系列賽的勝負已分 (例如 2-0)，則取消未來所有賽程。
        """
        # 1. 找出未來還有賽程的系列賽 (即將要打，但可能已經不需要打的)
        future_games = Schedule.query.filter(
            Schedule.season_id == season.id,
            Schedule.day >= season.current_day, # 包含今天
            Schedule.game_type == 3,
            Schedule.status == 'PUBLISHED'
        ).all()
        
        if not future_games: return

        # 取得所有相關的 series_id
        active_series_ids = set(g.series_id for g in future_games)
        
        for sid in active_series_ids:
            # 2. 統計該系列賽「目前為止」的戰績 (包含所有已完賽的)
            games = db.session.query(Schedule, Match).join(Match, Schedule.match_id == Match.id)\
                .filter(Schedule.season_id == season.id, Schedule.series_id == sid)\
                .all()
            
            wins = {}
            for sched, match in games:
                w = match.home_team_id if match.home_score > match.away_score else match.away_team_id
                wins[w] = wins.get(w, 0) + 1
            
            # 3. 判斷賽制長度 (總場數)
            total_scheduled = Schedule.query.filter_by(season_id=season.id, series_id=sid).count()
            target_wins = math.ceil(total_scheduled / 2)
            
            # 4. 檢查是否有人達到勝場目標
            if any(w >= target_wins for w in wins.values()):
                # 取消後續比賽
                games_to_cancel = [g for g in future_games if g.series_id == sid]
                
                for g in games_to_cancel:
                    g.status = 'CANCELLED'
                    print(f"ℹ️ [季後賽] 系列賽 {sid} 已分勝負，取消第 {g.game_number} 戰 (Day {g.day})。")

    # =====================================================
    # 4. 比賽執行與聲望 (Match Execution)
    # =====================================================

    @staticmethod
    def process_match_execution_1900():
        """
        [19:00] 比賽執行作業
        修正: 加入讀取 TeamTactics 戰術設定，確保引擎使用正確的輪替陣容。
        """
        season = LeagueService.get_current_season()
        
        games = Schedule.query.filter_by(
            season_id=season.id, 
            day=season.current_day, 
            status='PUBLISHED'
        ).all()
        
        if not games:
            print(f"💤 [聯盟] 第 {season.current_day} 天沒有比賽需要模擬")
            return

        print(f"🏀 [聯盟] 開始模擬 {len(games)} 場比賽...")
        
        config = GameConfigLoader.load()
        
        for game in games:
            try:
                home = Team.query.get(game.home_team_id)
                away = Team.query.get(game.away_team_id)
                
                # 1. 讀取戰術設定 (Tactics)
                # 這裡假設每個球隊只有一個主要的戰術設定，或者取第一個
                home_tactics = TeamTactics.query.filter_by(team_id=home.id).first()
                away_tactics = TeamTactics.query.filter_by(team_id=away.id).first()
                
                # 2. 轉換為引擎物件 (傳入戰術)
                # DBToEngineAdapter 需要根據 tactics.roster_list 來決定誰是先發、誰是替補
                home_engine = DBToEngineAdapter.convert_team(home, tactics=home_tactics)
                away_engine = DBToEngineAdapter.convert_team(away, tactics=away_tactics)
                
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
                
                # 儲存球隊數據
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

                # 儲存球員數據
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
                
                db.session.flush() 
                
                # 只有正式比賽才更新戰績與聲望
                if game.game_type == 1:
                    home.update_season_stats()
                    away.update_season_stats()
                    LeagueService._update_reputation(home, away, result.home_score, result.away_score, is_playoff=False)
                elif game.game_type == 3:
                    # 季後賽聲望
                    LeagueService._update_reputation(home, away, result.home_score, result.away_score, is_playoff=True)
                
            except Exception as e:
                print(f"❌ 模擬比賽 {game.id} 時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                continue
        
        db.session.commit()
        print(f"✅ [聯盟] 第 {season.current_day} 天模擬完成。")

    @staticmethod
    def _update_reputation(home, away, home_score, away_score, is_playoff=False):
        """
        [聲望系統] 依據 Spec 5 實作
        """
        rep_config = GameConfigLoader.get('league_system.reputation')
        
        if home_score > away_score:
            winner, loser = home, away
        else:
            winner, loser = away, home
        
        if not is_playoff:
            # === 例行賽 ===
            cfg = rep_config.get('regular', {})
            
            # 基礎分
            winner.reputation += cfg.get('win', 1)
            loser.reputation += cfg.get('loss', -1)
            
            # 下剋上判定 (需有排名資訊，這裡簡化用聲望差代替)
            # 假設聲望高 = 排名高
            threshold = cfg.get('upset_threshold', 5) # 雖然這裡用聲望差，但保留參數讀取
            
            # 邏輯: 若輸家聲望比贏家高出一定程度，視為爆冷
            if loser.reputation - winner.reputation > 100: # 簡化閾值，實際應查排名
                winner.reputation += cfg.get('upset_win_bonus', 2)
                loser.reputation += cfg.get('upset_loss_penalty', -1)
                
        else:
            # === 季後賽 ===
            cfg = rep_config.get('playoff', {})
            
            # 出賽獎勵
            winner.reputation += cfg.get('participation', 1)
            loser.reputation += cfg.get('participation', 1)
            
            # 勝場獎勵
            winner.reputation += cfg.get('win', 1)
            
            # 強者挑戰 (下剋上)
            if loser.reputation - winner.reputation > 100:
                winner.reputation += cfg.get('upset_bonus', 1)

    @staticmethod
    def _get_or_create_ghost_bot():
        bot = Team.query.filter_by(status='BOT').first()
        if not bot:
            bot = LeagueService._create_new_bot_team("Ghost_Bot")
        return bot