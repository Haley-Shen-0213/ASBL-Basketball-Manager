# app/services/match_engine/core.py

from typing import Dict, List, Optional, Tuple, Union
import math

from .structures import EngineTeam, EnginePlayer, MatchState, MatchResult
from .utils.calculator import Calculator
from .utils.rng import rng
from .systems.stamina import StaminaSystem
from .systems.substitution import SubstitutionSystem
from .systems.attribution import AttributionSystem

class MatchEngine:
    """
    ASBL 比賽引擎核心 (Level 4 - Phase 2 Final)
    對應規格書: Match Engine Specification v1.8
    
    [Phase 2 Updates]
    - 整合 Pace 計算 (Record Possession)。
    - 整合快攻效率統計 (Record Fastbreak)。
    - 輸出包含進階數據的 MatchResult。
    """

    def __init__(self, home_team: EngineTeam, away_team: EngineTeam, config: Dict, game_id: str = "SIM_GAME"):
        self.home_team = home_team
        self.away_team = away_team
        self.config = config
        self.game_id = game_id
        
        # 1. 初始化比賽狀態
        general_config = config.get('match_engine', {}).get('general', {})
        self.quarter_length = general_config.get('quarter_length', 720)
        self.ot_length = general_config.get('ot_length', 300)
        
        self.state = MatchState(time_remaining=float(self.quarter_length))
        
        # 2. 執行賽前準備
        self._initialize_match()
        
        # 3. 初始化 PBP Logs
        self.pbp_logs = []

    def _initialize_match(self):
        """賽前準備流程"""
        for team in [self.home_team, self.away_team]:
            self._calculate_all_positional_scores(team)
            self._determine_best_five(team)
            self._distribute_team_minutes(team)
            self._set_initial_lineup(team)

    def _calculate_all_positional_scores(self, team: EngineTeam):
        """[Spec 1.1] 計算位置評分"""
        scoring_rules = self.config.get('match_engine', {}).get('positional_scoring', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})
        positions = ["C", "PF", "SF", "SG", "PG"]

        for player in team.roster:
            player.pos_scores = {}
            for pos in positions:
                rule_attrs = scoring_rules.get(pos, [])
                score = Calculator.get_player_attr_sum(player, rule_attrs, attr_pools)
                player.pos_scores[pos] = score

    def _determine_best_five(self, team: EngineTeam):
        """[Spec 1.1] 標記最強陣容"""
        positions = ["C", "PF", "SF", "SG", "PG"]
        best_five = [None] * 5
        taken_ids = set()
        candidates = []
        
        for p in team.roster:
            for i, pos in enumerate(positions):
                candidates.append((p.pos_scores[pos], i, p))
        
        candidates.sort(key=lambda x: x[0], reverse=True)

        for score, pos_idx, player in candidates:
            if best_five[pos_idx] is None and player.id not in taken_ids:
                best_five[pos_idx] = player
                taken_ids.add(player.id)
            if all(best_five): break
        
        if not all(best_five):
            remaining = [p for p in team.roster if p.id not in taken_ids]
            for i in range(5):
                if best_five[i] is None and remaining:
                    p = remaining.pop(0)
                    best_five[i] = p
                    taken_ids.add(p.id)
        team.best_five = best_five

    def _distribute_team_minutes(self, team: EngineTeam):
        """[Spec 1.4 & 2.6] 上場時間分配"""
        min_config = self.config.get('minutes_distribution', {})
        total_minutes = min_config.get('total_minutes', 240)
        role_config = min_config.get('roles', {})

        total_base = 0.0
        active_players = []
        for player in team.roster:
            role_data = role_config.get(player.role, role_config.get('Bench'))
            total_base += role_data.get('base', 0)
            active_players.append(player)

        remaining_time = max(0, total_minutes - total_base)
        
        total_weight = 0.0
        player_weights = {}
        for player in active_players:
            role_data = role_config.get(player.role, role_config.get('Bench'))
            min_w = role_data.get('min_w', 0)
            max_w = role_data.get('max_w', 10)
            w = rng.get_float(float(min_w), float(max_w))
            player_weights[player.id] = w
            total_weight += w

        unit_value = remaining_time / total_weight if total_weight > 0 else 0
        allocated_sum = 0.0

        for i, player in enumerate(active_players):
            role_data = role_config.get(player.role, role_config.get('Bench'))
            base = role_data.get('base', 0)
            raw = base + (player_weights[player.id] * unit_value)
            final = math.floor(raw * 10) / 10.0
            
            if i == len(active_players) - 1:
                diff = total_minutes - allocated_sum
                if diff > 0: final = diff
            
            allocated_sum += final
            player.target_seconds = final * 60.0
            player.seconds_played = 0.0

    def _set_initial_lineup(self, team: EngineTeam):
        """[Spec 1.2] 決定先發陣容"""
        positions = ["PG", "SG", "SF", "PF", "C"]
        starters = [None] * 5
        taken_ids = set()

        def try_fill(player):
            my_scores = []
            for i, pos in enumerate(positions):
                if starters[i] is None:
                    my_scores.append((player.pos_scores[pos], i))
            my_scores.sort(key=lambda x: x[0], reverse=True)
            if my_scores:
                _, idx = my_scores[0]
                starters[idx] = player
                taken_ids.add(player.id)
                player.position = positions[idx]
                return True
            return False

        for role in ['Star', 'Starter']:
            for p in [x for x in team.roster if x.role == role]:
                try_fill(p)
        
        remaining = [p for p in team.roster if p.id not in taken_ids]
        for i, pos in enumerate(positions):
            if starters[i] is None:
                best_p = max(remaining, key=lambda p: p.pos_scores[pos], default=None)
                if best_p:
                    starters[i] = best_p
                    best_p.position = pos
                    taken_ids.add(best_p.id)
                    remaining.remove(best_p)

        team.on_court = [p for p in starters if p]
        team.bench = [p for p in team.roster if p.id not in taken_ids]

    def _resolve_formula(self, formula: Union[str, List[str]], attr_pools: Dict) -> List[str]:
        if isinstance(formula, str):
            return attr_pools.get(formula, [])
        return formula

    # =========================================================================
    # Simulation Loop
    # =========================================================================

    def simulate(self) -> MatchResult:
        """
        [Spec v1.8] 執行整場模擬
        """
        # 1. 跳球
        jb_winner = self._jump_ball()
        jb_loser = self.home_team.id if jb_winner == self.away_team.id else self.away_team.id
        
        # 2. 節次球權
        q_possessions = {1: jb_winner, 2: jb_loser, 3: jb_loser, 4: jb_winner}

        # 3. 正規賽
        for q in range(1, 5):
            self.state.quarter = q
            self.state.time_remaining = float(self.quarter_length)
            self.state.possession = q_possessions[q]
            self.pbp_logs.append(f"=== Q{q} Start (Possession: {self.state.possession}) ===")
            self._simulate_quarter()

        # 4. 延長賽
        while self.home_team.score == self.away_team.score:
            self.state.quarter += 1
            self.state.time_remaining = float(self.ot_length)
            ot_winner = self._jump_ball()
            self.state.possession = ot_winner
            self.pbp_logs.append(f"=== OT{self.state.quarter-4} Start ===")
            self._simulate_quarter()

        self.state.is_over = True
        
        # 5. 計算 Pace (Possessions per 48 min)
        total_possessions = self.home_team.stat_possessions + self.away_team.stat_possessions
        total_minutes = self.state.game_time_elapsed / 60.0
        pace = 0.0
        if total_minutes > 0:
            # Pace = 48 * (Total Poss / 2) / Minutes ? 
            # Standard Pace = (Team Poss + Opp Poss) / 2 * (48 / Minutes)
            pace = (total_possessions / 2.0) * (48.0 / total_minutes)

        # 6. 回傳結果
        return MatchResult(
            game_id=self.game_id,
            home_team_id=self.home_team.id,
            away_team_id=self.away_team.id,
            home_score=self.home_team.score,
            away_score=self.away_team.score,
            is_ot=(self.state.quarter > 4),
            total_quarters=self.state.quarter,
            pbp_log=self.pbp_logs,
            # Phase 2 Data
            pace=pace,
            home_possessions=self.home_team.stat_possessions,
            away_possessions=self.away_team.stat_possessions,
            home_fb_made=self.home_team.stat_fb_made,
            home_fb_attempt=self.home_team.stat_fb_attempt,
            away_fb_made=self.away_team.stat_fb_made,
            away_fb_attempt=self.away_team.stat_fb_attempt
        )

    def _jump_ball(self) -> str:
        """(Spec 1.5) 跳球"""
        jb_config = self.config.get('match_engine', {}).get('jump_ball', {})
        attrs = jb_config.get('participant_formula', ['height', 'ath_jump', 'talent_offiq'])
        
        def get_jumper(team):
            c = [p for p in team.on_court if p.position == 'C']
            return c[0] if c else max(team.on_court, key=lambda p: p.pos_scores.get('C', 0))

        h_jumper = get_jumper(self.home_team)
        a_jumper = get_jumper(self.away_team)
        
        h_score = Calculator.get_player_attr_sum(h_jumper, attrs)
        a_score = Calculator.get_player_attr_sum(a_jumper, attrs)
        total = h_score + a_score or 1
        
        if rng.decision(h_score / total):
            self.pbp_logs.append(f"Jump Ball: {self.home_team.name} wins")
            return self.home_team.id
        else:
            self.pbp_logs.append(f"Jump Ball: {self.away_team.name} wins")
            return self.away_team.id

    def _simulate_quarter(self):
        """
        模擬單節比賽流程
        [Phase 2] 加入 Possession 記錄邏輯
        """
        is_opening = (self.state.quarter == 1)
        
        # 標記是否為新的一波球權 (節次開始或攻守交換後)
        is_new_possession = True 

        while self.state.time_remaining > 0:
            self._check_substitutions()
            
            # 1. 確定當前進攻方
            if self.state.possession == self.home_team.id:
                off_team = self.home_team
            else:
                off_team = self.away_team
            
            # 2. 若是新球權，記錄之 (Pace Calculation)
            if is_new_possession:
                AttributionSystem.record_possession(off_team)
                is_new_possession = False

            # 3. 執行回合
            elapsed, desc, keep = self._simulate_possession(is_opening)
            
            self.state.time_remaining -= elapsed
            self.state.game_time_elapsed += elapsed
            
            # Update Stamina & Time
            for team in [self.home_team, self.away_team]:
                for p in team.on_court:
                    p.seconds_played += elapsed
                    StaminaSystem.update_stamina(p, elapsed, True, self.config)
                for p in team.bench:
                    StaminaSystem.update_stamina(p, elapsed, False, self.config)
            
            self.pbp_logs.append(f"[{self.state.quarter}Q {self.state.time_remaining:.1f}] {desc}")
            
            # 4. 攻守交換判定
            if not keep:
                # 交換球權
                self.state.possession = self.away_team.id if self.state.possession == self.home_team.id else self.home_team.id
                is_new_possession = True # 下一回合為新球權
            else:
                # 進攻籃板，維持球權 (不計為新 Possession)
                is_new_possession = False
            
            is_opening = False
        
        if self.state.quarter == 2:
            StaminaSystem.apply_halftime_recovery(self.home_team.roster, self.config)
            StaminaSystem.apply_halftime_recovery(self.away_team.roster, self.config)

    def _check_substitutions(self):
        """換人檢查"""
        is_clutch = (self.state.quarter >= 4 and self.state.time_remaining <= 180.0)
        if is_clutch: return 
        
        for team in [self.home_team, self.away_team]:
            logs = SubstitutionSystem.check_auto_substitution(
                team, self.state.quarter, self.state.time_remaining, self.config
            )
            self.pbp_logs.extend(logs)

    def _simulate_possession(self, is_opening: bool) -> Tuple[float, str, bool]:
        if self.state.possession == self.home_team.id:
            off_team, def_team = self.home_team, self.away_team
        else:
            off_team, def_team = self.away_team, self.home_team

        # 1. Backcourt
        elapsed_bc, res, desc = self._run_backcourt(off_team, def_team, is_opening)
        if res != 'frontcourt': return elapsed_bc, desc, False

        # 2. Frontcourt
        elapsed_fc, res, desc, ctx = self._run_frontcourt(off_team, def_team, elapsed_bc)
        total_elapsed = elapsed_bc + elapsed_fc
        if res != 'shooting': return total_elapsed, desc, False

        # 3. Shooting
        desc_shoot, keep = self._run_shooting(off_team, def_team, ctx)
        return total_elapsed, desc_shoot, keep

    def _run_backcourt(self, off_team: EngineTeam, def_team: EngineTeam, is_opening: bool):
        """(Spec 3) 後場"""
        bc_config = self.config.get('match_engine', {}).get('backcourt', {})
        params = bc_config.get('params', {})
        formulas = bc_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})

        # Calc Time
        off_sum = Calculator.get_team_attr_sum(off_team.on_court[:3], self._resolve_formula(formulas.get('off_sum', []), attr_pools), attr_pools)
        def_sum = Calculator.get_team_attr_sum(def_team.on_court[:3], self._resolve_formula(formulas.get('def_sum', []), attr_pools), attr_pools)
        
        if is_opening:
            final_time = params.get('opening_seconds', 2.0)
        else:
            base = rng.get_float(params.get('time_base_min', 1.0), params.get('time_base_max', 8.0))
            final_time = max(0.5, min(8.1, base + (def_sum - off_sum) * params.get('time_coeff', 0.008)))

        # Events
        if final_time > params.get('violation_threshold', 8.0):
            AttributionSystem.record_team_turnover(off_team)
            return final_time, 'turnover', f"{off_team.name} 8-sec Violation"
        
        if final_time > params.get('steal_threshold', 3.0):
            prob = params.get('steal_base_prob', 0.01) + (def_sum - off_sum) * params.get('steal_bonus_coeff', 0.001)
            if rng.decision(prob):
                stealer = AttributionSystem.determine_stealer(def_team, self.config)
                AttributionSystem.record_steal(stealer, off_team)
                return final_time, 'turnover', f"{def_team.name} {stealer.name} Backcourt Steal"
        
        if final_time < params.get('fastbreak_threshold', 1.0):
            return self._run_fastbreak(off_team, def_team, final_time)
        
        return final_time, 'frontcourt', "Advance"

    def _run_frontcourt(self, off_team: EngineTeam, def_team: EngineTeam, elapsed_bc: float):
        """(Spec 4) 前場"""
        fc_config = self.config.get('match_engine', {}).get('frontcourt', {})
        params = fc_config.get('params', {})
        formulas = fc_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})
        
        ctx = {'quality': 0.0, 'spacing': 0.0}
        
        # Time & Quality
        red_attr = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('time_reduction', []), attr_pools), attr_pools)
        reduction = (red_attr / 1000.0) * 0.5
        min_time = max(4.0, 4.0 - reduction)
        elapsed = rng.get_float(min_time, max(min_time+1, 24.0-elapsed_bc))
        if elapsed < 7.0: ctx['quality'] = (7.0 - elapsed) * 0.01
        
        # Spacing
        off_sp = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('spacing_off', []), attr_pools), attr_pools)
        def_sp = Calculator.get_team_attr_sum(def_team.on_court, self._resolve_formula(formulas.get('spacing_def', []), attr_pools), attr_pools) or 1
        sp_bonus = max(-1.0, min(1.0, (off_sp - def_sp)/def_sp + rng.get_float(-0.1, 0.1)))
        ctx['spacing'] = sp_bonus

        # Block (Spec 4.3)
        if sp_bonus <= 0.5:
            blk_prob = 0.01 + (0.05 if sp_bonus < 0 else 0)
            if rng.decision(blk_prob):
                # Block Success Check
                trigger_off_f = self._resolve_formula(formulas.get('block', {}).get('formulas', {}).get('trigger_off', []), attr_pools)
                trigger_def_f = self._resolve_formula(formulas.get('block', {}).get('formulas', {}).get('trigger_def', []), attr_pools)
                
                blocker = AttributionSystem.determine_rebounder(off_team, def_team, True, self.config) 
                shooter = AttributionSystem.determine_shooter(off_team, False, self.config) 
                
                AttributionSystem.record_block(blocker, shooter)
                return elapsed, 'turnover', f"{def_team.name} Block", ctx

        # Steal (Spec 4.4)
        stl_prob = 0.01
        if rng.decision(stl_prob):
            stealer = AttributionSystem.determine_stealer(def_team, self.config)
            AttributionSystem.record_steal(stealer, off_team)
            return elapsed, 'turnover', f"{def_team.name} Frontcourt Steal", ctx

        return elapsed, 'shooting', "Shot Attempt", ctx

    def _run_fastbreak(self, off_team: EngineTeam, def_team: EngineTeam, elapsed: float) -> Tuple[float, str, str]:
        """
        (Spec 3.5) 快攻
        [Phase 2] 整合 record_fastbreak_event
        """
        fb_config = self.config.get('match_engine', {}).get('backcourt', {}).get('fastbreak', {})
        formulas = fb_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})
        
        # 簡化實作: 隨機選人 (或可改為 Spec 邏輯)
        runner = off_team.on_court[0]
        chaser = def_team.on_court[0]
        
        # 成功率
        off_power = Calculator.get_player_attr_sum(runner, self._resolve_formula(formulas.get('off_power', []), attr_pools), attr_pools)
        def_power = Calculator.get_player_attr_sum(chaser, self._resolve_formula(formulas.get('def_power', []), attr_pools), attr_pools)
        
        success_prob = 0.5 + (off_power - def_power) * 0.005
        is_success = rng.decision(success_prob)
        
        # [Phase 2] 記錄快攻事件
        AttributionSystem.record_fastbreak_event(off_team, runner, is_success)
        
        if is_success:
            AttributionSystem.record_score(off_team, runner, 2, False)
            return elapsed, 'score', f"{off_team.name} {runner.name} Fastbreak Score"
        else:
            AttributionSystem.record_rebound(chaser, False)
            return elapsed, 'turnover', f"{off_team.name} {runner.name} Fastbreak Stopped by {chaser.name}"

    def _run_shooting(self, off_team: EngineTeam, def_team: EngineTeam, ctx: Dict) -> Tuple[str, bool]:
        """
        [Spec 5] 投籃結算
        """
        sht_config = self.config.get('match_engine', {}).get('shooting', {})
        params = sht_config.get('params', {})
        formulas = sht_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})

        # 1. Type
        range_sum = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('range_attr', []), attr_pools), attr_pools) or 1
        threshold = 1.0 / (range_sum / 100.0)
        is_3pt = rng.get_float(0.0, 1.0) > threshold
        points = 3 if is_3pt else 2
        base_rate = params.get('base_rate_3pt', 0.20) if is_3pt else params.get('base_rate_2pt', 0.40)

        # 2. Shooter
        shooter = AttributionSystem.determine_shooter(off_team, is_3pt, self.config)

        # 3. Hit Rate
        off_total = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('off_total', []), attr_pools), attr_pools)
        def_total = Calculator.get_team_attr_sum(def_team.on_court, self._resolve_formula(formulas.get('def_total', []), attr_pools), attr_pools) or 1
        
        stat_diff = (off_total - def_total) / def_total
        hit_rate = (base_rate + stat_diff) * (1 + ctx.get('spacing', 0)*0.1) * (1 + ctx.get('quality', 0))
        is_hit = rng.decision(hit_rate)

        # 4. Foul
        off_iq = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('foul_off_iq', []), attr_pools), attr_pools)
        def_iq = Calculator.get_team_attr_sum(def_team.on_court, self._resolve_formula(formulas.get('foul_def_iq', []), attr_pools), attr_pools) or 1
        foul_prob = max(0.01, (off_iq - def_iq) / def_iq)
        is_foul = rng.decision(foul_prob)
        
        log = ""
        keep = False

        if is_hit:
            AttributionSystem.record_score(off_team, shooter, points, is_3pt)
            log = f"{off_team.name} {shooter.name} {points}pt Good"
            
            # Assist
            ast_config = sht_config.get('assist', {})
            ast_formulas = ast_config.get('formulas', {})
            team_stat = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(ast_formulas.get('team_stat', []), attr_pools), attr_pools)
            luck_stat = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(ast_formulas.get('luck_stat', []), attr_pools), attr_pools) or 1
            
            ast_prob = (team_stat / (1.0/luck_stat)) * params.get('assist_prob_coeff', 0.1)
            
            if rng.decision(ast_prob):
                passer = AttributionSystem.determine_assist_provider(off_team, shooter, self.config)
                if passer:
                    AttributionSystem.record_assist(passer)
                    log += f" (Ast {passer.name})"
            
            if is_foul:
                fouler = rng.choice(def_team.on_court)
                AttributionSystem.record_foul(fouler)
                self._run_free_throw(off_team, shooter, 1)
                log += " (And-1)"
        else:
            AttributionSystem.record_attempt(shooter, is_3pt)
            log = f"{off_team.name} {shooter.name} {points}pt Miss"
            
            if is_foul:
                fouler = rng.choice(def_team.on_court)
                AttributionSystem.record_foul(fouler)
                ft_count = 3 if is_3pt else 2
                made = self._run_free_throw(off_team, shooter, ft_count)
                log += f" (Foul {made}/{ft_count})"
            else:
                # Rebound
                reb_config = sht_config.get('rebound', {})
                reb_formulas = reb_config.get('formulas', {})
                
                off_reb_attr = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(reb_formulas.get('off_attr', []), attr_pools), attr_pools)
                def_reb_attr = Calculator.get_team_attr_sum(def_team.on_court, self._resolve_formula(reb_formulas.get('def_attr', []), attr_pools), attr_pools)
                
                dr_prob = 0.10 + (def_reb_attr / (off_reb_attr + def_reb_attr or 1))
                
                if rng.decision(dr_prob):
                    rebounder = AttributionSystem.determine_rebounder(off_team, def_team, True, self.config)
                    AttributionSystem.record_rebound(rebounder, False)
                    log += f" (Reb {rebounder.name})"
                    keep = False
                else:
                    rebounder = AttributionSystem.determine_rebounder(off_team, def_team, False, self.config)
                    AttributionSystem.record_rebound(rebounder, True)
                    log += f" (Off Reb {rebounder.name})"
                    keep = True

        return log, keep

    def _run_free_throw(self, team: EngineTeam, shooter: EnginePlayer, count: int) -> int:
        made = 0
        ft_config = self.config.get('match_engine', {}).get('shooting', {}).get('ft', {})
        params = ft_config.get('params', {})
        formulas = ft_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})
        
        base = rng.get_float(params.get('base_min', 0.40), params.get('base_max', 0.95))
        bonus_formula = self._resolve_formula(formulas.get('bonus_attrs', ['talent_luck', 'shot_touch']), attr_pools)
        attr_sum = Calculator.get_player_attr_sum(shooter, bonus_formula, attr_pools)
        
        prob = min(0.99, max(0.01, base + attr_sum * params.get('attr_coeff', 0.0001)))

        for _ in range(count):
            if rng.decision(prob):
                AttributionSystem.record_free_throw(team, shooter, True)
                made += 1
            else:
                AttributionSystem.record_free_throw(team, shooter, False)
        return made