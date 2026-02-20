# app/services/scout_service.py (球探服務邏輯)
from flask import current_app
from datetime import datetime, timedelta
from app import db
from app.models.team import Team
from app.models.player import Player
from app.models.contract import Contract
from app.models.scout import ScoutingRecord
from app.models.user import User
from app.services.player_generator import PlayerGenerator
from app.utils.game_config_loader import GameConfigLoader
from app.services.image_generation_service import ImageGenerationService

class ScoutService:
    
    @staticmethod
    def generate_scouted_player(team_id, source="MANUAL"):
        """
        生成一名新球員並加入該隊的待簽名單
        """
        # 1. 生成球員 (不指定 Team ID，暫時為自由球員狀態)
        payload = PlayerGenerator.generate_payload()
        player, _ = PlayerGenerator.save_to_db(payload, user_id=None, team_id=None)
        
        # 2. 設定過期時間
        days = GameConfigLoader.get('scout_system.pending_expire_days', 7)
        expire_at = datetime.utcnow() + timedelta(days=days)
        
        # 3. 建立球探紀錄
        record = ScoutingRecord(
            team_id=team_id,
            player_id=player.id,
            expire_at=expire_at
        )
        db.session.add(record)
        db.session.commit()

        # 4. [New] 觸發背景圖片生成
        try:
            # 檢查是否有 App Context (如果是從排程呼叫，可能需要注意)
            if current_app:
                ImageGenerationService.start_background_generation(
                    current_app._get_current_object(), 
                    [player.id]
                )
        except Exception as e:
            print(f"⚠️ [Scout] 圖片生成觸發失敗: {e}")
        
        return player

    @staticmethod
    def process_daily_scout_event():
        """
        [系統排程] 每日結算：
        1. 扣除球隊資金並產生對應數量的球員
        2. 檢查過期名單 -> 轉入自由市場
        3. 檢查不活躍球隊 -> 清除名單
        """
        config = GameConfigLoader.get('scout_system')
        cost_per_level = config.get('cost_per_level', 1000)
        inactive_days = config.get('inactive_team_days', 7)
        
        teams = Team.query.all()
        logs = []
        
        for team in teams:
            # A. 每日自動產生
            n = team.daily_scout_level
            if n > 0:
                cost = n * cost_per_level
                if team.funds >= cost:
                    team.funds -= cost
                    for _ in range(n):
                        ScoutService.generate_scouted_player(team.id, source="DAILY")
                    logs.append(f"Team {team.name}: Spent {cost}, Generated {n} players.")
                else:
                    # 資金不足，強制歸零設定
                    team.daily_scout_level = 0
                    logs.append(f"Team {team.name}: Insufficient funds, scout level reset to 0.")
            
            # B. 檢查不活躍球隊 (擁有者超過 7 天沒登入)
            if team.owner and team.owner.last_login:
                delta = datetime.utcnow() - team.owner.last_login
                if delta.days >= inactive_days:
                    # 刪除該隊所有待簽紀錄 (球員變成完全自由球員，或者直接刪除球員？)
                    # 需求：未簽約名單直接消失 -> 刪除 Record 且 刪除 Player (因為是新生成的)
                    records = ScoutingRecord.query.filter_by(team_id=team.id).all()
                    for r in records:
                        p = Player.query.get(r.player_id)
                        db.session.delete(r)
                        if p and not p.team_id: # 雙重確認沒簽約
                            db.session.delete(p)
                    logs.append(f"Team {team.name}: Inactive for {delta.days} days, cleared pending list.")

        # C. 檢查過期名單 (超過 7 天沒簽約 -> 納入自由市場)
        now = datetime.utcnow()
        expired_records = ScoutingRecord.query.filter(ScoutingRecord.expire_at <= now).all()
        
        for r in expired_records:
            # 刪除紀錄，球員保留在 Players 表中但 team_id 為 Null -> 成為自由球員
            db.session.delete(r)
            # 可以在這裡加上標記，例如 player.is_free_agent = True
        
        db.session.commit()
        return logs

    @staticmethod
    def sign_player(team_id, player_id):
        """簽約球員"""
        team = Team.query.get(team_id)
        record = ScoutingRecord.query.filter_by(team_id=team_id, player_id=player_id).first()
        
        if not record:
            raise ValueError("球員不在待簽名單中")
            
        player = Player.query.get(player_id)
        if not player:
            raise ValueError("球員不存在")
            
        # 檢查人數上限
        limit = GameConfigLoader.get('system.initial_team_settings.roster_limit', 40)
        if team.players.count() >= limit:
            raise ValueError(f"球隊人數已達上限 ({limit}人)")

        # 執行簽約
        # 1. 產生合約 (依據等級)
        grade_rules = GameConfigLoader.get(f'generation.contracts.{player.grade}')
        salary_factor = GameConfigLoader.get(f'generation.salary_factors.{player.grade}')
        base_salary = int(player.rating * salary_factor)
        
        contract = Contract(
            player_id=player.id,
            team_id=team.id,
            salary=base_salary,
            years=grade_rules['years'],
            years_left=grade_rules['years'],
            role=grade_rules['role']
        )
        
        # 2. 更新球員狀態
        player.team_id = team.id
        player.user_id = team.user_id
        
        # 3. 移除待簽紀錄
        db.session.add(contract)
        db.session.delete(record)
        db.session.commit()
        
        return player
