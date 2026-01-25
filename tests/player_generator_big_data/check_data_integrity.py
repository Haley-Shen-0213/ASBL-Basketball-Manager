# tests/player_generator_big_data/check_data_integrity.py
import os
import sys
import glob
import pyarrow.parquet as pq
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# ==========================================
# 設定
# ==========================================
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def check_file(filepath):
    """
    嘗試讀取單個 Parquet 檔案的 Schema 和第一批數據
    以驗證檔案是否損壞或字典編碼是否有誤
    """
    try:
        # 僅讀取 Metadata 與第一行數據，速度較快
        parquet_file = pq.ParquetFile(filepath)
        _ = parquet_file.metadata
        _ = parquet_file.read_row_group(0)
        return None  # 成功
    except Exception as e:
        return (filepath, str(e))

def main():
    print(f"Checking data integrity in: {DATA_DIR}")
    files = glob.glob(os.path.join(DATA_DIR, "*.parquet"))
    
    if not files:
        print("No parquet files found.")
        return

    print(f"Found {len(files)} files. Starting verification...")
    
    bad_files = []
    
    # 使用多進程加速檢查
    with ProcessPoolExecutor(max_workers=20) as executor:
        results = list(tqdm(executor.map(check_file, files), total=len(files), unit="file"))
    
    for res in results:
        if res is not None:
            bad_files.append(res)
    
    print("-" * 60)
    if bad_files:
        print(f"❌ Found {len(bad_files)} corrupted files:")
        for fpath, err in bad_files:
            print(f"File: {os.path.basename(fpath)}")
            print(f"Error: {err}")
            # 選項：自動刪除壞檔
            # os.remove(fpath)
            # print("Deleted.")
        print("\n建議：請手動刪除上述損壞檔案後，再執行分析報告。")
    else:
        print("✅ All files passed integrity check.")
    print("-" * 60)

if __name__ == "__main__":
    main()