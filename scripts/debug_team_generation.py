# scripts/debug_team_generation.py
# ==========================================
# ASBL Team Generation Debug Script (Weighted Analysis + Parquet Export)
# 用途: 驗證 TeamCreator 與 PlayerGenerator 的邏輯正確性
#       計算加權戰力，並將結果輸出至 Parquet 供模擬比賽測試使用
#       (支援多球隊生成版本 + 高階球員細節分析)
# ==========================================

import sys
import os
import time
import pandas as pd
from pprint import pprint
from collections import Counter

# 確保可以引用到 app 模組
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.services.team_creator import TeamCreator
from app.services.player_generator import PlayerGenerator

# ==========================================
# 設定與映射表
# ==========================================

# 生成球隊數量設定
NUM_TEAMS_TO_GENERATE = 4

# 屬性加權倍率
STAT_WEIGHTS = {
    'talent_offiq': 1.08,  # 進攻智商
    'talent_defiq': 1.07,  # 防守智商
    'ath_speed': 1.07,     # 速度
    'off_move': 1.05,      # 跑位
    'ath_strength': 1.05,  # 力量
    'ath_jump': 1.05,      # 彈跳
    'off_pass': 1.04,      # 傳球
    'def_contest': 1.04,   # 干擾
    'off_handle': 1.04,    # 控球
    'off_dribble': 1.04,   # 運球
    'def_disrupt': 1.04,   # 抄截
    'shot_touch': 1.03,    # 手感
    'shot_release': 1.03,  # 出手速度
    'def_boxout': 1.03,    # 卡位
    'shot_range': 1.02,    # 射程
    'def_rebound': 1.02,   # 籃板
    'shot_accuracy': 1.02, # 投籃技巧
}

# 中文名稱映射 (Config Key -> 中文)
NAME_MAPPING = {
    # Physical
    'ath_stamina': '體力',
    'ath_strength': '力量',
    'ath_speed': '速度',
    'ath_jump': '彈跳',
    'talent_health': '健康',
    # Offense
    'shot_touch': '手感',
    'shot_release': '出手速度',
    'shot_accuracy': '投籃技巧',
    'shot_range': '射程',
    'off_pass': '傳球',
    'off_dribble': '運球',
    'off_handle': '控球',
    'off_move': '跑位',
    # Defense
    'def_rebound': '籃板',
    'def_boxout': '卡位',
    'def_contest': '干擾',
    'def_disrupt': '抄截',
    # Mental
    'talent_offiq': '進攻智商',
    'talent_defiq': '防守智商',
    'talent_luck': '運氣'
}

# 顯示順序分組
DISPLAY_GROUPS = {
    "體能": ['ath_stamina', 'ath_strength', 'ath_speed', 'ath_jump', 'talent_health'],
    "進攻": ['shot_touch', 'shot_release', 'shot_accuracy', 'shot_range', 'off_pass', 'off_dribble', 'off_handle', 'off_move'],
    "防守": ['def_rebound', 'def_boxout', 'def_contest', 'def_disrupt'],
    "心理": ['talent_offiq', 'talent_defiq', 'talent_luck']
}

def print_separator(title=""):
    """印出分隔線"""
    print(f"\n{'='*25} {title} {'='*25}")

def calculate_weighted_score(raw_stats):
    """計算單一球員的加權總分"""
    total_score = 0.0
    for key, value in raw_stats.items():
        multiplier = STAT_WEIGHTS.get(key, 1.0)
        total_score += value * multiplier
    return total_score

def print_player_card(index, player):
    """
    以繁體中文印出球員詳細屬性與加權分數
    Returns:
        float: 該球員的加權總分
    """
    pos = player['position']
    name = player['name']
    age = player['age']
    grade = player['grade']
    height = player['height']
    rating = player['rating']
    salary = player['salary']
    years = player['contract_rule']['years']
    role = player['contract_rule']['role']
    
    weighted_score = calculate_weighted_score(player['raw_stats'])
    
    print(f"\n[{index+1:02d}] {pos} - {name} ({age}歲)")
    print(f"     等級: {grade:<3} | 身高: {height}cm | 評分: {rating}")
    print(f"     薪資: ${salary:,} | 合約: {years}年 ({role})")
    print(f"     >> 加權戰力: {weighted_score:.2f}")

    raw = player['raw_stats']
    for group_name, keys in DISPLAY_GROUPS.items():
        line_items = []
        for k in keys:
            cn_name = NAME_MAPPING.get(k, k)
            val = raw.get(k, 0)
            line_items.append(f"{cn_name}:{val}")
        print(f"     [{group_name}] " + " ".join(line_items))
        
    return weighted_score

def prepare_player_data_for_parquet(roster, team_id):
    """
    將球員列表轉換為適合存入 Parquet 的字典列表 (扁平化結構)
    """
    data_list = []
    for p in roster:
        # 生成唯一 Player ID (格式: {team_id}_{name})
        pid = f"{team_id}_{p['name']}"

        # 基礎資料
        player_data = {
            "player_id": pid,          # 統一 ID
            "team_id": team_id,
            "name": p['name'],
            "grade": p['grade'],
            "age": p['age'],
            "height": p['height'],
            "position": p['position'],
            "rating": p['rating'],
            "salary": p['salary'],
            "contract_years": p['contract_rule']['years'],
            "contract_role": p['contract_rule']['role'],
            "role": p['contract_rule']['role'], # Alias for simulation engine
        }
        
        # 展開 raw_stats (扁平化屬性)
        for k, v in p['raw_stats'].items():
            player_data[k] = v
            
        # 加入加權分數
        player_data['weighted_score'] = calculate_weighted_score(p['raw_stats'])
        
        data_list.append(player_data)
    return data_list

def save_to_parquet(rosters_dict):
    """
    將多隊資料合併並寫入 Parquet 檔案
    Args:
        rosters_dict (dict): { 'team_id': [player_list], ... }
    """
    print_separator("資料輸出 (DATA EXPORT)")
    
    all_data = []
    
    # 1. 迭代所有球隊並準備資料
    for team_id, roster in rosters_dict.items():
        print(f"[處理中] 正在轉換 {team_id} 的資料...")
        team_data = prepare_player_data_for_parquet(roster, team_id)
        all_data.extend(team_data)
    
    # 2. 轉換為 DataFrame
    df = pd.DataFrame(all_data)
    
    # 3. 確保目錄存在
    output_dir = os.path.join("tests", "match_test", "team")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "team_players.parquet")
    
    # 4. 寫入檔案 (覆蓋模式)
    try:
        df.to_parquet(output_path, index=False)
        print(f"\n[成功] 球隊資料已寫入: {output_path}")
        print(f"[資訊] 總球員筆數: {len(df)} (共 {len(rosters_dict)} 隊)")
        
        # 驗證關鍵欄位是否存在
        required_cols = ['player_id', 'role', 'team_id', 'name', 'grade']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"[警告] 缺少關鍵欄位: {missing}")
        else:
            print(f"[驗證] 關鍵欄位檢查通過: {required_cols}")
            
        print(f"[資訊] 欄位預覽: {list(df.columns[:5])} ...")
    except Exception as e:
        print(f"[錯誤] Parquet 寫入失敗: {str(e)}")

def run_debug_generation():
    app = create_app()
    
    # 儲存所有生成的球隊名單 { 'team_001': [...], ... }
    all_rosters = {}
    # 儲存球隊總戰力以供比較
    team_scores = {}
    
    with app.app_context():
        print_separator("系統初始化 (SYSTEM INITIALIZATION)")
        t_start = time.time()
        PlayerGenerator.initialize_class()
        t_end = time.time()
        print(f"[系統] 快取初始化完成，耗時 {t_end - t_start:.4f} 秒。")
        
        # ---------------------------------------------------
        # 迴圈生成球隊
        # ---------------------------------------------------
        for i in range(1, NUM_TEAMS_TO_GENERATE + 1):
            team_id = f"team_{i:03d}"
            print_separator(f"正在生成 {team_id} (GENERATING TEAM {i})")
            
            current_team_score = 0.0
            try:
                t_start = time.time()
                roster = TeamCreator.create_valid_roster()
                t_end = time.time()
                
                print(f"[成功] {team_id} 生成完畢，耗時 {t_end - t_start:.4f} 秒。")
                print(f"[資訊] 名單人數: {len(roster)}")
                
                # 印出球員卡並計算總分
                for idx, p in enumerate(roster):
                    score = print_player_card(idx, p)
                    current_team_score += score
                
                # 儲存結果
                all_rosters[team_id] = roster
                team_scores[team_id] = current_team_score
                
                # 簡單統計
                positions = [p['position'] for p in roster]
                grades = [p['grade'] for p in roster]
                print(f"\n[{team_id} 陣容結構]")
                print(f"位置分佈: {dict(Counter(positions))}")
                print(f"等級分佈: {dict(Counter(grades))}")
                
            except Exception as e:
                print(f"[錯誤] {team_id} 生成失敗: {str(e)}")
                import traceback
                traceback.print_exc()

        # ---------------------------------------------------
        # 最終比較
        # ---------------------------------------------------
        print_separator("戰力分析報告 (COMPARISON REPORT)")
        
        # 根據戰力排序
        sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)
        
        print(f"{'排名':<6} {'球隊ID':<12} {'總戰力':<12} {'平均戰力':<12}")
        print("-" * 45)
        
        for rank, (tid, score) in enumerate(sorted_teams, 1):
            roster_len = len(all_rosters.get(tid, []))
            avg_score = score / roster_len if roster_len > 0 else 0
            print(f"{rank:<6} {tid:<12} {score:,.2f}      {avg_score:.2f}")
        
        if len(sorted_teams) >= 2:
            diff = sorted_teams[0][1] - sorted_teams[-1][1]
            print(f"\n🏆 最強球隊: {sorted_teams[0][0]}")
            print(f"📉 最弱球隊: {sorted_teams[-1][0]}")
            print(f"⚖️ 首尾分差: {diff:,.2f}")

        # ---------------------------------------------------
        # 高階球員詳細戰力 (SSR/SS/S)
        # ---------------------------------------------------
        print_separator("高階球員詳細戰力 (HIGH TIER DETAILS)")
        target_grades = ['SSR', 'SS', 'S']
        
        for tid in sorted(all_rosters.keys()):
            roster = all_rosters[tid]
            print(f"\n[{tid}]")
            
            # 先將球員按等級分組
            grade_stats = {g: [] for g in target_grades}
            
            for p in roster:
                if p['grade'] in target_grades:
                    score = calculate_weighted_score(p['raw_stats'])
                    grade_stats[p['grade']].append((p['name'], score))
            
            # 依序印出
            has_high_tier = False
            for g in target_grades:
                players = grade_stats[g]
                if players:
                    has_high_tier = True
                    # 按分數排序
                    players.sort(key=lambda x: x[1], reverse=True)
                    
                    print(f"  > {g} ({len(players)}人):")
                    total_g_score = 0
                    for name, score in players:
                        print(f"    - {name:<15}: {score:.2f}")
                        total_g_score += score
                    
                    avg_g_score = total_g_score / len(players)
                    print(f"    >> {g} 總和: {total_g_score:.2f} | 平均: {avg_g_score:.2f}")
                else:
                    print(f"  > {g}: 無球員")
            
            if not has_high_tier:
                print("  (無 S 級以上球員)")

        # ---------------------------------------------------
        # 輸出 Parquet
        # ---------------------------------------------------
        if all_rosters:
            save_to_parquet(all_rosters)
        else:
            print("\n[警告] 沒有生成任何球隊資料，跳過存檔。")

if __name__ == "__main__":
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        pass
    run_debug_generation()