# app/services/player_generator.py
import random
import math
import re
from app import db
from app.models.player import Player, Contract
from app.models.system import NameLibrary
from app.utils.game_config_loader import GameConfigLoader

# ==========================================
# ASBL Player Generator Service
# Specification: v3.3 (Name Strategy Configurable)
# Features: 
#   - Multi-language Name Generation (Strategy A/B/C)
#   - Config-driven strategy mapping
#   - Dynamic Validation
# ==========================================

class PlayerGenerator:
    
    # -------------------------------------------------------------------------
    # 靜態快取區 (Static Cache)
    # -------------------------------------------------------------------------
    # 結構: 
    # _names_cache = {
    #    'en': {
    #       'surname': [{'content': 'Smith', 'weight': 10}, ...],
    #       'given_name': [{'content': 'John', 'weight': 20}, ...],
    #       'all': [...] # 混合列表 (for Strategy A)
    #    },
    #    'zh': ...
    # }
    _names_cache = {} 
    _config_cache = {}
    _is_initialized = False

    # [Spec v2.6] 屬性映射表
    ATTR_MAPPING = {
        # Untrainable (天賦)
        "ath_stamina":   ("physical", "stamina"),
        "ath_strength":  ("physical", "strength"),
        "ath_speed":     ("physical", "speed"),
        "ath_jump":      ("physical", "jumping"),
        "talent_health": ("physical", "health"),
        "shot_touch":    ("offense", "touch"),
        "shot_release":  ("offense", "release"),
        "talent_offiq":  ("mental", "off_iq"),
        "talent_defiq":  ("mental", "def_iq"),
        "talent_luck":   ("mental", "luck"),
        # Trainable (技術)
        "shot_accuracy": ("offense", "accuracy"),
        "shot_range":    ("offense", "range"),
        "off_pass":      ("offense", "passing"),
        "off_dribble":   ("offense", "dribble"),
        "off_handle":    ("offense", "handle"),
        "off_move":      ("offense", "move"),
        "def_rebound":   ("defense", "rebound"),
        "def_boxout":    ("defense", "boxout"),
        "def_contest":   ("defense", "contest"),
        "def_disrupt":   ("defense", "disrupt")
    }

    @classmethod
    def initialize_class(cls):
        """
        [系統初始化]
        在伺服器啟動時呼叫，將資料與設定載入記憶體。
        包含將 YAML 字串規則編譯為 Python 物件的邏輯。
        """
        if cls._is_initialized:
            return

        print("[PlayerGenerator] Initializing cache for High Performance Mode...")

        # 1. 載入姓名庫 (保留 Weight 資訊)
        # 使用 yield_per 優化大量數據讀取
        all_names = db.session.query(NameLibrary).yield_per(10000)
        
        cls._names_cache = {}
        
        # [v3.4 Update] 用於計算語系權重的計數器
        lang_counts = {}
        
        for row in all_names:
            lang = row.language
            cat = row.category
            
            if lang not in cls._names_cache:
                cls._names_cache[lang] = {'surname': [], 'given_name': [], 'all': []}
                lang_counts[lang] = 0 # 初始化計數
            
            item = {'content': row.content, 'weight': row.weight}
            
            # 分類儲存
            if cat in cls._names_cache[lang]:
                cls._names_cache[lang][cat].append(item)
            
            # 同時存入 'all' (供 Strategy A 使用)
            cls._names_cache[lang]['all'].append(item)
            
            # [v3.4 Update] 累加該語系的資料筆數
            lang_counts[lang] += 1

        # [v3.4 Update] 預先計算語系分佈權重，避免在 generate 時重複計算
        # 結構: {'langs': ['en', 'zh', ...], 'weights': [1050, 300, ...]}
        cls._config_cache['lang_distribution'] = {
            'langs': list(lang_counts.keys()),
            'weights': list(lang_counts.values())
        }

        # 2. 預載入 Config (基礎)
        cls._config_cache['grades'] = GameConfigLoader.get('generation.grades')
        cls._config_cache['grade_weights'] = GameConfigLoader.get('generation.grade_weights')
        cls._config_cache['untrainable_keys'] = GameConfigLoader.get('generation.attributes.untrainable')
        cls._config_cache['trainable_keys'] = GameConfigLoader.get('generation.attributes.trainable')
        cls._config_cache['height_modifiers'] = GameConfigLoader.get('generation.height_modifiers')
        cls._config_cache['weighted_bonus_keys'] = GameConfigLoader.get('generation.weighted_bonus_keys')
        
        # 2.1 載入姓名生成策略 (New Spec v3.3)
        cls._config_cache['name_strategies'] = GameConfigLoader.get('name_generation.strategies')
        
        # 3. 預載入身高與位置參數 (消除 Hardcode)
        cls._config_cache['height_dist'] = GameConfigLoader.get('generation.height_distribution')
        
        # 3.1 位置矩陣優化
        raw_pos_matrix = GameConfigLoader.get('generation.position_matrix')
        cls._config_cache['pos_matrix_optimized'] = []
        for entry in raw_pos_matrix:
            cls._config_cache['pos_matrix_optimized'].append({
                'threshold': entry['max_height'],
                'roles': list(entry['weights'].keys()),
                'weights': list(entry['weights'].values())
            })

        # 3.2 位置檢核規則編譯 (Rule Compiler)
        # 將 YAML 中的 "sum(a, b, c) > ..." 字串解析為 Python list ['a', 'b', 'c']
        raw_validation = GameConfigLoader.get('generation.position_validation')
        cls._config_cache['pos_validation_compiled'] = {}
        
        for pos, rule in raw_validation.items():
            condition_str = rule.get('condition', 'none')
            if condition_str == 'none':
                cls._config_cache['pos_validation_compiled'][pos] = None
            else:
                # 使用 Regex 提取 sum(...) 中的內容
                # 假設格式總是 sum(key1, key2...) > ...
                match = re.search(r"sum\((.*?)\)", condition_str)
                if match:
                    keys_str = match.group(1)
                    # 轉為 list: ['def_rebound', 'def_boxout', 'def_contest']
                    keys = [k.strip() for k in keys_str.split(',')]
                    cls._config_cache['pos_validation_compiled'][pos] = keys
                else:
                    # Fallback: 若解析失敗，視為無限制，避免 Crash
                    print(f"[Warning] Failed to parse validation rule for {pos}: {condition_str}")
                    cls._config_cache['pos_validation_compiled'][pos] = None

        # 4. 預載入各等級規則
        cls._config_cache['rules_by_grade'] = {}
        for g in cls._config_cache['grades']:
            cls._config_cache['rules_by_grade'][g] = {
                'untrainable': GameConfigLoader.get(f'generation.untrainable_rules.{g}'),
                'trainable_cap': GameConfigLoader.get(f'generation.trainable_caps.{g}'),
                'salary_factor': GameConfigLoader.get(f'generation.salary_factors.{g}'),
                'contract': GameConfigLoader.get(f'generation.contracts.{g}'),
                'age_offset': GameConfigLoader.get(f'generation.age_rules.offsets.{g}')
            }

        cls._is_initialized = True
        print(f"[PlayerGenerator] Cache initialized. Validation Rules Compiled.")

    # =========================================================================
    # 1. 姓名生成 (Name Generation) - v3.3 Update
    # ===================================================================================
    
    @staticmethod
    def _pick_weighted(items, k=1):
        """[Helper] 根據 weight 屬性進行加權隨機抽取"""
        if not items: return []
        population = [x['content'] for x in items]
        weights = [x['weight'] for x in items]
        return random.choices(population, weights=weights, k=k)

    @classmethod
    def _get_strategy_for_lang(cls, lang):
        """從 Config 中查找該語系對應的策略"""
        strategies = cls._config_cache['name_strategies']
        if lang in strategies.get('western', []):
            return 'A'
        elif lang in strategies.get('east_asian', []):
            return 'B'
        elif lang in strategies.get('indigenous', []):
            return 'C'
        return 'A' # Default fallback

    @classmethod
    def _generate_name_data(cls):
        """
        生成姓名與國籍
        Return: (full_name, nationality_code)
        """
        if not cls._is_initialized: cls.initialize_class()

        # [v3.4 Update] 決定語系邏輯變更
        # 從「語系均等」改為「依資料庫筆數權重」隨機抽取
        dist = cls._config_cache.get('lang_distribution')
        
        if not dist or not dist['langs']:
            return "Unknown Player", "en"
            
        # 使用 random.choices 進行加權抽取 (O(1) after initialization)
        selected_lang = random.choices(
            dist['langs'], 
            weights=dist['weights'], 
            k=1
        )[0]
        
        strategy = cls._get_strategy_for_lang(selected_lang)
        lang_data = cls._names_cache[selected_lang]
        full_name = ""

        # 2. 依語系執行策略
        if strategy == 'A': # 歐美語系 (Western)
            # 規則: 不分 category，依照權重隨機抽取 3 個內容組合，用間隔號分隔
            parts = cls._pick_weighted(lang_data['all'], k=3)
            full_name = "・".join(parts)

        elif strategy == 'B': # 東亞語系 (East Asian)
            # 規則: 
            # 1. 抽姓氏 (category='surname')
            # 2. 抽名字1 (category='given_name')
            # 3. 判定名字2 (70% 機率再抽一個 given_name)
            # 組合: 姓 + 名1 [+ 名2]
            
            surnames = lang_data.get('surname', [])
            given_names = lang_data.get('given_name', [])
            
            # 防呆：若資料不足，退回到 'all' 抽取
            if not surnames: surnames = lang_data['all']
            if not given_names: given_names = lang_data['all']

            sn = cls._pick_weighted(surnames, k=1)[0]
            gn1 = cls._pick_weighted(given_names, k=1)[0]
            
            full_name = sn + gn1
            
            # 70% 機率雙字名
            if random.random() < 0.7:
                gn2 = cls._pick_weighted(given_names, k=1)[0]
                full_name += gn2

        elif strategy == 'C': # 台灣原住民語系 (Indigenous)
            # 規則: 隨機抽取 2 個「不重複」的內容，用間隔號拼接
            pool = lang_data['all']
            if len(pool) < 2:
                parts = cls._pick_weighted(pool, k=len(pool)) # 資料不足就全拿
            else:
                # 抽取不重複邏輯
                # 由於 random.choices 是取後放回，這裡手動處理不重複
                selected = []
                temp_pool = list(pool) # Copy
                
                while len(selected) < 2 and temp_pool:
                    # 重新計算權重並抽取
                    pick_list = cls._pick_weighted(temp_pool, k=1)
                    if not pick_list: break
                    
                    val = pick_list[0]
                    selected.append(val)
                    
                    # 從暫存池移除已選中的 (避免重複)
                    # 注意：這裡假設 content 是唯一的，或者移除第一個匹配項
                    temp_pool = [x for x in temp_pool if x['content'] != val]
                
                parts = selected
                
            full_name = "・".join(parts)
        
        return full_name, selected_lang

    # =========================================================================
    # 2. 天賦生成 (Untrainable Stats)
    # =========================================================================
    @classmethod
    def _generate_untrainable_stats(cls, grade):
        keys = cls._config_cache['untrainable_keys']
        rule = cls._config_cache['rules_by_grade'][grade]['untrainable']
        
        stat_min, stat_max = rule["stat_min"], rule["stat_max"]
        sum_min, sum_max = rule["sum_min"], rule["sum_max"]
        
        while True:
            stats = {k: stat_min for k in keys}
            current_sum = sum(stats.values())
            target_sum = random.randint(sum_min, sum_max)
            remaining = target_sum - current_sum
            
            valid_keys = list(keys)
            while remaining > 0 and valid_keys:
                k = random.choice(valid_keys)
                space = stat_max - stats[k]
                if space <= 0:
                    valid_keys.remove(k)
                    continue
                
                step = random.randint(1, min(remaining, space, 10))
                stats[k] += step
                remaining -= step
            
            if remaining == 0:
                return stats

    # =========================================================================
    # 3. 身高與位置 (Height & Position) - Fully Configurable
    # =========================================================================
    @classmethod
    def _generate_height(cls):
        conf = cls._config_cache['height_dist']
        mean, std_dev = conf['mean'], conf['std_dev']
        min_h, max_h = conf['min'], conf['max']
        
        while True:
            u1, u2 = random.random(), random.random()
            z = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
            height = int(round(mean + z * std_dev))
            if min_h <= height <= max_h:
                return height

    @classmethod
    def _pick_position(cls, h):
        for rule in cls._config_cache['pos_matrix_optimized']:
            if h <= rule['threshold']:
                return random.choices(rule['roles'], weights=rule['weights'], k=1)[0]
        return "C"

    # =========================================================================
    # 4. 可訓練能力生成 (Trainable Stats)
    # =========================================================================
    
    @classmethod
    def _check_position_validation(cls, stats, pos):
        """
        [Spec 2.4.2] 位置檢核機制 (Dynamic)
        不再使用 Hardcode，而是讀取初始化時編譯好的 Key List
        """
        # 1. 取得該位置的關鍵屬性列表 (List of keys)
        core_keys = cls._config_cache['pos_validation_compiled'].get(pos)
        
        # 若無規則 (如 SF)，直接通過
        if not core_keys:
            return True
            
        # 2. 計算核心總和
        # 使用 Generator Expression 進行加總，效能極佳
        core_sum = sum(stats[k] for k in core_keys)
        
        # 3. 計算總和
        total_sum = sum(stats.values())
        
        # 4. 判定: 核心 > (總和 - 核心) => 核心 > 其他
        return core_sum > (total_sum - core_sum)

    @staticmethod
    def _safe_distribute(stats, target_keys, points_to_add):
        """[Helper] 安全分配點數，包含防爆機制 (Max 99)"""
        if points_to_add <= 0: return
        valid_keys = list(target_keys)
        while points_to_add > 0 and valid_keys:
            k = random.choice(valid_keys)
            capacity = 99 - stats[k]
            if capacity <= 0:
                valid_keys.remove(k)
                continue
            stats[k] += 1
            points_to_add -= 1

    @classmethod
    def _distribute_bonus_points(cls, stats, bonus, bonus_type, bonus_config=None):
        """[Spec 2.4.3] 執行加點邏輯 (Revised)"""
        if bonus <= 0: return stats
        
        all_keys = list(stats.keys())
        
        if bonus_type == 'flat':
            per_stat = bonus // len(all_keys)
            for k in all_keys:
                stats[k] = min(99, stats[k] + per_stat)
                
        elif bonus_type == 'weighted':
            ratio_min = bonus_config.get('key_ratio_min', 0.5) if bonus_config else 0.5
            ratio_max = bonus_config.get('key_ratio_max', 1.0) if bonus_config else 1.0
            
            ratio = random.uniform(ratio_min, ratio_max)
            key_pool = int(bonus * ratio)
            general_pool = bonus - key_pool
            
            high_p_keys = cls._config_cache['weighted_bonus_keys']['high_priority']
            
            cls._safe_distribute(stats, high_p_keys, key_pool)
            cls._safe_distribute(stats, all_keys, general_pool)
                    
        return stats

    @classmethod
    def _generate_trainable_stats(cls, grade, height, position):
        keys = cls._config_cache['trainable_keys']
        cap = cls._config_cache['rules_by_grade'][grade]['trainable_cap']
        
        # 1. 取得身高修正規則
        mod_rules = cls._config_cache['height_modifiers']
        # 區間判斷邏輯 (可以進一步優化為 Config 驅動，但此處為效能熱點，且區間變動機率低)
        if 160 <= height <= 169: rule = mod_rules['160-169']
        elif 170 <= height <= 179: rule = mod_rules['170-179']
        elif 180 <= height <= 189: rule = mod_rules['180-189']
        elif 190 <= height <= 209: rule = mod_rules['190-209']
        elif 210 <= height <= 219: rule = mod_rules['210-219']
        elif 220 <= height <= 230: rule = mod_rules['220-230']
        else: rule = mod_rules['190-209']

        trials = rule.get('trials', 1)
        selection = rule.get('selection', 'none')
        bonus = rule.get('bonus_points', 0)
        bonus_type = rule.get('bonus_type', 'none')

        candidates = []

        # 2. 執行 Trials (分階段重骰)
        for _ in range(trials):
            while True:
                temp_stats = {k: random.randint(1, 99) for k in keys}
                if sum(temp_stats.values()) > cap:
                    continue
                # [Dynamic Check]
                if not cls._check_position_validation(temp_stats, position):
                    continue
                candidates.append(temp_stats)
                break
        
        # 3. 選擇最佳/最差
        final_stats = candidates[0]
        if selection == 'max':
            final_stats = max(candidates, key=lambda x: sum(x.values()))
        elif selection == 'min':
            final_stats = min(candidates, key=lambda x: sum(x.values()))
            
        # 4. 應用身高獎勵
        final_stats = cls._distribute_bonus_points(final_stats, bonus, bonus_type, rule)
        
        return final_stats

    # =========================================================================
    # 主流程 (Main Workflow)
    # =========================================================================
    @classmethod
    def generate_payload(cls, specific_grade=None):
        if not cls._is_initialized: cls.initialize_class()

        # 1. Name & Nationality (Updated)
        name, nationality = cls._generate_name_data()

        # 2. Grade
        if specific_grade:
            grade = specific_grade
        else:
            grade = random.choices(
                cls._config_cache['grades'], 
                weights=cls._config_cache['grade_weights'], 
                k=1
            )[0]

        # 3. Untrainable
        untrainable = cls._generate_untrainable_stats(grade)

        # 4. Height & Position
        height = cls._generate_height()
        position = cls._pick_position(height)

        # 5. Trainable
        trainable = cls._generate_trainable_stats(grade, height, position)

        # 6. Age
        age_base = 18
        age_offset = cls._config_cache['rules_by_grade'][grade]['age_offset']
        age = age_base + random.randint(0, age_offset)

        # 7. Derived Data
        raw_stats = {**untrainable, **trainable}
        total_sum = sum(raw_stats.values())
        
        salary_factor = cls._config_cache['rules_by_grade'][grade]['salary_factor']
        salary = int(round(total_sum * salary_factor))
        
        contract_rule = cls._config_cache['rules_by_grade'][grade]['contract']

        # 8. Assembly
        detailed_stats = {"physical": {}, "offense": {}, "defense": {}, "mental": {}}
        for cfg_key, (cat, db_key) in cls.ATTR_MAPPING.items():
            if cfg_key in raw_stats:
                detailed_stats[cat][db_key] = raw_stats[cfg_key]

        return {
            "name": name,
            "nationality": nationality, # 新增國籍
            "grade": grade,
            "age": age,
            "height": height,
            "position": position,
            "rating": int(total_sum / 20),
            "salary": salary,
            "contract_rule": contract_rule,
            "detailed_stats": detailed_stats,
            "raw_stats": raw_stats
        }

    # ====================================================
    # 工具方法
    # ====================================================
    @staticmethod
    def to_flat_dict(payload):
        flat = {
            "name": payload['name'],
            "nationality": payload['nationality'], # [Update] 加入語系欄位
            "grade": payload['grade'],
            "age": payload['age'],
            "height": payload['height'],
            "position": payload['position'],
            "rating": payload['rating'],
            "salary": payload['salary'],
            "contract_years": payload['contract_rule']['years'],
            "contract_role": payload['contract_rule']['role']
        }
        for cat, stats in payload['detailed_stats'].items():
            for k, v in stats.items():
                flat[f"{cat}_{k}"] = v
        return flat

    @classmethod
    def save_to_db(cls, payload, user_id=None, team_id=None):
        player = Player(
            name=payload['name'],
            nationality=payload['nationality'], # [Update] 儲存國籍
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