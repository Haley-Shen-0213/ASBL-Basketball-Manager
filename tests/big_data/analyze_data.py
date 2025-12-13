# tests/big_data/analyze_data.py
import pandas as pd
import os
import sys

# 設定檔案路徑
FILE_PATH = 'tests/big_data/output/dry_run/dry_run.parquet'

def analyze_parquet():
    if not os.path.exists(FILE_PATH):
        print(f"錯誤: 找不到檔案 {FILE_PATH}")
        return

    try:
        df = pd.read_parquet(FILE_PATH)
    except Exception as e:
        print(f"讀取失敗: {e}")
        return

    print(f"=== 資料集概覽 ===")
    print(f"總筆數: {len(df):,}")
    print(f"欄位數: {len(df.columns)}")
    print(f"記憶體佔用: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    print("-" * 30)

    # 1. 檢查缺失值
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print("⚠️ 發現缺失值:")
        print(missing[missing > 0])
    else:
        print("✅ 無缺失值")
    print("-" * 30)

    # 2. 數值欄位統計 (Rating, Age, Height, Salary)
    numeric_cols = ['rating', 'age', 'height', 'salary', 'physical_stamina']
    print(f"=== 關鍵數值統計 ===")
    print(df[numeric_cols].describe().round(2))
    print("-" * 30)

    # 3. 類別分佈 (Position, Grade)
    print(f"=== 位置分佈 (Position) ===")
    print(df['position'].value_counts(normalize=True).mul(100).round(1).astype(str) + '%')
    
    print(f"\n=== 等級分佈 (Grade) ===")
    print(df['grade'].value_counts(normalize=True).mul(100).round(1).astype(str) + '%')
    print("-" * 30)

    # 4. 邏輯檢查
    print(f"=== 邏輯檢查 ===")
    invalid_ratings = df[(df['rating'] > 100) | (df['rating'] < 0)]
    print(f"能力值異常 (0-100以外): {len(invalid_ratings)} 筆")
    
    invalid_salary = df[df['salary'] < 0]
    print(f"薪資異常 (負數): {len(invalid_salary)} 筆")
    
    # 檢查是否有重複名字
    duplicate_names = df[df.duplicated(subset=['name'], keep=False)]
    print(f"重複姓名: {len(duplicate_names)} 筆")
    
    print("-" * 30)
    print("前 3 筆資料範例:")
    print(df.head(3).T)

if __name__ == "__main__":
    analyze_parquet()