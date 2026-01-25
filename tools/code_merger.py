# /ASBL-Basketball-Manager/tools/code_merger.py
# -*- coding: utf-8 -*-
"""
專案名稱：ASBL-Basketball-Manager (籃球數據遊戲)
模組名稱：程式碼合併工具 (Code Merger)
功能描述：
    此腳本用於將專案中指定的「核心邏輯」與「規格文件」合併為單一文字檔。
    便於開發者進行上下文檢視或提供給 AI 進行架構審查。
    
使用說明：
    1. 請將此檔案放置於專案根目錄下的 tools/ 資料夾中。
    2. 於專案根目錄執行指令：python tools/code_merger.py
    
作者：Monica (AI Assistant)
日期：2026-01-04
"""

import os

# ==========================================
# 配置區域 (Configuration)
# ==========================================

# 專案根目錄 (假設此腳本位於 tools/ 目錄下，故向上尋找兩層)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 輸出檔案名稱
OUTPUT_FILE = "project_context.txt"

# 指定要包含的檔案清單 (白名單)
# 依據 ASBL 專案結構配置，包含核心引擎、生成器、設定檔與規格書
SPECIFIC_FILES = [
    # --- 文件 (Documentation) ---
    "ASBL_Match_Engine_Specification.md",
    "ASBL_Player_System_Specification.md",

    # --- 設定檔 (Configuration) ---
    "config/game_config.yaml",

    # --- 應用程式服務層 (App Services) ---
    "app/services/player_generator.py",
    "app/services/team_creator.py",

    # --- 比賽引擎核心 (Match Engine Core) ---
    "app/services/match_engine/core.py",
    "app/services/match_engine/service.py",
    "app/services/match_engine/structures.py",

    # --- 比賽引擎子系統 (Match Engine Systems) ---
    "app/services/match_engine/systems/attribution.py",
    "app/services/match_engine/systems/play_logic.py",
    "app/services/match_engine/systems/stamina.py",
    "app/services/match_engine/systems/substitution.py",

    # --- 比賽引擎工具 (Match Engine Utils) ---
    "app/services/match_engine/utils/calculator.py",
    "app/services/match_engine/utils/rng.py",

    # --- 比賽引擎測試工具 (Match Engine Test Utils) ---
    "tests/match_bigdata_test/run_core_bigdata_test.py",
]

# ==========================================
# 主程式邏輯 (Main Logic)
# ==========================================

def merge_files():
    """
    執行檔案合併作業
    """
    output_path = os.path.join(PROJECT_ROOT, OUTPUT_FILE)
    total_files = 0
    missing_files = []
    
    print(f"🚀 [ASBL] 開始執行程式碼合併作業...")
    print(f"📂 專案根目錄: {PROJECT_ROOT}")
    print(f"📄 目標檔案數: {len(SPECIFIC_FILES)}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            # 寫入檔頭資訊
            outfile.write(f"ASBL Basketball Manager - 專案程式碼匯總\n")
            outfile.write(f"生成時間: {os.popen('date').read().strip() if os.name != 'nt' else 'N/A'}\n")
            outfile.write("=" * 60 + "\n\n")

            # 遍歷指定清單進行處理
            for rel_path in SPECIFIC_FILES:
                full_path = os.path.join(PROJECT_ROOT, rel_path)
                
                if os.path.exists(full_path):
                    process_file(full_path, outfile, PROJECT_ROOT)
                    total_files += 1
                else:
                    print(f"⚠️  警告: 找不到檔案 -> {rel_path}")
                    missing_files.append(rel_path)
                    # 即使檔案遺失，也在輸出檔中標記，以便開發者察覺
                    outfile.write(f"File: {rel_path}\n")
                    outfile.write(f"!!! FILE NOT FOUND !!!\n")
                    outfile.write("\n" + "=" * 60 + "\n\n")

        print(f"\n✅ 合併完成！")
        print(f"📊 成功處理: {total_files}/{len(SPECIFIC_FILES)} 個檔案")
        
        if missing_files:
            print(f"❌ 遺失檔案列表:")
            for mf in missing_files:
                print(f"   - {mf}")
                
        print(f"💾 輸出檔案位置: {output_path}")

    except Exception as e:
        print(f"\n❌ 發生致命錯誤: {str(e)}")

def process_file(file_path, outfile, root_path):
    """
    讀取單個檔案並寫入輸出檔
    
    Args:
        file_path (str): 檔案絕對路徑
        outfile (file object): 輸出檔案物件
        root_path (str): 專案根目錄
    """
    rel_path = os.path.relpath(file_path, root_path)
    print(f"   正在處理: {rel_path}")
    
    outfile.write(f"File: {rel_path}\n")
    outfile.write("-" * 60 + "\n")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as infile:
            content = infile.read()
            outfile.write(content)
    except UnicodeDecodeError:
        outfile.write(f"[錯誤: 無法以 UTF-8 格式讀取此檔案，可能是二進制文件]\n")
    except Exception as e:
        outfile.write(f"[錯誤: 讀取檔案時發生異常 - {str(e)}]\n")
        
    outfile.write("\n\n" + "=" * 60 + "\n\n")

if __name__ == "__main__":
    merge_files()