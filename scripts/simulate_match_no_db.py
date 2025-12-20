# scripts/simulate_match_no_db.py

import sys
import os
import time
import math

# 1. 設定 Python 路徑，確保能 import app 模組
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

# 2. 引入專案模組
from app.utils.game_config_loader import GameConfigLoader
from app.services.team_creator import TeamCreator
from app.services.match_engine.core import MatchEngine
from app.services.match_engine.structures import EngineTeam, EnginePlayer

# 3. 初始化 Flask App Context (為了讓 PlayerGenerator 能讀取 NameLibrary DB)
app_instance = None
try:
    # 嘗試標準 Factory Pattern
    from app import create_app
    app_instance = create_app()
except ImportError:
    try:
        # 嘗試直接引用 app 物件
        from app import app as app_instance
    except ImportError:
        print("[Warning] 無法載入 Flask App，若 TeamCreator 需要資料庫連線可能會失敗。")

# =============================================================================
# Helper Functions (UI & Conversion)
# =============================================================================

def convert_payload_to_engine_player(payload, p_id):
    """
    將 PlayerGenerator 產生的字典 (Payload) 轉換為 MatchEngine 需要的 EnginePlayer 物件。
    """
    # 複製基本資料
    data = {
        'id': str(p_id),
        'name': payload['name'],
        'position': payload['position'],
        'height': payload['height'],
        'role': payload['contract_rule']['role']
    }
    
    # 合併數值屬性 (raw_stats 包含 ath_stamina, shot_accuracy 等 Config 定義的 Key)
    # 這是 EnginePlayer 初始化所需的扁平化結構
    if 'raw_stats' in payload:
        data.update(payload['raw_stats'])
    else:
        # 若無 raw_stats，嘗試從 detailed_stats 攤平 (Fallback)
        for cat, stats in payload.get('detailed_stats', {}).items():
            for k, v in stats.items():
                # 這裡需要對應回 config key，略顯複雜，假設 raw_stats 必存
                pass
        if not 'ath_stamina' in data and 'raw_stats' not in payload:
             print(f"[Warning] Player {payload['name']} missing stats.")

    return EnginePlayer(data)

def format_time(seconds):
    """將秒數轉換為 MM:SS 格式"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def print_separator(char='-', length=100):
    print(char * length)

def print_header(text):
    print_separator('=')
    print(f"| {text.center(96)} |")
    print_separator('=')

def print_box_score(team_name, players):
    """列印美化的 Box Score 表格"""
    print(f" >> {team_name} Box Score")
    print_separator()
    # Header
    header = f"{'Name':<20} {'Pos':<4} {'Role':<9} {'Min':<6} {'Pts':>3} {'Reb':>3} {'Ast':>3} {'Stl':>3} {'Blk':>3} {'TO':>3} {'FG':>6} {'3PT':>6} {'FT':>6}"
    print(header)
    print_separator('-')

    total_stats = {k: 0 for k in ['pts', 'reb', 'ast', 'stl', 'blk', 'tov', 'fgm', 'fga', '3pm', '3pa', 'ftm', 'fta']}

    # 排序: 先發 (上場時間 > 0) 優先，再依時間長短排序
    active_players = sorted(players, key=lambda p: p.seconds_played, reverse=True)

    for p in active_players:
        # 格式化數據
        min_str = format_time(p.seconds_played)
        fg_str = f"{p.stat_fgm}/{p.stat_fga}"
        tp_str = f"{p.stat_3pm}/{p.stat_3pa}"
        ft_str = f"{p.stat_ftm}/{p.stat_fta}"
        
        row = (
            f"{p.name:<20} {p.position:<4} {p.role:<9} {min_str:<6} "
            f"{p.stat_pts:>3} {p.stat_reb:>3} {p.stat_ast:>3} {p.stat_stl:>3} {p.stat_blk:>3} {p.stat_tov:>3} "
            f"{fg_str:>6} {tp_str:>6} {ft_str:>6}"
        )
        print(row)

        # 加總
        total_stats['pts'] += p.stat_pts
        total_stats['reb'] += p.stat_reb
        total_stats['ast'] += p.stat_ast
        total_stats['stl'] += p.stat_stl
        total_stats['blk'] += p.stat_blk
        total_stats['tov'] += p.stat_tov
        total_stats['fgm'] += p.stat_fgm
        total_stats['fga'] += p.stat_fga
        total_stats['3pm'] += p.stat_3pm
        total_stats['3pa'] += p.stat_3pa
        total_stats['ftm'] += p.stat_ftm
        total_stats['fta'] += p.stat_fta

    print_separator('-')
    # Totals Row
    fg_tot = f"{total_stats['fgm']}/{total_stats['fga']}"
    tp_tot = f"{total_stats['3pm']}/{total_stats['3pa']}"
    ft_tot = f"{total_stats['ftm']}/{total_stats['fta']}"
    
    total_row = (
        f"{'TOTALS':<20} {'':<4} {'':<9} {'240:00':<6} "
        f"{total_stats['pts']:>3} {total_stats['reb']:>3} {total_stats['ast']:>3} "
        f"{total_stats['stl']:>3} {total_stats['blk']:>3} {total_stats['tov']:>3} "
        f"{fg_tot:>6} {tp_tot:>6} {ft_tot:>6}"
    )
    print(total_row)
    print_separator('=')
    print("")

# =============================================================================
# Main Simulation Flow
# =============================================================================

def main():
    # 0. 啟動 Flask App Context (確保 DB 連線可用)
    if app_instance:
        ctx = app_instance.app_context()
        ctx.push()
        print("[System] Flask App Context active. Database connected.")
    
    # 1. Load Config
    print("[System] Loading Game Config...")
    # [Fix] 使用 get() 取得完整設定檔 (default key_path=None)
    config = GameConfigLoader.get()
    
    if not config:
        print("[Error] Config load failed. Please check config/game_config.yaml or .env")
        return

    # 2. Create Teams using TeamCreator
    print("[System] Generating Rosters via TeamCreator (accessing DB for names)...")
    
    try:
        # 生成主隊 Payload
        home_roster_payload = TeamCreator.create_valid_roster()
        home_name = "Taipei Kings (Home)"
        
        # 生成客隊 Payload
        away_roster_payload = TeamCreator.create_valid_roster()
        away_name = "Kaohsiung Steelers (Away)"
        
    except Exception as e:
        print(f"[Error] Team generation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Convert to Engine Structures
    print("[System] Initializing Engine Structures...")
    
    # Helper to build EngineTeam
    def build_engine_team(team_id, team_name, roster_payload):
        engine_roster = []
        for idx, p_data in enumerate(roster_payload):
            # 賦予一個臨時 ID
            p_id = f"{team_id}_P{idx:02d}"
            engine_player = convert_payload_to_engine_player(p_data, p_id)
            engine_roster.append(engine_player)
        return EngineTeam(team_id, team_name, engine_roster)

    home_team = build_engine_team("HOME", home_name, home_roster_payload)
    away_team = build_engine_team("AWAY", away_name, away_roster_payload)

    # 4. Initialize Match Engine
    print("[System] Booting Match Engine v1.6...")
    engine = MatchEngine(home_team, away_team, config)

    # 5. Run Simulation
    print(f"[Match] Simulating: {home_name} vs {away_name}")
    start_time = time.time()
    
    result = engine.simulate()
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"[Match] Simulation Complete in {duration:.4f} seconds.")
    print("")

    # 6. Display Results
    
    # --- Scoreboard ---
    print_header("ASBL MATCH RESULT")
    
    ot_text = f" (OT{result.total_quarters - 4})" if result.is_ot else ""
    
    print(f"\n   {home_name:<30}  {result.home_score:>3}")
    print(f"   {away_name:<30}  {result.away_score:>3}")
    print(f"\n   Duration: {result.total_quarters} Quarters{ot_text}")
    print("")

    # --- Box Scores ---
    print_box_score(home_name, home_team.roster)
    print_box_score(away_name, away_team.roster)

    # --- PBP Snippet (Last 10 events) ---
    print_header("Play-by-Play (Last 10 Events)")
    if result.pbp_log:
        for log in result.pbp_log[-10:]:
            print(f"   {log}")
    else:
        print("   (No logs generated)")
    print_separator('=')

if __name__ == "__main__":
    main()
