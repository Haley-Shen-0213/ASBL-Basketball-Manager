# app/services/match_engine/core.py

from typing import Dict, List, Optional, Tuple
import math

from .structures import EngineTeam, EnginePlayer, MatchState, MatchResult
from .utils.calculator import Calculator
from .utils.rng import rng
from .systems.stamina import StaminaSystem
from .systems.substitution import SubstitutionSystem
from .systems.attribution import AttributionSystem

class MatchEngine:
    """
    ASBL 比賽引擎核心 (Level 4)
    負責控制比賽流程、時間流逝、調度與事件觸發。
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
        1. 計算位置評分
        2. 分配上場時間
        3. 決定先發陣容
        4. 鎖定 Best 5
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
        # 若多位 Star，依據他們在最佳位置的分數高低排序，高者先選
        # (這裡簡化處理，直接依球員順序，若需極致優化可再排)
        for p in stars:
            try_fill_position(p)

        # 2. Starter 填補
        starter_players = [p for p in team.roster if p.role == 'Starter' and p.id not in taken_ids]
        for p in starter_players:
            try_fill_position(p)

        # 3. 剩餘填補 (Fill Gaps)
        # 若還有空缺，從剩餘球員中找該位置分數最高的
        remaining_players = [p for p in team.roster if p.id not in taken_ids]
        
        for i, pos in enumerate(positions):
            if starters[i] is None:
                # 找剩餘球員中這個位置分數最高的
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
                    # 從剩餘名單移除以加速後續搜尋 (非必要但好習慣)
                    # remaining_players.remove(best_p) 

        # 4. 分配至 EngineTeam
        team.on_court = [p for p in starters if p is not None]
        team.bench = [p for p in team.roster if p.id not in taken_ids]
        
        # 防呆: 如果先發不足 5 人 (極端情況)，從板凳拉人
        while len(team.on_court) < 5 and team.bench:
            p = team.bench.pop(0)
            # 隨便找個空位塞
            for i, pos in enumerate(positions):
                if starters[i] is None:
                    p.position = pos
                    starters[i] = p
                    team.on_court.append(p)
                    break