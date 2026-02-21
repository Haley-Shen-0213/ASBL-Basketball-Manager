# manage.py
from app import create_app
from app.services.league_service import LeagueService

app = create_app()

def manual_trigger():
    print("========================================")
    print("ASBL 聯賽手動觸發工具")
    print("========================================")
    print("1. 執行換日 (00:00) - 推進日期、生成賽程")
    print("2. 執行比賽 (19:00) - 模擬當日賽事")
    print("3. 自動模擬 (換日 + 比賽) 直到第 N 天")
    print("========================================")
    
    choice = input("請選擇操作 (1-3): ")
    
    with app.app_context():
        if choice == '1':
            print("🚀 [手動] 執行換日程序...")
            LeagueService.process_day_change_0000()
            print("✅ 換日完成。")
            
        elif choice == '2':
            print("🚀 [手動] 執行比賽模擬...")
            LeagueService.process_match_execution_1900()
            print("✅ 比賽模擬完成。")
            
        elif choice == '3':
            try:
                target_day_str = input("請輸入目標天數 (例如 70): ")
                target_day = int(target_day_str)
                
                print(f"🚀 [自動模擬] 開始連續執行，目標: 第 {target_day} 天...")
                
                while True:
                    # 1. 獲取當前賽季狀態
                    season = LeagueService.get_current_season()
                    
                    # 2. 檢查是否已達到目標天數
                    # 如果當前天數已經 >= 目標天數，且當日比賽已完成 (這裡簡單判斷天數即可)
                    # 邏輯: 若現在是 Day 69，執行換日變 Day 70，執行比賽，Loop 結束。
                    if season.current_day >= target_day:
                        print(f"🛑 [自動模擬] 已推進至第 {season.current_day} 天，目標達成，停止執行。")
                        break
                    
                    print(f"\n--- 正在處理第 {season.current_day + 1} 天 ---")
                    
                    # 3. 執行換日 (Day N -> Day N+1)
                    LeagueService.process_day_change_0000()
                    
                    # 4. 執行比賽
                    LeagueService.process_match_execution_1900()
                    
            except ValueError:
                print("❌ 錯誤: 請輸入有效的數字天數。")
            except Exception as e:
                print(f"❌ 發生未預期的錯誤: {e}")
                import traceback
                traceback.print_exc()
                
        else:
            print("❌ 無效的選擇")

if __name__ == '__main__':
    manual_trigger()