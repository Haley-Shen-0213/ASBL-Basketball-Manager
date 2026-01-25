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
    
    [Update 2026-01-16]
    - 新增: 正負值 (+/-) 統計
    - 新增: 回合時間 (Possession Time) 記錄
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
        
        # [修正] 讀取換人相關參數 (犯規上限 & 關鍵時刻閾值)
        sub_config = general_config.get('substitution', {})
        self.foul_limit = sub_config.get('foul_limit', 6)
        self.clutch_threshold = sub_config.get('clutch_time_threshold', 120.0)
        
        self.state = MatchState(time_remaining=float(self.quarter_length))
        
        # 2. 執行賽前準備
        self._initialize_match()
        
        # 3. 初始化 PBP Logs
        self.pbp_logs = []

    def _initialize_match(self):
        """賽前準備流程"""
        # [新增] Spec v2.1 Section 1.5 賽前身高修正 (必須在體力與評分計算前執行)
        self._apply_height_correction(self.home_team)
        self._apply_height_correction(self.away_team)

        for team in [self.home_team, self.away_team]:
            self._calculate_all_positional_scores(team)
            self._determine_best_five(team)
            self._distribute_team_minutes(team)
            self._set_initial_lineup(team)

    # [新增整個方法]
    def _apply_height_correction(self, team: EngineTeam):
        """
        [Spec v2.1 Section 1.5] 身高屬性修正 (Initial Height Correction)
        針對特定屬性進行基於身高的物理修正，此為永久性修正。
        """
        hc_config = self.config.get('match_engine', {}).get('height_correction', {})
        bonus_h = hc_config.get('bonus_threshold', 190)
        nerf_h = hc_config.get('nerf_threshold', 210)
        affected_attrs = hc_config.get('affected_attrs', {})

        for player in team.roster:
            h = getattr(player, 'height', 195)
            
            # 計算修正倍率因子
            # 公式: max(BONUS_H - h, min(NERF_H - h, 0))
            factor = max(bonus_h - h, min(nerf_h - h, 0))
            
            if factor == 0:
                continue

            # 應用修正
            for _, rule in affected_attrs.items():
                keys = rule.get('keys', [])
                coeff = rule.get('coeff', 0.0)
                multiplier = 1.0 + (factor * coeff)
                
                for key in keys:
                    original_val = getattr(player, key, 0)
                    if original_val > 0:
                        new_val = original_val * multiplier
                        # 確保數值邊界
                        new_val = max(1, min(999, new_val)) 
                        setattr(player, key, new_val)

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
            away_fb_attempt=self.away_team.stat_fb_attempt,
            # [New] 回合時間統計與平均值計算
            home_possession_history=self.home_team.stat_possession_history,
            away_possession_history=self.away_team.stat_possession_history,
            home_avg_seconds_per_poss=(self.home_team.stat_possession_seconds / self.home_team.stat_possessions) if self.home_team.stat_possessions > 0 else 0.0,
            away_avg_seconds_per_poss=(self.away_team.stat_possession_seconds / self.away_team.stat_possessions) if self.away_team.stat_possessions > 0 else 0.0,
            
            # =========== [FIX START] 補上違例數據 ===========
            home_violation_8s=self.home_team.stat_violation_8s,
            home_violation_24s=self.home_team.stat_violation_24s,
            away_violation_8s=self.away_team.stat_violation_8s,
            away_violation_24s=self.away_team.stat_violation_24s
            # =========== [FIX END] ========================
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
                off_team, def_team = self.home_team, self.away_team
            else:
                off_team, def_team = self.away_team, self.home_team
            
            # 2. 若是新球權，記錄之 (Pace Calculation)
            if is_new_possession:
                AttributionSystem.record_possession(off_team)
                is_new_possession = False

            # 3. 執行回合
            elapsed, desc, keep = self._simulate_possession(is_opening)
            
            # [New] 記錄回合消耗時間
            # 將該次進攻所花費的時間，歸屬給進攻方
            AttributionSystem.record_possession_time(off_team, elapsed)
            
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
        
        # 讀取時間設定
        gen_config = self.config.get('match_engine', {}).get('general', {})
        halftime_min = gen_config.get('stamina_recovery_halftime', 20.0)
        quarter_break_min = gen_config.get('stamina_recovery_quarter', 2.0)
        
        if self.state.quarter == 2:
            # 中場休息 (Q2 結束)
            self.pbp_logs.append(f"=== Halftime Break ({halftime_min} mins) ===")
            StaminaSystem.apply_rest(self.home_team.roster, halftime_min, self.config)
            StaminaSystem.apply_rest(self.away_team.roster, halftime_min, self.config)
            
        elif self.state.quarter in [1, 3]:
            # 節間休息 (Q1, Q3 結束)
            self.pbp_logs.append(f"=== Quarter Break ({quarter_break_min} mins) ===")
            StaminaSystem.apply_rest(self.home_team.roster, quarter_break_min, self.config)
            StaminaSystem.apply_rest(self.away_team.roster, quarter_break_min, self.config)

        # 3. 延長賽前休息 (Q4 結束平手, 或 OT 結束平手)
        # 邏輯: 若現在是 Q4 或 OT (Q>=4)，且分數平手，代表即將進入下一節，需要休息
        elif self.state.quarter >= 4 and self.home_team.score == self.away_team.score:
            self.pbp_logs.append(f"=== Overtime Break ({quarter_break_min} mins) ===")
            StaminaSystem.apply_rest(self.home_team.roster, quarter_break_min, self.config)
            StaminaSystem.apply_rest(self.away_team.roster, quarter_break_min, self.config)

    def _check_substitutions(self):
        """換人檢查"""
        # 判斷是否為關鍵時刻 (Q4 或 OT 的最後 2 分鐘)
        is_clutch = (self.state.quarter >= 4 and self.state.time_remaining <= self.clutch_threshold)
        
        if is_clutch:
            #  關鍵時刻：強制執行 Best 5 調度
            for team in [self.home_team, self.away_team]:
                logs = SubstitutionSystem.enforce_best_lineup(team, self.config)
                self.pbp_logs.extend(logs)
            return # 執行完強制調度後，依然不進行常規體力檢查
        
        # 非關鍵時刻：執行常規換人檢查 (體力/時間)
        for team in [self.home_team, self.away_team]:
            logs = SubstitutionSystem.check_auto_substitution(
                team, self.state.quarter, self.state.time_remaining, self.config
            )
            self.pbp_logs.extend(logs)

    def _simulate_possession(self, is_opening: bool) -> Tuple[float, str, bool]:
        """
        單一回合模擬
        更新 v2.4: 支援後場抄截後的「即時攻守交換」(Instant Transition)
        """
        # 1. 確定初始攻守方
        if self.state.possession == self.home_team.id:
            off_team, def_team = self.home_team, self.away_team
        else:
            off_team, def_team = self.away_team, self.home_team

        # ============================================================
        # Phase 1: Backcourt (後場)
        # ============================================================
        elapsed_bc, res, desc = self._run_backcourt(off_team, def_team, is_opening)
        
        # [Case A] 正常推進 -> 進入前場
        if res == 'frontcourt':
            pass # 繼續執行 Phase 2

        # [Case B] 普通失誤 (8秒/出界) -> 結束回合
        elif res == 'turnover':
            return elapsed_bc, desc, False

        # [Case C] 抄截後的轉換 (Steal Transition) [New v2.4]
        elif res in ['steal_fastbreak', 'steal_frontcourt']:
            # 這裡發生了「回合內攻守交換」
            # 原防守方 (def_team) 變成了 進攻方
            # 原進攻方 (off_team) 變成了 防守方
            # 1. 記錄防守方(現在的進攻方)的球權 (因為他們發動了快攻/反擊)
            AttributionSystem.record_possession(def_team)
            
            # 2. 處理快攻分支
            if res == 'steal_fastbreak':
                # 執行快攻 (注意參數順序互換)
                # [Update] 傳入 def_team 以計算 +/- (因為 def_team 現在是進攻方)
                elapsed_fb, fb_res, fb_desc = self._run_fastbreak(def_team, off_team, elapsed_bc)
                
                # 處理回傳的 keep 邏輯 (反轉)
                # 若快攻進球(keep=False)，我們希望下一回合球權給原進攻方(A)，而當前possession是A
                # 外層迴圈邏輯: if not keep: switch.
                # 若我們回傳 False -> switch -> 變 B 球權 (錯)
                # 若我們回傳 True -> no switch -> 變 A 球權 (對)
                # 結論: 抄截反擊的結果需要 invert keep
                
                # 特殊情況: 快攻失敗(被蓋/籃板)，回傳的是 turnover 嗎?
                # _run_fastbreak 回傳: ('score', desc) 或 ('turnover', desc)
                # 這裡的 turnover 代表防守成功(原攻方拿回球權/籃板)，相當於 keep=False (B沒拿到球)
                # 所以邏輯一致，直接回傳 True 即可讓 A 拿回球權?
                # 等等，_run_fastbreak 沒有回傳 keep，它回傳 (elapsed, type, desc)
                
                # 讓我們看 _run_fastbreak 的實作:
                # 進球 -> record_score -> return 'score'
                # 失敗 -> record_rebound(chaser) -> return 'turnover'
                
                if fb_res == 'score':
                    # 因為回傳 keep=True，主迴圈會誤以為是進攻籃板而不計數
                    # 所以這裡預先幫 off_team 記錄下一次的球權
                    AttributionSystem.record_possession(off_team)
                    return elapsed_fb, fb_desc, True # A 拿回球權
                else:
                    # 同上，off_team 獲得防守籃板，視為新回合開始
                    AttributionSystem.record_possession(off_team)
                    # 快攻失敗 (被 A 守住/抓板) -> A 拿回球權
                    return elapsed_fb, fb_desc, True

            # 3. 處理直接前場分支 (Skip Backcourt)
            elif res == 'steal_frontcourt':
                # 直接進入前場階段 (注意參數順序互換)
                # 時間繼承: 已經過了 elapsed_bc 秒
                elapsed_fc, fc_res, fc_desc, ctx = self._run_frontcourt(def_team, off_team, elapsed_bc)
                
                if fc_res == 'shooting':
                    shoot_desc, shoot_keep = self._run_shooting(def_team, off_team, ctx)
                    # 這裡 shoot_keep 是針對 def_team (現在的進攻方) 而言
                    # 如果 B 搶到進攻籃板 (True) -> 下一回合 B 繼續攻 -> possession 需切換為 B -> return False
                    # 如果 B 進球/被抓板 (False) -> 下一回合 A 攻 -> possession 維持 A -> return True
                    return elapsed_bc + elapsed_fc, shoot_desc, not shoot_keep
                else:
                    # 前場失誤 (def_team 失誤) -> off_team 拿回球權
                    # 手動補 off_team 球權
                    AttributionSystem.record_possession(off_team) # <--- 新增這行
                    # 前場失誤 (B 失誤) -> A 拿回球權
                    return elapsed_bc + elapsed_fc, fc_desc, True

        # ============================================================
        # Phase 2: Frontcourt (前場)
        # ============================================================
        elapsed_fc, res, desc, ctx = self._run_frontcourt(off_team, def_team, elapsed_bc)
        total_elapsed = elapsed_bc + elapsed_fc
        
        if res != 'shooting': 
            return total_elapsed, desc, False

        # ============================================================
        # Phase 3: Shooting (投籃)
        # ============================================================
        desc_shoot, keep = self._run_shooting(off_team, def_team, ctx)
        return total_elapsed, desc_shoot, keep

    def _run_backcourt(self, off_team: EngineTeam, def_team: EngineTeam, is_opening: bool):
        """
        (Spec 3) 後場階段
        更新 v2.3: 實作速度總和判定的攻守轉換
        """
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
            diff_mod = (def_sum - off_sum) * params.get('time_coeff', 0.008)
            
            # [New v2.4] 速度折扣
            spd_formula = formulas.get('backcourt_speed', ['ath_speed'])
            spd_sum_off = Calculator.get_team_attr_sum(off_team.on_court[:3], spd_formula, attr_pools)
            avg_spd_off = spd_sum_off / 3.0 if spd_sum_off > 0 else 50.0
            spd_sum_def = Calculator.get_team_attr_sum(def_team.on_court[:3], spd_formula, attr_pools)
            avg_spd_def = spd_sum_def / 3.0 if spd_sum_def > 0 else 50.0
            
            discount_coeff = params.get('speed_discount_coeff', 0.1)
            discount_coeff_def = params.get('speed_discount_coeff_def', 0.5)
            discount_off = rng.get_float(0.0, avg_spd_off * discount_coeff)
            discount_def = rng.get_float(0.0, avg_spd_def * discount_coeff) * discount_coeff_def
            
            final_time = base + diff_mod - discount_off + discount_def
            
            # 物理下限
            min_limit = params.get('min_time_limit', 0.5)
            final_time = max(min_limit, final_time)

        # 2. 8秒違例判定 (修改記錄方法)
        if final_time > params.get('violation_threshold', 8.0):
            # [Modified] 改用專屬的 8秒違例記錄方法
            AttributionSystem.record_8sec_violation(off_team)
            final_time = 8.0
            return final_time, 'turnover', f"{off_team.name} 8-sec Violation"
        
        # [Modified] 抄截判定
        if final_time > params.get('steal_threshold', 3.0):
            prob = params.get('steal_base_prob', 0.01) + (def_sum - off_sum) * params.get('steal_bonus_coeff', 0.001)
            
            if rng.decision(prob):
                stealer = AttributionSystem.determine_stealer(def_team, self.config)
                AttributionSystem.record_steal(stealer, off_team)
                
                # [New v2.4] 攻守轉換判定 (Transition Decision)
                # 1. 計算雙方全隊速度總和
                spd_formula = formulas.get('team_speed_sum', ['ath_speed'])
                off_spd_sum = Calculator.get_team_attr_sum(off_team.on_court, spd_formula, attr_pools)
                def_spd_sum = Calculator.get_team_attr_sum(def_team.on_court, spd_formula, attr_pools)
                
                # 2. 計算轉換機率
                # 公式: 50% + (守方總和 - 攻方總和) / 攻方總和
                base_prob = params.get('transition_base_prob', 0.50)
                ratio = 0.0
                if off_spd_sum > 0:
                    ratio = (def_spd_sum - off_spd_sum) / off_spd_sum
                
                transition_prob = base_prob + ratio
                
                # 3. 判定分支
                if rng.decision(transition_prob):
                    # 觸發快攻
                    return final_time, 'steal_fastbreak', f"{def_team.name} Steal & Fastbreak"
                else:
                    # 觸發陣地戰 (直接進前場)
                    return final_time, 'steal_frontcourt', f"{def_team.name} Steal & Transition"

        # 快攻判定：需同時滿足「時間門檻」與「機率檢定」
        # 1. 檢查時間是否夠快
        if final_time < params.get('fastbreak_threshold', 1.0):
            # 2. 取得觸發機率 (預設 0.5)
            fb_prob = params.get('fastbreak_trigger_prob', 0.5)
            
            # 3. 進行機率骰子 (rng.random() 會回傳 0.0 ~ 1.0 之間的浮點數)
            if rng.decision(fb_prob):
                return self._run_fastbreak(off_team, def_team, final_time)
        
        return final_time, 'frontcourt', "Advance"

    def _run_frontcourt(self, off_team: EngineTeam, def_team: EngineTeam, elapsed_bc: float):
        """(Spec 4) 前場階段 [Update v2.4 速度折扣 & 24秒違例]"""
        # 1. 讀取設定檔參數
        fc_config = self.config.get('match_engine', {}).get('frontcourt', {})
        params = fc_config.get('params', {})
        formulas = fc_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})
        
        ctx = {'quality': 0.0, 'spacing': 0.0}
        
        # 2. 時間計算 (Time Calculation)
        # 計算基於智商與傳導的時間縮減量
        red_attr = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('time_reduction', []), attr_pools), attr_pools)
        reduction = (red_attr / 1000.0) * 0.5
        min_time = max(4.0, 4.0 - reduction)
        
        # 計算本回合剩餘可用的進攻時間上限 (24秒 - 後場已用時間)
        # 確保上限至少比下限大 1.0 秒，避免隨機錯誤
        max_time = max(min_time + 1.0, 24.0 - elapsed_bc)
        
        # 初步隨機產生花費時間
        elapsed = rng.get_float(min_time, max_time)
        
        # [New v2.4] 速度折扣 (Speed Discount)
        # 計算進攻方場上 5 人的速度總和
        spd_formula = formulas.get('frontcourt_speed', ['ath_speed'])
        spd_sum_off = Calculator.get_team_attr_sum(off_team.on_court, spd_formula, attr_pools)
        avg_spd_off = spd_sum_off / 5.0 if spd_sum_off > 0 else 50.0
        spd_sum_def = Calculator.get_team_attr_sum(def_team.on_court, spd_formula, attr_pools)
        avg_spd_def = spd_sum_def / 5.0 if spd_sum_def > 0 else 50.0
        
        # 計算折扣秒數 (速度越快，花費時間越少)
        discount_coeff = params.get('speed_discount_coeff', 0.1)
        discount_off = rng.get_float(0.0, avg_spd_off * discount_coeff)
        discount_def = rng.get_float(0.0, avg_spd_def * discount_coeff)
        
        # 應用折扣
        elapsed -= discount_off
        elapsed += discount_def
        
        # 確保物理時間下限 (不能低於 1.0 秒)
        abs_min = params.get('absolute_min_time', 1.0)
        elapsed = max(abs_min, elapsed)
        
        # 3. 24秒違例判定 (24-Sec Violation)
        # 若 (後場時間 + 前場時間) 超過 24 秒，則判定違例
        violation_limit = params.get('violation_threshold', 24.0)
        if (elapsed_bc + elapsed) > violation_limit:
            AttributionSystem.record_24sec_violation(off_team)
            elapsed = 24.0
            return elapsed, 'turnover', f"{off_team.name} 24秒進攻違例", ctx

        # 4. 計算出手品質 (Quality)
        # 時間花費越少，品質越高 (代表跑出空檔或流暢配合)
        if elapsed < 7.0: 
            ctx['quality'] = (7.0 - elapsed) * 0.01
        
        # 5. 空間與跑位判定 (Spacing)
        off_sp = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('spacing_off', []), attr_pools), attr_pools)
        def_sp = Calculator.get_team_attr_sum(def_team.on_court, self._resolve_formula(formulas.get('spacing_def', []), attr_pools), attr_pools) or 1
        
        # 計算空間加成 (-1.0 ~ 1.0)
        sp_bonus = max(-1.0, min(1.0, (off_sp - def_sp)/def_sp + rng.get_float(-0.1, 0.1)))
        ctx['spacing'] = sp_bonus

        # 6. 封阻判定 (Block - Spec 4.3)
        # 若空間擁擠 (sp_bonus <= 0.5)，封阻機率提升
        if sp_bonus <= 0.5:
            # --- 階段一：觸發判定 (Attempt Check) ---
            blk_config = formulas.get('block', {})
            blk_params = blk_config.get('params', {}) # 注意: YAML結構可能在 frontcourt.block 下
            # 若讀取不到，嘗試從外層讀取 (視 YAML 結構而定，這裡假設在 frontcourt.block)
            if not blk_config:
                blk_config = formulas.get('block', {}) # Retry
            
            # 讀取公式 Key
            blk_formulas = blk_config.get('formulas', {})
            trigger_off_keys = self._resolve_formula(blk_formulas.get('trigger_off', ['off_move']), attr_pools)
            trigger_def_keys = self._resolve_formula(blk_formulas.get('trigger_def', ['def_contest', 'talent_defiq']), attr_pools)
            
            # 計算團隊觸發值 (Team Sum)
            trig_off_val = Calculator.get_team_attr_sum(off_team.on_court, trigger_off_keys, attr_pools)
            trig_def_val = Calculator.get_team_attr_sum(def_team.on_court, trigger_def_keys, attr_pools)
            
            # 計算機率
            # 基礎機率 1%
            base_prob = blk_config.get('params', {}).get('base_prob', 0.01)
            # 屬性修正: (防守 - 進攻) * 0.0001 (每100點差值+1%)
            attr_mod = (trig_def_val - trig_off_val) * 0.0001
            # 空間懲罰: 空間擁擠時大幅提升封蓋率
            spacing_penalty = blk_config.get('params', {}).get('spacing_penalty_prob', 0.05) if sp_bonus < 0 else 0.0
            
            attempt_prob = max(0.0, base_prob + attr_mod + spacing_penalty)
            
            if rng.decision(attempt_prob):
                # --- 階段二：對抗判定 (Success Check) ---
                
                # 1. 決定角色
                # 預測出手者 (Shooter)
                shooter = AttributionSystem.determine_shooter(off_team, False, self.config)
                # 決定對位防守者 (Blocker) - 依據 Spec 6.6 封蓋歸屬規則
                blocker = AttributionSystem.get_position_matchup(shooter, def_team)
                
                # 2. 計算對抗能力 (Power)
                power_off_keys = self._resolve_formula(blk_formulas.get('power_off', ['ath_strength', 'ath_jump', 'talent_offiq', 'height']), attr_pools)
                power_def_keys = self._resolve_formula(blk_formulas.get('power_def', ['ath_strength', 'ath_jump', 'def_contest', 'talent_defiq', 'height']), attr_pools)
                
                p_off = Calculator.get_player_attr_sum(shooter, power_off_keys, attr_pools)
                p_def = Calculator.get_player_attr_sum(blocker, power_def_keys, attr_pools)
                
                # 3. 計算成功率
                # Spec: Ratio = Off / Def. 數值越低防守優勢越大.
                # 轉換為機率: Def / (Off + Def)
                # 若 Off=500, Def=500 -> 50% 機率蓋掉
                # 若 Off=400, Def=600 -> 60% 機率蓋掉
                success_prob = p_def / (p_off + p_def) if (p_off + p_def) > 0 else 0.5
                
                if rng.decision(success_prob):
                    # 封蓋成功 -> 失誤
                    AttributionSystem.record_block(blocker, shooter)
                    return elapsed, 'turnover', f"{def_team.name} {blocker.name} 封阻成功 (Block {shooter.name})", ctx
                else:
                    # 封蓋失敗 -> 進攻方強行出手 (繼續流程)
                    # 可以在 ctx 中標記 'contested'，影響後續命中率或犯規率 (Optional)
                    ctx['is_contested'] = True
                    # Log (Optional)
                    # print(f"Block Attempt Failed: {shooter.name} powered through {blocker.name}")
                    pass

        # 7. 抄截判定 (Steal - Spec 4.4 Full Implementation)
        # 讀取設定
        stl_config = fc_config.get('steal', {})
        stl_params = stl_config.get('params', {})
        stl_formulas = stl_config.get('formulas', {})

        # 1. 解析屬性公式 (Spec: Off_Ball vs Def_Steal)
        # 預設值對應 YAML: off_dribble+off_handle+off_pass+off_iq-height
        off_keys = self._resolve_formula(stl_formulas.get('off_attr', []), attr_pools)
        # 預設值對應 YAML: speed+def_disrupt+def_iq-height
        def_keys = self._resolve_formula(stl_formulas.get('def_attr', []), attr_pools)

        # 2. 計算團隊屬性總和
        # 這裡使用團隊總和來代表當下防守壓迫力與進攻穩定度
        off_val = Calculator.get_team_attr_sum(off_team.on_court, off_keys, attr_pools)
        def_val = Calculator.get_team_attr_sum(def_team.on_court, def_keys, attr_pools)

        # 3. 計算最終機率
        base_prob = stl_params.get('base_prob', 0.01)       # 基礎 1%
        coeff = stl_params.get('stat_diff_coeff', 0.001)    # 係數 0.1%
        
        # 公式: 1% + (Def_Steal - Off_Ball) * 係數
        final_prob = max(0.001, base_prob + (def_val - off_val) * coeff)

        if rng.decision(final_prob):
            # 決定抄截者 (Spec 6.5)
            stealer = AttributionSystem.determine_stealer(def_team, self.config)
            # 記錄抄截與失誤 (Spec 6.7)
            AttributionSystem.record_steal(stealer, off_team)
            return elapsed, 'turnover', f"{def_team.name} {stealer.name} 前場抄截", ctx

        # 8. 進入投籃階段
        return elapsed, 'shooting', "投籃出手", ctx

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
            # [New] 更新 +/-
            AttributionSystem.update_plus_minus(off_team, def_team, 2)
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

        # 1. Type (決定是 2分 或 3分)
        # 這部分涉及隨機判定，保留在 Core 中
        range_sum = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('range_attr', []), attr_pools), attr_pools) or 1
        threshold = 1.0 / (range_sum / 100.0)
        is_3pt = rng.get_float(0.0, 1.0) > threshold
        points = 3 if is_3pt else 2

        # 2. Shooter (決定出手者)
        shooter = AttributionSystem.determine_shooter(off_team, is_3pt, self.config)

        # 3. Hit Rate (命中率計算) - [Refactored] 完全呼叫 Calculator
        hit_rate = Calculator.calculate_shooting_rate(
          off_players=off_team.on_court,  # 進攻全隊 (用於對抗)
          def_players=def_team.on_court,  # 防守全隊 (用於對抗)
          shooter=shooter,                # 出手者 (用於技巧加成)
          config=self.config,
          spacing_factor=ctx.get('spacing', 0.0),
          quality_bonus=ctx.get('quality', 0.0),
          is_3pt=is_3pt
        )
        
        is_hit = rng.decision(hit_rate)

        # 4. Foul (犯規判定)
        off_iq = Calculator.get_team_attr_sum(off_team.on_court, self._resolve_formula(formulas.get('foul_off_iq', []), attr_pools), attr_pools)
        def_iq = Calculator.get_team_attr_sum(def_team.on_court, self._resolve_formula(formulas.get('foul_def_iq', []), attr_pools), attr_pools) or 1
        foul_prob = max(0.01, (off_iq - def_iq) / def_iq)
        is_foul = rng.decision(foul_prob)
        
        log = ""
        keep = False

        if is_hit:
            AttributionSystem.record_score(off_team, shooter, points, is_3pt)
            # [New] 更新 +/-
            AttributionSystem.update_plus_minus(off_team, def_team, points)
            
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
                # [Update] 傳入 def_team 以計算 +/-
                self._run_free_throw(off_team, def_team, shooter, 1)
                log += " (And-1)"
                # [新增] 檢查是否犯滿離場
                self._check_and_handle_foul_out(def_team, fouler)
        else:
            AttributionSystem.record_attempt(shooter, is_3pt)
            log = f"{off_team.name} {shooter.name} {points}pt Miss"
            
            if is_foul:
                fouler = rng.choice(def_team.on_court)
                AttributionSystem.record_foul(fouler)
                ft_count = 3 if is_3pt else 2
                # [Update] 傳入 def_team 以計算 +/-
                made = self._run_free_throw(off_team, def_team, shooter, ft_count)
                log += f" (Foul {made}/{ft_count})"
                # [新增] 檢查是否犯滿離場
                self._check_and_handle_foul_out(def_team, fouler)
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

    def _run_free_throw(self, team: EngineTeam, def_team: EngineTeam, shooter: EnginePlayer, count: int) -> int:
        """
        [Update] 新增 def_team 參數以支援 +/- 計算
        """
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
                # [New] 更新 +/-
                AttributionSystem.update_plus_minus(team, def_team, 1)
                made += 1
            else:
                AttributionSystem.record_free_throw(team, shooter, False)
        return made
    def _check_and_handle_foul_out(self, team: EngineTeam, player: EnginePlayer):
        """
         檢查並處理犯滿離場
        邏輯：
        1. 若犯規數達標，強制從 on_court 移除。
        2. 將該球員剩餘的 target_seconds 按比例分配給其他未犯滿球員。
        3. 從 bench 挑選替補上場。
        """
        # [Correction] 直接讀取 .fouls，避免 getattr 預設值 0 導致的邏輯失效
        # EnginePlayer 使用 __slots__，直接存取比 getattr 快且安全
        current_fouls = player.fouls
        
        if current_fouls >= self.foul_limit:
            player.is_fouled_out = True 
            self.pbp_logs.append(f"{team.name} {player.name} Fouled Out ({current_fouls})")
            
            # 1. 從場上移除
            if player in team.on_court:
                team.on_court.remove(player)
            
            # =================================================================
            # [新增邏輯] 時間重新分配 (Redistribute Minutes)
            # =================================================================
            # 計算該球員原本預計還要打多久
            remaining_seconds = max(0.0, player.target_seconds - player.seconds_played)
            
            # 將犯滿球員的目標時間鎖定為「已上場時間」，確保系統不再分配時間給他
            player.target_seconds = player.seconds_played
            
            if remaining_seconds > 0:
                # [修正] Spec 2.6 邏輯: C->PF->SF->SG->PG 各取前3名，共15個 slot
                # 排除已犯滿者
                valid_players = [p for p in (team.on_court + team.bench) if not p.is_fouled_out]
                
                if valid_players:
                    # 找出這 15 個 slot 的歸屬者
                    slots = []
                    positions = ["C", "PF", "SF", "SG", "PG"]
                    top_k = 3
                    
                    for pos in positions:
                        # 該位置評分前 K 名
                        sorted_by_pos = sorted(valid_players, key=lambda p: p.pos_scores.get(pos, 0), reverse=True)
                        slots.extend(sorted_by_pos[:top_k])
                    
                    # 平均分配給這些 slot
                    if slots:
                        time_per_slot = remaining_seconds / len(slots)
                        for receiver in slots:
                            receiver.target_seconds += time_per_slot
                        
                    # 記錄日誌以便除錯
                    # self.pbp_logs.append(f"Debug: Redistributed {remaining_seconds:.1f}s among {len(valid_recipients)} players")
            # =================================================================

            # 2. 尋找替補 (排除同樣犯滿的球員)
            candidates = [
                p for p in team.bench 
                if not p.is_fouled_out
            ]
            
            if not candidates:
                # 極端保護：若板凳全犯滿，強制讓原球員繼續打以防 Crash，並記錄警告
                # 注意：雖然前面把時間分配掉了，但為了不讓程式崩潰，還是得讓他上
                team.on_court.append(player)
                self.pbp_logs.append(f"WARNING: No available subs for {team.name}, {player.name} stays on court.")
                return

            # 3. 挑選最佳替補 (優先同位置，其次最高分)
            sub = None
            target_pos = getattr(player, 'position', 'C')
            
            pos_candidates = [p for p in candidates if p.pos_scores.get(target_pos, 0) > 0]
            if pos_candidates:
                sub = max(pos_candidates, key=lambda p: p.pos_scores.get(target_pos, 0))
            else:
                sub = max(candidates, key=lambda p: sum(p.pos_scores.values()))
            
            # 4. 執行替換
            team.bench.remove(sub)
            sub.position = target_pos # 繼承位置
            team.on_court.append(sub)
            
            # 將犯滿球員移至板凳
            team.bench.append(player)
            
            self.pbp_logs.append(f"Substitution: {sub.name} replaces {player.name} (Foul Out)")
