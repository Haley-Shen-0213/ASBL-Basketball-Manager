# app/services/player_generator.py
import random
import math
from sqlalchemy.sql.expression import func
from app import db
from app.models.player import Player, Contract
from app.models.system import NameLibrary
from app.utils.game_config_loader import GameConfigLoader

# ==========================================
# ASBL Player Generator Service
# Based on Specification v2.6 (Attributes Updated)
# ==========================================

class PlayerGenerator:
    
    # [Spec v2.6 Section 2.3] 屬性映射表
    # Key: game_config.yaml 中的設定鍵值
    # Value: (Category, DB_Field_Key) 存入資料庫的結構路徑
    ATTR_MAPPING = {
        # === Untrainable Stats (天賦) ===
        "ath_stamina":   ("physical", "stamina"),
        "ath_strength":  ("physical", "strength"),
        "ath_speed":     ("physical", "speed"),
        "ath_jump":      ("physical", "jumping"),
        "talent_health": ("physical", "health"),
        
        "shot_touch":    ("offense", "touch"),    # 修正: inside -> touch
        "shot_release":  ("offense", "release"),  # 修正: 獨立欄位，不再與 accuracy 衝突
        
        "talent_offiq":  ("mental", "off_iq"),
        "talent_defiq":  ("mental", "def_iq"),
        "talent_luck":   ("mental", "luck"),
        
        # === Trainable Stats (技術) ===
        "shot_accuracy": ("offense", "accuracy"), # 修正: mid_range -> accuracy
        "shot_range":    ("offense", "range"),    # 修正: three_point -> range
        
        "off_pass":      ("offense", "passing"),
        "off_dribble":   ("offense", "dribble"),
        "off_handle":    ("offense", "handle"),
        "off_move":      ("offense", "move"),
        
        "def_rebound":   ("defense", "rebound"),
        "def_boxout":    ("defense", "boxout"),
        "def_contest":   ("defense", "contest"),
        "def_disrupt":   ("defense", "disrupt")
    }

    @staticmethod
    def _get_random_text(category, length_filter=None):
        """從資料庫隨機取得姓名"""
        query = NameLibrary.query.filter_by(category=category)
        
        if length_filter:
            if length_filter == '1':
                query = query.filter(func.char_length(NameLibrary.text) == 1)
            elif length_filter == '2':
                query = query.filter(func.char_length(NameLibrary.text) == 2)
            elif length_filter == '3+':
                query = query.filter(func.char_length(NameLibrary.text) >= 3)
        
        obj = query.order_by(func.random()).first()
        # Fallback: 如果找不到特定長度的字，則隨機取一個
        if not obj and length_filter:
             obj = NameLibrary.query.filter_by(category=category).order_by(func.random()).first()
             
        return obj.text if obj else ""

    @classmethod
    def _generate_name(cls):
        """生成符合規則的姓名 (Spec v2.2)"""
        r = random.random()
        # 姓氏長度機率: 單字(80%), 雙字(15%), 長字(5%)
        if r < 0.80: len_filter = '1'
        elif r < 0.95: len_filter = '2'
        else: len_filter = '3+'
            
        last_name = cls._get_random_text('last', length_filter=len_filter) or "無名"
        first_name = cls._get_random_text('first') or "氏"
        full_name = last_name + first_name
        
        # 補字邏輯
        should_add_char = False
        if len(full_name) <= 2:
            if random.choice([True, False]): should_add_char = True
        elif len(last_name) > 1 and len(first_name) == 1:
            if random.choice([True, False]): should_add_char = True
        
        if should_add_char:
            second_char = cls._get_random_text('first')
            # 防呆: 只有當補的字是單字時才加上，避免變成四字以上怪名
            if second_char and len(second_char) == 1:
                full_name += second_char
        
        return full_name

    @staticmethod
    def _generate_height():
        """生成身高 (Box-Muller Transform)"""
        mean, std_dev = 195, 10
        min_h, max_h = 160, 230
        while True:
            u1, u2 = random.random(), random.random()
            z = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
            height = mean + z * std_dev
            if min_h <= height <= max_h:
                return min(int(round(height)), max_h)

    @staticmethod
    def _pick_position(height_cm):
        """根據身高決定位置 (機率分佈)"""
        r = random.random()
        if height_cm < 190:
            return "PG" if r < 0.60 else "SG"
        elif height_cm < 200:
            if r < 0.35: return "PG"
            elif r < 0.80: return "SG"
            else: return "SF"
        elif height_cm < 210:
            if r < 0.05: return "PG"
            elif r < 0.15: return "SG"
            elif r < 0.35: return "SF"
            elif r < 0.85: return "PF"
            else: return "C"
        else:
            if r < 0.05: return "PG"
            elif r < 0.15: return "SG"
            elif r < 0.25: return "SF"
            elif r < 0.55: return "PF"
            else: return "C"

    @classmethod
    def _generate_stats_by_grade(cls, grade):
        """根據等級生成屬性 (Spec v2.3 & v2.6)"""
        untrainable_keys = GameConfigLoader.get('generation.attributes.untrainable')
        trainable_keys = GameConfigLoader.get('generation.attributes.trainable')
        
        u_rule = GameConfigLoader.get(f'generation.untrainable_rules.{grade}')
        t_cap = GameConfigLoader.get(f'generation.trainable_caps.{grade}')

        # 1. 生成 Untrainable Stats (天賦)
        stat_min, stat_max = u_rule["stat_min"], u_rule["stat_max"]
        stats = {k: stat_min for k in untrainable_keys}
        
        target_sum = random.randint(u_rule["sum_min"], u_rule["sum_max"])
        remaining = target_sum - sum(stats.values())
        capacity = {k: (stat_max - stats[k]) for k in untrainable_keys}

        while remaining > 0:
            candidates = [k for k in untrainable_keys if capacity[k] > 0]
            if not candidates: break
            k = random.choice(candidates)
            step = min(remaining, capacity[k], random.randint(1, 3))
            stats[k] += step
            capacity[k] -= step
            remaining -= step
        
        # 2. 生成 Trainable Stats (技術) - Reroll 機制
        while True:
            trainable_stats = {k: random.randint(1, 99) for k in trainable_keys}
            if sum(trainable_stats.values()) <= t_cap:
                break
        
        stats.update(trainable_stats)
        return stats

    @classmethod
    def generate_payload(cls, specific_grade=None):
        """
        [核心] 生成單一球員數據 Payload (不寫入 DB)
        """
        if specific_grade:
            grade = specific_grade
        else:
            grades = GameConfigLoader.get('generation.grades')
            weights = GameConfigLoader.get('generation.grade_weights')
            grade = random.choices(grades, weights=weights, k=1)[0]

        name = cls._generate_name()
        height = cls._generate_height()
        position = cls._pick_position(height)
        
        # Spec v2.4 年齡生成
        age_base = GameConfigLoader.get('generation.age_rules.base', 18)
        age_offset = GameConfigLoader.get(f'generation.age_rules.offsets.{grade}', 6)
        age = age_base + random.randint(0, age_offset)

        raw_stats = cls._generate_stats_by_grade(grade)
        total_stats_sum = sum(raw_stats.values())

        # Spec v2.1 薪資計算
        salary_factor = GameConfigLoader.get(f'generation.salary_factors.{grade}', 1.0)
        salary = int(round(total_stats_sum * salary_factor))

        # Spec v2.4 初始合約
        contract_rule = GameConfigLoader.get(f'generation.contracts.{grade}')
        
        # 根據 ATTR_MAPPING 組裝詳細屬性結構
        detailed_stats = {
            "physical": {}, "offense": {}, "defense": {}, "mental": {}
        }
        
        for config_key, (category, model_key) in cls.ATTR_MAPPING.items():
            if config_key in raw_stats:
                detailed_stats[category][model_key] = raw_stats[config_key]

        return {
            "name": name,
            "grade": grade,
            "age": age,
            "height": height,
            "position": position,
            "rating": int(total_stats_sum / 20),
            "salary": salary,
            "contract_rule": contract_rule,
            "detailed_stats": detailed_stats,
            "raw_stats": raw_stats
        }

    # ====================================================
    # 輸出方式 1: 大數據測試用 (CSV/Flat Format)
    # ====================================================
    @staticmethod
    def to_flat_dict(payload):
        """
        將巢狀的 payload 攤平成單層字典，方便匯出 CSV 或 Pandas 分析。
        """
        flat = {
            "name": payload['name'],
            "grade": payload['grade'],
            "age": payload['age'],
            "height": payload['height'],
            "position": payload['position'],
            "rating": payload['rating'],
            "salary": payload['salary'],
            "contract_years": payload['contract_rule']['years'],
            "contract_role": payload['contract_rule']['role']
        }
        
        # 將詳細屬性攤平，例如: physical_speed, offense_accuracy
        for category, stats in payload['detailed_stats'].items():
            for key, val in stats.items():
                flat[f"{category}_{key}"] = val
                
        return flat

    # ====================================================
    # 輸出方式 2: 正式營運用 (MySQL/SQLAlchemy)
    # ====================================================
    @classmethod
    def save_to_db(cls, payload, user_id=None, team_id=None):
        """
        將 Payload 轉換為 ORM 物件並寫入資料庫
        """
        player = Player(
            name=payload['name'],
            age=payload['age'],
            height=payload['height'],
            position=payload['position'],
            rating=payload['rating'],
            detailed_stats=payload['detailed_stats'],
            user_id=user_id,
            team_id=team_id,
            training_points=0
        )
        db.session.add(player)
        db.session.flush()

        contract_data = None
        if team_id:
            rule = payload['contract_rule']
            contract = Contract(
                player_id=player.id,
                team_id=team_id,
                salary=payload['salary'],
                years=rule['years'],
                years_left=rule['years'],
                role=rule['role']
            )
            db.session.add(contract)
            contract_data = rule

        return player, contract_data

    # ====================================================
    # 舊接口相容 (預設走 DB)
    # ====================================================
    @classmethod
    def generate_and_persist(cls, count=1, user_id=None, team_id=None):
        new_players_preview = []
        try:
            for _ in range(count):
                payload = cls.generate_payload()
                player, contract_rule = cls.save_to_db(payload, user_id, team_id)
                
                preview_data = {
                    "player_id": player.id,
                    "player_name": player.name,
                    "grade": payload['grade'],
                    "age": player.age,
                    "salary": payload['salary'],
                    "contract": contract_rule
                }
                new_players_preview.append(preview_data)

            db.session.commit()
            return {"total_inserted": count, "preview": new_players_preview}

        except Exception as e:
            db.session.rollback()
            print(f"Error in generate_and_persist: {e}")
            return {"total_inserted": 0, "preview": []}