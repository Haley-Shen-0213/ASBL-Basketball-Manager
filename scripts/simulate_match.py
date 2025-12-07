# scripts/simulate_match.py
import sys
import os
import random
import math
import string

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from scripts.simulate_team_creation import create_team_roster, calculate_minutes

# ==========================================
# 0. 全域設定與屬性定義 (General Rules)
# ==========================================

ATTR_OFF_13 = [
    'ath_strength', 'ath_speed', 'ath_jump', 'shot_touch', 'shot_release', 
    'talent_offiq', 'talent_luck', 'shot_accuracy', 'shot_range', 'off_move', 
    'off_dribble', 'off_pass', 'off_handle'
]

ATTR_DEF_12 = [
    'ath_strength', 'ath_speed', 'ath_jump', 'shot_touch', 'shot_release', 
    'talent_defiq', 'talent_luck', 'def_rebound', 'def_boxout', 'def_contest', 
    'def_disrupt', 'off_move'
]

# ==========================================
# 1. 類別定義
# ==========================================
class PlayerObj:
    def __init__(self, data_dict):
        self.name = data_dict['name']
        self.role = data_dict['contract']['role']
        self.pos = data_dict['pos']
        self.height = data_dict['height']
        self.stats = data_dict['stats']
        self.target_minutes = data_dict.get('minutes', 0)
        
        self.stamina = 100.0
        self.minutes_played = 0.0
        
        self.minutes_breakdown = {k: 0.0 for k in ["C", "PF", "SF", "SG", "PG"]}
        self.current_court_pos = None 
        
        self.pos_scores = {}
        self.primary_pos = self.pos
        
        # 個人數據統計 (Spec v1.4 新增)
        self.game_stats = {
            "pts": 0, "fga": 0, "fgm": 0, "3pa": 0, "3pm": 0,
            "fta": 0, "ftm": 0, "oreb": 0, "dreb": 0,
            "ast": 0, "stl": 0, "blk": 0, "tov": 0
        }
        
        self.calculate_pos_scores()

    def get_current_stat(self, stat_name):
        base_val = self.stats.get(stat_name, 50)
        multiplier = 1.0
        
        if self.stamina < 1.5:
            multiplier = 0.21
        elif self.stamina < 80:
            multiplier = 1.0 - (80 - self.stamina) * 0.01
            if multiplier < 0.21: multiplier = 0.21
        else:
            multiplier = 1.0
            
        return base_val * multiplier

    def calculate_pos_scores(self):
        s = self.stats
        h = self.height
        def val(k): return s.get(k, 50)
        
        self.pos_scores = {
            "C":  h + val('ath_strength') + val('def_rebound') + val('def_boxout') + val('def_contest'),
            "PF": h + val('ath_strength') + val('def_rebound') + val('def_boxout') + val('def_contest') + val('ath_jump') + val('ath_speed'),
            "SF": sum(s.values()) + h,
            "SG": val('shot_touch') + val('shot_release') + val('talent_offiq') + val('talent_defiq') + val('def_contest') + val('def_disrupt') + val('shot_range'),
            "PG": val('ath_speed') + val('talent_offiq') + val('def_disrupt') + val('off_dribble') + val('off_pass') + val('off_handle') - h
        }
        self.primary_pos = max(self.pos_scores, key=self.pos_scores.get)

class Team:
    def __init__(self, name, roster_dicts):
        self.name = name
        self.roster = [PlayerObj(p) for p in roster_dicts]
        self.on_court = []
        self.score = 0
        self.best_5 = {}
        self.starters = {}
        
        # 團隊數據 (包含團隊失誤)
        self.stats = {
            "pts": 0, "fga": 0, "fgm": 0, "3pa": 0, "3pm": 0,
            "fta": 0, "ftm": 0, "oreb": 0, "dreb": 0,
            "ast": 0, "stl": 0, "blk": 0, "tov": 0, # 這裡的 TOV 包含團隊失誤
            "team_tov": 0 # 純團隊失誤 (8秒/24秒)
        }

    def get_team_stat_sum(self, players, stat_list):
        total = 0
        for p in players:
            for stat in stat_list:
                total += p.get_current_stat(stat)
        return total

# ==========================================
# 2. 比賽引擎核心
# ==========================================
class MatchEngine:
    def __init__(self, home_team, away_team):
        self.home = home_team
        self.away = away_team
        self.log_file = open("match_simulation_log.txt", "w", encoding="utf-8")
        self.quarter = 1
        self.time_remaining = 720.0
        self.is_ot = False
        self.possessions = 0
        
        chars = string.ascii_uppercase + string.digits
        self.match_id = ''.join(random.choices(chars, k=8))
        
    def log_debug(self, msg):
        self.log_file.write(msg + "\n")
        
    def log_process(self, msg):
        self.log_file.write(msg + "\n")

    def determine_lineups(self, team):
        # [Spec v1.4] 顯示優化 (Role 縮寫)
        header_msg = f"\n[{team.name}] Lineup (Role: ★=Star, S=Start, R=Rot, r=Role, B=Bench)"
        print(header_msg)
        self.log_debug(header_msg)
        
        positions = ["C", "PF", "SF", "SG", "PG"]
        player_ranks = {p.name: {} for p in team.roster}

        for pos in positions:
            sorted_players = sorted(team.roster, key=lambda x: x.pos_scores[pos], reverse=True)
            for rank, p in enumerate(sorted_players, 1):
                player_ranks[p.name][pos] = rank

        tbl_header = f"{'Name(Rl)':<13} {'C':<2} {'PF':<2} {'SF':<2} {'SG':<2} {'PG':<2}"
        print(tbl_header)
        self.log_debug(tbl_header)

        role_map = {"Star": "★", "Starter": "S", "Rotation": "R", "Role": "r", "Bench": "B"}
        role_order = {"Star": 0, "Starter": 1, "Rotation": 2, "Role": 3, "Bench": 4}
        sorted_roster = sorted(team.roster, key=lambda x: role_order.get(x.role, 5))

        for p in sorted_roster:
            r = player_ranks[p.name]
            r_abbr = role_map.get(p.role, "?")
            name_display = f"{p.name}({r_abbr})"
            row = f"{name_display:<13} {r['C']:<2} {r['PF']:<2} {r['SF']:<2} {r['SG']:<2} {r['PG']:<2}"
            print(row)
            self.log_debug(row)

        # Best 5
        remaining = team.roster[:]
        team.best_5 = {}
        for pos in ["C", "PF", "SF", "SG", "PG"]:
            if not remaining: break
            candidate = max(remaining, key=lambda x: x.pos_scores[pos])
            team.best_5[pos] = candidate
            remaining.remove(candidate)
            
        # Starters
        team.starters = {}
        pool = team.roster[:]
        
        stars = [p for p in pool if p.role == "Star"]
        for p in stars:
            if p.primary_pos not in team.starters:
                team.starters[p.primary_pos] = p
                pool.remove(p)
                
        starters = [p for p in pool if p.role == "Starter"]
        for p in starters:
            if p.primary_pos not in team.starters:
                team.starters[p.primary_pos] = p
                pool.remove(p)
                
        for pos in ["PG", "SG", "SF", "PF", "C"]:
            if pos not in team.starters:
                if not pool: break
                cand = max(pool, key=lambda x: x.pos_scores[pos])
                team.starters[pos] = cand
                pool.remove(cand)
        
        team.on_court = list(team.starters.values())
        for pos, p in team.starters.items():
            p.current_court_pos = pos

        lineup_parts = [f"{pos}{p.name}" for pos, p in team.starters.items()]
        lineup_str = "先發: " + ", ".join(lineup_parts)
        print(lineup_str)
        self.log_debug(lineup_str)

    def run(self):
        print(f"=== ASBL 模擬比賽開始 (Spec v1.4) ===")
        print(f"🆔 Match ID: {self.match_id}")
        
        self.log_debug(f"=== 比賽詳細運算紀錄 (MATCH LOG) ===")
        self.log_debug(f"Match ID: {self.match_id}")
        
        self.determine_lineups(self.home)
        self.determine_lineups(self.away)
        
        for q in range(1, 5):
            self.quarter = q
            self.time_remaining = 720.0
            self.play_quarter()
            if q == 2: self.recover_stamina()
                
        while self.home.score == self.away.score:
            self.is_ot = True
            self.log_process("\n=== 進入延長賽 (OT) ===")
            self.time_remaining = 300.0
            self.play_quarter()
            
        print(f"\n=== 比賽結束 ===\n最終比分: {self.home.name} {self.home.score} - {self.away.score} {self.away.name}")
        self.print_team_stats()
        self.print_player_stats()
        self.log_file.close()
        print(f"\n✅ 詳細運算紀錄已儲存至: {os.path.abspath('match_simulation_log.txt')}")

    def recover_stamina(self):
        self.log_debug("\n[中場休息] 全員體力 +20")
        for t in [self.home, self.away]:
            for p in t.roster: 
                old = p.stamina
                p.stamina = min(100, p.stamina + 20)
                self.log_debug(f"  > {p.name}: {old:.1f} -> {p.stamina:.1f}")

    def format_time(self):
        m = int(self.time_remaining // 60)
        s = self.time_remaining % 60
        return f"Q{self.quarter} {m:02d}:{s:04.1f}"

    def play_quarter(self):
        self.log_process(f"\n>>> 第 {self.quarter} 節開始 (OT: {self.is_ot}) <<<")
        possession = self.home if random.random() > 0.5 else self.away
        
        while self.time_remaining > 0:
            off_team = possession
            def_team = self.away if off_team == self.home else self.home
            
            self.check_subs(off_team)
            self.check_subs(def_team)
            
            elapsed, result, next_poss = self.process_possession(off_team, def_team)
            
            actual_elapsed = min(elapsed, self.time_remaining)
            self.time_remaining -= actual_elapsed
            self.update_stamina(actual_elapsed)
            
            self.log_process(f"[{self.format_time()}] {off_team.name} {result} | 用時 {actual_elapsed:.1f}s | {self.home.score}:{self.away.score}")
            
            if next_poss == "switch":
                possession = def_team
                self.possessions += 1
            else:
                possession = off_team

    def check_subs(self, team):
        is_clutch = (self.quarter == 4 and self.time_remaining <= 180) or self.is_ot
        if is_clutch:
            needed = list(team.best_5.values())
            current = team.on_court
            if set(needed) != set(current):
                team.on_court = []
                for pos, p in team.best_5.items():
                    p.current_court_pos = pos
                    team.on_court.append(p)
                self.log_process(f"🔥 [關鍵時刻] {team.name} 強制換上 Best 5")
            return

        for p_out in team.on_court[:]:
            reason = ""
            if p_out.stamina < 80: reason = f"體力低({p_out.stamina:.0f})"
            elif p_out.minutes_played > p_out.target_minutes: reason = f"時間到({p_out.minutes_played:.1f}/{p_out.target_minutes})"
            
            if reason:
                cands = [c for c in team.roster 
                         if c not in team.on_court 
                         and c.pos == p_out.pos
                         and c.stamina > p_out.stamina 
                         and c.minutes_played < c.target_minutes]
                
                if not cands:
                     cands = [c for c in team.roster 
                         if c not in team.on_court 
                         and c.stamina > p_out.stamina 
                         and c.minutes_played < c.target_minutes]

                if cands:
                    p_in = max(cands, key=lambda x: x.pos_scores[x.primary_pos])
                    p_in.current_court_pos = p_out.current_court_pos
                    p_out.current_court_pos = None
                    
                    team.on_court.remove(p_out)
                    team.on_court.append(p_in)
                    self.log_process(f"🔄 [換人] {team.name}: {p_in.name} 換 {p_out.name} ({reason})")

    def update_stamina(self, elapsed):
        mins = elapsed / 60.0
        self.log_debug(f"\n--- 體力更新 (經過 {elapsed:.1f}秒) ---")
        
        for t in [self.home, self.away]:
            self.log_debug(f"[{t.name}]")
            for p in t.on_court:
                ath_pct = p.stats['ath_stamina'] / 100.0
                hlt_pct = p.stats['talent_health'] / 100.0
                # [Spec v1.3] 消耗係數改為 3.0
                drain = (3.0 * (1 + (1 - ath_pct)) + (1 - hlt_pct)) * mins
                old_s = p.stamina
                p.stamina = max(1, p.stamina - drain)
                p.minutes_played += mins
                
                if p.current_court_pos:
                    p.minutes_breakdown[p.current_court_pos] += mins
                
                self.log_debug(f"  [場上] {p.name}: {old_s:.2f} -> {p.stamina:.2f} (消耗 {drain:.2f})")
                
            for p in [x for x in t.roster if x not in t.on_court]:
                ath_pct = p.stats['ath_stamina'] / 100.0
                hlt_pct = p.stats['talent_health'] / 100.0
                rec = (1.0 + ath_pct - (1 - hlt_pct)) * mins
                old_s = p.stamina
                p.stamina = min(100, p.stamina + rec)
                self.log_debug(f"  [板凳] {p.name}: {old_s:.2f} -> {p.stamina:.2f} (回復 {rec:.2f})")

    # ==========================================
    # 權重分配工具 (Spec v1.4 新增)
    # ==========================================
    def weighted_choice(self, candidates, weight_func):
        """
        通用權重選擇函數
        candidates: 候選球員列表
        weight_func: 計算權重的 lambda 函數 (輸入 player, 回傳 weight)
        """
        weights = {p: weight_func(p) for p in candidates}
        total_w = sum(weights.values())
        if total_w <= 0: return random.choice(candidates)
        
        # 排序: 權重占比最小的優先判定
        sorted_cands = sorted(candidates, key=lambda p: weights[p])
        
        r = random.random()
        cumulative = 0.0
        
        for p in sorted_cands:
            ratio = weights[p] / total_w
            cumulative += ratio
            if r <= cumulative:
                return p
        return sorted_cands[-1]

    def process_possession(self, off, defe):
        self.log_debug(f"\n========================================")
        self.log_debug(f"球權: {off.name} (攻) vs {defe.name} (守)")
        
        off3 = random.sample(off.on_court, 3)
        def3 = random.sample(defe.on_court, 3)
        off_sum = off.get_team_stat_sum(off3, ['off_dribble', 'off_pass', 'talent_offiq'])
        def_sum = defe.get_team_stat_sum(def3, ['def_disrupt', 'def_contest', 'talent_defiq'])
        
        base_t = random.uniform(1.0, 8.0)
        mod_t = (def_sum - off_sum) * 0.008
        back_t = max(0.5, min(8.1, base_t + mod_t))
        self.log_debug(f"[後場時間] 基礎{base_t:.2f} + 修正{mod_t:.2f} = {back_t:.2f}")

        if back_t > 8.0: 
            # [Spec v1.4] 8秒違例 -> 團隊失誤
            off.stats['tov'] += 1
            off.stats['team_tov'] += 1
            self.log_debug(f"[違例] 8秒違例! 時間 {back_t:.2f} > 8.0")
            return (back_t, "8秒違例", "switch")
        
        if back_t > 3.0:
            base_steal = 0.01
            mod_steal = (def_sum - off_sum) * 0.001
            final_steal_prob = base_steal + mod_steal
            roll = random.random()
            
            if roll <= final_steal_prob:
                # [Spec v1.4] 後場抄截歸屬
                # 抄截者: 權重分配
                stealer = self.weighted_choice(defe.on_court, lambda p: 
                    p.get_current_stat('def_disrupt') + p.get_current_stat('talent_defiq') + 
                    p.get_current_stat('ath_speed') + p.get_current_stat('def_contest'))
                
                # 失誤者: 對位球員 (這裡簡化為隨機持球者)
                loser = self.weighted_choice(off.on_court, lambda p: 
                    p.get_current_stat('off_handle') + p.get_current_stat('off_dribble'))
                
                off.stats['tov'] += 1
                loser.game_stats['tov'] += 1
                
                defe.stats['stl'] += 1
                stealer.game_stats['stl'] += 1
                
                self.log_debug(f"[後場抄截] {stealer.name} 抄截 {loser.name}")
                return (back_t, f"後場被抄截({stealer.name})", "switch")

        if back_t < 1.0:
            runner = max(off.on_court, key=lambda x: x.get_current_stat('ath_speed') + x.get_current_stat('off_dribble'))
            chaser = max(defe.on_court, key=lambda x: x.get_current_stat('ath_speed') + x.get_current_stat('talent_defiq'))
            
            off_s = sum(runner.get_current_stat(k) for k in ['ath_strength','ath_speed','ath_jump','shot_touch','shot_release','talent_offiq','talent_luck','off_move','off_dribble'])
            def_s = sum(chaser.get_current_stat(k) for k in ['ath_strength','ath_speed','ath_jump','shot_touch','shot_release','talent_defiq','talent_luck','def_contest','def_disrupt'])
            
            base_succ = random.uniform(0.3, 1.0)
            mod_succ = (off_s - def_s) * 0.005
            final_succ = min(1.0, base_succ + mod_succ)
            
            roll_goal = random.random()
            is_goal = roll_goal <= final_succ
            
            off_iq = runner.get_current_stat('talent_offiq')
            def_iq = chaser.get_current_stat('talent_defiq')
            foul_prob = max(0.001, 0.01 + (off_iq - def_iq) * 0.01)
            roll_foul = random.random()
            is_foul = roll_foul <= foul_prob
            
            msg = f"快攻({runner.name})"
            pts = 0
            if is_goal:
                pts = 2
                off.stats['pts'] += 2
                off.stats['fga'] += 1
                off.stats['fgm'] += 1
                
                runner.game_stats['pts'] += 2
                runner.game_stats['fga'] += 1
                runner.game_stats['fgm'] += 1
                
                if is_foul: 
                    pts += self.shoot_ft(off, runner, 1)
                    msg += " 進算加罰"
                else: msg += " 得分"
            else:
                off.stats['fga'] += 1
                runner.game_stats['fga'] += 1
                if is_foul:
                    pts += self.shoot_ft(off, runner, 2)
                    msg += " 犯規罰球"
                else: msg += " 失敗"
            
            off.score += pts
            return (back_t, msg, "switch")

        # 前場邏輯
        team_spd = off.get_team_stat_sum(off.on_court, ['ath_speed', 'talent_offiq', 'off_pass'])
        min_ft = max(4.0, 14.0 - (team_spd / 500.0))
        max_ft = max(min_ft + 1, 24.0 - back_t)
        front_t = random.uniform(min_ft, max_ft)
        total_t = back_t + front_t
        
        quality = (7.0 - front_t) * 0.01
        
        off_sp = off.get_team_stat_sum(off.on_court, ['off_move', 'talent_offiq'])
        def_sp = defe.get_team_stat_sum(defe.on_court, ['off_move', 'talent_defiq'])
        spacing = (off_sp - def_sp) / def_sp if def_sp > 0 else 0
        spacing = max(0.25, min(1.0, spacing))
        
        # [Spec v1.4] 投籃判定前先決定是否是 3分球 (影響出手者權重)
        rng = off.get_team_stat_sum(off.on_court, ['shot_range'])
        threshold = 1.0 / (rng / 100.0) if rng > 0 else 999
        is_3pt = random.random() > threshold

        # [Spec v1.4] 決定出手者 (Shooter) - 權重分配
        def shooter_weight(p):
            # 基礎權重 (Off_Total)
            w = sum(p.get_current_stat(k) for k in ATTR_OFF_13)
            # 特殊加成
            if is_3pt:
                w += (p.get_current_stat('shot_release') + p.get_current_stat('shot_range') + p.get_current_stat('off_move')) * 2
            # 戰術加成
            if p.role == "Star": w *= 1.5
            elif p.role == "Starter": w *= 1.2
            return w

        shooter = self.weighted_choice(off.on_court, shooter_weight)
        
        # 封蓋判定 (對位防守者)
        # 這裡簡化對位: 假設防守方同位置的人來防
        defender = next((d for d in defe.on_court if d.current_court_pos == shooter.current_court_pos), random.choice(defe.on_court))

        if spacing <= 0.5:
            base_blk = 0.01
            if spacing < 0: base_blk += 0.05
            
            trig_prob = base_blk
            if random.random() <= trig_prob:
                off_p = sum(shooter.get_current_stat(k) for k in ['ath_strength','ath_jump','talent_offiq'])
                def_p = sum(defender.get_current_stat(k) for k in ['ath_strength','ath_jump','def_contest','talent_defiq'])
                ratio = off_p / def_p if def_p > 0 else 1.0
                
                blk_success_prob = 1.0 / (1.0 + ratio**2)
                
                if random.random() <= blk_success_prob:
                    # [Spec v1.4] 封蓋歸屬
                    defe.stats['blk'] += 1
                    defender.game_stats['blk'] += 1
                    
                    off.stats['fga'] += 1
                    shooter.game_stats['fga'] += 1
                    if is_3pt:
                        off.stats['3pa'] += 1
                        shooter.game_stats['3pa'] += 1
                        
                    return (total_t, f"被封蓋({defender.name})", "switch")

        # 前場抄截
        off_ball = off.get_team_stat_sum(off.on_court, ['off_dribble', 'off_handle', 'off_pass'])
        def_steal = defe.get_team_stat_sum(defe.on_court, ['ath_speed', 'def_disrupt', 'talent_defiq'])
        
        steal_prob = 0.01 + (def_steal - off_ball) * 0.001
        if random.random() <= steal_prob:
            # [Spec v1.4] 抄截歸屬
            stealer = self.weighted_choice(defe.on_court, lambda p: 
                p.get_current_stat('def_disrupt') + p.get_current_stat('talent_defiq') + 
                p.get_current_stat('ath_speed') + p.get_current_stat('def_contest'))
            
            # 對位失誤
            loser = next((o for o in off.on_court if o.current_court_pos == stealer.current_court_pos), random.choice(off.on_court))
            
            off.stats['tov'] += 1
            loser.game_stats['tov'] += 1
            defe.stats['stl'] += 1
            stealer.game_stats['stl'] += 1
            
            return (total_t, f"前場被抄截({stealer.name})", "switch")

        # 投籃命中判定
        off_tot = off.get_team_stat_sum(off.on_court, ATTR_OFF_13)
        def_tot = defe.get_team_stat_sum(defe.on_court, ATTR_DEF_12)
        
        base_rate = (0.40 + (off_tot - def_tot) / def_tot) if def_tot > 0 else 0.4
        final_rate = base_rate * (1 + spacing*0.1) * (1 + quality)
        
        is_hit = random.random() <= final_rate
        
        off_iq = off.get_team_stat_sum(off.on_court, ['talent_offiq'])
        def_iq = defe.get_team_stat_sum(defe.on_court, ['talent_defiq'])
        foul_prob = max(0.0, min(1.0, (off_iq - def_iq) / def_iq if def_iq > 0 else 0))
        is_foul = random.random() <= foul_prob
        
        msg = f"投籃({'3分' if is_3pt else '2分'})"
        
        # 記錄出手數據
        off.stats['fga'] += 1
        shooter.game_stats['fga'] += 1
        if is_3pt: 
            off.stats['3pa'] += 1
            shooter.game_stats['3pa'] += 1
        
        if is_hit:
            pts = 3 if is_3pt else 2
            msg += f" {shooter.name}命中"
            
            off.stats['pts'] += pts
            off.stats['fgm'] += 1
            shooter.game_stats['pts'] += pts
            shooter.game_stats['fgm'] += 1
            
            if is_3pt: 
                off.stats['3pm'] += 1
                shooter.game_stats['3pm'] += 1
            
            # [Spec v1.4] 助攻判定 (固定順序 C->PF->SF->SG->PG)
            team_stat = off.get_team_stat_sum(off.on_court, ['talent_offiq', 'off_handle', 'off_pass', 'off_move'])
            luck_sum = off.get_team_stat_sum(off.on_court, ['talent_luck'])
            assist_coeff = luck_sum if luck_sum > 0 else 1
            ast_prob = (team_stat / assist_coeff) * 0.1 
            
            if random.random() <= ast_prob:
                candidates = [p for p in off.on_court if p != shooter]
                if candidates:
                    # 計算權重
                    cand_weights = {p: p.get_current_stat('off_handle') + p.get_current_stat('off_pass') + p.get_current_stat('talent_offiq') for p in candidates}
                    total_w = sum(cand_weights.values())
                    
                    # 固定順序判定
                    pos_priority = ["C", "PF", "SF", "SG", "PG"]
                    # 依照位置順序排序 candidates
                    sorted_cands = sorted(candidates, key=lambda x: pos_priority.index(x.current_court_pos) if x.current_court_pos in pos_priority else -1)
                    
                    r = random.random()
                    cum = 0.0
                    passer = sorted_cands[-1] # default
                    
                    for p in sorted_cands:
                        ratio = cand_weights[p] / total_w if total_w > 0 else 0
                        cum += ratio
                        if r <= cum:
                            passer = p
                            break
                    
                    off.stats['ast'] += 1
                    passer.game_stats['ast'] += 1
                    msg += f"(助攻:{passer.name})"
            
            if is_foul:
                msg += " [And-1]"
                pts += self.shoot_ft(off, shooter, 1)
            
            off.score += pts
            return (total_t, msg, "switch")
        else:
            # 沒進
            if is_foul:
                pts = self.shoot_ft(off, shooter, 3 if is_3pt else 2)
                off.score += pts
                return (total_t, f"{msg} 沒進但犯規(罰球+{pts})", "switch")
            else:
                # 籃板判定
                off_reb_stat = off.get_team_stat_sum(off.on_court, ['talent_offiq', 'def_rebound', 'def_boxout'])
                def_reb_stat = defe.get_team_stat_sum(defe.on_court, ['talent_defiq', 'def_rebound', 'def_boxout'])
                
                def_reb_rate = 0.10 + def_reb_stat / (off_reb_stat + def_reb_stat)
                
                if random.random() <= def_reb_rate:
                    # [Spec v1.4] 防守籃板歸屬
                    # 權重: 力量+速度+跑位 + (身高+彈跳+籃板+卡位)*1.5 + 防守智商
                    rebounder = self.weighted_choice(defe.on_court, lambda p:
                        p.get_current_stat('ath_strength') + p.get_current_stat('ath_speed') + p.get_current_stat('off_move') +
                        (p.height + p.get_current_stat('ath_jump') + p.get_current_stat('def_rebound') + p.get_current_stat('def_boxout')) * 1.5 +
                        p.get_current_stat('talent_defiq')
                    )
                    defe.stats['dreb'] += 1
                    rebounder.game_stats['dreb'] += 1
                    return (total_t, f"{msg} 沒進(防守籃板:{rebounder.name})", "switch")
                else:
                    # [Spec v1.4] 進攻籃板歸屬
                    rebounder = self.weighted_choice(off.on_court, lambda p:
                        p.get_current_stat('ath_strength') + p.get_current_stat('ath_speed') + p.get_current_stat('off_move') +
                        (p.height + p.get_current_stat('ath_jump') + p.get_current_stat('def_rebound') + p.get_current_stat('def_boxout')) * 1.5 +
                        p.get_current_stat('talent_offiq')
                    )
                    off.stats['oreb'] += 1
                    rebounder.game_stats['oreb'] += 1
                    return (total_t, f"{msg} 沒進(進攻籃板:{rebounder.name})", "keep")

    def shoot_ft(self, team, p, count):
        made = 0
        for _ in range(count):
            team.stats['fta'] += 1
            p.game_stats['fta'] += 1
            
            base = random.uniform(0.40, 0.95)
            bonus = (p.get_current_stat('talent_luck') + p.get_current_stat('shot_touch')) * 0.0001
            
            final_prob = base + bonus
            m = random.random() <= final_prob
            
            if m: 
                made += 1
                team.stats['ftm'] += 1
                p.game_stats['ftm'] += 1
                p.game_stats['pts'] += 1
        return made

    def print_team_stats(self):
        print("\n" + "="*60)
        print("📊 團隊數據統計 (Team Stats)")
        print("="*60)
        
        print(f"{'項目':<12} | {'Home':<15} | {'Away':<15}")
        print("-" * 60)
        
        h, a = self.home.stats, self.away.stats
        
        h_fg_pct = h['fgm']/h['fga'] if h['fga']>0 else 0
        a_fg_pct = a['fgm']/a['fga'] if a['fga']>0 else 0
        h_3p_pct = h['3pm']/h['3pa'] if h['3pa']>0 else 0
        a_3p_pct = a['3pm']/a['3pa'] if a['3pa']>0 else 0
        h_ft_pct = h['ftm']/h['fta'] if h['fta']>0 else 0
        a_ft_pct = a['ftm']/a['fta'] if a['fta']>0 else 0

        rows = [
            ("得分 (PTS)", h['pts'], a['pts']),
            ("投籃 (FG)", f"{h['fgm']}/{h['fga']} ({h_fg_pct:.1%})", f"{a['fgm']}/{a['fga']} ({a_fg_pct:.1%})"),
            ("三分 (3PT)", f"{h['3pm']}/{h['3pa']} ({h_3p_pct:.1%})", f"{a['3pm']}/{a['3pa']} ({a_3p_pct:.1%})"),
            ("罰球 (FT)", f"{h['ftm']}/{h['fta']} ({h_ft_pct:.1%})", f"{a['ftm']}/{a['fta']} ({a_ft_pct:.1%})"),
            ("進攻籃板 (OR)", h['oreb'], a['oreb']),
            ("防守籃板 (DR)", h['dreb'], a['dreb']),
            ("總籃板 (REB)", h['oreb']+h['dreb'], a['oreb']+a['dreb']),
            ("助攻 (AST)", h['ast'], a['ast']),
            ("抄截 (STL)", h['stl'], a['stl']),
            ("封蓋 (BLK)", h['blk'], a['blk']),
            ("失誤 (TOV)", h['tov'], a['tov']),
            (" (團隊失誤)", h['team_tov'], a['team_tov'])
        ]

        for label, h_val, a_val in rows:
            print(f"{label:<12} | {str(h_val):<15} | {str(a_val):<15}")
        print("-" * 60)
        print(f"總回合數 (Poss): {self.possessions}")
        print("="*60)

    def print_player_stats(self):
        print("\n" + "="*80)
        print("🏃 球員詳細數據 (Player Stats)")
        print("="*80)
        
        for team in [self.home, self.away]:
            print(f"\n[{team.name}]")
            # 擴充顯示欄位: PTS, REB, AST, STL, BLK
            print(f"{'Pos':<4} | {'Name':<18} | {'Min':<5} | {'PTS':<3} | {'REB':<3} | {'AST':<3} | {'STL':<3} | {'BLK':<3} | {'TOV':<3} | {'FG':<8}")
            print("-" * 90)
            
            sorted_roster = sorted(team.roster, key=lambda x: x.minutes_played, reverse=True)
            
            for p in sorted_roster:
                gs = p.game_stats
                reb = gs['oreb'] + gs['dreb']
                fg_str = f"{gs['fgm']}/{gs['fga']}"
                print(f"{p.pos:<4} | {p.name:<18} | {p.minutes_played:<5.1f} | {gs['pts']:<3} | {reb:<3} | {gs['ast']:<3} | {gs['stl']:<3} | {gs['blk']:<3} | {gs['tov']:<3} | {fg_str:<8}")
        print("="*80)

# ==========================================
# 3. 主程式
# ==========================================
def simulate_match():
    app = create_app()
    with app.app_context():
        print("🏗️ 正在準備比賽隊伍...")
        home_roster = create_team_roster("Home")
        away_roster = create_team_roster("Away")
        
        engine = MatchEngine(Team("Home", home_roster), Team("Away", away_roster))
        engine.run()

if __name__ == "__main__":
    from terminal import clear_terminal
    clear_terminal()
    simulate_match()