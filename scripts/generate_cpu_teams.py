# scripts/generate_cpu_teams.py
import sys
import os
import time

# 將專案根目錄加入 Python 路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User
from app.models.team import Team
from app.models.tactics import TeamTactics
from app.services.team_creator import TeamCreator
from app.services.player_generator import PlayerGenerator
from app.utils.game_config_loader import GameConfigLoader

def generate_cpu_teams(count=35):
    """
    生成指定數量的 CPU 球隊
    流程比照 auth.py 的 register 邏輯，並額外建立 TeamTactics
    """
    app = create_app()
    
    with app.app_context():
        print(f"🚀 開始生成 {count} 支 CPU 球隊...")
        
        # 1. 初始化生成器快取 (只需一次)
        print("📥 初始化 PlayerGenerator 快取...")
        PlayerGenerator.initialize_class()
        
        # 2. 讀取初始設定
        init_settings = GameConfigLoader.get('system.initial_team_settings', {})
        init_funds = init_settings.get('funds', 300000)
        init_rep = init_settings.get('reputation', 0)
        init_scout = init_settings.get('scout_chances', 100)
        
        created_count = 0
        skipped_count = 0
        start_time = time.time()

        for i in range(1, count + 1):
            # 格式化名稱: CPUTeam_001, CPUTeam_002...
            team_name = f"CPUTeam_{i:03d}"
            manager_name = f"CPU_Manager_{i:03d}"
            email = f"cpu_manager_{i:03d}@asbl.game"
            
            # 檢查是否已存在
            if Team.query.filter_by(name=team_name).first():
                print(f"⚠️  [跳過] 球隊 {team_name} 已存在")
                skipped_count += 1
                continue
            
            if User.query.filter_by(username=manager_name).first():
                print(f"⚠️  [跳過] 使用者 {manager_name} 已存在")
                skipped_count += 1
                continue

            try:
                # --- 步驟 A: 建立使用者 (Owner) ---
                user = User(username=manager_name, email=email)
                user.set_password("cpu_password_secure") # 設定預設密碼
                user.last_login = None # CPU 不登入
                
                db.session.add(user)
                db.session.flush() # 取得 user.id
                
                # --- 步驟 B: 建立球隊 (Team) ---
                team = Team(
                    name=team_name,
                    owner=user,
                    funds=init_funds,
                    reputation=init_rep,
                    arena_name=f"{team_name} Arena",    # 預設場館名
                    fanpage_name=f"{team_name} Official", # 預設粉絲團
                    scout_chances=init_scout
                )
                db.session.add(team)
                db.session.flush() # 取得 team.id
                
                # --- 步驟 C: 生成 15 人名單 (Roster) ---
                # 使用 TeamCreator 確保符合開隊規則 (C>=2, PG>=2 等)
                roster_payloads = TeamCreator.create_valid_roster()
                
                player_ids = []
                for p_data in roster_payloads:
                    # 儲存球員與合約
                    player, _ = PlayerGenerator.save_to_db(p_data, user_id=user.id, team_id=team.id)
                    player_ids.append(player.id)
                
                # --- 步驟 D: 建立戰術配置 (Tactics) ---
                # CPU 球隊預設將所有生成的 15 人都放入登錄名單
                tactics = TeamTactics(
                    team_id=team.id,
                    roster_list=player_ids # 直接填入 ID 列表
                )
                db.session.add(tactics)

                # --- 提交交易 ---
                db.session.commit()
                created_count += 1
                
                # 進度顯示
                elapsed = time.time() - start_time
                print(f"✅ [建立成功] {team_name} (ID: {team.id}) - 擁有 {len(player_ids)} 名球員")

            except Exception as e:
                db.session.rollback()
                print(f"❌ [建立失敗] {team_name}: {str(e)}")

        print("-" * 50)
        print(f"🎉 作業完成！")
        print(f"   - 新增: {created_count}")
        print(f"   - 跳過: {skipped_count}")
        print(f"   - 總耗時: {time.time() - start_time:.2f} 秒")

if __name__ == "__main__":
    # 執行腳本
    generate_cpu_teams(35)
