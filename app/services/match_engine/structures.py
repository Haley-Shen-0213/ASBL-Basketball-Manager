# app/services/match_engine/structures.py

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

class EnginePlayer:
    """
    比賽引擎專用的球員資料結構。
    使用 __slots__ 優化記憶體與存取速度。
    包含: 靜態屬性(能力值) + 動態狀態(體力/犯規) + 數據統計(得分/籃板)
    修正: 統一時間單位為 '秒 (seconds)'，避免分鐘與秒混淆。
    """
    __slots__ = (
        # === Identity (身分) ===
        'id', 'name', 'position', 'height', 'role',
        
        # === Untrainable Stats (天賦 - Spec v2.6) ===
        'ath_stamina', 'ath_strength', 'ath_speed', 'ath_jump',
        'shot_touch', 'shot_release',
        'talent_offiq', 'talent_defiq', 'talent_health', 'talent_luck',
        
        # === Trainable Stats (技術 - Spec v2.6) ===
        'shot_accuracy', 'shot_range',
        'def_rebound', 'def_boxout', 'def_contest', 'def_disrupt',
        'off_move', 'off_dribble', 'off_pass', 'off_handle',
        
        # === Dynamic State (比賽動態狀態) ===
        'current_stamina',   # 當前體力值 (0.0 - 100.0)
        'stamina_coeff',     # 體力修正係數 (0.21 - 1.0)，由 StaminaSystem 更新
        'fouls',             # 犯規次數
        'is_fouled_out',     # 是否犯滿離場
        'seconds_played',    # [Fix] 上場時間 (秒)，原 minutes_played
        'target_seconds',    # 目標上場時間 (秒) - 用於換人邏輯
        'pos_scores',        # [New] 五個位置的適性評分 Cache (Dict[str, float]) - Spec 1.1
        
        # === Match Stats (單場數據統計) ===
        'stat_pts', 'stat_reb', 'stat_ast', 'stat_stl', 'stat_blk', 'stat_tov',
        'stat_fga', 'stat_fgm', 'stat_3pa', 'stat_3pm',
        'stat_fta', 'stat_ftm', 'stat_orb', 'stat_drb'
    )

    def __init__(self, data: Dict[str, Any]):
        """
        初始化球員物件。
        data: 來自資料庫或生成器的球員資料字典
        """
        # Identity
        self.id = data.get('id', '')
        self.name = data.get('name', 'Unknown')
        self.position = data.get('position', 'G')
        self.height = data.get('height', 190)
        self.role = data.get('role', 'Bench')

        # Attributes - 預設值給 1 避免計算錯誤
        # Untrainable
        self.ath_stamina = data.get('ath_stamina', 50)
        self.ath_strength = data.get('ath_strength', 1)
        self.ath_speed = data.get('ath_speed', 1)
        self.ath_jump = data.get('ath_jump', 1)
        self.shot_touch = data.get('shot_touch', 1)
        self.shot_release = data.get('shot_release', 1)
        self.talent_offiq = data.get('talent_offiq', 1)
        self.talent_defiq = data.get('talent_defiq', 1)
        self.talent_health = data.get('talent_health', 50)
        self.talent_luck = data.get('talent_luck', 50)

        # Trainable
        self.shot_accuracy = data.get('shot_accuracy', 1)
        self.shot_range = data.get('shot_range', 1)
        self.def_rebound = data.get('def_rebound', 1)
        self.def_boxout = data.get('def_boxout', 1)
        self.def_contest = data.get('def_contest', 1)
        self.def_disrupt = data.get('def_disrupt', 1)
        self.off_move = data.get('off_move', 1)
        self.off_dribble = data.get('off_dribble', 1)
        self.off_pass = data.get('off_pass', 1)
        self.off_handle = data.get('off_handle', 1)

        # Dynamic State Init
        self.current_stamina = 100.0
        self.stamina_coeff = 1.0
        self.fouls = 0
        self.is_fouled_out = False
        self.seconds_played = 0.0 # [Fix] 初始化為 0.0 秒
        self.target_seconds = 0.0 # 需由教練系統設定
        self.pos_scores = {}      # [New] 初始化為空字典

        # Stats Init
        self.stat_pts = 0
        self.stat_reb = 0
        self.stat_ast = 0
        self.stat_stl = 0
        self.stat_blk = 0
        self.stat_tov = 0
        self.stat_fga = 0
        self.stat_fgm = 0
        self.stat_3pa = 0
        self.stat_3pm = 0
        self.stat_fta = 0
        self.stat_ftm = 0
        self.stat_orb = 0
        self.stat_drb = 0

    def __repr__(self):
        return f"<Player {self.name} ({self.position}) Pts:{self.stat_pts}>"


class EngineTeam:
    """
    比賽引擎專用的隊伍資料結構。
    """
    __slots__ = (
        'id', 'name',
        'roster',       # List[EnginePlayer] - 全隊名單 (12-15人)
        'on_court',     # List[EnginePlayer] - 目前場上 5 人
        'bench',        # List[EnginePlayer] - 目前板凳球員
        'score',        # 當前得分
        'timeouts',     # 剩餘暫停數 (預留)
        'strategy',     # 戰術設定 (預留)
        'best_five',    # List[EnginePlayer] - 預先計算好的最強5人 (Clutch Time用)
        'stat_tov'      # [New] 團隊失誤統計 (Spec 6.7.B)
    )

    def __init__(self, team_id: str, name: str, roster: List[EnginePlayer]):
        self.id = team_id
        self.name = name
        self.roster = roster
        self.on_court = [] # 需由 Service 初始化時填入
        self.bench = []    # 需由 Service 初始化時填入
        self.score = 0
        self.timeouts = 7
        self.strategy = {}
        self.best_five = [] # 需由 Service 計算後填入
        self.stat_tov = 0   # [New] 初始化

    def __repr__(self):
        return f"<Team {self.name} Score:{self.score}>"


class MatchState:
    """
    比賽狀態快照。
    """
    __slots__ = (
        'quarter',          # 當前節數 (1-4, >4 為 OT)
        'time_remaining',   # 該節剩餘秒數 (float)
        'home_score',       # 主隊分數 (快取用，實際以 Team.score 為準)
        'away_score',       # 客隊分數
        'possession',       # 當前球權: 'home' 或 'away' (或 None)
        'is_over',          # 比賽是否結束
        'game_time_elapsed' # 總比賽經過時間 (秒)
    )

    def __init__(self, quarter_length: int):
        self.quarter = 1
        self.time_remaining = float(quarter_length)
        self.home_score = 0
        self.away_score = 0
        self.possession = None
        self.is_over = False
        self.game_time_elapsed = 0.0

    def __repr__(self):
        return f"<MatchState Q{self.quarter} {self.time_remaining:.1f}s | {self.home_score}-{self.away_score}>"


@dataclass
class MatchResult:
    """
    比賽結果報表。
    使用 dataclass 因為它主要用於輸出，不需要極致的運算效能優化。
    """
    game_id: str
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    is_ot: bool
    total_quarters: int
    
    # Box Score: { team_id: { player_id: { stat_key: value } } }
    box_score: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)
    
    # Play-by-Play log (Optional, can be disabled for performance)
    pbp_log: List[str] = field(default_factory=list)