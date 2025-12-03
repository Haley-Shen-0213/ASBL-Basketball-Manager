# app/services/player_generator.py
import random
import math
from sqlalchemy.sql.expression import func
from app import db
from app.models.player import Player, Contract
from app.models.system import NameLibrary

# ==========================================
# ASBL Player Generator Service
# Based on Specification v2.4
# ==========================================

STAT_MIN, STAT_MAX = 1, 99

OVERALL_GRADES = ["G", "C", "B", "A", "S", "SS", "SSR"]
OVERALL_GRADE_WEIGHTS = [0.28, 0.26, 0.22, 0.14, 0.07, 0.025, 0.005]

GRADE_FACTOR = {
    "G": 1.0, "C": 1.1, "B": 1.3, "A": 1.6, "S": 2.0, "SS": 2.5, "SSR": 3.0,
}

# v2.4 新增: 年齡浮動範圍 (18 + random(0, offset))
AGE_OFFSETS = {
    "SSR": 0, # 固定 18
    "SS": 1,  # 18-19
    "S": 2,   # 18-20
    "A": 3,   # 18-21
    "B": 4,   # 18-22
    "C": 5,   # 18-23
    "G": 6    # 18-24
}

# v2.4 新增: 初始合約規則
CONTRACT_RULES = {
    "SSR": {"years": 4, "role": "Star"},
    "SS":  {"years": 4, "role": "Starter"},
    "S":   {"years": 4, "role": "Starter"},
    "A":   {"years": 2, "role": "Rotation"},
    "B":   {"years": 2, "role": "Rotation"},
    "C":   {"years": 1, "role": "Role"},
    "G":   {"years": 1, "role": "Bench"},
}

UNTRAINABLE_RULES = {
    "G":  {"sum_min": 10,  "sum_max": 400, "stat_min": 1, "stat_max": 99},
    "C":  {"sum_min": 399, "sum_max": 600, "stat_min": 1, "stat_max": 99},
    "B":  {"sum_min": 599, "sum_max": 700, "stat_min": 1, "stat_max": 99},
    "A":  {"sum_min": 699, "sum_max": 800, "stat_min": 10, "stat_max": 99},
    "S":  {"sum_min": 799, "sum_max": 900, "stat_min": 20, "stat_max": 99},
    "SS": {"sum_min": 900, "sum_max": 950, "stat_min": 30, "stat_max": 99},
    "SSR":{"sum_min": 951, "sum_max": 990, "stat_min": 91, "stat_max": 99},
}

TRAINABLE_CAPS = {
    "G": 800, "C": 700, "B": 650, "A": 600, "S": 550, "SS": 550, "SSR": 550
}

UNTRAINABLE_KEYS = [
    "ath_stamina", "ath_strength", "ath_speed", "ath_jump",
    "shot_touch", "shot_release",
    "talent_offiq", "talent_defiq", "talent_health", "talent_luck",
]

TRAINABLE_KEYS = [
    "shot_accuracy", "shot_range",
    "def_rebound", "def_boxout", "def_contest", "def_disrupt",
    "off_move", "off_dribble", "off_pass", "off_handle",
]

class PlayerGenerator:
    
    @staticmethod
    def _get_random_text(category, length_filter=None):
        query = NameLibrary.query.filter_by(category=category)
        
        if length_filter:
            if length_filter == '1':
                query = query.filter(func.char_length(NameLibrary.text) == 1)
            elif length_filter == '2':
                query = query.filter(func.char_length(NameLibrary.text) == 2)
            elif length_filter == '3+':
                query = query.filter(func.char_length(NameLibrary.text) >= 3)
        
        obj = query.order_by(func.random()).first()
        if not obj and length_filter:
             obj = NameLibrary.query.filter_by(category=category).order_by(func.random()).first()
             
        return obj.text if obj else ""

    @classmethod
    def _generate_name(cls):
        r = random.random()
        if r < 0.80: len_filter = '1'
        elif r < 0.95: len_filter = '2'
        else: len_filter = '3+'
            
        last_name = cls._get_random_text('last', length_filter=len_filter) or "無名"
        first_name = cls._get_random_text('first') or "氏"
        full_name = last_name + first_name
        
        should_add_char = False
        if len(full_name) <= 2:
            if random.choice([True, False]): should_add_char = True
        elif len(last_name) > 1 and len(first_name) == 1:
            if random.choice([True, False]): should_add_char = True
        
        if should_add_char:
            second_char = cls._get_random_text('first')
            if second_char and len(second_char) == 1:
                full_name += second_char
        
        return full_name

    @staticmethod
    def _generate_height():
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

    @staticmethod
    def _generate_stats_by_grade(grade):
        rule = UNTRAINABLE_RULES[grade]
        stat_min, stat_max = rule["stat_min"], rule["stat_max"]
        stats = {k: stat_min for k in UNTRAINABLE_KEYS}
        target_sum = random.randint(rule["sum_min"], rule["sum_max"])
        remaining = target_sum - sum(stats.values())
        capacity = {k: (stat_max - stats[k]) for k in UNTRAINABLE_KEYS}

        while remaining > 0:
            candidates = [k for k in UNTRAINABLE_KEYS if capacity[k] > 0]
            if not candidates: break
            k = random.choice(candidates)
            step = min(remaining, capacity[k], random.randint(1, 3))
            stats[k] += step
            capacity[k] -= step
            remaining -= step
        
        cap = TRAINABLE_CAPS[grade]
        while True:
            trainable_stats = {k: random.randint(STAT_MIN, STAT_MAX) for k in TRAINABLE_KEYS}
            if sum(trainable_stats.values()) <= cap:
                break
        
        stats.update(trainable_stats)
        return stats

    # v2.4 新增: 根據等級生成年齡
    @staticmethod
    def _generate_age(grade):
        offset = AGE_OFFSETS.get(grade, 6)
        return 18 + random.randint(0, offset)

    # v2.4 新增: 取得合約規則
    @staticmethod
    def _get_contract_rules(grade):
        return CONTRACT_RULES.get(grade, {"years": 1, "role": "Bench"})

    @classmethod
    def generate_and_persist(cls, count=1, user_id=None, team_id=None):
        new_players_preview = []
        try:
            for _ in range(count):
                # 1. 基礎生成
                grade = random.choices(OVERALL_GRADES, weights=OVERALL_GRADE_WEIGHTS, k=1)[0]
                name = cls._generate_name()
                height = cls._generate_height()
                position = cls._pick_position(height)
                age = cls._generate_age(grade) # v2.4
                
                # 2. 數值生成
                raw_stats = cls._generate_stats_by_grade(grade)
                total_stats_sum = sum(raw_stats.values())
                
                # 3. 薪資與合約計算
                salary = int(round(total_stats_sum * GRADE_FACTOR[grade]))
                contract_rule = cls._get_contract_rules(grade) # v2.4

                # 4. 詳細數據結構
                detailed_stats = {
                    "physical": {
                        "stamina": raw_stats.get("ath_stamina"),
                        "strength": raw_stats.get("ath_strength"),
                        "speed": raw_stats.get("ath_speed"),
                        "jumping": raw_stats.get("ath_jump"),
                        "health": raw_stats.get("talent_health")
                    },
                    "offense": {
                        "inside": raw_stats.get("shot_touch"),
                        "mid_range": raw_stats.get("shot_accuracy"),
                        "three_point": raw_stats.get("shot_range"),
                        "passing": raw_stats.get("off_pass"),
                        "dribble": raw_stats.get("off_dribble"),
                        "handle": raw_stats.get("off_handle"),
                        "move": raw_stats.get("off_move")
                    },
                    "defense": {
                        "rebound": raw_stats.get("def_rebound"),
                        "boxout": raw_stats.get("def_boxout"),
                        "contest": raw_stats.get("def_contest"),
                        "disrupt": raw_stats.get("def_disrupt"),
                        "perimeter": raw_stats.get("def_disrupt"),
                        "interior": raw_stats.get("def_contest")
                    },
                    "mental": {
                        "off_iq": raw_stats.get("talent_offiq"),
                        "def_iq": raw_stats.get("talent_defiq"),
                        "luck": raw_stats.get("talent_luck")
                    }
                }

                # 5. 建立 Player 物件
                player = Player(
                    name=name,
                    age=age, # v2.4
                    height=height,
                    position=position,
                    rating=int(total_stats_sum / 20),
                    detailed_stats=detailed_stats,
                    user_id=user_id,
                    team_id=team_id,
                    training_points=0
                )
                db.session.add(player)
                db.session.flush() # 取得 player.id

                # 6. 建立 Contract 物件 (v2.4)
                # 若沒有 team_id (例如首抽預覽)，則暫時不建立 Contract，或建立無 team 的 Contract
                if team_id:
                    contract = Contract(
                        player_id=player.id,
                        team_id=team_id,
                        salary=salary,
                        years=contract_rule['years'],
                        years_left=contract_rule['years'],
                        role=contract_rule['role']
                    )
                    db.session.add(contract)

                preview_data = {
                    "player_id": player.id,
                    "player_name": player.name,
                    "grade": grade,
                    "age": age,
                    "salary": salary,
                    "contract": contract_rule
                }
                new_players_preview.append(preview_data)

            db.session.commit()
            return {"total_inserted": count, "preview": new_players_preview}

        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            return {"total_inserted": 0, "preview": []}