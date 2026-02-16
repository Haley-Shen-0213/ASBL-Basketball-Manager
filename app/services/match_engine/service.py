# app/services/match_engine/service.py

from app.models.player import Player
# [修正] Team 定義在 app.models.team
from app.models.team import Team
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

        # 簡單評級推導
        grade = "B" 
        if db_player.rating:
            if db_player.rating >= 950: grade = "SSR"
            elif db_player.rating >= 900: grade = "SS"
            elif db_player.rating >= 800: grade = "S"
            elif db_player.rating >= 700: grade = "A"
            elif db_player.rating >= 600: grade = "B"
            elif db_player.rating >= 400: grade = "C"
            else: grade = "G"

        return EnginePlayer(
            id=str(db_player.id),
            name=db_player.name,
            nationality=db_player.nationality,
            position=db_player.position,
            role=role,
            grade=grade,
            height=float(db_player.height),
            age=db_player.age,
            
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
    def convert_team(db_team: Team) -> EngineTeam:
        roster = [DBToEngineAdapter.convert_player(p) for p in db_team.players]
        return EngineTeam(
            id=str(db_team.id),
            name=db_team.name,
            roster=roster
        )
