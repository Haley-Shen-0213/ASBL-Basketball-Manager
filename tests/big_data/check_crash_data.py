# tests/big_data/check_crash_data.py
import os
import pandas as pd
import glob
from pathlib import Path

# =================設定=================
# 請確認這是您剛剛輸出的目錄路徑
OUTPUT_DIR = os.path.join('tests', 'big_data', 'output', 'run_v2_6_dataset_20251212')
# ======================================

def analyze_crash_data():
    if not os.path.exists(OUTPUT_DIR):
        print(f"錯誤：找不到目錄 {OUTPUT_DIR}")
        return

    print(f"正在掃描目錄：{OUTPUT_DIR} ...")
    
    # 取得所有 parquet 檔案
    parquet_files = glob.glob(os.path.join(OUTPUT_DIR, "*.parquet"))
    
    if not parquet_files:
        print("目錄中沒有找到任何 .parquet 檔案。")
        return

    print(f"找到 {len(parquet_files)} 個檔案。開始驗證完整性...\n")

    total_records = 0
    valid_files = 0
    corrupted_files = []
    sample_df = None

    # 排序檔案以便觀察進度 (依檔名 part_00000 排序)
    parquet_files.sort()

    for i, file_path in enumerate(parquet_files):
        file_name = os.path.basename(file_path)
        try:
            # 嘗試讀取檔案
            df = pd.read_parquet(file_path)
            
            # 累加筆數
            count = len(df)
            total_records += count
            valid_files += 1
            
            # 保留第一份成功的檔案作為範例展示
            if sample_df is None:
                sample_df = df

            # 每處理 100 個檔案顯示一次進度，避免刷屏
            if (i + 1) % 100 == 0:
                print(f"已檢查 {i + 1}/{len(parquet_files)} 個檔案... (目前累計 {total_records:,} 筆)")

        except Exception as e:
            # 如果讀取失敗（通常是當機時正在寫入的那個檔案）
            print(f"⚠️ 發現損壞檔案: {file_name} (原因: {e})")
            corrupted_files.append(file_name)

    print("\n" + "="*30)
    print("       災後清點報告       ")
    print("="*30)
    print(f"✅ 完整檔案數: {valid_files}")
    print(f"❌ 損壞檔案數: {len(corrupted_files)}")
    if corrupted_files:
        print(f"   (建議刪除: {', '.join(corrupted_files)})")
    print(f"📊 成功救回資料: {total_records:,} 筆")
    print("="*30)

    if sample_df is not None:
        print("\n=== 救回資料範例 (前 5 筆) ===")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(sample_df.head(5))
        
        print("\n=== 欄位檢查 ===")
        print(list(sample_df.columns))

if __name__ == "__main__":
    analyze_crash_data()