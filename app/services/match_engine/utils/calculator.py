# app/services/match_engine/utils/calculator.py

from typing import List, Dict, Optional
from ..structures import EnginePlayer

class Calculator:
    """
    通用公式計算器 (Level 2)。
    修正: 
    1. 移除 Python 內寫死的 ALL_ATTRIBUTE_NAMES。
    2. 支援遞迴解析 attr_pools，實現真正的 Config Driven。
    3. 投籃公式正確讀取 spacing_weight。
    """

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
            
            # 3. 既非屬性也非 Pool，視為 0 (或可選擇噴錯)
            else:
                pass 
        
        return total

    @staticmethod
    def get_team_attr_sum(players: List[EnginePlayer], attrs: List[str], attr_pools: Optional[Dict[str, List[str]]] = None) -> float:
        """計算一組球員的屬性總和"""
        return sum(Calculator.get_player_attr_sum(p, attrs, attr_pools) for p in players)

    @staticmethod
    def resolve_diff_formula(
        off_val: float, 
        def_val: float, 
        base: float, 
        coeff: float,
        min_limit: float = 0.0,
        max_limit: float = 1.0
    ) -> float:
        """通用差值公式: Base + (Off - Def) * Coeff"""
        prob = base + (off_val - def_val) * coeff
        return max(min_limit, min(max_limit, prob))

    @staticmethod
    def resolve_ratio_formula(off_val: float, def_val: float) -> float:
        """通用比率公式: Off / Def"""
        if def_val == 0: return 999.0 
        return off_val / def_val

    @staticmethod
    def calculate_shooting_rate(
        off_player: EnginePlayer,
        def_players: List[EnginePlayer],
        config: Dict,
        spacing_factor: float = 0.0,
        quality_bonus: float = 0.0
    ) -> float:
        """
        [Spec 5.1] 投籃命中率計算
        """
        # 1. 導航 Config
        me_config = config.get('match_engine', {})
        shooting_config = me_config.get('shooting', {})
        formulas = shooting_config.get('formulas', {})
        params = shooting_config.get('params', {})
        attr_pools = me_config.get('attr_pools', {})

        # 2. 取得 Key
        off_key = formulas.get('off_total', 'off_13')
        def_key = formulas.get('def_total', 'def_12')
        
        # 3. 取得列表 (這裡直接傳 key 給 get_player_attr_sum 也可以，但為了明確性先取出來)
        # 修正邏輯: 因為現在支援遞迴，我們其實可以直接傳 [off_key] 進去，
        # 但為了保險起見，還是先嘗試從 attr_pools 拿，拿不到就當作 list
        off_attrs = attr_pools.get(off_key, [off_key])
        def_attrs = attr_pools.get(def_key, [def_key])

        # 4. 計算數值 (傳入 attr_pools 以支援遞迴)
        off_sum = Calculator.get_player_attr_sum(off_player, off_attrs, attr_pools)
        def_sum = Calculator.get_team_attr_sum(def_players, def_attrs, attr_pools)

        # 5. 參數應用
        base_rate = params.get('base_rate', 0.40)
        spacing_weight = params.get('spacing_weight', 0.1)
        
        if def_sum == 0: def_sum = 1
        
        # 6. 公式計算
        raw_rate = base_rate + (off_sum - def_sum) / def_sum
        final_spacing_mult = 1.0 + (spacing_factor * spacing_weight)
        final_rate = raw_rate * final_spacing_mult * (1.0 + quality_bonus)
        
        return max(0.01, min(0.99, final_rate))