# app/services/match_engine/utils/rng.py
import random
from typing import List, Any, Optional

class RNG:
    """
    極致效能優化版的隨機數生成器。
    針對「單次、高頻率」呼叫場景優化 (Event-Driven Simulation)。
    """
    __slots__ = () # 節省記憶體，雖然此類別通常只用 staticmethod
    
    # 直接綁定 random 模組的底層函數到類別屬性
    # 這樣可以減少每次呼叫時的 module lookup (字典查詢) 開銷
    _random = random.random
    _uniform = random.uniform
    _choice = random.choice
    
    # 如果未來需要固定 Seed，可以在這裡實作初始化
    @classmethod
    def seed(cls, seed_val: Any):
        random.seed(seed_val)

    @staticmethod
    def get_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
        """
        回傳 [min_val, max_val] 之間的浮點數。
        優化：直接使用綁定的 _random 進行線性運算，比呼叫 random.uniform 快一點點
        """
        # 邏輯: min + (max - min) * random()
        # 這裡直接用 random.uniform 其實已經是 C 實作，差異極小，
        # 但為了極致，我們使用綁定的 _uniform
        return RNG._uniform(min_val, max_val)

    @staticmethod
    def decision(probability: float) -> bool:
        """
        判定事件是否發生。
        probability: 0.0 ~ 1.0
        優化：減少邊界檢查，假設呼叫端會傳入合法數值，以換取速度。
        """
        # 在 100 萬場模擬中，這行會被呼叫上億次，省去 if check 至關重要
        # 若 probability > 1.0，random() < prob 恆為 True，邏輯正確
        # 若 probability < 0.0，random() < prob 恆為 False，邏輯正確
        return RNG._random() < probability

    @staticmethod
    def choice(items: List[Any]) -> Any:
        """
        從列表中選擇一個項目。
        """
        return RNG._choice(items)

    @staticmethod
    def weighted_index(weights: List[float]) -> int:
        """
        根據權重回傳索引值。
        這是效能瓶頸點，Python 原生迴圈較慢。
        如果 weights 長度固定且很短 (如 5個位置)，這段 Python code 夠快。
        如果很長，這部分才是未來需要用 numpy 優化的地方。
        """
        r = RNG._random() * sum(weights)
        upto = 0.0
        for i, w in enumerate(weights):
            if w + upto >= r:
                return i
            upto += w
        return len(weights) - 1

# 為了方便其他模組呼叫，直接暴露實例或類別
# 但為了效能，建議其他模組直接 import RNG class 並呼叫靜態方法
rng = RNG