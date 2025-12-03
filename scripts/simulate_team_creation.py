# scripts/simulate_team_creation.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.services.player_generator import (
    PlayerGenerator, GRADE_FACTOR, 
    UNTRAINABLE_KEYS, TRAINABLE_KEYS
)

KEY_MAP = {
# 不可訓練 (天賦)
"ath_stamina": "體力",
"ath_strength": "力量",
"ath_speed": "速度",
"ath_jump": "彈跳",
"shot_touch": "手感",
"shot_release": "出手速度",
"talent_offiq": "進攻智商",
"talent_defiq": "防守智商",
"talent_health": "健康",
"talent_luck": "運氣",

# 可訓練 (技術)
"shot_accuracy": "投籃準心", 
"shot_range": "射程", 
"def_rebound": "籃板", 
"def_boxout": "卡位", 
"def_contest": "干擾", 
"def_disrupt": "抄截",
"off_move": "跑位", 
"off_dribble": "運球", 
"off_pass": "傳球", 
"off_handle": "控球"
}

ROSTER_PLAN = [
    "G", "G", "G", "G", "G",
    "C", "C", "C",
    "B", "B",
    "A", "A",
    "S", "SS", "SSR"
]

def simulate():
    app = create_app()
    with app.app_context():
        print(f"\n{'='*100}")
        print(f"🏀 ASBL 新球隊開局模擬 (Spec v2.3 - 修正顯示名稱)")
        print(f"{'='*100}\n")

        attempt = 0
        
        while True:
            attempt += 1
            # 1. 暫存列表
            temp_roster = []
            pos_counts = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
            
            # 2. 生成 15 人
            for grade in ROSTER_PLAN:
                name = PlayerGenerator._generate_name()
                height = PlayerGenerator._generate_height()
                pos = PlayerGenerator._pick_position(height)
                stats = PlayerGenerator._generate_stats_by_grade(grade)
                
                pos_counts[pos] += 1
                
                temp_roster.append({
                    "grade": grade,
                    "name": name,
                    "height": height,
                    "pos": pos,
                    "stats": stats
                })
            
            # 3. 檢核條件
            # - C 總數至少 2
            # - PG 數量至少 2
            # - PG+SG 總數至少 4
            # - PF+SF 總數至少 4
            
            cond_c = pos_counts["C"] >= 2
            cond_pg = pos_counts["PG"] >= 2
            cond_guards = (pos_counts["PG"] + pos_counts["SG"]) >= 4
            cond_forwards = (pos_counts["PF"] + pos_counts["SF"]) >= 4
            
            if cond_c and cond_pg and cond_guards and cond_forwards:
                print(f"✅ 第 {attempt} 次嘗試成功！陣容符合規則。")
                print(f"📋 位置統計: PG:{pos_counts['PG']} SG:{pos_counts['SG']} SF:{pos_counts['SF']} PF:{pos_counts['PF']} C:{pos_counts['C']}")
                break
            else:
                # 失敗，繼續下一次迴圈 (不印出失敗的細節以免洗版)
                continue

        # 4. 輸出最終結果
        print(f"{'-'*100}")
        total_salary = 0
        
        for i, p in enumerate(temp_roster, 1):
            grade = p['grade']
            stats = p['stats']
            
            untrainable_sum = sum(stats[k] for k in UNTRAINABLE_KEYS)
            trainable_sum = sum(stats[k] for k in TRAINABLE_KEYS)
            total_stats = untrainable_sum + trainable_sum
            
            salary = int(round(total_stats * GRADE_FACTOR[grade]))
            total_salary += salary

            print(f"[{i:02d}] {grade:<3} {p['name']} ({p['pos']}, {p['height']}cm)")
            print(f"     💰 薪資: ${salary:,} | 📊 總能力: {total_stats}")
            print(f"     🔹 天賦: {untrainable_sum:<3} | 🔸 技術: {trainable_sum:<3}")
            
            print("     [天賦] ", end="")
            for k in UNTRAINABLE_KEYS: print(f"{KEY_MAP[k]}:{stats[k]:<2} ", end="")
            print("")
            print("     [技術] ", end="")
            for k in TRAINABLE_KEYS: print(f"{KEY_MAP[k]}:{stats[k]:<2} ", end="")
            print("\n" + "-"*60)

        print(f"\n💰 團隊薪資總額: ${total_salary:,}")
        print(f"📊 平均薪資: ${int(total_salary / len(ROSTER_PLAN)):,}")
        print(f"\n{'='*100}")

if __name__ == "__main__":
    simulate()