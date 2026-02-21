# app/services/match_engine/service.py
# 模組名稱: 資料庫轉引擎適配器
# 修正: 
# 1. convert_team 新增 tactics 參數以解決 TypeError
# 2. 根據 tactics.roster_list 過濾出賽名單

from app.models.player import Player
from app.models.team import Team
from app.models.tactics import TeamTactics
from app.services.match_engine.structures import EngineTeam, EnginePlayer

class DBToEngineAdapter:
    """
    負責將資料庫模型 (SQLAlchemy Models) 轉換為 比賽引擎模型 (Dataclasses)
    """
    
    @staticmethod
    def convert_player(db_player: Player) -> EnginePlayer:
        # 解析 JSON stats
        stats = db_player.detailed_stats or {}
        phy = stats.get('physical', {})
        off = stats.get('offense', {})
        def_ = stats.get('defense', {})
        men = stats.get('mental', {})

        # 嘗試從 contract 獲取角色，若無則預設 Bench
        role = 'Bench'
        if db_player.contract:
            role = db_player.contract.role

        # [修正] 直接讀取資料庫中的等級，不再重新推導
        grade = db_player.grade if db_player.grade else "G"

        return EnginePlayer(
            id=str(db_player.id),
            name=db_player.name,
            nationality=db_player.nationality,
            position=db_player.position,
            role=role,
            grade=grade,
            height=float(db_player.height),
            age=db_player.age,
            training_points=db_player.training_points,
            
            # --- 屬性對應 (Mapping) ---
            ath_stamina=float(phy.get('stamina', 50)),
            ath_strength=float(phy.get('strength', 50)),
            ath_speed=float(phy.get('speed', 50)),
            ath_jump=float(phy.get('jumping', 50)),
            talent_health=float(phy.get('health', 50)),
            
            shot_touch=float(off.get('touch', 50)),
            shot_release=float(off.get('release', 50)),
            shot_accuracy=float(off.get('accuracy', 50)),
            shot_range=float(off.get('range', 50)),
            
            off_pass=float(off.get('passing', 50)),
            off_dribble=float(off.get('dribble', 50)),
            off_handle=float(off.get('handle', 50)),
            off_move=float(off.get('move', 50)),
            
            def_rebound=float(def_.get('rebound', 50)),
            def_boxout=float(def_.get('boxout', 50)),
            def_contest=float(def_.get('contest', 50)),
            def_disrupt=float(def_.get('disrupt', 50)),
            
            talent_offiq=float(men.get('off_iq', 50)),
            talent_defiq=float(men.get('def_iq', 50)),
            talent_luck=float(men.get('luck', 50)),
            
            attr_sum=db_player.rating or 0
        )

    @staticmethod
    def convert_team(db_team: Team, tactics: TeamTactics = None) -> EngineTeam:
        """
        將 DB Team 轉換為 EngineTeam
        :param db_team: 資料庫球隊物件
        :param tactics: (Optional) 戰術設定，用於決定登錄名單
        """
        # 1. 先轉換所有球員
        all_players = [DBToEngineAdapter.convert_player(p) for p in db_team.players]
        
        final_roster = all_players

        # 2. 若有傳入戰術設定，則過濾出 Active Roster
        if tactics and tactics.roster_list:
            # roster_list 存的是 int ID，EnginePlayer.id 是 str，需轉換比對
            active_ids = set(tactics.roster_list) # Set for O(1) lookup
            
            filtered = [p for p in all_players if int(p.id) in active_ids]
            
            # 防呆：如果過濾後沒人 (例如 ID 對不上)，則回退到全部，避免比賽崩潰
            if filtered:
                final_roster = filtered

        return EngineTeam(
            id=str(db_team.id),
            name=db_team.name,
            roster=final_roster
        )