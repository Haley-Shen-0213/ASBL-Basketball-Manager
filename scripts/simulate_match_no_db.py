# scripts/simulate_match_no_db.py
import sys
import os
import time
import random
import contextlib  # [New] 用於重導向輸出
from dataclasses import asdict

# ==========================================
# 1. 環境設定與路徑掛載
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../'))
sys.path.append(project_root)

from app import create_app
from config import Config
from app.utils.game_config_loader import GameConfigLoader

# 匯入服務
from app.services.team_creator import TeamCreator
from app.services.player_generator import PlayerGenerator
from app.services.match_engine.core import MatchEngine
from app.services.match_engine.structures import EngineTeam, EnginePlayer
from app.services.match_engine.systems.attribution import AttributionSystem

# ==========================================
# 2. Mock (模擬) 與 Patch (熱修復) 區域
# ==========================================

# [Mock 1] 替換 PlayerGenerator 的資料庫查詢
def mock_get_random_text(category, length_filter=None):
    if category == 'last':
        return random.choice(["林", "陳", "張", "王", "李", "黃", "吳", "劉"])
    return random.choice(["豪", "明", "傑", "偉", "志", "雄", "文", "華"])

# print("[System] Mocking PlayerGenerator DB calls...") # 移至 Main 內以免干擾輸出
PlayerGenerator._get_random_text = staticmethod(mock_get_random_text)

# [Patch 1] 修復 EnginePlayer 屬性缺失 (minutes vs seconds)
if not hasattr(EnginePlayer, 'minutes_played'):
    @property
    def minutes_played(self):
        return self.seconds_played / 60.0
    EnginePlayer.minutes_played = minutes_played

if not hasattr(EnginePlayer, 'target_minutes'):
    @property
    def target_minutes(self):
        if not hasattr(self, 'target_seconds'): return 0.0
        return self.target_seconds / 60.0
    EnginePlayer.target_minutes = target_minutes

# [Patch 2] 修復 AttributionSystem 方法名稱不一致
if not hasattr(AttributionSystem, 'record_attempt'):
    if hasattr(AttributionSystem, 'record_shot_attempt'):
        AttributionSystem.record_attempt = AttributionSystem.record_shot_attempt
    else:
        @staticmethod
        def mock_record_attempt(player, is_3pt):
            player.stat_fga += 1
            if is_3pt:
                player.stat_3pa += 1
        AttributionSystem.record_attempt = mock_record_attempt

# ==========================================
# 3. Adapter (轉接器)
# ==========================================

class TestEnginePlayer(EnginePlayer):
    def __init__(self, data):
        super().__init__(data)
        self.seconds_played = 0.0
        self.target_seconds = 0.0 

def payload_to_engine_player(payload, player_id_prefix):
    """
    將 TeamCreator 產生的 Dictionary 轉換為 EnginePlayer 物件
    並執行 v2.6 規格的欄位映射
    """
    raw = payload.get('raw_stats', {})
    
    mapping = {
        # Untrainable (10)
        'ath_stamina':  ['ath_stamina', 'stamina'],
        'ath_strength': ['ath_strength', 'strength'],
        'ath_speed':    ['ath_speed', 'speed'],
        'ath_jump':     ['ath_jump', 'jump', 'jumping'],
        'talent_health':['talent_health', 'health'],
        'shot_touch':   ['shot_touch', 'touch'],
        'shot_release': ['shot_release', 'release'],
        'talent_offiq': ['talent_offiq', 'off_iq', 'offiq'],
        'talent_defiq': ['talent_defiq', 'def_iq', 'defiq'],
        'talent_luck':  ['talent_luck', 'luck'],
        
        # Trainable (10)
        'shot_accuracy':['shot_accuracy', 'accuracy', 'shot'],
        'shot_range':   ['shot_range', 'range'],
        'off_pass':     ['off_pass', 'passing', 'pass'],
        'off_dribble':  ['off_dribble', 'dribble'],
        'off_handle':   ['off_handle', 'handle', 'ball_handling'],
        'off_move':     ['off_move', 'move', 'movement'],
        'def_rebound':  ['def_rebound', 'rebound'],
        'def_boxout':   ['def_boxout', 'boxout'],
        'def_contest':  ['def_contest', 'contest'],
        'def_disrupt':  ['def_disrupt', 'disrupt', 'steal']
    }

    mapped_stats = {}
    
    for engine_key, source_keys in mapping.items():
        val = 1 
        found = False
        for src in source_keys:
            if src in raw:
                val = raw[src]
                found = True
                break
        if not found:
            for src in source_keys:
                if src in payload:
                    val = payload[src]
                    found = True
                    break
        mapped_stats[engine_key] = val

    data = {
        "id": f"{player_id_prefix}_{payload['name']}_{random.randint(100,999)}", 
        "name": payload['name'],
        "position": payload['position'],
        "height": payload['height'],
        "role": payload['contract_rule']['role'],
        "grade": payload.get('grade', 'N/A') 
    }
    data.update(mapped_stats)
    
    player = TestEnginePlayer(data)
    player.grade = data['grade']
    return player

# ==========================================
# 4. 輔助顯示函式
# ==========================================
def print_roster_details_full(team_name: str, players: list):
    print(f"\n📋 {team_name} 完整能力值 (Spec v2.6)")
    header_1 = f"{'NAME':<8} {'POS':<3} {'GRD':<3} | {'STM':<3} {'STR':<3} {'SPD':<3} {'JMP':<3} {'HLT':<3} {'LUK':<3} | {'OIQ':<3} {'DIQ':<3} | {'TCH':<3} {'REL':<3} {'ACC':<3} {'RNG':<3} | {'HAN':<3} {'PAS':<3} {'DRI':<3} {'MOV':<3} | {'REB':<3} {'BOX':<3} {'CON':<3} {'DIS':<3}"
    print(header_1)
    print("-" * 140)
    
    pos_order = {"C": 0, "PF": 1, "SF": 2, "SG": 3, "PG": 4}
    sorted_players = sorted(players, key=lambda p: pos_order.get(p.position, 99))
    
    grade_counts = {}

    for p in sorted_players:
        g = getattr(p, 'grade', '?')
        grade_counts[g] = grade_counts.get(g, 0) + 1
        row = (
            f"{p.name:<8} {p.position:<3} {g:<3} | "
            f"{getattr(p, 'ath_stamina', 0):<3} {getattr(p, 'ath_strength', 0):<3} {getattr(p, 'ath_speed', 0):<3} {getattr(p, 'ath_jump', 0):<3} {getattr(p, 'talent_health', 0):<3} {getattr(p, 'talent_luck', 0):<3} | "
            f"{getattr(p, 'talent_offiq', 0):<3} {getattr(p, 'talent_defiq', 0):<3} | "
            f"{getattr(p, 'shot_touch', 0):<3} {getattr(p, 'shot_release', 0):<3} {getattr(p, 'shot_accuracy', 0):<3} {getattr(p, 'shot_range', 0):<3} | "
            f"{getattr(p, 'off_handle', 0):<3} {getattr(p, 'off_pass', 0):<3} {getattr(p, 'off_dribble', 0):<3} {getattr(p, 'off_move', 0):<3} | "
            f"{getattr(p, 'def_rebound', 0):<3} {getattr(p, 'def_boxout', 0):<3} {getattr(p, 'def_contest', 0):<3} {getattr(p, 'def_disrupt', 0):<3}"
        )
        print(row)
    
    print("-" * 140)
    print(f"📌 等級分佈: {dict(sorted(grade_counts.items()))}")

def print_box_score(team: EngineTeam):
    print(f"\n📊 {team.name} Box Score")
    print(f"{'POS':<4} {'NAME':<16} {'ROLE':<8} | {'MIN':<5} {'PTS':<4} {'REB':<4} {'AST':<4} | {'FG':<7} {'3PT':<7} | {'+/-':<4}")
    print("-" * 85)
    sorted_roster = sorted(team.roster, key=lambda p: p.seconds_played, reverse=True)
    for p in sorted_roster:
        if p.seconds_played == 0: continue
        min_str = f"{p.seconds_played/60:.1f}"
        fg_str = f"{p.stat_fgm}/{p.stat_fga}"
        tp_str = f"{p.stat_3pm}/{p.stat_3pa}"
        print(f"{p.position:<4} {p.name:<16} {p.role:<8} | {min_str:<5} {p.stat_pts:<4} {p.stat_reb:<4} {p.stat_ast:<4} | {fg_str:<7} {tp_str:<7} | {p.current_stamina:.0f}")

# ==========================================
# 5. 核心模擬邏輯 (被包裹的函式)
# ==========================================
def run_simulation_logic():
    print("🏀 ASBL Simulation: Team Creation -> Match Engine (Full Logs) 🏀")
    print("=" * 60)
    print("[System] Mocking PlayerGenerator DB calls...")

    app = create_app(Config)
    
    with app.app_context():
        print("[Step 1] Loading Game Config...")
        config = GameConfigLoader.load()
        
        print("[Step 2] Calling TeamCreator...")
        try:
            home_payloads = TeamCreator.create_valid_roster()
            away_payloads = TeamCreator.create_valid_roster()
        except Exception as e:
            print(f"[Error] Team Creation Failed: {e}")
            import traceback
            traceback.print_exc()
            return

        print("[Step 3] Adapting data...")
        home_players = [payload_to_engine_player(p, "H") for p in home_payloads]
        away_players = [payload_to_engine_player(p, "A") for p in away_payloads]
        
        home_team = EngineTeam("HOME", "臺北富邦勇士 (Sim)", home_players)
        away_team = EngineTeam("AWAY", "新北國王 (Sim)", away_players)

        print_roster_details_full(home_team.name, home_players)
        print_roster_details_full(away_team.name, away_players)

        print("[Step 4] Initializing Match Engine...")
        engine = MatchEngine(home_team, away_team, config)
        
        print("[Step 5] Simulating...")
        start_time = time.time()
        result = engine.simulate()
        duration = time.time() - start_time

        print("\n" + "=" * 60)
        print(f"🏁 FINAL SCORE (Simulated in {duration:.4f}s)")
        print("=" * 60)
        print(f"{home_team.name}: {result.home_score}")
        print(f"{away_team.name}: {result.away_score}")
        
        print_box_score(home_team)
        print_box_score(away_team)
        
        print("\n📜 Full Play-by-Play with Calculations:")
        print("=" * 80)
        if result.pbp_log:
            for log in result.pbp_log:
                print(log)

# ==========================================
# 6. 主程式 (處理檔案輸出)
# ==========================================
def main():
    # 1. 產生檔案名稱
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_filename = f"match_log_{timestamp}.txt"
    log_path = os.path.join(project_root, log_filename)

    print(f"🚀 啟動模擬程式...")
    print(f"📂 輸出日誌將儲存至: {log_path}")
    print(f"⏳ 正在模擬中，請稍候...")

    # 2. 開啟檔案並重導向 stdout
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            with contextlib.redirect_stdout(f):
                run_simulation_logic()
        
        print(f"✅ 模擬完成！請查看檔案: {log_filename}")
    
    except Exception as e:
        # 恢復 stdout 以顯示錯誤
        sys.stdout = sys.__stdout__
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        from scripts.terminal import clear_terminal
        clear_terminal()
    except ImportError: pass
    except Exception: pass
    main()