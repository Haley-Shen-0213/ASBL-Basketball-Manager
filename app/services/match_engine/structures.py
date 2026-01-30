# app/services/match_engine/structures.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# [Optimization] 使用 slots=True
# 原理：Python 預設使用 __dict__ 字典儲存物件屬性，這會消耗大量記憶體。
# slots=True 告訴直譯器預先分配固定的記憶體空間給這些屬性。
# 效益：記憶體佔用減少約 40-50%，屬性存取速度提升約 20%。
# 對於 1 億場模擬 (涉及數十億次屬性讀取) 至關重要。

@dataclass(slots=True)
class EnginePlayer:
    """
    比賽引擎專用球員物件 (Level 4 - Phase 2 Ready)
    包含基本資訊、能力屬性、以及完整的比賽統計數據。
    """
    # --- 1. 識別與基本資訊 ---
    id: str
    name: str
    position: str  # 當前場上位置 (PG, SG, SF, PF, C)
    role: str      # 合約角色 (Star, Starter, etc.) - 用於計算上場時間權重
    grade: str     # 等級 (SSR, S, etc.) - 用於 Phase 2 數據分析
    height: float  # 身高 (cm)
    age: int = 18  # 年齡
    
    # --- 2. 體力系統 (Spec 2) ---
    current_stamina: float = 100.0
    stamina_coeff: float = 1.0  # 當前能力修正係數 (體力低於 80 開始衰退)
    
    # --- 3. 上場時間管理 (Spec 1.4 & 2.6) ---
    target_seconds: float = 0.0 # 目標上場秒數 (由 Minutes Distribution 計算)
    seconds_played: float = 0.0 # 已上場秒數
    is_fouled_out: bool = False # 是否犯滿離場
    
    # --- 4. 屬性緩存 (Spec 2.3) ---
    # 為了效能，我們將 DB 中的巢狀結構 (physical.strength) 展平為單層屬性。
    
    # 不可訓練屬性 (Untrainable)
    ath_stamina: float = 0.0
    ath_strength: float = 0.0
    ath_speed: float = 0.0
    ath_jump: float = 0.0
    talent_health: float = 0.0
    shot_touch: float = 0.0
    shot_release: float = 0.0
    talent_offiq: float = 0.0
    talent_defiq: float = 0.0
    talent_luck: float = 0.0
    
    # 可訓練屬性 (Trainable)
    shot_accuracy: float = 0.0
    shot_range: float = 0.0
    off_pass: float = 0.0
    off_dribble: float = 0.0
    off_handle: float = 0.0
    off_move: float = 0.0
    def_rebound: float = 0.0
    def_boxout: float = 0.0
    def_contest: float = 0.0
    def_disrupt: float = 0.0 # 抄截
    
    # 屬性總和 (用於 Phase 2 驗證 "能力與表現相關性")
    attr_sum: int = 0
    
    # --- 5. 位置評分緩存 (Spec 1.1) ---
    # 儲存該球員在 5 個位置的適性分數，避免重複計算
    pos_scores: Dict[str, float] = field(default_factory=dict)
    
    # --- 6. 統計數據 (Spec 7.2 Output Data) ---
    # 這些欄位將構成 Box Score，用於 Phase 2 的大數據分析
    
    # 基礎數據
    stat_pts: int = 0   # 得分
    stat_reb: int = 0   # 總籃板
    stat_ast: int = 0   # 助攻
    stat_stl: int = 0   # 抄截
    stat_blk: int = 0   # 阻攻
    stat_tov: int = 0   # 個人失誤
    fouls: int = 0      # 犯規次數
    stat_plus_minus: int = 0 # 正負值 (+/-)
    
    # 投籃細項
    stat_fgm: int = 0   # 投籃命中 (含2分與3分)
    stat_fga: int = 0   # 投籃出手
    stat_3pm: int = 0   # 三分命中
    stat_3pa: int = 0   # 三分出手
    stat_ftm: int = 0   # 罰球命中
    stat_fta: int = 0   # 罰球出手
    
    # 進階數據
    stat_orb: int = 0   # 進攻籃板
    stat_drb: int = 0   # 防守籃板
    
    # [Phase 2 新增] 快攻數據
    # 用於驗證 "速度" 屬性是否正確轉化為快攻得分
    stat_fb_made: int = 0    # 快攻進球數
    stat_fb_attempt: int = 0 # 快攻嘗試數
    
    # [Phase 2 新增] 體力分析
    # 記錄比賽結束時的剩餘體力，用於分析體力消耗與上場時間的關係
    stat_remaining_stamina: float = 0.0

@dataclass(slots=True)
class EngineTeam:
    """
    比賽引擎專用球隊物件
    """
    id: str
    name: str
    roster: List[EnginePlayer]
    
    # 動態陣容管理
    on_court: List[EnginePlayer] = field(default_factory=list) # 場上 5 人
    bench: List[EnginePlayer] = field(default_factory=list)    # 板凳球員
    best_five: List[Optional[EnginePlayer]] = field(default_factory=list) # 最強 5 人
    
    # 團隊統計 (Spec 7.3)
    score: int = 0
    stat_tov: int = 0 # 團隊失誤 (如 8秒違例/24秒違例)
    
    # [New v2.4] 違例統計
    stat_violation_8s: int = 0
    stat_violation_24s: int = 0
    
    # [Phase 2 新增] 進階團隊數據
    stat_possessions: int = 0 # 回合數 (用於計算 Pace)
    stat_possession_seconds: float = 0.0 # 累積進攻時間 (秒)
    stat_possession_history: List[float] = field(default_factory=list) # 記錄每一回合的時間 (List)
    stat_fb_made: int = 0     # 團隊快攻進球
    stat_fb_attempt: int = 0  # 團隊快攻嘗試

@dataclass(slots=True)
class MatchState:
    """
    比賽狀態追蹤
    """
    quarter: int = 1
    time_remaining: float = 720.0
    game_time_elapsed: float = 0.0
    possession: str = "" # 當前擁有球權的球隊 ID
    is_over: bool = False
  
@dataclass(slots=True)
class MatchResult:
    """
    比賽結果輸出 (Spec 7.1)
    這是 Phase 2 數據分析的主要輸入來源。
    """
    game_id: str          # 唯一識別碼
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    is_ot: bool           # 是否有延長賽
    total_quarters: int   # 總節數
    pbp_log: List[str]    # 文字轉播紀錄
    
    # [Phase 2 新增] 環境與節奏數據
    # 這些數據對於驗證 "比賽引擎是否符合現代籃球節奏" 至關重要
    pace: float = 0.0           # 節奏 (Possessions per 48 min)
    home_possessions: int = 0   # 主隊總回合數
    away_possessions: int = 0   # 客隊總回合數
    
    # 詳細的回合時間紀錄 (List)
    home_possession_history: List[float] = field(default_factory=list)
    away_possession_history: List[float] = field(default_factory=list)
    # 平均回合時間 (秒)
    home_avg_seconds_per_poss: float = 0.0
    away_avg_seconds_per_poss: float = 0.0
    
    # 快攻統計 (用於驗證 Phase 4.4 節奏與環境)
    home_fb_made: int = 0
    home_fb_attempt: int = 0
    away_fb_made: int = 0
    away_fb_attempt: int = 0
    
    # [New v2.4] 違例統計 (Team Level)
    home_violation_8s: int = 0
    home_violation_24s: int = 0
    away_violation_8s: int = 0
    away_violation_24s: int = 0