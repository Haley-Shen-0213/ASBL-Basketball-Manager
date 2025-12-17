# app/services/team_creator.py

from collections import Counter
from app.services.player_generator import PlayerGenerator
from app.utils.game_config_loader import GameConfigLoader

class TeamCreator:
    """
    ASBL 開隊陣容生成服務 (Pure Logic Version)
    只負責生成符合規則的球員資料結構，不涉及資料庫寫入。
    對應規格書: Player System Specification v2.2 Section 5
    """

    @classmethod
    def create_valid_roster(cls, max_attempts=1000):
        """
        [Spec 5] 生成符合檢核條件的 15 人名單
        邏輯: 生成 -> 檢查 -> 若失敗則整隊重骰
        Returns:
            List[Dict]: 包含 15 個球員 Payload 的列表
        """
        # 1. 從參數檔讀取設定
        # {SSR: 1, SS: 1, S: 1, A: 2, B: 2, C: 3, G: 5}
        comp_rules = GameConfigLoader.get('team_creation.composition_count')
        
        # {min_c: 2, min_pg: 2, min_guards: 4, min_forwards: 4}
        val_rules = GameConfigLoader.get('team_creation.validation')

        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            roster = []

            # 2. 依據等級分佈生成球員
            for grade, count in comp_rules.items():
                for _ in range(count):
                    # 呼叫 PlayerGenerator 生成單一球員 Payload
                    player_payload = PlayerGenerator.generate_payload(specific_grade=grade)
                    roster.append(player_payload)

            # 3. 執行陣容檢核
            if cls._validate_roster(roster, val_rules):
                return roster
        
        raise Exception(f"Failed to generate a valid team after {max_attempts} attempts. Please check config constraints.")

    @staticmethod
    def _validate_roster(roster, rules):
        """
        [Spec 5] 檢核條件邏輯
        """
        # 統計位置數量
        positions = [p['position'] for p in roster]
        counts = Counter(positions)
        
        # 1. C (中鋒) 數量至少 min_c
        if counts['C'] < rules.get('min_c', 2):
            return False
        
        # 2. PG (控球後衛) 數量至少 min_pg
        if counts['PG'] < rules.get('min_pg', 2):
            return False
        
        # 3. 後衛組 (PG + SG) 總數至少 min_guards
        guard_count = counts['PG'] + counts['SG']
        if guard_count < rules.get('min_guards', 4):
            return False
        
        # 4. 前鋒組 (PF + SF) 總數至少 min_forwards
        forward_count = counts['PF'] + counts['SF']
        if forward_count < rules.get('min_forwards', 4):
            return False
            
        return True