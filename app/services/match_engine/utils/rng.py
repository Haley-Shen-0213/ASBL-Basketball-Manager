# app/services/match_engine/utils/rng.py
import random
from typing import List, Any, Optional

# [Optimization] 將方法綁定移至模組層級 (Module Level)
# 這避免了在 Python 3.13+ 中，將綁定方法(Bound Method)指派給類別屬性時可能發生的參數傳遞錯誤。
# 同時保留了減少屬性查找(Attribute Lookup)的效能優勢。
_sys_random = random.random
_sys_uniform = random.uniform
_sys_choice = random.choice

class RNG:
    """
    極致效能優化版的隨機數生成器。
    針對「單次、高頻率」呼叫場景優化 (Event-Driven Simulation)。
    """
    __slots__ = () # 節省記憶體
    
    # 如果未來需要固定 Seed，可以在這裡實作初始化
    @classmethod
    def seed(cls, seed_val: Any):
        random.seed(seed_val)

    @staticmethod
    def get_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        回傳 [min_val, max_val] 之間的浮點數。
        """
        # 直接呼叫模組層級的別名，避免類別屬性查找的開銷與綁定問題
        return _sys_uniform(min_val, max_val)

    @staticmethod
    def decision(probability: float) -> bool:
        """
        判定事件是否發生。
        probability: 0.0 ~ 1.0
        """
        # 優化：減少邊界檢查，假設呼叫端會傳入合法數值
        return _sys_random() < probability

    @staticmethod
    def choice(items: List[Any]) -> Any:
        """
        從列表中選擇一個項目。
        """
        return _sys_choice(items)

    @staticmethod
    def weighted_index(weights: List[float]) -> int:
        """
        根據權重回傳索引值。
        這是效能瓶頸點，Python 原生迴圈較慢。
        如果 weights 長度固定且很短 (如 5個位置)，這段 Python code 夠快。
        """
        r = _sys_random() * sum(weights)
        upto = 0.0
        for i, w in enumerate(weights):
            if w + upto >= r:
                return i
            upto += w
        return len(weights) - 1

# 為了方便其他模組呼叫，直接暴露實例或類別
rng = RNG