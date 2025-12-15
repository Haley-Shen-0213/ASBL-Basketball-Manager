# app/services/match_engine/systems/stamina.py

from typing import Dict
from ..structures import EnginePlayer

class StaminaSystem:
    """
    體力系統 (Level 3) - Config Driven
    完全依賴傳入的 config 字典進行計算，不寫死任何係數。
    對應 Spec v1.5 Section 2
    """

    @staticmethod
    def update_stamina(player: EnginePlayer, seconds: float, is_on_court: bool, config: Dict):
        """
        更新球員體力。
        """
        # 1. 讀取設定參數
        me_config = config.get('match_engine', {})
        gen_config = me_config.get('general', {})
        sys_config = me_config.get('stamina_system', {})
        
        # 取得屬性名稱 (從 Config 定義)
        # 預設值為 Spec 定義的欄位，防呆用
        drain_attrs = sys_config.get('drain_attrs', ['ath_stamina', 'talent_health'])
        recover_attrs = sys_config.get('recover_attrs', ['ath_stamina', 'talent_health'])
        
        # 取得係數
        drain_coeff = gen_config.get('stamina_drain_coeff', 3.0)
        
        # 2. 取得球員屬性並轉為百分比 (0.01 ~ 0.99)
        # 注意: Config 定義 drain_attrs[0] 是體能, [1] 是健康
        stamina_val = getattr(player, drain_attrs[0], 50)
        health_val = getattr(player, drain_attrs[1], 50)
        
        stamina_pct = max(0.01, min(0.99, stamina_val / 100.0))
        health_pct = max(0.01, min(0.99, health_val / 100.0))

        change_per_minute = 0.0

        if is_on_court:
            # [Spec 2.3] 消耗公式
            # 消耗量/分 = Coeff * [1 + (1 - 體能%)] + (1 - 健康%)
            drain_per_min = drain_coeff * (1.0 + (1.0 - stamina_pct)) + (1.0 - health_pct)
            change_per_minute = -drain_per_min
        else:
            # [Spec 2.4] 恢復公式
            # 恢復量/分 = 1.0 + (體能%) - (1 - 健康%)
            # 這裡假設基礎恢復速率固定為 1.0 (Spec未定義此參數為變數，若需要可加入Config)
            base_recover = 1.0 
            recover_per_min = base_recover + stamina_pct - (1.0 - health_pct)
            change_per_minute = recover_per_min

        # 3. 應用變更
        change = (change_per_minute / 60.0) * seconds
        new_val = player.current_stamina + change
        
        # 限制範圍
        if new_val > 100.0: new_val = 100.0
        elif new_val < 1.0: new_val = 1.0
        
        player.current_stamina = new_val

        # 4. 更新修正係數
        StaminaSystem._update_coefficient(player, gen_config)

    @staticmethod
    def _update_coefficient(player: EnginePlayer, gen_config: Dict):
        """
        [Spec 2.2] 能力值動態修正
        """
        threshold = gen_config.get('stamina_nerf_threshold', 80.0)
        min_multiplier = gen_config.get('stamina_min_multiplier', 0.21)
        
        current = player.current_stamina

        if current >= threshold:
            player.stamina_coeff = 1.0
        elif current > 1.0:
            # 線性衰退公式: 1.0 - (閾值 - 當前) * 0.01
            penalty = (threshold - current) * 0.01
            player.stamina_coeff = 1.0 - penalty
        else:
            # 極限狀態
            player.stamina_coeff = min_multiplier

    @staticmethod
    def apply_halftime_recovery(team_players: list, config: Dict):
        """[Spec 2.1] 中場回復"""
        me_config = config.get('match_engine', {})
        recovery_amount = me_config.get('general', {}).get('stamina_recovery_halftime', 20)
        
        for player in team_players:
            player.current_stamina = min(100.0, player.current_stamina + recovery_amount)
            # 更新係數需要傳入 config
            StaminaSystem._update_coefficient(player, me_config.get('general', {}))