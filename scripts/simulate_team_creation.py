# scripts/simulate_team_creation.py
import sys
import os
import random
import math
from terminal import clear_terminal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.services.player_generator import (
    PlayerGenerator, GRADE_FACTOR, 
    UNTRAINABLE_KEYS, TRAINABLE_KEYS
)

# ==========================================
# 設定與對照表
# ==========================================

# 角色時間配置 (Spec v2.5)
ROLE_CONFIG = {
    "Star":     {"base": 30, "min_w": -1, "max_w": 5},
    "Starter":  {"base": 20, "min_w": -2, "max_w": 7},
    "Rotation": {"base": 10, "min_w": 5,  "max_w": 15},
    "Role":     {"base": 0,  "min_w": 5,  "max_w": 12},
    "Bench":    {"base": 0,  "min_w": 0,  "max_w": 10},
}

# 陣容規劃
ROSTER_PLAN = [
    "SSR",       # 1 Star
    "SS", "S",   # 2 Starters
    "A", "A", "B", "B", # 4 Rotation
    "C", "C", "C",      # 3 Role
    "G", "G", "G", "G", "G" # 5 Bench
]

# 中文屬性對照 (對應系統實際 Key)
ATTR_MAP = {
    # 天賦 (Untrainable)
    'ath_stamina': '體力', 'ath_strength': '力量', 'ath_speed': '速度', 'ath_jump': '彈跳',
    'shot_touch': '手感', 'shot_release': '出手速度', 'talent_offiq': '進攻智商', 'talent_defiq': '防守智商',
    'talent_health': '健康', 'talent_luck': '運氣',
    # 技術 (Trainable)
    'shot_accuracy': '投籃準心', 'shot_range': '射程', 'def_rebound': '籃板', 'def_boxout': '卡位',
    'def_contest': '干擾', 'def_disrupt': '抄截', 'off_move': '跑位', 'off_dribble': '運球',
    'off_pass': '傳球', 'off_handle': '控球'
}

# ==========================================
# 時間計算邏輯
# ==========================================
def calculate_minutes(roster, verbose=False):
    total_game_time = 240
    total_base = 0
    
    # 1. 計算總保底時間與生成權重
    for p in roster:
        role = p['contract']['role']
        cfg = ROLE_CONFIG[role]
        
        base_min = cfg['base']
        weight = random.randint(cfg['min_w'], cfg['max_w'])
        
        p['temp_calc'] = {
            "base": base_min,
            "weight": weight
        }
        total_base += base_min
    
    remaining_time = total_game_time - total_base
    total_weight = sum(p['temp_calc']['weight'] for p in roster)
    
    if total_weight == 0: unit = 0
    else: unit = remaining_time / total_weight
    
    if verbose:
        print(f"📊 [單場計算] 總保底 {total_base} | 剩餘 {remaining_time} | 總權重 {total_weight} | Unit {unit:.4f}")

    # 2. 分配時間
    current_total = 0
    for p in roster:
        t = p['temp_calc']
        extra_raw = t['weight'] * unit
        final_raw = t['base'] + extra_raw
        
        final_rounded = math.floor(final_raw * 10) / 10
        
        p['minutes'] = final_rounded
        current_total += final_rounded
    
    # 3. 尾數修正
    remainder = round(total_game_time - current_total, 1)
    if remainder > 0.0001:
        roster[-1]['minutes'] = round(roster[-1]['minutes'] + remainder, 1)

    return roster

# ==========================================
# 輔助功能：生成完整球隊 (供外部呼叫)
# ==========================================
def create_team_roster(team_name):
    """生成一支完整球隊，包含屬性與時間分配"""
    final_roster = []
    while True:
        temp_roster = []
        pos_counts = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
        
        for grade in ROSTER_PLAN:
            name = PlayerGenerator._generate_name()
            height = PlayerGenerator._generate_height()
            pos = PlayerGenerator._pick_position(height)
            contract = PlayerGenerator._get_contract_rules(grade)
            
            # --- [修正] 在此處直接生成屬性，不呼叫 PlayerGenerator 方法 ---
            base_stat = 90 if grade == "SSR" else (80 if grade in ["SS", "S"] else (70 if grade in ["A", "B"] else 60))
            stats = {}
            # 結合從 app 引入的 Key
            all_keys = UNTRAINABLE_KEYS + TRAINABLE_KEYS
            for k in all_keys:
                # 簡單的高斯分佈生成
                val = int(random.gauss(base_stat, 5))
                stats[k] = max(1, min(99, val))
            # -------------------------------------------------------
            
            # 計算總值與薪資 (模擬)
            talent_sum = sum(stats.get(k, 0) for k in UNTRAINABLE_KEYS)
            skill_sum = sum(stats.get(k, 0) for k in TRAINABLE_KEYS)
            total_rating = talent_sum + skill_sum
            salary = int(total_rating * 1.5) # 簡易薪資公式

            pos_counts[pos] += 1
            
            temp_roster.append({
                "name": name,
                "grade": grade,
                "pos": pos,
                "height": height,
                "contract": contract,
                "stats": stats,
                "salary": salary,
                "talent_sum": talent_sum,
                "skill_sum": skill_sum,
                "total_rating": total_rating,
                "game_logs": []
            })
        
        if pos_counts["C"] >= 2 and pos_counts["PG"] >= 2:
            final_roster = temp_roster
            break
    
    # 排序: Star -> Starter -> Rotation -> Role -> Bench
    role_order = {"Star": 1, "Starter": 2, "Rotation": 3, "Role": 4, "Bench": 5}
    final_roster.sort(key=lambda x: role_order[x['contract']['role']])
    
    # 計算時間
    calculate_minutes(final_roster)
    
    return final_roster

def print_roster_card(roster):
    """印出符合照片格式的球員資料"""
    print("-" * 100)
    for i, p in enumerate(roster):
        print(f"[{i+1:02d}] {p['grade']}  {p['name']} ({p['pos']}, {p['height']}cm)")
        print(f"     💰 薪資: ${p['salary']} | 📊 總能力: {p['total_rating']}")
        print(f"     🔹 天賦: {p['talent_sum']} | 🔸 技術: {p['skill_sum']}")
        
        # 天賦列
        t_str = " ".join([f"{ATTR_MAP.get(k, k)}:{p['stats'].get(k,0)}" for k in UNTRAINABLE_KEYS])
        print(f"     [天賦] {t_str}")
        
        # 技術列
        s_str = " ".join([f"{ATTR_MAP.get(k, k)}:{p['stats'].get(k,0)}" for k in TRAINABLE_KEYS])
        print(f"     [技術] {s_str}")
        print("-" * 100)

# ==========================================
# 主程式
# ==========================================
def simulate():
    app = create_app()
    with app.app_context():
        print(f"\n{'='*100}")
        print(f"🏀 ASBL 新球隊開局模擬 (Spec v2.5 - 資料展示)")
        print(f"{'='*100}\n")

        # 1. 生成 Home Team
        print("🏗️ 正在建立主隊 (Home)...")
        home_roster = create_team_roster("Home")
        print(f"✅ 主隊建立完成! (PG:{sum(1 for p in home_roster if p['pos']=='PG')} C:{sum(1 for p in home_roster if p['pos']=='C')})")
        print_roster_card(home_roster)

        print("\n")

        # 2. 生成 Away Team
        print("🏗️ 正在建立客隊 (Away)...")
        away_roster = create_team_roster("Away")
        print(f"✅ 客隊建立完成!")
        print_roster_card(away_roster)

if __name__ == "__main__":
    clear_terminal()
    simulate()
