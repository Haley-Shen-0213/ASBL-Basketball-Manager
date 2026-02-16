# tests/team_bigdata_test/manual_merge.py
# Description: 救援崩潰數據 V2 - 修正字串解析錯誤 (Fix String/List parsing issue)

import os
import sys
import pandas as pd
import numpy as np
import ast
from datetime import datetime
from collections import Counter
import glob

# ==========================================
# 設定區
# ==========================================
TARGET_DIR = r"D:\ASBL-Basketball-Manager\tests\team_bigdata_test\data\20251229_202911"

def parse_names(val):
    """
    嘗試將各種奇形怪狀的資料轉回 List
    """
    if isinstance(val, list):
        return val
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, str):
        val = val.strip()
        if val.startswith('[') and val.endswith(']'):
            try:
                # 將字串 "['A', 'B']" 轉回 list ['A', 'B']
                return ast.literal_eval(val)
            except:
                pass
        return [val] # 真的只是單一字串
    return []

def main():
    print(f"正在救援目錄: {TARGET_DIR}")
    
    temp_dir = os.path.join(TARGET_DIR, "temp_parts")
    final_parquet_path = os.path.join(TARGET_DIR, 'teams_data.parquet')
    report_file = os.path.join(TARGET_DIR, "report_rescued_v2.md")

    if not os.path.exists(temp_dir):
        print(f"錯誤: 找不到暫存目錄 {temp_dir}")
        return

    # 1. 讀取並合併數據
    print("正在讀取所有分塊檔案...")
    try:
        files = glob.glob(os.path.join(temp_dir, "*.parquet"))
        if not files:
            print("沒有檔案可以合併。")
            return

        df_all = pd.read_parquet(temp_dir)
        print(f"合併成功！總資料筆數: {len(df_all):,}")
        
        # 存檔
        df_all.to_parquet(final_parquet_path, engine='pyarrow')
        print(f"已儲存合併檔案至: {final_parquet_path}")
        
    except Exception as e:
        print(f"合併失敗: {e}")
        return

    # 2. 生成報告
    print("正在重新計算統計數據並生成報告...")
    
    try:
        scores = df_all['weighted_score']
        times = df_all['generation_time']
        
        avg_score = scores.mean()
        stdev_score = scores.std()
        min_score = scores.min()
        max_score = scores.max()
        avg_time = times.mean()
        
        print("正在分析名字重複率 (正在解析字串，請稍候)...")
        global_name_counter = Counter()
        
        # 使用 apply 進行批次處理，比 for loop 快一點
        # 但為了保險起見，我們用明確的迭代並加入進度顯示
        all_names = []
        total_rows = len(df_all)
        
        for idx, row_names in enumerate(df_all['player_names']):
            parsed_list = parse_names(row_names)
            all_names.extend(parsed_list)
            
            if idx % 50000 == 0:
                print(f"已處理 {idx}/{total_rows} 隊...")
        
        global_name_counter.update(all_names)
        
        total_players = sum(global_name_counter.values())
        unique_names = len(global_name_counter)
        duplicate_ratio = ((total_players - unique_names) / total_players) * 100 if total_players > 0 else 0
        top_duplicates = global_name_counter.most_common(20) # 看前 20 名

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# ASBL 隊伍生成大數據壓力測試報告 (救援修正版)\n")
            f.write(f"**救援時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**資料路徑**: `{TARGET_DIR}`\n")
            f.write(f"**救援資料筆數**: {len(df_all):,}\n")
            f.write(f"**總球員人次**: {total_players:,}\n\n")
            
            f.write(f"## 1. 統計數據\n")
            f.write(f"- **平均加權分**: {avg_score:.4f}\n")
            f.write(f"- **標準差**: {stdev_score:.4f}\n")
            f.write(f"- **最小/最大分**: {min_score:.4f} / {max_score:.4f}\n")
            f.write(f"- **平均生成時間**: {avg_time:.6f} 秒/隊\n")
            f.write(f"- **名字重複率**: {duplicate_ratio:.4f}%\n")
            
            f.write(f"## 2. 前 20 名重複名字\n")
            f.write(f"| 排名 | 名字 | 次數 |\n|---|---|---|\n")
            for i, (name, count) in enumerate(top_duplicates, 1):
                f.write(f"| {i} | {name} | {count} |\n")
                
        print(f"修正版報告已生成於：{report_file}")
        print("這次應該可以看到真實的重複率了！")
        
    except Exception as e:
        print(f"報告生成失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()