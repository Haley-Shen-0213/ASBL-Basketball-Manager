# tests/match_bigdata_test/run_core_bigdata_test.py
# -*- coding: utf-8 -*-
"""
ASBL Core Bigdata Test Runner (Forensic Version v2.5)

[更新重點]
1. 啟用 faulthandler：捕捉 C-level Segfault/Crash。
2. Flush 隔離機制：存檔失敗僅丟棄該 Batch，不中斷主迴圈。
3. 捕捉 BaseException：防止 SystemExit 等底層例外逃脫。
4. 詳細錯誤日誌：確保所有 Warning 都有完整 Traceback。
"""

from __future__ import annotations

import os
import sys
import traceback
import faulthandler # [New] 啟用底層錯誤捕捉

# 啟用 Fault Handler，若發生 Segfault 會將 Traceback 印到 stderr
faulthandler.enable()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import argparse
import datetime as _dt
import gc
import time
import subprocess
from itertools import combinations
from typing import Any, Dict, List

import pandas as pd
import psutil
import yaml
from tqdm import tqdm

# 引用既有引擎程式碼
from app.services.match_engine.core import MatchEngine
from app.services.match_engine.structures import EngineTeam, EnginePlayer
from app.services.match_engine.utils.rng import rng


DEFAULT_PARQUET = "tests/match_bigdata_test/team/team_players.parquet"
DEFAULT_OUTPUT_ROOT = "tests/match_bigdata_test/output"
MAX_RETRIES_PER_GAME = 100


def now_id() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def make_snapshot(output_dir: str) -> str:
    snapshot_dir = os.path.join(output_dir, "snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)

    tool_path = os.path.join(PROJECT_ROOT, "tools", "code_merger.py")
    if os.path.exists(tool_path):
        try:
            subprocess.run([sys.executable, tool_path], cwd=PROJECT_ROOT, check=True)
            ctx_src = os.path.join(PROJECT_ROOT, "project_context.txt")
            if os.path.exists(ctx_src):
                with open(ctx_src, "rb") as rf, open(os.path.join(snapshot_dir, "project_context.txt"), "wb") as wf:
                    wf.write(rf.read())
        except Exception as e:
            print(f"[Warning] Snapshot creation failed: {e}")

    cfg_src = os.path.join(PROJECT_ROOT, "config", "game_config.yaml")
    if os.path.exists(cfg_src):
        with open(cfg_src, "rb") as rf, open(os.path.join(snapshot_dir, "game_config.yaml"), "wb") as wf:
            wf.write(rf.read())

    return snapshot_dir


def load_config() -> Dict[str, Any]:
    cfg_path = os.path.join(PROJECT_ROOT, "config", "game_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


STAT_20 = [
    "ath_stamina", "ath_strength", "ath_speed", "ath_jump",
    "shot_touch", "shot_release", "talent_offiq", "talent_defiq", "talent_health", "talent_luck",
    "shot_accuracy", "shot_range", "def_rebound", "def_boxout", "def_contest", "def_disrupt",
    "off_move", "off_dribble", "off_pass", "off_handle",
]


def build_engine_player(row: Dict[str, Any]) -> EnginePlayer:
    attr_sum = int(sum(int(row.get(k, 0) or 0) for k in STAT_20))
    return EnginePlayer(
        id=str(row["player_id"]),
        name=str(row["name"]),
        position=str(row["position"]),
        role=str(row.get("role", row.get("contract_role", "Bench"))),
        grade=str(row.get("grade", "G")),
        height=float(row.get("height", 195)),
        age=int(row.get("age", 25)), # <--- 讀取 age

        ath_stamina=float(row.get("ath_stamina", 0)),
        ath_strength=float(row.get("ath_strength", 0)),
        ath_speed=float(row.get("ath_speed", 0)),
        ath_jump=float(row.get("ath_jump", 0)),
        talent_health=float(row.get("talent_health", 0)),
        shot_touch=float(row.get("shot_touch", 0)),
        shot_release=float(row.get("shot_release", 0)),
        talent_offiq=float(row.get("talent_offiq", 0)),
        talent_defiq=float(row.get("talent_defiq", 0)),
        talent_luck=float(row.get("talent_luck", 0)),

        shot_accuracy=float(row.get("shot_accuracy", 0)),
        shot_range=float(row.get("shot_range", 0)),
        def_rebound=float(row.get("def_rebound", 0)),
        def_boxout=float(row.get("def_boxout", 0)),
        def_contest=float(row.get("def_contest", 0)),
        def_disrupt=float(row.get("def_disrupt", 0)),
        off_move=float(row.get("off_move", 0)),
        off_dribble=float(row.get("off_dribble", 0)),
        off_pass=float(row.get("off_pass", 0)),
        off_handle=float(row.get("off_handle", 0)),

        attr_sum=attr_sum,
    )


def load_teams(parquet_rel: str) -> Dict[str, EngineTeam]:
    df = pd.read_parquet(os.path.join(PROJECT_ROOT, parquet_rel))
    if "team_id" not in df.columns:
        raise ValueError("team_players.parquet 缺少 team_id")

    teams: Dict[str, EngineTeam] = {}
    for tid, g in df.groupby("team_id"):
        roster = [build_engine_player(rec) for rec in g.to_dict(orient="records")]
        teams[str(tid)] = EngineTeam(id=str(tid), name=str(tid), roster=roster)

    if len(teams) != 4:
        raise ValueError(f"預期 4 隊，實際 {len(teams)}：{list(teams.keys())}")

    for tid, t in teams.items():
        if len(t.roster) != 15:
            raise ValueError(f"{tid} roster 不是 15 人：{len(t.roster)}")

    return teams


def clone_team(src: EngineTeam) -> EngineTeam:
    roster = []
    for p in src.roster:
        row = {
            "player_id": p.id,
            "name": p.name,
            "position": p.position,
            "role": p.role,
            "grade": p.grade,
            "height": p.height,
        }
        for k in STAT_20:
            row[k] = getattr(p, k)
        roster.append(build_engine_player(row))
    return EngineTeam(id=src.id, name=src.name, roster=roster)


def write_parquet(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)


def concat_parquets(files: List[str], out_path: str):
    if not files:
        raise ValueError(f"沒有檔案可合併：{out_path}")
    
    dfs = []
    desc = f"Merging {os.path.basename(out_path)}"
    for fp in tqdm(files, desc=desc, leave=False, unit="file"):
        dfs.append(pd.read_parquet(fp))
    
    pd.concat(dfs, ignore_index=True).to_parquet(out_path, index=False)


def extract_box_rows(game_id: str, team: EngineTeam, opp_id: str) -> List[Dict[str, Any]]:
    rows = []
    for p in team.roster:
        rows.append({
            "game_id": game_id,
            "team_id": team.id,
            "opponent_team_id": opp_id,
            "player_id": p.id,
            "name": p.name,
            "grade": p.grade,
            "role": p.role,
            "position": p.position,
            "height": float(p.height),
            "attr_sum": int(p.attr_sum),

            "stat_pts": int(p.stat_pts),
            "stat_reb": int(p.stat_reb),
            "stat_ast": int(p.stat_ast),
            "stat_stl": int(p.stat_stl),
            "stat_blk": int(p.stat_blk),
            "stat_tov": int(p.stat_tov),
            "fouls": int(p.fouls),
            "stat_plus_minus": int(p.stat_plus_minus),

            "stat_fgm": int(p.stat_fgm),
            "stat_fga": int(p.stat_fga),
            "stat_3pm": int(p.stat_3pm),
            "stat_3pa": int(p.stat_3pa),
            "stat_ftm": int(p.stat_ftm),
            "stat_fta": int(p.stat_fta),

            "stat_orb": int(p.stat_orb),
            "stat_drb": int(p.stat_drb),

            "seconds_played": float(p.seconds_played),
            "current_stamina": float(p.current_stamina),
            "is_fouled_out": bool(p.is_fouled_out),

            "stat_fb_made": int(p.stat_fb_made),
            "stat_fb_attempt": int(p.stat_fb_attempt),
        })
    return rows


def extract_possession_rows(game_id: str, team: EngineTeam, opp_id: str) -> List[Dict[str, Any]]:
    rows = []
    for i, sec in enumerate(team.stat_possession_history):
        rows.append({
            "game_id": game_id,
            "team_id": team.id,
            "opponent_team_id": opp_id,
            "possession_index": int(i),
            "seconds": float(sec),
        })
    return rows


def calc_orating(points: int, poss: int) -> float:
    return (points / poss * 100.0) if poss > 0 else 0.0


def _team_strength(team: EngineTeam) -> int:
    return int(sum(int(p.attr_sum) for p in team.roster))


def _fmt_pct(x: float) -> str:
    return f"{x*100:.2f}%"

def _roster_stats_table(team: EngineTeam, box_df: pd.DataFrame) -> str:
    team_box = box_df[box_df['team_id'] == team.id]
    stats_agg = team_box.groupby('player_id').agg(
        G=('game_id', 'count'),
        PTS=('stat_pts', 'mean'),
        REB=('stat_reb', 'mean'),
        AST=('stat_ast', 'mean'),
        STL=('stat_stl', 'mean'),
        BLK=('stat_blk', 'mean'),
        TOV=('stat_tov', 'mean'),
        PF=('fouls', 'mean'),
        PM=('stat_plus_minus', 'mean'),
        FGM=('stat_fgm', 'mean'),
        FGA=('stat_fga', 'mean'),
        M3PM=('stat_3pm', 'mean'),
        M3PA=('stat_3pa', 'mean'),
        FTM=('stat_ftm', 'mean'),
        FTA=('stat_fta', 'mean'),
        ORB=('stat_orb', 'mean'),
        DRB=('stat_drb', 'mean'),
        FB_M=('stat_fb_made', 'mean'),
        FB_A=('stat_fb_attempt', 'mean'),
        REM_ST=('current_stamina', 'mean'),
        SEC=('seconds_played', 'mean')
    ).reset_index()

    stats_map = stats_agg.set_index('player_id').to_dict('index')

    header = (
        "| 名稱 | 位置 | 等級 | 時間 | 得分 | 籃板 | 助攻 | 抄截 | 阻攻 | 失誤 | 犯規 | +/- | "
        "FG | 3PT | FT | OR/DR | 快攻(M/A) | 體力 | "
        "體能 | 力量 | 速度 | 彈跳 | 健康 | 手感 | 出手 | 攻智 | 守智 | 運氣 | "
        "投籃 | 射程 | 傳球 | 運球 | 控球 | 跑位 | 籃板 | 卡位 | 干擾 | 抄截 |\n"
    )
    sep = "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    
    lines = [header, sep]
    
    for p in team.roster:
        s = stats_map.get(p.id, {})
        mpg = s.get('SEC', 0) / 60.0
        
        fg_str = f"{s.get('FGM',0):.1f}/{s.get('FGA',0):.1f}"
        tp_str = f"{s.get('M3PM',0):.1f}/{s.get('M3PA',0):.1f}"
        ft_str = f"{s.get('FTM',0):.1f}/{s.get('FTA',0):.1f}"
        reb_split = f"{s.get('ORB',0):.1f}/{s.get('DRB',0):.1f}"
        fb_str = f"{s.get('FB_M',0):.1f}/{s.get('FB_A',0):.1f}"
        
        line = (
            f"| {p.name} | {p.position} | {p.grade} | {mpg:.1f} | "
            f"**{s.get('PTS',0):.1f}** | {s.get('REB',0):.1f} | {s.get('AST',0):.1f} | {s.get('STL',0):.1f} | "
            f"{s.get('BLK',0):.1f} | {s.get('TOV',0):.1f} | {s.get('PF',0):.1f} | {s.get('PM',0):+.1f} | "
            f"{fg_str} | {tp_str} | {ft_str} | {reb_split} | {fb_str} | {s.get('REM_ST',0):.1f} | "
            f"{int(p.ath_stamina)} | {int(p.ath_strength)} | {int(p.ath_speed)} | {int(p.ath_jump)} | {int(p.talent_health)} | "
            f"{int(p.shot_touch)} | {int(p.shot_release)} | {int(p.talent_offiq)} | {int(p.talent_defiq)} | {int(p.talent_luck)} | "
            f"{int(p.shot_accuracy)} | {int(p.shot_range)} | {int(p.off_pass)} | {int(p.off_dribble)} | {int(p.off_handle)} | {int(p.off_move)} | "
            f"{int(p.def_rebound)} | {int(p.def_boxout)} | {int(p.def_contest)} | {int(p.def_disrupt)} |\n"
        )
        lines.append(line)
        
    return "".join(lines)

def _slice_bin(sec: float) -> int:
    if sec >= 24.0:
        return 23
    if sec < 0:
        return 0
    return int(sec)

def build_report(
    report_path: str,
    run_id: str,
    config: Dict[str, Any],
    teams_src: Dict[str, EngineTeam],
    matches_df: pd.DataFrame,
    team_df: pd.DataFrame,
    box_df: pd.DataFrame,
    poss_df: pd.DataFrame,
):
    now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pbar = tqdm(total=13, desc="Analyzing & Reporting", unit="step")

    # 1) 概況
    total_games = int(matches_df.shape[0])
    ot_games = int(matches_df["is_ot"].sum())
    q_dist = matches_df["total_quarters"].value_counts().sort_index().to_dict()
    pbar.update(1)

    # 1.2) Config Snapshot
    me = config.get("match_engine", {})
    gen = me.get("general", {})
    sub = gen.get("substitution", {})
    shoot = me.get("shooting", {}).get("params", {})
    match_engine_yaml = yaml.safe_dump(me, allow_unicode=True, sort_keys=False)
    pbar.update(1)

    # 2) Roster Stats Preparation
    team_ids = sorted(list(teams_src.keys()))
    strengths = {tid: _team_strength(teams_src[tid]) for tid in team_ids}
    pbar.update(1)

    # 3) Win Rate & Diff
    h2h_stats = {} 
    matches_df['diff_abs'] = (matches_df['team_a_score'] - matches_df['team_b_score']).abs()
    
    win_counts = {tid: 0 for tid in team_ids}
    game_counts = {tid: 0 for tid in team_ids}
    
    for _, r in matches_df.iterrows():
        a, b = r['team_a_id'], r['team_b_id']
        sa, sb = r['team_a_score'], r['team_b_score']
        
        game_counts[a] += 1
        game_counts[b] += 1
        
        key_a = (a, b)
        key_b = (b, a)
        if key_a not in h2h_stats: h2h_stats[key_a] = [0, 0]
        if key_b not in h2h_stats: h2h_stats[key_b] = [0, 0]
        
        h2h_stats[key_a][1] += 1
        h2h_stats[key_b][1] += 1
        
        if sa > sb:
            win_counts[a] += 1
            h2h_stats[key_a][0] += 1
        elif sb > sa:
            win_counts[b] += 1
            h2h_stats[key_b][0] += 1
            
    bins = [0, 5, 10, 15, 20, 30, 40, 50, 999]
    labels = ["1-5", "6-10", "11-15", "16-20", "21-30", "31-40", "41-50", ">50"]
    diff_cats = pd.cut(matches_df['diff_abs'], bins=bins, labels=labels, right=False)
    diff_dist = diff_cats.value_counts().sort_index()
    
    diff_mean = matches_df['diff_abs'].mean()
    diff_std = matches_df['diff_abs'].std()
    pbar.update(1)

    # 4) Team Stats Aggregation
    t_agg = team_df.groupby("team_id").agg(
        G=("game_id", "count"),
        PTS=("points", "mean"),
        Opp_PTS=("opp_points", "mean"),
        Pace=("pace", "mean"),
        Poss=("possessions", "mean"),
        SecPerPoss=("sec_per_poss", "mean"),
        ORtg=("ortg", "mean"),
        DRtg=("drtg", "mean"),
        Net=("net", "mean"),
        FB_Att=("fb_attempt", "mean"),
        FB_Made=("fb_made", "mean"),
        Vio8=("violation_8s", "mean"),
        Vio24=("violation_24s", "mean"),
    ).reset_index()
    t_agg["FB%"] = t_agg.apply(lambda r: (r["FB_Made"] / r["FB_Att"]) if r["FB_Att"] > 0 else 0.0, axis=1)
    t_agg["FB_Freq"] = t_agg.apply(lambda r: (r["FB_Att"] / r["Poss"] * 100.0) if r["Poss"] > 0 else 0.0, axis=1)
    pbar.update(1)

    # 5) Player Correlation
    box_play = box_df.copy()
    box_play["mp"] = box_play["seconds_played"].astype(float) / 60.0
    box_play = box_play[box_play["mp"] > 5.0].copy()

    def summarize_skill(df: pd.DataFrame) -> pd.DataFrame:
        out = df.groupby("grade").agg(
            attr_sum=("attr_sum", "mean"),
            MPG=("mp", "mean"),
            PPG=("stat_pts", "mean"),
            RPG=("stat_reb", "mean"),
            APG=("stat_ast", "mean"),
            SPG=("stat_stl", "mean"),
            BPG=("stat_blk", "mean"),
            TO=("stat_tov", "mean"),
            PM=("stat_plus_minus", "mean"),
            FGM=("stat_fgm", "sum"),
            FGA=("stat_fga", "sum"),
            N=("player_id", "count"),
        ).reset_index()
        out["FG%"] = out.apply(lambda r: (r["FGM"] / r["FGA"]) if r["FGA"] > 0 else 0.0, axis=1)
        out["Pts/36"] = out.apply(lambda r: (r["PPG"] / r["MPG"] * 36.0) if r["MPG"] > 0 else 0.0, axis=1)
        out["Eff/36"] = out.apply(
            lambda r: ((r["PPG"] + r["RPG"] + r["APG"] + r["SPG"] + r["BPG"] - r["TO"]) / r["MPG"] * 36.0) if r["MPG"] > 0 else 0.0,
            axis=1
        )
        return out
    pbar.update(1)

    # 6) Stamina
    def stamina_bucket(s: float) -> str:
        if s >= 80: return "正常 (80-100)"
        if s >= 60: return "稍微疲累 (60-79)"
        if s >= 40: return "有點疲累 (40-59)"
        if s >= 20: return "疲累 (20-39)"
        return "非常疲累 (1-19)"

    box_df["st_bucket"] = box_df["current_stamina"].astype(float).apply(stamina_bucket)
    pbar.update(1)

    # 7) Fouls
    avg_pf = float(box_df["fouls"].mean())
    max_pf = int(box_df["fouls"].max())
    fouled_out_cnt = int(box_df["is_fouled_out"].sum())
    pf_team_game = box_df.groupby(["game_id", "team_id"])["fouls"].sum().reset_index()
    pf_team_avg = pf_team_game.groupby("team_id")["fouls"].mean().to_dict()
    pf_dist = {}
    for tid in team_ids:
        subdf = box_df[box_df["team_id"] == tid]
        pf_dist[tid] = subdf["fouls"].value_counts().sort_index().to_dict()
    pbar.update(1)

    # 8) Possession Time & Violations
    slice_counts = {tid: [0] * 24 for tid in team_ids}
    poss_stats = {} 
    
    for tid in team_ids:
        t_poss = poss_df[poss_df['team_id'] == tid]['seconds']
        poss_stats[tid] = {
            'mean': t_poss.mean(),
            'std': t_poss.std(),
            'count': t_poss.count()
        }
        
    for _, r in poss_df.iterrows():
        tid = r["team_id"]
        sec = float(r["seconds"])
        slice_counts[tid][_slice_bin(sec)] += 1

    v8 = team_df.groupby("team_id")["violation_8s"].sum().to_dict()
    v24 = team_df.groupby("team_id")["violation_24s"].sum().to_dict()
    pbar.update(1)

    # 10) Speed vs Pace Correlation (Weighted by Minutes)
    team_speed_data = []
    for tid in team_ids:
        # Get static speed from roster
        t_roster = teams_src[tid].roster
        spd_map = {p.id: p.ath_speed for p in t_roster}
        
        # Get minutes played for this team
        t_box = box_df[box_df['team_id'] == tid]
        p_minutes = t_box.groupby('player_id')['seconds_played'].sum()
        
        total_sec = 0
        weighted_sum = 0
        for pid, sec in p_minutes.items():
            s = spd_map.get(pid, 0)
            weighted_sum += s * sec
            total_sec += sec
            
        avg_w_speed = weighted_sum / total_sec if total_sec > 0 else 0
        
        team_row = t_agg[t_agg['team_id'] == tid].iloc[0]
        team_speed_data.append({
            'team_id': tid,
            'w_speed': avg_w_speed,
            'pace': team_row['Pace'],
            'poss': team_row['Poss']
        })
    speed_df = pd.DataFrame(team_speed_data)
    pbar.update(1)

    # 11) High Grade Player Ranking (SSR/SS/S)
    high_grade_box = box_df[box_df['grade'].isin(['SSR', 'SS', 'S'])].copy()
    high_grade_box["mp"] = high_grade_box["seconds_played"].astype(float) / 60.0
    
    hg_stats = high_grade_box.groupby(['player_id', 'name', 'team_id', 'position', 'grade']).agg(
        MPG=('mp', 'mean'),
        PPG=('stat_pts', 'mean'),
        RPG=('stat_reb', 'mean'),
        APG=('stat_ast', 'mean'),
        SPG=('stat_stl', 'mean'),
        BPG=('stat_blk', 'mean'),
        TO=('stat_tov', 'mean'),
        FGM=('stat_fgm', 'sum'),
        FGA=('stat_fga', 'sum'),
    ).reset_index()
    
    hg_stats["FG%"] = hg_stats.apply(lambda r: (r["FGM"] / r["FGA"]) if r["FGA"] > 0 else 0.0, axis=1)
    # Sort by PPG descending
    hg_stats = hg_stats.sort_values('PPG', ascending=False).head(20)
    pbar.update(1)

    # 12) Violation Distribution
    vio_dist_data = {}
    for tid in team_ids:
        tdf = team_df[team_df['team_id'] == tid]
        v8_counts = tdf['violation_8s'].value_counts().sort_index().to_dict()
        v24_counts = tdf['violation_24s'].value_counts().sort_index().to_dict()
        vio_dist_data[tid] = {'v8': v8_counts, 'v24': v24_counts}
    pbar.update(1)

    # ---- WRITE REPORT ----
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ASBL 模擬平衡性分析報告 (v2.4)\n")
        f.write(f"**分析時間:** {now_str}\n")
        f.write(f"**資料來源:** `{run_id}`\n\n")

        f.write("## 1. 模擬概況\n")
        f.write(f"- **實際分析場數:** {total_games}\n")
        f.write(f"- **總球員人次 (boxscores rows):** {int(box_df.shape[0])}\n")
        f.write(f"- **OT 場數:** {ot_games} ({_fmt_pct(ot_games / max(1, total_games))})\n")
        dist_str = ", ".join([f"{k}節={v}" for k, v in q_dist.items()])
        f.write(f"- **節數分佈:** {dist_str}\n\n")

        f.write("### 1.2 參數設定 (Config Snapshot)\n")
        f.write("| 參數類別 | 參數名稱 | 設定值 |\n|---|---|---|\n")
        f.write(f"| **全域設定** | 每節長度 | `{gen.get('quarter_length')}` |\n")
        f.write(f"| | 犯滿次數 | `{sub.get('foul_limit')}` |\n")
        f.write(f"| **體力系統** | 消耗係數 | `{gen.get('stamina_drain_coeff')}` |\n")
        f.write(f"| | 衰退閾值 | `{gen.get('stamina_nerf_threshold')}` |\n")
        f.write(f"| **投籃設定** | 兩分基數 | `{shoot.get('base_rate_2pt')}` |\n")
        f.write(f"| | 三分基數 | `{shoot.get('base_rate_3pt')}` |\n\n")

        f.write("#### match_engine 全設定 (YAML)\n")
        f.write("```yaml\n")
        f.write(match_engine_yaml)
        f.write("```\n\n")

        f.write("## 2. 測試球隊陣容 (含場均數據)\n")
        f.write("> 註：數據為本批次模擬之平均值\n")
        for tid in team_ids:
            t = teams_src[tid]
            f.write(f"### 球隊代碼: `{tid}` (戰力總和: {strengths[tid]:,})\n")
            f.write(_roster_stats_table(t, box_df))
            f.write("\n")

        f.write("## 3. 球隊勝率與分差分佈\n")
        f.write("### 3.1 總勝率\n")
        f.write("| 球隊代碼 | 勝場 | 總場數 | 勝率 |\n|---|---:|---:|---:|\n")
        for tid in team_ids:
            g = int(game_counts[tid])
            w = int(win_counts[tid])
            wr = (w / g) if g > 0 else 0.0
            f.write(f"| `{tid}` | {w} | {g} | **{_fmt_pct(wr)}** |\n")
        f.write("\n")

        f.write("### 3.2 對戰組合勝率\n")
        f.write("| 對戰組合 (A vs B) | A 勝場 | B 勝場 | 總場數 | A 勝率 |\n|---|---:|---:|---:|---:|\n")
        for (a, b), stats in sorted(h2h_stats.items()):
            if a < b: # 只顯示單向組合避免重複
                w_a = stats[0]
                total = stats[1]
                w_b = total - w_a
                wr_a = w_a / total if total > 0 else 0
                f.write(f"| {a} vs {b} | {w_a} | {w_b} | {total} | **{_fmt_pct(wr_a)}** |\n")
        f.write("\n")

        f.write("### 3.3 分差分佈 (勝分差絕對值)\n")
        f.write("| 分差區間 | 場數 | 比例 |\n|---|---:|---:|\n")
        for lab, cnt in diff_dist.items():
            f.write(f"| {lab} | {int(cnt)} | {_fmt_pct(int(cnt)/max(1,total_games))} |\n")
        f.write("\n")

        f.write("### 3.4 勝分差常態分佈分析\n")
        f.write(f"- **平均分差 (Mean):** {diff_mean:.2f} 分\n")
        f.write(f"- **標準差 (Std Dev):** {diff_std:.2f}\n")
        f.write(f"- **68% 區間 (Mean ± 1σ):** {max(0, diff_mean-diff_std):.1f} ~ {diff_mean+diff_std:.1f} 分\n\n")

        f.write("## 4. 節奏、回合數、快攻與效率 (團隊場均)\n")
        f.write("### 4.1 綜合數據表\n")
        f.write("| 球隊 | 場數 | 得分 | 失分 | 節奏(Pace) | 回合數 | 每回合秒數 | 進攻效率(ORtg) | 防守效率(DRtg) | 淨效率(Net) | 快攻出手 | 快攻命中率 | 快攻頻率(%) | 8秒違例 | 24秒違例 |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for _, r in t_agg.sort_values("team_id").iterrows():
            f.write(
                f"| `{r['team_id']}` | {int(r['G'])} | {r['PTS']:.1f} | {r['Opp_PTS']:.1f} | {r['Pace']:.2f} | {r['Poss']:.2f} | "
                f"{r['SecPerPoss']:.2f} | {r['ORtg']:.1f} | {r['DRtg']:.1f} | {r['Net']:+.1f} | {r['FB_Att']:.2f} | "
                f"{_fmt_pct(float(r['FB%']))} | {r['FB_Freq']:.2f}% | {r['Vio8']:.2f} | {r['Vio24']:.2f} |\n"
            )
        f.write("\n")

        f.write("## 5. 能力與表現相關性 (分級分析)\n")
        f.write("> 排序：SSR -> G\n")
        grade_order = {"SSR": 0, "SS": 1, "S": 2, "A": 3, "B": 4, "C": 5, "G": 6}
        
        for tid in team_ids:
            f.write(f"### 球隊: `{tid}`\n")
            subdf = box_play[box_play["team_id"] == tid]
            if subdf.empty:
                f.write("> 無符合篩選條件的樣本\n\n")
                continue
            summ = summarize_skill(subdf)
            # Sort
            summ['sort_key'] = summ['grade'].map(lambda x: grade_order.get(x, 99))
            summ = summ.sort_values('sort_key')
            
            f.write("| 等級 | 平均屬性 | 上場(分) | 得分 | 籃板 | 助攻 | 抄截 | 阻攻 | 失誤 | +/- | 命中率 | Pts/36 | 效率/36 | 樣本數 |\n")
            f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
            for _, r in summ.iterrows():
                f.write(
                    f"| **{r['grade']}** | {float(r['attr_sum']):.1f} | {float(r['MPG']):.1f} | {float(r['PPG']):.1f} | "
                    f"{float(r['RPG']):.1f} | {float(r['APG']):.1f} | {float(r['SPG']):.1f} | {float(r['BPG']):.1f} | "
                    f"{float(r['TO']):.1f} | {float(r['PM']):+.1f} | {_fmt_pct(float(r['FG%']))} | {float(r['Pts/36']):.1f} | "
                    f"{float(r['Eff/36']):.1f} | {int(r['N'])} |\n"
                )
            f.write("\n")

        f.write("## 6. 體力系統分析\n")
        f.write("### 6.1 賽後體力分佈 (命中率影響)\n")
        f.write("| 體力狀態 | 命中率 (FG%) | 出手樣本數 (FGA) |\n|---|---:|---:|\n")
        
        g_stam = box_df.groupby("st_bucket").agg(
            FGM=("stat_fgm", "sum"),
            FGA=("stat_fga", "sum"),
        ).reset_index()
        g_stam["FG%"] = g_stam.apply(lambda r: (r["FGM"] / r["FGA"]) if r["FGA"] > 0 else 0.0, axis=1)
        
        order = ["正常 (80-100)", "稍微疲累 (60-79)", "有點疲累 (40-59)", "疲累 (20-39)", "非常疲累 (1-19)"]
        # Ensure ordering
        g_stam["st_bucket"] = pd.Categorical(g_stam["st_bucket"], categories=order, ordered=True)
        g_stam = g_stam.sort_values("st_bucket")
        
        for _, r in g_stam.iterrows():
            f.write(f"| {r['st_bucket']} | **{_fmt_pct(float(r['FG%']))}** | {int(r['FGA'])} |\n")
        f.write("\n")

        f.write("## 7. 犯規系統\n")
        f.write(f"- **平均單場個人犯規:** {avg_pf:.2f}\n")
        f.write(f"- **單人單場最大犯規:** {max_pf}\n")
        f.write(f"- **犯滿離場人次:** {fouled_out_cnt}\n\n")

        f.write("### 7.1 各隊平均每場犯規次數\n")
        for tid in team_ids:
            f.write(f"- **{tid}:** {float(pf_team_avg.get(tid, 0.0)):.2f} 次/場\n")
        f.write("\n")

        f.write("### 7.2 犯規次數分佈 (Debug)\n")
        for tid in team_ids:
            f.write(f"#### 球隊: `{tid}`\n")
            f.write("| 犯規次數 | 人次 | 異常標記 |\n|---:|---:|---|\n")
            dist = pf_dist.get(tid, {})
            for k in sorted(dist.keys()):
                f.write(f"| {int(k)} | {int(dist[k])} |  |\n")
            f.write("\n")

        f.write("## 8. 每隊每回合花費時間切片分布與違例\n")
        for tid in team_ids:
            stats = poss_stats[tid]
            total_poss = stats['count']
            
            f.write(f"### 球隊: `{tid}`\n")
            f.write(f"- **8秒違例 (總計):** {int(v8.get(tid, 0))}\n")
            f.write(f"- **24秒違例 (總計):** {int(v24.get(tid, 0))}\n")
            f.write(f"- **平均時間:** {stats['mean']:.2f} 秒 (σ={stats['std']:.2f})\n\n")
            
            f.write("| 區間 | 次數 | 佔比 |\n|---|---:|---:|\n")
            for i in range(24):
                cnt = int(slice_counts[tid][i])
                pct = cnt / total_poss if total_poss > 0 else 0
                f.write(f"| {i}~{i+1} 秒 | {cnt} | {_fmt_pct(pct)} |\n")
            f.write("\n")

        f.write("## 9. 快攻數據詳情 (Team-Level)\n")
        f.write("| 球隊 | 場均快攻出手 | 場均快攻得分 | 快攻命中率 | 快攻得分佔比 |\n|---|---:|---:|---:|---:|\n")
        for _, r in t_agg.sort_values("team_id").iterrows():
            fb_pts = r['FB_Made'] * 2 # 假設快攻都是2分
            pts_pct = (fb_pts / r['PTS']) if r['PTS'] > 0 else 0
            f.write(
                f"| `{r['team_id']}` | {r['FB_Att']:.2f} | {fb_pts:.1f} | "
                f"{_fmt_pct(float(r['FB%']))} | {_fmt_pct(pts_pct)} |\n"
            )
        f.write("\n")

        f.write("## 10. 速度對球隊回合數 (Pace) 的影響\n")
        f.write("> 註：平均速度改採「上場時間加權 (Minutes Weighted)」，更能反映場上實際陣容速度。\n\n")
        f.write("| 球隊 | 加權平均速度 | 場均 Pace | 場均回合數 |\n|---|---:|---:|---:|\n")
        for _, r in speed_df.iterrows():
            f.write(f"| `{r['team_id']}` | {r['w_speed']:.1f} | {r['pace']:.2f} | {r['poss']:.2f} |\n")
        f.write("\n")
        
        if len(speed_df) > 1:
            corr = speed_df['w_speed'].corr(speed_df['pace'])
            f.write(f"\n**加權速度與 Pace 的相關係數 (Correlation):** {corr:.4f}\n")
            
        f.write("\n## 11. 高階球員表現排行 (SSR/SS/S)\n")
        f.write("> 依場均得分 (PPG) 排序，取前 20 名\n\n")
        f.write("| 排名 | 球員 | 隊伍 | 位置 | 等級 | PPG | RPG | APG | FG% | MPG |\n")
        f.write("|---:|---|---|---|---|---:|---:|---:|---:|---:|\n")
        
        rank = 1
        for _, r in hg_stats.iterrows():
            f.write(
                f"| {rank} | {r['name']} | {r['team_id']} | {r['position']} | {r['grade']} | "
                f"**{r['PPG']:.1f}** | {r['RPG']:.1f} | {r['APG']:.1f} | {_fmt_pct(r['FG%'])} | {r['MPG']:.1f} |\n"
            )
            rank += 1
        f.write("\n")
        
        f.write("## 12. 違例詳細分析 (Distribution)\n")
        for tid in team_ids:
            f.write(f"### 球隊: `{tid}`\n")
            d = vio_dist_data[tid]
            
            # 8s
            f.write("**8秒違例單場次數分佈:**\n")
            f.write("| 次數 | 場數 | 佔比 |\n|---:|---:|---:|\n")
            total_g = sum(d['v8'].values())
            for k, v in d['v8'].items():
                if v > 0:
                    f.write(f"| {k} 次 | {v} | {_fmt_pct(v/total_g)} |\n")
            
            # 24s
            f.write("\n**24秒違例單場次數分佈:**\n")
            f.write("| 次數 | 場數 | 佔比 |\n|---:|---:|---:|\n")
            total_g = sum(d['v24'].values())
            for k, v in d['v24'].items():
                if v > 0:
                    f.write(f"| {k} 次 | {v} | {_fmt_pct(v/total_g)} |\n")
            f.write("\n")
    
    pbar.update(1) # Step 13 Done
    pbar.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", type=str, default=DEFAULT_PARQUET)
    parser.add_argument("--cycles", type=int, default=500, help="每 cycle 6 場；總場數=cycles*6")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-root", type=str, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    if args.seed is not None:
        rng.seed(args.seed)

    run_id = now_id()
    output_dir = os.path.join(PROJECT_ROOT, args.output_root, run_id)
    os.makedirs(output_dir, exist_ok=True)
    
    error_log_path = os.path.join(output_dir, "error_log.txt")

    snapshot_dir = make_snapshot(output_dir)
    print(f"[Snapshot] {snapshot_dir}")

    config = load_config()
    teams_src = load_teams(args.parquet)
    team_ids = sorted(list(teams_src.keys()))
    pairs = list(combinations(team_ids, 2))  # 4隊=6場

    total_games = args.cycles * len(pairs)
    print(f"[Run] cycles={args.cycles}, total_games={total_games}, batch_size={args.batch_size}")

    proc = psutil.Process(os.getpid())
    t0 = time.time()

    # buffers
    matches_rows: List[Dict[str, Any]] = []
    team_game_rows: List[Dict[str, Any]] = []
    box_rows: List[Dict[str, Any]] = []
    poss_rows: List[Dict[str, Any]] = []

    # batch files
    mf, tf, bf, pf = [], [], [], []
    batch_idx = 0
    game_idx = 0

    def flush():
        nonlocal batch_idx, matches_rows, team_game_rows, box_rows, poss_rows
        if not matches_rows:
            return

        try:
            mdf = pd.DataFrame(matches_rows)
            tdf = pd.DataFrame(team_game_rows)
            bdf = pd.DataFrame(box_rows)
            pdf = pd.DataFrame(poss_rows)

            base = os.path.join(output_dir, "batches")
            os.makedirs(base, exist_ok=True)
            m_path = os.path.join(base, f"matches_{batch_idx:05d}.parquet")
            t_path = os.path.join(base, f"team_game_stats_{batch_idx:05d}.parquet")
            b_path = os.path.join(base, f"boxscores_{batch_idx:05d}.parquet")
            p_path = os.path.join(base, f"possession_times_{batch_idx:05d}.parquet")

            write_parquet(mdf, m_path)
            write_parquet(tdf, t_path)
            write_parquet(bdf, b_path)
            write_parquet(pdf, p_path)

            mf.append(m_path)
            tf.append(t_path)
            bf.append(b_path)
            pf.append(p_path)

            # Clear buffers
            matches_rows = []
            team_game_rows = []
            box_rows = []
            poss_rows = []

            batch_idx += 1
            
            # [Forensic] Aggressive GC to prevent OOM
            gc.collect()
            
        except Exception as e:
            # [Forensic] Flush Isolation - Log and discard batch, do NOT crash main loop
            err_msg = f"=== Flush Error at Batch {batch_idx} ===\n{traceback.format_exc()}\n"
            tqdm.write(f"[Critical] Flush failed: {e}")
            with open(error_log_path, "a", encoding="utf-8") as ef:
                ef.write(err_msg)
                ef.flush()
                os.fsync(ef.fileno())
            
            # Discard buffers to prevent memory leak
            matches_rows = []
            team_game_rows = []
            box_rows = []
            poss_rows = []

    pbar = tqdm(total=total_games, ncols=120)

    try:
        for _ in range(args.cycles):
            for a_id, b_id in pairs:
                game_idx += 1
                game_id = f"{run_id}_G{game_idx:06d}"
                
                retries = 0
                success = False
                
                while not success and retries < MAX_RETRIES_PER_GAME:
                    try:
                        team_a = clone_team(teams_src[a_id])
                        team_b = clone_team(teams_src[b_id])

                        engine = MatchEngine(team_a, team_b, config, game_id=game_id)
                        result = engine.simulate()
                        
                        success = True

                        a_8sec = int(result.home_violation_8s)
                        a_24sec = int(result.home_violation_24s)
                        b_8sec = int(result.away_violation_8s)
                        b_24sec = int(result.away_violation_24s)

                        matches_rows.append({
                            "game_id": game_id,
                            "team_a_id": team_a.id,
                            "team_b_id": team_b.id,
                            "team_a_score": int(result.home_score),
                            "team_b_score": int(result.away_score),
                            "is_ot": bool(result.is_ot),
                            "total_quarters": int(result.total_quarters),
                            "pace": float(result.pace),
                            "team_a_possessions": int(result.home_possessions),
                            "team_b_possessions": int(result.away_possessions),
                            "team_a_fb_made": int(result.home_fb_made),
                            "team_a_fb_attempt": int(result.home_fb_attempt),
                            "team_b_fb_made": int(result.away_fb_made),
                            "team_b_fb_attempt": int(result.away_fb_attempt),
                            "team_a_violation_8s": a_8sec,
                            "team_a_violation_24s": a_24sec,
                            "team_b_violation_8s": b_8sec,
                            "team_b_violation_24s": b_24sec,
                        })

                        a_poss = int(result.home_possessions)
                        b_poss = int(result.away_possessions)

                        a_pts = int(result.home_score)
                        b_pts = int(result.away_score)
                        
                        base_row = {
                            "game_id": game_id,
                            "pace": float(result.pace),
                            "is_ot": bool(result.is_ot),
                            "total_quarters": int(result.total_quarters),
                        }
                        
                        team_game_rows.append({
                            **base_row,
                            "team_id": team_a.id,
                            "opponent_team_id": team_b.id,
                            "points": a_pts,
                            "opp_points": b_pts,
                            "possessions": a_poss,
                            "sec_per_poss": float(team_a.stat_possession_seconds / a_poss) if a_poss > 0 else 0.0,
                            "ortg": calc_orating(a_pts, a_poss),
                            "drtg": calc_orating(b_pts, a_poss),
                            "net": calc_orating(a_pts, a_poss) - calc_orating(b_pts, a_poss),
                            "fb_made": int(result.home_fb_made),
                            "fb_attempt": int(result.home_fb_attempt),
                            "violation_8s": a_8sec,
                            "violation_24s": a_24sec,
                        })
                        
                        team_game_rows.append({
                            **base_row,
                            "team_id": team_b.id,
                            "opponent_team_id": team_a.id,
                            "points": b_pts,
                            "opp_points": a_pts,
                            "possessions": b_poss,
                            "sec_per_poss": float(team_b.stat_possession_seconds / b_poss) if b_poss > 0 else 0.0,
                            "ortg": calc_orating(b_pts, b_poss),
                            "drtg": calc_orating(a_pts, b_poss),
                            "net": calc_orating(b_pts, b_poss) - calc_orating(a_pts, b_poss),
                            "fb_made": int(result.away_fb_made),
                            "fb_attempt": int(result.away_fb_attempt),
                            "violation_8s": b_8sec,
                            "violation_24s": b_24sec,
                        })

                        box_rows.extend(extract_box_rows(game_id, team_a, team_b.id))
                        box_rows.extend(extract_box_rows(game_id, team_b, team_a.id))

                        poss_rows.extend(extract_possession_rows(game_id, team_a, team_b.id))
                        poss_rows.extend(extract_possession_rows(game_id, team_b, team_a.id))

                    except BaseException as e: # [Forensic] Catch everything including SystemExit/KeyboardInterrupt
                        retries += 1
                        error_msg = traceback.format_exc()
                        tqdm.write(f"[Warning] Game {game_id} failed (Retry {retries}/{MAX_RETRIES_PER_GAME})")
                        
                        with open(error_log_path, "a", encoding="utf-8") as ef:
                            ef.write(f"=== Error in {game_id} (Retry {retries}/{MAX_RETRIES_PER_GAME}) ===\n")
                            ef.write(f"Teams: {a_id} vs {b_id}\n")
                            ef.write(error_msg)
                            ef.write("\n" + "="*50 + "\n")
                            ef.flush()
                            os.fsync(ef.fileno())
                        
                        if isinstance(e, KeyboardInterrupt):
                            raise e

                if not success:
                    tqdm.write(f"[CRITICAL] Game {game_id} failed after {MAX_RETRIES_PER_GAME} retries.")

                # Update Progress & Resource Monitor
                if game_idx == 1 or game_idx % 100 == 0:
                    cpu = psutil.cpu_percent(interval=None)
                    ram_mb = proc.memory_info().rss / (1024**2)
                    elapsed = time.time() - t0
                    pbar.set_postfix({"CPU%": f"{cpu:.0f}", "RAM(MB)": f"{ram_mb:.0f}", "Elapsed(s)": f"{elapsed:.0f}"})

                pbar.update(1)

                if game_idx % args.batch_size == 0:
                    flush()

        # Final flush
        flush()
        
    except KeyboardInterrupt:
        tqdm.write("\n[Stopped] User interrupted.")
        flush()
    except BaseException as e: # [Forensic] Catch ALL, including SystemExit
        tqdm.write(f"\n[CRITICAL ERROR] Main loop crashed: {e}")
        with open(error_log_path, "a", encoding="utf-8") as ef:
            ef.write(f"=== CRITICAL MAIN LOOP CRASH ===\n{traceback.format_exc()}\n")
            ef.flush()
            os.fsync(ef.fileno())
    finally:
        pbar.close()

    # merge outputs
    out_matches = os.path.join(output_dir, "matches.parquet")
    out_team = os.path.join(output_dir, "team_game_stats.parquet")
    out_box = os.path.join(output_dir, "boxscores.parquet")
    out_poss = os.path.join(output_dir, "possession_times.parquet")

    print("\n[Merging] Consolidating batch files...")
    if mf:
        concat_parquets(mf, out_matches)
        concat_parquets(tf, out_team)
        concat_parquets(bf, out_box)
        concat_parquets(pf, out_poss)

        print(f"\n[Loading] Reading merged dataframes...")
        matches_df = pd.read_parquet(out_matches)
        team_df = pd.read_parquet(out_team)
        box_df = pd.read_parquet(out_box)
        poss_df = pd.read_parquet(out_poss)

        report_path = os.path.join(output_dir, "report.md")
        build_report(
            report_path=report_path,
            run_id=run_id,
            config=config,
            teams_src=teams_src,
            matches_df=matches_df,
            team_df=team_df,
            box_df=box_df,
            poss_df=poss_df,
        )

        cpu = psutil.cpu_percent(interval=None)
        ram_mb = proc.memory_info().rss / (1024**2)
        elapsed = time.time() - t0

        print("\n=== DONE ===")
        print(f"run_id: {run_id}")
        print(f"output_dir: {output_dir}")
        print(f"matches: {matches_df.shape[0]}")
        print(f"team_game_stats: {team_df.shape[0]}")
        print(f"possession_rows: {poss_df.shape[0]}")
        print(f"report: {report_path}")
        print(f"CPU%: {cpu:.0f}  RAM(MB): {ram_mb:.0f}  elapsed(s): {elapsed:.1f}")
    else:
        print("\n[Warning] No data generated. Check error logs.")


if __name__ == "__main__":
    try:
        # Optional: Clear terminal for cleaner output
        from scripts.terminal import clear_terminal
        clear_terminal()
        pass
    except ImportError:
        pass
    except Exception:
        pass
    main()