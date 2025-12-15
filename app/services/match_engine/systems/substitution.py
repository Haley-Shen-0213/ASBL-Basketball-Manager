# app/services/match_engine/systems/substitution.py

from typing import List, Optional, Dict
from ..structures import EngineTeam, EnginePlayer

class SubstitutionSystem:
    """
    換人系統 (Level 3) - Config Driven
    對應 Spec v1.5 Section 2.5 & 2.6
    修正: 統一使用秒 (seconds) 進行時間比較。
    """

    @staticmethod
    def check_auto_substitution(team: EngineTeam, quarter: int, time_remaining: float, config: Dict) -> List[str]:
        """
        [Spec 2.5] 常規換人檢查
        """
        logs = []
        
        # 讀取 Config
        sub_config = config.get('match_engine', {}).get('general', {}).get('substitution', {})
        fatigue_threshold = sub_config.get('stamina_threshold', 80.0)
        
        to_sub_out = []
        
        for player in team.on_court:
            reason = None
            # 條件 1: 體力過低
            if player.current_stamina < fatigue_threshold:
                reason = "體力低"
            
            # 條件 2: 時間已到 (容許 1 分鐘緩衝)
            elif (player.minutes_played > player.target_minutes + 1.0):
                reason = "時間到"

            if reason:
                to_sub_out.append((player, reason))
        
        for p_out, reason in to_sub_out:
            p_in = SubstitutionSystem._pick_bench_player(team, p_out.position, p_out.current_stamina)
            
            if p_in:
                SubstitutionSystem.execute_sub(team, p_out, p_in)
                logs.append(f"{team.name} 換人: {p_in.name} 替換 {p_out.name} ({reason})")
        
        return logs

    @staticmethod
    def handle_fouled_out(team: EngineTeam, fouled_player: EnginePlayer, config: Dict) -> str:
        """
        [Spec 2.6] 處理犯滿離場與時間重分配
        """
        fouled_player.is_fouled_out = True
        
        # 計算剩餘時間 [Fix] 使用 seconds
        remaining_minutes = max(0.0, fouled_player.target_minutes - fouled_player.seconds_played)
        fouled_player.target_minutes = fouled_player.seconds_played # 鎖定目標為當前已打時間
        
        # 時間重分配
        if remaining_minutes > 0:
            # 讀取重分配設定
            redis_config = config.get('match_engine', {}).get('general', {}).get('substitution', {}).get('redistribution', {})
            SubstitutionSystem._redistribute_minutes(team, remaining_minutes, redis_config)

        # 強制換人
        p_in = SubstitutionSystem._pick_best_available(team, fouled_player.position)
        
        if p_in:
            SubstitutionSystem.execute_sub(team, fouled_player, p_in)
            return f"{fouled_player.name} 犯滿離場(剩餘{remaining_minutes:.1f}分已分配)，由 {p_in.name} 接替"
        else:
            return f"{fouled_player.name} 犯滿離場，板凳無可用之兵！"

    @staticmethod
    def _redistribute_minutes(team: EngineTeam, minutes: float, redis_config: Dict):
        """
        [Spec 2.6] 分配邏輯
        """
        # 從 Config 讀取順序與數量
        positions_order = redis_config.get('positions', ["C", "PF", "SF", "SG", "PG"])
        top_k = redis_config.get('top_k', 3)
        
        all_players = team.on_court + team.bench
        targets = []
        
        for pos in positions_order:
            valid_players = [p for p in all_players if not p.is_fouled_out]
            # 排序依據該位置分數
            valid_players.sort(key=lambda p: p.pos_scores.get(pos, 0), reverse=True)
            targets.extend(valid_players[:top_k])
        
        # 分配時間 (總份數 = 位置數 * Top_K)
        total_slots = len(positions_order) * top_k
        if total_slots > 0:
            unit_time = minutes / float(total_slots)
            for p in targets:
                p.target_minutes += unit_time

    @staticmethod
    def execute_sub(team: EngineTeam, p_out: EnginePlayer, p_in: EnginePlayer):
        """執行換人"""
        if p_out in team.on_court and p_in in team.bench:
            team.on_court.remove(p_out)
            team.bench.append(p_out)
            team.bench.remove(p_in)
            team.on_court.append(p_in)
            p_in.position = p_out.position

    @staticmethod
    def _pick_bench_player(team: EngineTeam, target_position: str, current_stamina_threshold: float) -> Optional[EnginePlayer]:
        """常規替補選擇"""
        candidates = [
            p for p in team.bench 
            if not p.is_fouled_out 
            and p.current_stamina > current_stamina_threshold
            and p.minutes_played < p.target_minutes
        ]
        if not candidates: return None
        candidates.sort(key=lambda p: p.pos_scores.get(target_position, 0), reverse=True)
        return candidates[0]

    @staticmethod
    def _pick_best_available(team: EngineTeam, target_position: str) -> Optional[EnginePlayer]:
        """緊急替補選擇"""
        candidates = [p for p in team.bench if not p.is_fouled_out]
        if not candidates: return None
        candidates.sort(key=lambda p: p.pos_scores.get(target_position, 0), reverse=True)
        return candidates[0]