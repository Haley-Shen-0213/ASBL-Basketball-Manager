# app/services/team_creator.py

from collections import Counter
from app.services.player_generator import PlayerGenerator
from app.utils.game_config_loader import GameConfigLoader

class TeamCreator:
    """
    ASBL 開隊陣容生成服務 (Pure Logic Version)
    只負責生成符合規則的球員資料結構，不涉及資料庫寫入。
    對應規格書: Player System Specification v3.2 Section 5
    """

    @classmethod
    def create_valid_roster(cls, max_attempts=1000):
        """
        [Spec 5] 生成符合檢核條件的 15 人名單
        邏輯: 
          1. 依據等級分佈生成球員
          2. [Spec 5.4] 針對每一位生成的球員進行「下限檢核」，不合格則單兵重骰
          3. [Spec 5.2] 針對整隊進行「位置檢核」，不合格則整隊重骰
        Returns:
            List[Dict]: 包含 15 個球員 Payload 的列表
        """
        # 1. 從參數檔讀取設定
        comp_rules = GameConfigLoader.get('team_creation.composition_count')
        val_rules = GameConfigLoader.get('team_creation.validation')
        
        # [Spec 5.4] 讀取開隊特殊規則參數
        min_ratio = GameConfigLoader.get('team_creation.initial_team_min_ratio', 0.5)
        trainable_caps = GameConfigLoader.get('generation.trainable_caps')
        trainable_attrs = GameConfigLoader.get('generation.attributes.trainable')

        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            roster = []

            # 2. 依據等級分佈生成球員
            # 注意: Python 3.7+ 字典保持插入順序，通常 SSR 會先被執行
            for grade, count in comp_rules.items():
                # 取得該等級的能力上限，用於計算下限門檻
                grade_cap = trainable_caps.get(grade, 9999)
                lower_bound = grade_cap * min_ratio

                for _ in range(count):
                    # 單兵生成迴圈 (針對下限檢核)
                    player_payload = cls._generate_qualified_player(
                        grade, 
                        lower_bound, 
                        trainable_attrs
                    )
                    roster.append(player_payload)

            # 3. 執行整隊陣容檢核 (位置數量)
            if cls._validate_roster_positions(roster, val_rules):
                return roster
        
        raise Exception(f"Failed to generate a valid team after {max_attempts} attempts. Please check config constraints.")

    @classmethod
    def _generate_qualified_player(cls, grade, lower_bound, trainable_attrs, max_single_attempts=100):
        """
        [Spec 5.4] 生成並檢核單一球員是否符合開隊下限
        若生成的球員能力總和低於 lower_bound，則視為無效(太弱)，重新生成。
        """
        for _ in range(max_single_attempts):
            # 呼叫純粹的生成器
            payload = PlayerGenerator.generate_payload(specific_grade=grade)
            
            # [Fix] 修正屬性讀取路徑
            # PlayerGenerator 可能將數值放在 'raw_stats' (扁平) 或 'attributes' (巢狀)
            stats_source = {}
            
            if 'raw_stats' in payload:
                # 優先使用 raw_stats，因為這是最完整的扁平化數據
                stats_source = payload['raw_stats']
            else:
                # Fallback: 嘗試解析 attributes 結構
                attrs = payload.get('attributes', {})
                if 'trainable' in attrs:
                    # 若結構為 {'attributes': {'trainable': {...}}}
                    stats_source = attrs['trainable']
                else:
                    # 若結構為 {'attributes': {...扁平...}}
                    stats_source = attrs

            # 計算可訓練能力總和
            total_score = sum(stats_source.get(attr, 0) for attr in trainable_attrs)

            # 檢核下限
            if total_score >= lower_bound:
                return payload
        
        # 若連續 100 次都失敗，通常代表數據讀取錯誤 (total_score=0) 或下限設定不合理
        raise Exception(f"Failed to generate a qualified player for grade {grade} (Target > {lower_bound}). Last Score: {total_score}")

    @staticmethod
    def _validate_roster_positions(roster, rules):
        """
        [Spec 5.2] 檢核整隊位置分佈
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