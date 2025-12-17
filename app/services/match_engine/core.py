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
    ASBL 比賽引擎核心 (Level 4 - Fixed)
    負責控制比賽流程、時間流逝、調度與事件觸發。
    對應規格書: Match Engine Specification v1.6
    
    [Fix Log]
    - Added `_resolve_formula` method to handle string references in config.
      (e.g., converting 'off_13' string to the actual list of attributes defined in attr_pools).
    - Applied formula resolution to ALL calculation phases (Backcourt, Frontcourt, Shooting, Rebounding, etc.)
      to prevent the "Zero Stats" bug where attributes were not being read correctly.
    """

    def __init__(self, home_team: EngineTeam, away_team: EngineTeam, config: Dict):
        self.home_team = home_team
        self.away_team = away_team
        self.config = config
        
        # 1. 初始化比賽狀態
        general_config = config.get('match_engine', {}).get('general', {})
        self.quarter_length = general_config.get('quarter_length', 720)
        self.ot_length = general_config.get('ot_length', 300)
        
        self.state = MatchState(quarter_length=self.quarter_length)
        
        # 2. 執行賽前準備 (Pre-Game Setup)
        self._initialize_match()
        
        # 3. 初始化 PBP Logs
        self.pbp_logs = []

    def _initialize_match(self):
        """
        賽前準備流程:
        1. 計算位置評分 [Spec 1.1]
        2. 鎖定 Best 5 [Spec 1.1]
        3. 分配上場時間 [Spec 1.4 & 2.6]
        4. 決定先發陣容 [Spec 1.2]
        """
        # 對兩隊執行相同的初始化邏輯
        for team in [self.home_team, self.away_team]:
            self._calculate_all_positional_scores(team)
            self._determine_best_five(team)
            self._distribute_team_minutes(team)
            self._set_initial_lineup(team)

    def _calculate_all_positional_scores(self, team: EngineTeam):
        """
        [Spec 1.1] 計算全隊每個球員在 5 個位置的適性分數
        """
        scoring_rules = self.config.get('match_engine', {}).get('positional_scoring', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})
        
        positions = ["C", "PF", "SF", "SG", "PG"]

        for player in team.roster:
            player.pos_scores = {}
            for pos in positions:
                rule_attrs = scoring_rules.get(pos, [])
                # 使用 Calculator 計算總分
                score = Calculator.get_player_attr_sum(player, rule_attrs, attr_pools)
                player.pos_scores[pos] = score

    def _determine_best_five(self, team: EngineTeam):
        """
        [Spec 1.1] 標記最強陣容 (Best 5)
        邏輯: 每個位置取分數最高者 (簡單貪婪法，若一人多位最強則需分配)
        為了效能與簡化，這裡採用「優先填補最高分位置」的策略。
        """
        positions = ["C", "PF", "SF", "SG", "PG"]
        best_five = [None] * 5 # 對應 positions 索引
        taken_player_ids = set()

        # 建立一個列表: (分數, 位置, 球員)
        candidates = []
        for p in team.roster:
            for i, pos in enumerate(positions):
                candidates.append((p.pos_scores[pos], i, p))
        
        # 依分數由高到低排序
        candidates.sort(key=lambda x: x[0], reverse=True)

        # 填補位置
        for score, pos_idx, player in candidates:
            if best_five[pos_idx] is None and player.id not in taken_player_ids:
                best_five[pos_idx] = player
                taken_player_ids.add(player.id)
            
            # 若 5 個位置都滿了，跳出
            if all(p is not None for p in best_five):
                break
        
        # 防呆: 萬一沒填滿 (例如球員少於 5 人)，用剩餘球員填補
        if not all(p is not None for p in best_five):
            remaining = [p for p in team.roster if p.id not in taken_player_ids]
            for i in range(5):
                if best_five[i] is None and remaining:
                    p = remaining.pop(0)
                    best_five[i] = p
                    taken_player_ids.add(p.id)

        team.best_five = best_five

    def _distribute_team_minutes(self, team: EngineTeam):
        """
        [Spec 1.4 & 2.6] 上場時間分配系統
        重點: 計算出的分鐘數需轉換為 '秒 (target_seconds)'
        """
        min_config = self.config.get('minutes_distribution', {})
        total_minutes = min_config.get('total_minutes', 240)
        role_config = min_config.get('roles', {})

        # 1. 計算總保底時間與剩餘時間
        total_base = 0.0
        active_players = [] # 參與分配的球員 (排除受傷等，目前假設全部參與)

        for player in team.roster:
            role_data = role_config.get(player.role, role_config.get('Bench')) # 預設 Bench
            total_base += role_data.get('base', 0)
            active_players.append(player)

        remaining_time = max(0, total_minutes - total_base)

        # 2. 生成權重並計算總權重
        total_weight = 0.0
        player_weights = {} # id -> weight

        for player in active_players:
            role_data = role_config.get(player.role, role_config.get('Bench'))
            min_w = role_data.get('min_w', 0)
            max_w = role_data.get('max_w', 10)
            
            # 隨機生成權重
            w = rng.get_float(float(min_w), float(max_w))
            player_weights[player.id] = w
            total_weight += w

        # 3. 計算單位時間價值
        unit_value = 0.0
        if total_weight > 0:
            unit_value = remaining_time / total_weight

        # 4. 計算個人時間並轉換為秒
        allocated_minutes_sum = 0.0
        
        for i, player in enumerate(active_players):
            role_data = role_config.get(player.role, role_config.get('Bench'))
            base = role_data.get('base', 0)
            w = player_weights[player.id]
            
            raw_minutes = base + (w * unit_value)
            
            # 捨去規則: 取至小數點第一位
            final_minutes = math.floor(raw_minutes * 10) / 10.0
            
            # 尾數修正: 最後一位球員拿走所有剩餘誤差
            if i == len(active_players) - 1:
                diff = total_minutes - allocated_minutes_sum
                if diff > 0:
                    final_minutes = diff # 這裡就不捨去了，直接補滿

            allocated_minutes_sum += final_minutes
            
            # [Critical] 轉換為秒數並存入
            player.target_seconds = final_minutes * 60.0
            player.seconds_played = 0.0 # 重置已上場時間

    def _set_initial_lineup(self, team: EngineTeam):
        """
        [Spec 1.2] 決定先發陣容
        順序: Star -> Starter -> Fill Gaps
        """
        positions = ["PG", "SG", "SF", "PF", "C"]
        starters = [None] * 5 # 對應 positions
        taken_ids = set()

        # Helper: 嘗試將球員填入其最佳空缺位置
        def try_fill_position(player):
            # 找出該球員分數最高且尚未被填滿的位置
            # 排序: (分數, 位置索引)
            my_pos_scores = []
            for i, pos in enumerate(positions):
                if starters[i] is None:
                    my_pos_scores.append((player.pos_scores[pos], i))
            
            my_pos_scores.sort(key=lambda x: x[0], reverse=True)
            
            if my_pos_scores:
                best_score, idx = my_pos_scores[0]
                starters[idx] = player
                taken_ids.add(player.id)
                # 設定球員當前位置
                player.position = positions[idx] 
                return True
            return False

        # 1. Star 優先
        stars = [p for p in team.roster if p.role == 'Star']
        for p in stars:
            try_fill_position(p)

        # 2. Starter 填補
        starter_players = [p for p in team.roster if p.role == 'Starter' and p.id not in taken_ids]
        for p in starter_players:
            try_fill_position(p)

        # 3. 剩餘填補 (Fill Gaps)
        remaining_players = [p for p in team.roster if p.id not in taken_ids]
        
        for i, pos in enumerate(positions):
            if starters[i] is None:
                best_p = None
                best_score = -1.0
                
                for p in remaining_players:
                    if p.id in taken_ids: continue
                    if p.pos_scores[pos] > best_score:
                        best_score = p.pos_scores[pos]
                        best_p = p
                
                if best_p:
                    starters[i] = best_p
                    best_p.position = pos
                    taken_ids.add(best_p.id)

        # 4. 分配至 EngineTeam
        team.on_court = [p for p in starters if p is not None]
        team.bench = [p for p in team.roster if p.id not in taken_ids]
        
        # 防呆: 如果先發不足 5 人 (極端情況)，從板凳拉人
        while len(team.on_court) < 5 and team.bench:
            p = team.bench.pop(0)
            for i, pos in enumerate(positions):
                if starters[i] is None:
                    p.position = pos
                    starters[i] = p
                    team.on_court.append(p)
                    break

    # =========================================================================
    # Helper: Resolve Formula (Fix for String References)
    # =========================================================================
    def _resolve_formula(self, formula: Union[str, List[str]], attr_pools: Dict) -> List[str]:
        """
        [Critical Fix] 解析公式配置:
        如果 formula 是字串 (例如 'off_13')，則從 attr_pools 查找對應的屬性列表。
        如果是列表，則直接回傳。
        這樣可以修復 Config 中使用字串引用導致 Calculator 讀取不到屬性的問題。
        """
        if isinstance(formula, str):
            return attr_pools.get(formula, [])
        return formula

    # =========================================================================
    # Step 2: 流程控制 (Flow Control)
    # =========================================================================

    def simulate(self) -> MatchResult:
        """
        執行整場比賽模擬。
        包含: 跳球 -> 4節正規賽 -> (若平手) 延長賽 -> 結算
        """
        # 1. 開場跳球 (Spec v1.6)
        jump_ball_winner = self._jump_ball()
        jump_ball_loser = self.home_team.id if jump_ball_winner == self.away_team.id else self.away_team.id
        
        # 2. 定義節次球權輪替 (Spec v1.6)
        # Q1: 勝方, Q2: 負方, Q3: 負方, Q4: 勝方
        quarter_possessions = {
            1: jump_ball_winner,
            2: jump_ball_loser,
            3: jump_ball_loser,
            4: jump_ball_winner
        }

        # 3. 正規賽迴圈 (Q1 - Q4)
        for q in range(1, 5):
            self.state.quarter = q
            self.state.time_remaining = float(self.quarter_length)
            
            # 設定該節開球方
            self.state.possession = quarter_possessions[q]
            self.pbp_logs.append(f"=== 第 {q} 節開始 (球權: {self.state.possession}) ===")
            
            self._simulate_quarter()

        # 4. 延長賽處理 (OT)
        while self.home_team.score == self.away_team.score:
            self.state.quarter += 1
            self.state.time_remaining = float(self.ot_length)
            
            # OT 重新跳球 (Spec v1.6)
            ot_winner = self._jump_ball()
            self.state.possession = ot_winner
            self.pbp_logs.append(f"=== 延長賽 (OT{self.state.quarter-4}) 開始 (球權: {ot_winner}) ===")
            
            self._simulate_quarter()

        # 5. 比賽結束，回傳結果
        self.state.is_over = True
        return MatchResult(
            game_id="SIM_GAME", # 暫時 ID
            home_team_id=self.home_team.id,
            away_team_id=self.away_team.id,
            home_score=self.home_team.score,
            away_score=self.away_team.score,
            is_ot=(self.state.quarter > 4),
            total_quarters=self.state.quarter,
            pbp_log=self.pbp_logs
        )

    def _jump_ball(self) -> str:
        """
        跳球邏輯 (Spec v1.6: Config Driven)
        """
        # 1. 讀取 Config
        jb_config = self.config.get('match_engine', {}).get('jump_ball', {})
        attrs = jb_config.get('participant_formula', ['height', 'ath_jump', 'talent_offiq'])
        
        # 2. 找出雙方跳球代表 (中鋒或第一人)
        def get_jumper(team):
            c_candidates = [p for p in team.on_court if p.position == 'C']
            if c_candidates: return c_candidates[0]
            # 若無 C，找 C 分數最高的
            return max(team.on_court, key=lambda p: p.pos_scores.get('C', 0))

        home_jumper = get_jumper(self.home_team)
        away_jumper = get_jumper(self.away_team)
        
        # 3. 計算雙方數值總和
        h_score = Calculator.get_player_attr_sum(home_jumper, attrs)
        a_score = Calculator.get_player_attr_sum(away_jumper, attrs)
        
        # 4. 計算獲勝機率 (Spec v1.6: Score / Total)
        total_score = h_score + a_score
        if total_score == 0: total_score = 1 # 防除以零
        prob_home = h_score / total_score
        
        # [DEBUG]
        self.pbp_logs.append(f"   [CALC] 跳球: {home_jumper.name}({h_score:.0f}) vs {away_jumper.name}({a_score:.0f}) -> HomeProb: {prob_home:.2%}")
        
        # 5. 判定結果
        if rng.decision(prob_home):
            winner = self.home_team.id
            log = f"跳球: {self.home_team.name} ({home_jumper.name}) 贏得球權"
        else:
            winner = self.away_team.id
            log = f"跳球: {self.away_team.name} ({away_jumper.name}) 贏得球權"
            
        self.pbp_logs.append(log)
        return winner

    def _simulate_quarter(self):
        """
        模擬單節比賽流程
        """
        # [Spec v1.6] 開場首回合例外標記
        is_opening_possession = (self.state.quarter == 1)
        
        while self.state.time_remaining > 0:
            # 1. 換人檢查
            self._check_substitutions()
            
            # 2. 執行一個回合 (Possession)
            # Returns: (elapsed, log, keep_possession)
            elapsed, event_desc, keep_possession = self._simulate_possession(is_opening_possession)
            
            # 3. 更新時間
            self.state.time_remaining -= elapsed
            self.state.game_time_elapsed += elapsed
            
            # 更新球員上場時間與體力
            for team in [self.home_team, self.away_team]:
                # 場上球員: 消耗體力, 增加時間
                for p in team.on_court:
                    p.seconds_played += elapsed
                    StaminaSystem.update_stamina(p, elapsed, is_on_court=True, config=self.config)
                
                # 板凳球員: 恢復體力
                for p in team.bench:
                    StaminaSystem.update_stamina(p, elapsed, is_on_court=False, config=self.config)
            
            # 記錄 Log
            self.pbp_logs.append(f"[{self.state.quarter}Q {self.state.time_remaining:.1f}] {event_desc}")

            # 4. 攻守交換邏輯
            if keep_possession:
                # [Spec 5.4] 進攻籃板 -> 繼續進攻 (不交換球權)
                pass
            else:
                # 正常交換
                if self.state.possession == self.home_team.id:
                    self.state.possession = self.away_team.id
                else:
                    self.state.possession = self.home_team.id
            
            # 關閉開場標記
            is_opening_possession = False

        # 節間休息: 體力回復 (Spec 2.1 僅定義中場休息)
        if self.state.quarter == 2: # 半場結束
             StaminaSystem.apply_halftime_recovery(self.home_team.roster, self.config)
             StaminaSystem.apply_halftime_recovery(self.away_team.roster, self.config)
             self.pbp_logs.append("=== 中場休息 (體力回復) ===")

    def _check_substitutions(self):
        """
        檢查並執行換人
        """
        # 第 4 節最後 3 分鐘或 OT -> 關鍵時刻 (Spec 2.5)
        is_clutch = (self.state.quarter >= 4 and self.state.time_remaining <= 180.0)
        
        for team in [self.home_team, self.away_team]:
            # 處理犯滿離場 (優先級最高)
            # 這部分邏輯通常在發生犯規時即時觸發，但在此處做雙重檢查也可
            
            if is_clutch:
                # TODO: 強制換上 Best 5 (需實作邏輯)
                pass 
            else:
                # 常規換人
                logs = SubstitutionSystem.check_auto_substitution(
                    team, self.state.quarter, self.state.time_remaining, self.config
                )
                self.pbp_logs.extend(logs)
                
    # =========================================================================
    # Step 3: 回合模擬邏輯 (Possession Logic)
    # =========================================================================

    def _simulate_possession(self, is_opening: bool) -> Tuple[float, str, bool]:
        """
        模擬單一回合的完整流程。
        流程: 後場 -> (若未結束) -> 前場 -> (若未結束) -> 投籃
        Returns:
            elapsed (float): 消耗時間
            desc (str): 事件描述
            keep_possession (bool): 是否維持球權 (進攻籃板)
        """
        # 1. 確定攻守方
        if self.state.possession == self.home_team.id:
            off_team, def_team = self.home_team, self.away_team
        else:
            off_team, def_team = self.away_team, self.home_team

        # 2. 執行後場階段 (Backcourt Phase)
        # result_type: 'turnover', 'score', 'frontcourt'
        elapsed_bc, result_type, desc = self._run_backcourt(off_team, def_team, is_opening)
        
        # 如果後場就結束了 (失誤、快攻得分/罰球)，直接回傳
        if result_type != 'frontcourt':
            return elapsed_bc, desc, False

        # 3. 執行前場階段 (Frontcourt Phase)
        # result_type: 'turnover', 'shooting'
        # context: 包含 spacing_bonus, quality_bonus 等資訊，供投籃階段使用
        elapsed_fc, result_type, desc, context = self._run_frontcourt(off_team, def_team, elapsed_bc)
        
        total_elapsed = elapsed_bc + elapsed_fc

        # 如果前場發生失誤 (被抄截、封蓋)，直接回傳
        if result_type != 'shooting':
            return total_elapsed, desc, False

        # 4. 執行投籃與結算 (Shooting Phase)
        # Returns: (log_desc, keep_possession)
        desc_shoot, keep_possession = self._run_shooting(off_team, def_team, context)
        
        return total_elapsed, desc_shoot, keep_possession

    def _run_backcourt(self, off_team: EngineTeam, def_team: EngineTeam, is_opening: bool) -> Tuple[float, str, str]:
        """
        [Spec 3] 後場階段邏輯
        Returns: (elapsed_time, result_type, description)
        """
        bc_config = self.config.get('match_engine', {}).get('backcourt', {})
        params = bc_config.get('params', {})
        formulas = bc_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})

        # --- 3.1 參與者與屬性計算 ---
        # 進攻方: PG + SG + Random 1
        guards = [p for p in off_team.on_court if p.position in ['PG', 'SG']]
        others = [p for p in off_team.on_court if p not in guards]
        participants_off = (guards + others)[:3] 
        
        # 防守方: 對應的 3 人 (簡化為隨機 3 人或對位，這裡取前 3 人即可)
        participants_def = def_team.on_court[:3]

        # [Fix] 解析公式，確保字串引用能被正確轉換為列表
        off_sum_formula = self._resolve_formula(formulas.get('off_sum', []), attr_pools)
        def_sum_formula = self._resolve_formula(formulas.get('def_sum', []), attr_pools)

        # 計算 Off_Sum 與 Def_Sum
        off_sum = Calculator.get_team_attr_sum(participants_off, off_sum_formula, attr_pools)
        def_sum = Calculator.get_team_attr_sum(participants_def, def_sum_formula, attr_pools)

        # --- 3.2 時間計算 ---
        if is_opening:
            final_time = params.get('opening_seconds', 2.0)
        else:
            base_time = rng.get_float(params.get('time_base_min', 1.0), params.get('time_base_max', 8.0))
            correction = (def_sum - off_sum) * params.get('time_coeff', 0.008)
            final_time = base_time + correction
            # 鎖定上下限
            final_time = max(0.5, min(8.1, final_time))

        # --- 3.3 事件判定 ---
        # A. 8秒違例
        if final_time > params.get('violation_threshold', 8.0):
            AttributionSystem.record_team_turnover(off_team)
            return final_time, 'turnover', f"{off_team.name} 8秒違例"

        # B. 抄截判定 (> 3.0s)
        if final_time > params.get('steal_threshold', 3.0):
            # [Spec 3.4]
            base_prob = params.get('steal_base_prob', 0.01)
            bonus = (def_sum - off_sum) * params.get('steal_bonus_coeff', 0.001)
            steal_prob = base_prob + bonus
            
            if rng.decision(steal_prob):
                stealer = AttributionSystem.determine_stealer(def_team, self.config)
                AttributionSystem.record_steal(stealer, off_team)
                return final_time, 'turnover', f"{def_team.name} {stealer.name} 後場抄截"

        # C. 快攻判定 (< 1.0s)
        if final_time < params.get('fastbreak_threshold', 1.0):
            return self._run_fastbreak(off_team, def_team, final_time)

        # D. 正常推進
        return final_time, 'frontcourt', "正常過半場"
    
    def _run_frontcourt(self, off_team: EngineTeam, def_team: EngineTeam, elapsed_bc: float) -> Tuple[float, str, str, Dict]:
        """
        [Spec 4] 前場階段邏輯
        Returns: (elapsed_time, result_type, description, context_dict)
        """
        fc_config = self.config.get('match_engine', {}).get('frontcourt', {})
        params = fc_config.get('params', {})
        formulas = fc_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})

        context = {
            'quality': 0.0,
            'spacing': 0.0,
            'is_3pt': False # Step 5 決定
        }

        # --- 4.1 進攻時間與出手品質 ---
        # [Fix] 解析公式
        time_reduction_formula = self._resolve_formula(formulas.get('time_reduction', []), attr_pools)
        
        # 計算時間下限修正 (團隊屬性)
        time_reduction_attr = Calculator.get_team_attr_sum(off_team.on_court, time_reduction_formula, attr_pools)
        
        # 使用 params 讀取係數，預設值為 Spec 描述的 1000.0 與 0.5
        reduction_divisor = params.get('time_reduction_divisor', 1000.0)
        reduction_coeff = params.get('time_reduction_coeff', 0.5)
        reduction = (time_reduction_attr / reduction_divisor) * reduction_coeff
        
        min_time = max(4.0, params.get('time_min_limit', 4.0) - reduction)
        max_time = max(min_time + 1.0, 24.0 - elapsed_bc) # 確保 max > min
        
        # 實際花費時間
        elapsed = rng.get_float(min_time, max_time)
        
        # 計算品質加成 (時間越短品質越高)
        quality_base = params.get('time_quality_base', 7.0)
        if elapsed < quality_base:
            context['quality'] = (quality_base - elapsed) * 0.01
        
        # --- 4.2 空間與跑位 (Spacing) ---
        # [Fix] 解析公式
        spacing_off_formula = self._resolve_formula(formulas.get('spacing_off', []), attr_pools)
        spacing_def_formula = self._resolve_formula(formulas.get('spacing_def', []), attr_pools)
        
        off_spacing = Calculator.get_team_attr_sum(off_team.on_court, spacing_off_formula, attr_pools)
        def_spacing = Calculator.get_team_attr_sum(def_team.on_court, spacing_def_formula, attr_pools)
        
        if def_spacing == 0: def_spacing = 1 # 防除以零
        
        # 空間加成公式: (Off - Def) / Def
        # 範圍限制: -0.25 ~ 1.25 (Config 未定義，依 Spec 4.2 邏輯實作)
        raw_spacing = (off_spacing - def_spacing) / def_spacing
        spacing_bonus = max(-0.25, min(1.25, raw_spacing))
        
        # 隨機浮動 (Spec: "隨機產生") -> 這裡理解為在計算出的基礎值上做微幅波動，或直接視為機率分佈
        # 簡化實作: 直接使用計算值，並加上一個小的隨機擾動 (-0.1 ~ +0.1)
        spacing_bonus += rng.get_float(-0.1, 0.1)
        spacing_bonus = max(-1.0, min(1.0, spacing_bonus)) # 最終鎖定
        
        context['spacing'] = spacing_bonus

        # --- 4.3 防守事件: 封蓋 (Block) ---
        # 前提: 空間加成 > 0.5 (Wide Open) 則不觸發封蓋
        if spacing_bonus <= 0.5:
            blk_config = fc_config.get('block', {})
            blk_params = blk_config.get('params', {})
            blk_formulas = blk_config.get('formulas', {})
            
            # 階段一: 觸發判定
            base_prob = blk_params.get('base_prob', 0.01)
            
            # 空間懲罰: 若擁擠 (<0)，增加觸發率
            if spacing_bonus < 0:
                base_prob += blk_params.get('spacing_penalty_prob', 0.05)
            
            # [Fix] 解析公式
            trigger_off_formula = self._resolve_formula(blk_formulas.get('trigger_off', []), attr_pools)
            trigger_def_formula = self._resolve_formula(blk_formulas.get('trigger_def', []), attr_pools)

            # 屬性修正 (簡化: 取雙方最高者對決)
            trigger_off = max(off_team.on_court, key=lambda p: Calculator.get_player_attr_sum(p, trigger_off_formula, attr_pools))
            trigger_def = max(def_team.on_court, key=lambda p: Calculator.get_player_attr_sum(p, trigger_def_formula, attr_pools))
            
            off_val = Calculator.get_player_attr_sum(trigger_off, trigger_off_formula, attr_pools)
            def_val = Calculator.get_player_attr_sum(trigger_def, trigger_def_formula, attr_pools)
            
            # 觸發機率公式 (自定義): Base + (Def - Off) * 0.0001
            prob = base_prob + (def_val - off_val) * blk_params.get('prob_coeff', 0.0001)
            
            if rng.decision(prob):
                # 階段二: 對抗判定 (Power Ratio)
                # [Fix] 解析公式
                power_off_formula = self._resolve_formula(blk_formulas.get('power_off', []), attr_pools)
                power_def_formula = self._resolve_formula(blk_formulas.get('power_def', []), attr_pools)
                
                power_off = Calculator.get_player_attr_sum(trigger_off, power_off_formula, attr_pools)
                power_def = Calculator.get_player_attr_sum(trigger_def, power_def_formula, attr_pools)
                
                if power_def == 0: power_def = 1
                ratio = power_off / power_def
                
                # Ratio 越低，防守優勢越大 -> 封蓋成功
                # 閾值設定: 1.0 (勢均力敵) -> 50% 機率? 
                # Spec: "Ratio 數值越低: 封蓋成功"
                # 實作: 若 Ratio < 0.9 (進攻方弱勢) -> 成功; 若 > 1.1 -> 失敗; 中間隨機
                is_blocked = False
                if ratio < blk_params.get('ratio_threshold_success', 0.9): is_blocked = True
                elif ratio > blk_params.get('ratio_threshold_fail', 1.1): is_blocked = False
                else: is_blocked = rng.decision(0.5)
                
                if is_blocked:
                    # 歸屬: 封蓋者歸給 trigger_def (簡化)
                    # 實際上應該要找對位，這裡先暫用 trigger_def
                    AttributionSystem.record_block(trigger_def, trigger_off)
                    return elapsed, 'turnover', f"{def_team.name} {trigger_def.name} 封蓋成功", context

        # --- 4.4 防守事件: 前場抄截 (Steal) ---
        stl_config = fc_config.get('steal', {})
        stl_params = stl_config.get('params', {})
        stl_formulas = stl_config.get('formulas', {})
        
        base_prob = stl_params.get('base_prob', 0.01)
        
        # [Fix] 解析公式
        off_attr_formula = self._resolve_formula(stl_formulas.get('off_attr', []), attr_pools)
        def_attr_formula = self._resolve_formula(stl_formulas.get('def_attr', []), attr_pools)
        
        # 取平均屬性比較
        off_avg = Calculator.get_team_attr_sum(off_team.on_court, off_attr_formula, attr_pools) / 5.0
        def_avg = Calculator.get_team_attr_sum(def_team.on_court, def_attr_formula, attr_pools) / 5.0
        
        prob = base_prob + (def_avg - off_avg) * stl_params.get('stat_diff_coeff', 0.001)
        
        if rng.decision(prob):
            stealer = AttributionSystem.determine_stealer(def_team, self.config)
            AttributionSystem.record_steal(stealer, off_team)
            return elapsed, 'turnover', f"{def_team.name} {stealer.name} 前場抄截", context

        # 若無事件發生，進入投籃階段
        return elapsed, 'shooting', "進入投籃", context

    def _run_fastbreak(self, off_team: EngineTeam, def_team: EngineTeam, elapsed: float) -> Tuple[float, str, str]:
        """
        [Spec 3.5] 快攻判定邏輯
        """
        fb_config = self.config.get('match_engine', {}).get('backcourt', {}).get('fastbreak', {})
        params = fb_config.get('params', {})
        formulas = fb_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})

        # [Fix] 解析公式
        runner_sel_formula = self._resolve_formula(formulas.get('runner_selection', []), attr_pools)
        chaser_sel_formula = self._resolve_formula(formulas.get('chaser_selection', []), attr_pools)

        # A. 參與者選擇 (跑最快 vs 追最快)
        # 使用 Calculator 計算 runner_selection 屬性總和來排序
        runner = max(off_team.on_court, key=lambda p: Calculator.get_player_attr_sum(p, runner_sel_formula, attr_pools))
        chaser = max(def_team.on_court, key=lambda p: Calculator.get_player_attr_sum(p, chaser_sel_formula, attr_pools))

        # [Fix] 解析公式
        off_power_formula = self._resolve_formula(formulas.get('off_power', []), attr_pools)
        def_power_formula = self._resolve_formula(formulas.get('def_power', []), attr_pools)

        # B. 成功率計算
        off_stat = Calculator.get_player_attr_sum(runner, off_power_formula, attr_pools)
        def_stat = Calculator.get_player_attr_sum(chaser, def_power_formula, attr_pools)
        
        base_success = rng.get_float(params.get('base_success_min', 0.3), params.get('base_success_max', 1.0))
        success_prob = base_success + (off_stat - def_stat) * params.get('stat_diff_coeff', 0.005)
        success_prob = max(0.1, min(0.99, success_prob)) # 保底
        
        # [DEBUG]
        roll = rng.get_float(0.0, 1.0)
        is_success = (roll <= success_prob)
        self.pbp_logs.append(f"   [CALC] Fastbreak: {runner.name} Off({off_stat}) vs Def({def_stat}) -> Prob({success_prob:.2%}) | Roll({roll:.3f})")

        # [Fix] 解析公式
        foul_off_iq_formula = self._resolve_formula(formulas.get('foul_off_iq', []), attr_pools)
        foul_def_iq_formula = self._resolve_formula(formulas.get('foul_def_iq', []), attr_pools)

        # C. 犯規判定
        off_iq = Calculator.get_player_attr_sum(runner, foul_off_iq_formula, attr_pools)
        def_iq = Calculator.get_player_attr_sum(chaser, foul_def_iq_formula, attr_pools)
        
        foul_prob = params.get('foul_base_prob', 0.01) + (off_iq - def_iq) * params.get('foul_iq_coeff', 0.01)
        foul_prob = max(0.001, foul_prob) # 保底
        is_foul = rng.decision(foul_prob)

        # D. 結果結算
        result_desc = ""
        result_type = "score" # default

        if is_success:
            # 進球
            points = 2
            AttributionSystem.record_score(off_team, runner, points, False)
            result_desc = f"{off_team.name} {runner.name} 快攻得分"
            
            if is_foul:
                # And-1
                AttributionSystem.record_foul(chaser)
                # 執行 1 次罰球
                ft_made = self._run_free_throw(runner, 1)
                result_desc += " (And-1)"
                if ft_made > 0: result_desc += " 加罰命中"
        else:
            # 沒進
            if is_foul:
                # 阻擋犯規，罰球 2 次
                AttributionSystem.record_foul(chaser)
                ft_made = self._run_free_throw(runner, 2)
                result_desc = f"{off_team.name} {runner.name} 快攻遭犯規 (罰{ft_made}/2)"
                result_type = "score" # 視為得分回合結束(雖然是罰球)
            else:
                # 防守成功 (視為籃板/火鍋)
                # Spec: "視為籃板/火鍋" -> 這裡簡單判定為防守籃板
                AttributionSystem.record_rebound(chaser, False)
                result_desc = f"{def_team.name} {chaser.name} 成功阻止快攻"
                result_type = "turnover" # 進攻失敗，球權轉換

        return elapsed, result_type, result_desc

    def _run_free_throw(self, shooter: EnginePlayer, count: int) -> int:
        """
        [Helper] 執行罰球
        Returns: 命中的球數
        """
        made = 0
        ft_config = self.config.get('match_engine', {}).get('shooting', {}).get('ft', {})
        params = ft_config.get('params', {})
        formulas = ft_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})

        # 計算命中率
        base = rng.get_float(params.get('base_min', 0.40), params.get('base_max', 0.95))
        
        # [Fix] 解析公式
        bonus_attrs_formula = self._resolve_formula(formulas.get('bonus_attrs', ['talent_luck', 'shot_touch']), attr_pools)
        
        attr_sum = Calculator.get_player_attr_sum(shooter, bonus_attrs_formula, attr_pools)
        
        prob = base + attr_sum * params.get('attr_coeff', 0.0001)
        prob = min(0.99, max(0.01, prob))

        for _ in range(count):
            if rng.decision(prob):
                AttributionSystem.record_free_throw(shooter, True)
                made += 1
            else:
                AttributionSystem.record_free_throw(shooter, False)
        
        return made

    def _run_shooting(self, off_team: EngineTeam, def_team: EngineTeam, context: Dict) -> Tuple[str, bool]:
        """
        [Spec 5] 投籃與結算邏輯
        Returns: (log_description, keep_possession)
        """
        sht_config = self.config.get('match_engine', {}).get('shooting', {})
        params = sht_config.get('params', {})
        formulas = sht_config.get('formulas', {})
        attr_pools = self.config.get('match_engine', {}).get('attr_pools', {})

        # --- 5.3 得分分數判定 (Score Value) ---
        # [Fix] 解析公式
        range_attr_formula = self._resolve_formula(formulas.get('range_attr', []), attr_pools)

        # Threshold = 1 / (Team_Range / 100)
        team_range = Calculator.get_team_attr_sum(off_team.on_court, range_attr_formula, attr_pools)
        if team_range == 0: team_range = 1 # Prevent div by zero
        
        range_divisor = params.get('range_divisor', 100.0)
        threshold = 1.0 / (team_range / range_divisor)
        rand_val = rng.get_float(0.0, 1.0)
        
        is_3pt = (rand_val > threshold)
        points_attempt = 3 if is_3pt else 2
        
        context['is_3pt'] = is_3pt # Update context for attribution

        # [Spec 6.1] 決定出手者
        shooter = AttributionSystem.determine_shooter(off_team, is_3pt, self.config)

        # --- 5.1 命中率判定 (Hit Rate) ---
        # [Fix] 解析公式
        off_total_formula = self._resolve_formula(formulas.get('off_total', []), attr_pools)
        def_total_formula = self._resolve_formula(formulas.get('def_total', []), attr_pools)

        # Formula: (40% + (Off - Def)/Def) * (1 + Spacing*0.1) * (1 + Quality)
        off_total = Calculator.get_team_attr_sum(off_team.on_court, off_total_formula, attr_pools)
        def_total = Calculator.get_team_attr_sum(def_team.on_court, def_total_formula, attr_pools)
        
        if def_total == 0: def_total = 1
        
        base_rate = params.get('base_rate', 0.40)
        stat_diff = (off_total - def_total) / def_total
        
        spacing_weight = params.get('spacing_weight', 0.1)
        spacing_mod = 1.0 + (context.get('spacing', 0.0) * spacing_weight)
        
        quality_mod = 1.0 + context.get('quality', 0.0)
        
        hit_rate = (base_rate + stat_diff) * spacing_mod * quality_mod
        
        # 執行命中判定
        roll = rng.get_float(0.0, 1.0)
        is_hit = (roll <= hit_rate)
        
        # [DEBUG]
        shot_type = "3分" if is_3pt else "2分"
        self.pbp_logs.append(
            f"   [CALC] {shooter.name} {shot_type}: Off({off_total:.0f}) vs Def({def_total:.0f}) | "
            f"Base({base_rate:.2f}) + Diff({stat_diff:.2f}) + Spc({spacing_mod:.2f}) + Qual({quality_mod:.2f}) "
            f"= Rate({hit_rate:.2%}) | Roll({roll:.3f}) -> {'命中' if is_hit else '不進'}"
        )

        # --- 5.2 犯規判定 (Foul Check) ---
        # [Fix] 解析公式
        foul_off_iq_formula = self._resolve_formula(formulas.get('foul_off_iq', []), attr_pools)
        foul_def_iq_formula = self._resolve_formula(formulas.get('foul_def_iq', []), attr_pools)

        # Formula: (Off_IQ - Def_IQ) / Def_IQ
        off_iq = Calculator.get_team_attr_sum(off_team.on_court, foul_off_iq_formula, attr_pools)
        def_iq = Calculator.get_team_attr_sum(def_team.on_court, foul_def_iq_formula, attr_pools)
        
        if def_iq == 0: def_iq = 1
        foul_rate = (off_iq - def_iq) / def_iq
        
        is_foul = rng.decision(foul_rate)
        foul_desc = ""
        fouler = None
        
        if is_foul:
            fouler = rng.choice(def_team.on_court) # 隨機防守者犯規
            AttributionSystem.record_foul(fouler)
            foul_desc = f" ({fouler.name} 犯規)"

        # --- 結算流程 ---
        log_desc = ""
        keep_possession = False

        if is_hit:
            # [進球]
            AttributionSystem.record_score(off_team, shooter, points_attempt, is_3pt)
            log_desc = f"{off_team.name} {shooter.name} {points_attempt}分命中{foul_desc}"
            
            # [Spec 5.5] 助攻判定
            # Spec: (Team_Stat / 助攻係數) * 0.01
            # Spec: 助攻係數 = 1 / Luck_Sum
            # Formula Derivation: Team / (1/Luck) * 0.01 = Team * Luck * 0.01
            ast_config = sht_config.get('assist', {})
            ast_formulas = ast_config.get('formulas', {})
            
            # [Fix] 解析公式
            team_stat_formula = self._resolve_formula(ast_formulas.get('team_stat', []), attr_pools)
            luck_stat_formula = self._resolve_formula(ast_formulas.get('luck_stat', []), attr_pools)

            team_stat = Calculator.get_team_attr_sum(off_team.on_court, team_stat_formula, attr_pools)
            luck_stat = Calculator.get_team_attr_sum(off_team.on_court, luck_stat_formula, attr_pools)
            
            if luck_stat == 0: luck_stat = 1
            assist_coeff = 1.0 / luck_stat # Spec: 助攻係數 = 1 / Luck Sum
            
            # Implementation: (Team / Coeff) * Config_Value
            # This mathematically results in Team * Luck * Config_Value
            ast_prob = (team_stat / assist_coeff) * params.get('assist_prob_coeff', 0.1)
            
            if rng.decision(ast_prob):
                passer = AttributionSystem.determine_assist_provider(off_team, shooter, self.config)
                if passer:
                    AttributionSystem.record_assist(passer)
                    log_desc += f" (助攻: {passer.name})"
            
            # [And-1]
            if is_foul:
                ft_made = self._run_free_throw(shooter, 1)
                log_desc += " [And-1]"
                if ft_made: log_desc += " 加罰命中"
                
        else:
            # [不進]
            AttributionSystem.record_attempt(shooter, is_3pt)
            log_desc = f"{off_team.name} {shooter.name} {points_attempt}分不進{foul_desc}"
            
            if is_foul:
                # [罰球]
                ft_count = 3 if is_3pt else 2
                ft_made = self._run_free_throw(shooter, ft_count)
                log_desc += f" 獲罰球 ({ft_made}/{ft_count})"
            else:
                # [Spec 5.4] 籃板判定
                reb_config = sht_config.get('rebound', {})
                reb_params = reb_config.get('params', {})
                reb_formulas = reb_config.get('formulas', {})
                
                # [Fix] 解析公式
                reb_off_formula = self._resolve_formula(reb_formulas.get('off_attr', []), attr_pools)
                reb_def_formula = self._resolve_formula(reb_formulas.get('def_attr', []), attr_pools)

                off_reb_attr = Calculator.get_team_attr_sum(off_team.on_court, reb_off_formula, attr_pools)
                def_reb_attr = Calculator.get_team_attr_sum(def_team.on_court, reb_def_formula, attr_pools)
                
                total_reb = off_reb_attr + def_reb_attr
                if total_reb == 0: total_reb = 1
                
                # Def_Reb_Rate = 10% + Def / Total
                dr_prob = reb_params.get('def_base_rate', 0.10) + (def_reb_attr / total_reb)
                
                if rng.decision(dr_prob):
                    # 防守籃板 (Fix: 參數修正)
                    # is_defensive=True, is_offensive=False
                    rebounder = AttributionSystem.determine_rebounder(def_team, off_team, True, self.config)
                    AttributionSystem.record_rebound(rebounder, False)
                    log_desc += f" (籃板: {def_team.name} {rebounder.name})"
                    keep_possession = False
                else:
                    # 進攻籃板 (Fix: 參數修正)
                    # is_defensive=False, is_offensive=True
                    rebounder = AttributionSystem.determine_rebounder(off_team, def_team, False, self.config)
                    AttributionSystem.record_rebound(rebounder, True)
                    log_desc += f" (進攻籃板: {off_team.name} {rebounder.name})"
                    keep_possession = True # [Spec 5.4.C] 繼續進攻

        return log_desc, keep_possession