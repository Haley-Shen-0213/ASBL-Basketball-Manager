# scripts/simulate_team_creation.py
import sys
import os
import random
import math

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
# 主程式
# ==========================================
def simulate():
    app = create_app()
    with app.app_context():
        print(f"\n{'='*100}")
        print(f"🏀 ASBL 10場比賽時間分配模擬 (Spec v2.5)")
        print(f"{'='*100}\n")

        # 1. 生成一支固定球隊
        print("🏗️ 正在建立球隊名單...")
        final_roster = []
        while True:
            temp_roster = []
            pos_counts = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
            
            for grade in ROSTER_PLAN:
                name = PlayerGenerator._generate_name()
                height = PlayerGenerator._generate_height()
                pos = PlayerGenerator._pick_position(height)
                # 這裡只取需要顯示的資訊，簡化物件
                contract = PlayerGenerator._get_contract_rules(grade)
                
                pos_counts[pos] += 1
                
                temp_roster.append({
                    "name": name,
                    "grade": grade,
                    "pos": pos,
                    "contract": contract,
                    "game_logs": [] # 儲存10場的紀錄
                })
            
            if pos_counts["C"] >= 2 and pos_counts["PG"] >= 2:
                final_roster = temp_roster
                break
        
        # 排序: Star -> Starter -> Rotation -> Role -> Bench
        role_order = {"Star": 1, "Starter": 2, "Rotation": 3, "Role": 4, "Bench": 5}
        final_roster.sort(key=lambda x: role_order[x['contract']['role']])

        print(f"✅ 球隊建立完成！開始模擬 10 場比賽...\n")

        # 2. 模擬 10 場比賽
        for game_i in range(1, 11):
            # 計算該場時間
            calculate_minutes(final_roster, verbose=False)
            
            # 將結果存入 log
            for p in final_roster:
                p['game_logs'].append(p['minutes'])

        # 3. 輸出統計表格
        # 表頭
        header = f"{'球員':<12} {'角色':<8} | {'G1':<4} {'G2':<4} {'G3':<4} {'G4':<4} {'G5':<4} {'G6':<4} {'G7':<4} {'G8':<4} {'G9':<4} {'G10':<4} | {'Min':<4} {'Max':<4} {'Avg':<4}"
        print(header)
        print("-" * len(header))

        total_avg_sum = 0

        for p in final_roster:
            logs = p['game_logs']
            min_min = min(logs)
            max_min = max(logs)
            avg_min = sum(logs) / len(logs)
            total_avg_sum += avg_min

            # 格式化每一場的時間 (靠右對齊)
            logs_str = "".join([f"{m:>4.1f} " for m in logs])
            
            name_display = f"{p['grade']} {p['name']}"
            
            print(f"{name_display:<12} {p['contract']['role']:<8} | {logs_str}| {min_min:>4.1f} {max_min:>4.1f} {avg_min:>4.1f}")

        print("-" * len(header))
        print(f"📊 團隊場均總時間: {total_avg_sum:.1f} (驗證是否接近 240.0)")
        print(f"\n{'='*100}")

if __name__ == "__main__":
    simulate()