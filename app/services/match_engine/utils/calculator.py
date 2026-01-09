# app/services/match_engine/utils/calculator.py

from typing import List, Dict, Optional, Union
from ..structures import EnginePlayer

class Calculator:
    """
    通用公式計算器 (Level 2)。
    修正: 
    1. 移除 Python 內寫死的 ALL_ATTRIBUTE_NAMES。
    2. 支援遞迴解析 attr_pools，實現真正的 Config Driven。
    3. 投籃公式正確讀取 spacing_weight。
    4. 同步 Spec v2.2 技巧加成 (Skill Bonus) 邏輯。
    5. calculate_shooting_rate 支援 3分球特殊邏輯 (Multiplier & Base Rate)。
    """

    @staticmethod
    def _resolve_formula_keys(formula: Union[str, List[str]], attr_pools: Dict) -> List[str]:
        """Helper: 解析 Config 中的屬性列表引用"""
        if isinstance(formula, str):
            return attr_pools.get(formula, [])
        return formula

    @staticmethod
    def get_player_attr_sum(player: EnginePlayer, attrs: List[str], attr_pools: Optional[Dict[str, List[str]]] = None) -> float:
        """
        計算球員指定屬性列表的總和。
        
        Args:
            player: 球員物件
            attrs: 屬性名稱列表 (可包含 pool key)
            attr_pools: 屬性池字典 (用於遞迴展開 pool key)
        """
        total = 0.0
        coeff = player.stamina_coeff

        for attr in attrs:
            is_negative = False
            clean_attr = attr
            
            # 處理負號語法 (如 '-height')
            if attr.startswith('-'):
                is_negative = True
                clean_attr = attr[1:]

            # 1. 嘗試直接從球員取得屬性
            if hasattr(player, clean_attr):
                val = getattr(player, clean_attr)
                
                # 體力修正: 只有數值型屬性才乘係數 (height 不乘)
                if clean_attr != 'height':
                    val *= coeff
                
                if is_negative:
                    total -= val
                else:
                    total += val
            
            # 2. 若球員無此屬性，檢查是否為 Pool Key (遞迴展開)
            elif attr_pools and clean_attr in attr_pools:
                # 遞迴呼叫: 傳入 pool 定義的列表
                sub_total = Calculator.get_player_attr_sum(player, attr_pools[clean_attr], attr_pools)
                
                if is_negative:
                    total -= sub_total
                else:
                    total += sub_total
        
        return total

    @staticmethod
    def get_team_attr_sum(players: List[EnginePlayer], attrs: List[str], attr_pools: Optional[Dict[str, List[str]]] = None) -> float:
        """計算一組球員的屬性總和"""
        return sum(Calculator.get_player_attr_sum(p, attrs, attr_pools) for p in players)

    @staticmethod
    def calculate_shooting_rate(
        off_players: List[EnginePlayer], # [Fix] 改為傳入進攻全隊
        def_players: List[EnginePlayer],
        shooter: EnginePlayer,           # [Fix] 新增參數：出手者 (用於技巧加成)
        config: Dict,
        spacing_factor: float = 0.0,
        quality_bonus: float = 0.0,
        is_3pt: bool = False
    ) -> float:
        """
        [Spec 5.1 & 5.2] 投籃命中率計算 (修正版)
        邏輯:
          - 對抗 (Off_Total vs Def_Total): 使用 Team Sum vs Team Sum
          - 技巧 (Skill Bonus): 使用 Shooter Individual Stats
        """
        # 1. 導航 Config
        me_config = config.get('match_engine', {})
        shooting_config = me_config.get('shooting', {})
        formulas = shooting_config.get('formulas', {})
        params = shooting_config.get('params', {})
        attr_pools = me_config.get('attr_pools', {})

        # 2. 決定基礎命中率 (Base Rate)
        base_rate = params.get('base_rate_3pt', 0.20) if is_3pt else params.get('base_rate_2pt', 0.40)

        # 3. 計算進攻總值 (Offensive Rating) - [Fix] 使用 get_team_attr_sum
        base_off_keys = Calculator._resolve_formula_keys(formulas.get('off_total', 'off_13'), attr_pools)
        off_sum = Calculator.get_team_attr_sum(off_players, base_off_keys, attr_pools)

        if is_3pt:
            # [Spec 5.2.A] 3分球特殊加成 (也是看團隊)
            bonus_keys = Calculator._resolve_formula_keys(formulas.get('bonus_3pt_attrs', []), attr_pools)
            bonus_sum = Calculator.get_team_attr_sum(off_players, bonus_keys, attr_pools)
            mult = params.get('multiplier_3pt', 2.0)
            off_sum += bonus_sum * (mult - 1.0)

        # 4. 計算防守總值 (Defensive Rating)
        def_keys = Calculator._resolve_formula_keys(formulas.get('def_total', 'def_12'), attr_pools)
        def_sum = Calculator.get_team_attr_sum(def_players, def_keys, attr_pools)
        if def_sum == 0: def_sum = 1

        # 5. 計算技巧加成 (Skill Bonus) - [Fix] 針對 shooter 個人計算
        skill_keys = Calculator._resolve_formula_keys(formulas.get('skill_bonus_attrs', ['shot_accuracy', 'shot_range', 'off_move']), attr_pools)
        skill_sum = Calculator.get_player_attr_sum(shooter, skill_keys, attr_pools)
        skill_divisor = params.get('skill_bonus_divisor', 800.0)
        skill_multiplier = 1.0 + (skill_sum / skill_divisor)

        # 6. 最終公式計算
        stat_diff = (off_sum - def_sum) / def_sum
        spacing_weight = params.get('spacing_weight', 0.1)
        
        final_rate = (base_rate + stat_diff) * skill_multiplier * (1.0 + spacing_factor * spacing_weight) * (1.0 + quality_bonus)
        
        return max(0.01, min(0.99, final_rate))