# scripts/batch_generate_images.py
# -*- coding: utf-8 -*-
"""
專案名稱：ASBL-Basketball-Manager
模組名稱：球員卡牌批次生成工具 (Batch Generator)
功能描述：
    1. 掃描資料庫中的所有球員。
    2. 比對前端圖檔目錄，找出尚未生成圖片的球員 ID。
    3. 呼叫 ImageGenerationService 進行補圖。

使用說明：
    於專案根目錄執行： python scripts/batch_generate_images.py
"""

import os
import sys
import time

# 將專案根目錄加入路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.player import Player
from app.services.image_generation_service import ImageGenerationService

def main():
    app = create_app()
    
    with app.app_context():
        print("🚀 [ASBL] 啟動球員卡牌批次生成工具...")
        
        try:
            # 1. 初始化服務
            service = ImageGenerationService()
            print(f"📂 輸出目錄: {service.output_dir}")
            
            # 2. 準備模型 (只做一次)
            service.ensure_model_ready()
            
            # 3. 掃描資料庫
            print("🔍 正在掃描資料庫與檔案系統...")
            all_players = Player.query.all()
            
            missing_players = []
            for p in all_players:
                # 透過 Service 取得預期路徑，檢查是否存在
                img_path = service.get_image_path(p.id)
                if not os.path.exists(img_path):
                    missing_players.append(p)
            
            total_missing = len(missing_players)
            
            if total_missing == 0:
                print("✨ 檢查完畢：所有球員皆已有卡牌，無需生成。")
                return
            
            print(f"📋 發現 {total_missing} 名球員缺少卡牌，開始排程生成...")
            print("-" * 50)
            
            # 4. 執行生成迴圈
            success_count = 0
            fail_count = 0
            
            for idx, player in enumerate(missing_players):
                start_time = time.time()
                print(f"[{idx+1}/{total_missing}] 生成球員 ID: {player.id} | {player.name} ({player.grade})... ", end="", flush=True)
                
                result = service.generate_card_for_player(player)
                
                elapsed = time.time() - start_time
                
                if result:
                    print(f"✅ 完成 ({elapsed:.2f}s)")
                    success_count += 1
                else:
                    print(f"❌ 失敗")
                    fail_count += 1
                
                # 簡單的冷卻時間，避免 GPU 過熱或 API 塞車 (可視情況調整)
                # time.sleep(0.5)
            
            print("-" * 50)
            print(f"🎉 作業結束。")
            print(f"   - 成功: {success_count}")
            print(f"   - 失敗: {fail_count}")
            
        except Exception as e:
            print(f"❌ 發生未預期的錯誤: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()