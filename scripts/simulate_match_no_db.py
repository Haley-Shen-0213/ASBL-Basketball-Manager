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
        print("[警告] 無法載入 Flask App，若 TeamCreator 需要資料庫連線可能會失敗。")

# =============================================================================
# 輔助函式 (UI 與 資料轉換)
# =============================================================================

def convert_payload_to_engine_player(payload, p_id):
    """
    將 PlayerGenerator 產生的字典 (Payload) 轉換為 MatchEngine 需要的 EnginePlayer 物件。
    """
    # 1. 提取必要欄位
    data = {
        'id': str(p_id),
        'name': payload['name'],
        'position': payload['position'],
        'role': payload['contract_rule']['role'],
        'grade': payload.get('grade', 'G'),
        'height': payload['height']
    }
    
    # 2. 合併數值屬性
    if 'raw_stats' in payload:
        data.update(payload['raw_stats'])
    else:
        # 備案邏輯：若無 raw_stats，嘗試解析巢狀結構
        attrs = payload.get('attributes', {})
        if 'trainable' in attrs:
            # 合併巢狀字典
            flat_stats = {**attrs.get('untrainable', {}), **attrs.get('trainable', {})}
            data.update(flat_stats)
        else:
            data.update(attrs)

    # 3. 過濾多餘的 Key
    allowed_keys = EnginePlayer.__slots__ if hasattr(EnginePlayer, '__slots__') else EnginePlayer.__annotations__.keys()
    filtered_data = {k: v for k, v in data.items() if k in allowed_keys}

    # 4. 建立物件
    return EnginePlayer(**filtered_data)

def format_time(seconds):
    """將秒數轉換為 MM:SS 格式"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def print_separator(char='-', length=100):
    print(char * length)

def print_header(text):
    print_separator('=')
    # 考慮中文字寬問題，簡單置中處理
    print(f"| {text.center(94)} |") 
    print_separator('=')

def print_team_details(team_name, roster_payload):
    """
    [New] 列印詳細的球員等級與能力值 (繁體中文版)
    """
    print_header(f"球隊陣容詳情: {team_name}")
    
    # 表頭 (中英文對照或純中文，這裡使用中文簡稱以節省空間)
    # 等級 | 姓名 | 位置 | 角色 | 身高 | 總評
    print(f"{'等級':<6} {'姓名':<20} {'位置':<4} {'角色':<10} {'身高':<4} {'總評':<5}")
    print_separator('-')

    for p in roster_payload:
        grade = p.get('grade', 'N/A')
        name = p['name']
        pos = p['position']
        role = p['contract_rule']['role']
        height = p['height']
        
        # 取得屬性
        stats = p.get('raw_stats', {})
        if not stats:
             attrs = p.get('attributes', {})
             if 'trainable' in attrs:
                 stats = {**attrs.get('untrainable', {}), **attrs.get('trainable', {})}
             else:
                 stats = attrs
        
        total = sum(stats.values())
        
        # 列印基本資料
        print(f"[{grade:<3}] {name:<20} {pos:<4} {role:<10} {height:<4} {total:<5}")
        
        # 列印詳細屬性 (排序後，每行 5 個)
        items = list(stats.items())
        items.sort(key=lambda x: x[0]) # 依字母排序方便查找
        
        chunk_size = 5
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i+chunk_size]
            # 格式化屬性字串: key: value
            line_str = " | ".join([f"{k}: {v:>2}" for k, v in chunk])
            print(f"      {line_str}")
        print("-" * 100)
    print("\n")

def print_box_score(team_name, players):
    """列印美化的 Box Score 表格 (繁體中文版)"""
    print(f" >> {team_name} 數據統計")
    print_separator()
    # 表頭
    # 姓名 | 位置 | 角色 | 時間 | 得分 | 籃板 | 助攻 | 抄截 | 火鍋 | 失誤 | 投籃 | 三分 | 罰球
    header = f"{'姓名':<20} {'位置':<4} {'角色':<9} {'時間':<6} {'得分':>3} {'籃板':>3} {'助攻':>3} {'抄截':>3} {'火鍋':>3} {'失誤':>3} {'投籃':>6} {'三分':>6} {'罰球':>6}"
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
    # 總計行
    fg_tot = f"{total_stats['fgm']}/{total_stats['fga']}"
    tp_tot = f"{total_stats['3pm']}/{total_stats['3pa']}"
    ft_tot = f"{total_stats['ftm']}/{total_stats['fta']}"
    
    total_row = (
        f"{'全隊總計':<20} {'':<4} {'':<9} {'240:00':<6} "
        f"{total_stats['pts']:>3} {total_stats['reb']:>3} {total_stats['ast']:>3} "
        f"{total_stats['stl']:>3} {total_stats['blk']:>3} {total_stats['tov']:>3} "
        f"{fg_tot:>6} {tp_tot:>6} {ft_tot:>6}"
    )
    print(total_row)
    print_separator('=')
    print("")

# =============================================================================
# 主模擬流程 (Main Simulation Flow)
# =============================================================================

def main():
    # 0. 啟動 Flask App Context (確保 DB 連線可用)
    if app_instance:
        ctx = app_instance.app_context()
        ctx.push()
        print("[系統] Flask App Context 已啟動，資料庫連線中。")
    
    # 1. 載入設定檔
    print("[系統] 正在載入遊戲設定檔 (Game Config)...")
    config = GameConfigLoader.get()
    
    if not config:
        print("[錯誤] 設定檔載入失敗。請檢查 config/game_config.yaml 或 .env 檔案。")
        return

    # 2. 使用 TeamCreator 建立球隊
    print("[系統] 正在呼叫 TeamCreator 生成球隊陣容 (讀取資料庫姓名庫)...")
    
    try:
        # 生成主隊 Payload
        home_roster_payload = TeamCreator.create_valid_roster()
        home_name = "臺北國王 (主)"
        
        # 生成客隊 Payload
        away_roster_payload = TeamCreator.create_valid_roster()
        away_name = "高雄鋼鐵人 (客)"
        
    except Exception as e:
        print(f"[錯誤] 球隊生成失敗: {e}")
        import traceback
        traceback.print_exc()
        return

    # === [NEW] 列印詳細陣容資訊 (中文) ===
    print_team_details(home_name, home_roster_payload)
    print_team_details(away_name, away_roster_payload)
    # ========================================

    # 3. 轉換為引擎結構 (Engine Structures)
    print("[系統] 初始化比賽引擎資料結構...")
    
    # 建立 EngineTeam 的輔助函式
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

    # 4. 初始化比賽引擎
    print("[系統] 啟動 Match Engine v1.8 (Phase 2)...")
    engine = MatchEngine(home_team, away_team, config)

    # 5. 執行模擬
    print(f"[比賽] 開始模擬: {home_name} vs {away_name}")
    start_time = time.time()
    
    result = engine.simulate()
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"[比賽] 模擬完成，耗時 {duration:.4f} 秒。")
    print("")

    # 6. 顯示結果
    
    # --- 比分板 ---
    print_header("ASBL 比賽結果")
    
    ot_text = f" (OT{result.total_quarters - 4})" if result.is_ot else ""
    
    print(f"\n   {home_name:<30}  {result.home_score:>3}")
    print(f"   {away_name:<30}  {result.away_score:>3}")
    print(f"\n   比賽長度: {result.total_quarters} 節{ot_text}")
    print(f"   比賽節奏: {result.pace:.1f} (回合/48分鐘)")
    print("")
    
    # --- 快攻數據 ---
    print(f"   [快攻數據] 主隊: {result.home_fb_made}/{result.home_fb_attempt} | 客隊: {result.away_fb_made}/{result.away_fb_attempt}")
    print("")

    # --- 數據統計 (Box Scores) ---
    print_box_score(home_name, home_team.roster)
    print_box_score(away_name, away_team.roster)

    # --- 文字轉播 (最後 10 筆) ---
    print_header("比賽紀錄 (最後 10 筆)")
    if result.pbp_log:
        for log in result.pbp_log[-10:]:
            # 這裡的 log 內容通常由引擎內部生成，若引擎內部是英文，這裡仍會顯示英文
            # 若需全中文化，引擎內部的字串生成也需調整，目前僅調整外層顯示
            print(f"   {log}")
    else:
        print("   (無紀錄產生)")
    print_separator('=')

if __name__ == "__main__":
    try:
        from scripts.terminal import clear_terminal
        clear_terminal()
    except ImportError:
        pass
    except Exception:
        pass
    main()