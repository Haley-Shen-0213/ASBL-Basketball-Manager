# app/services/match_engine/systems/substitution.py

from typing import List, Optional, Dict, Set
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
            elif (player.seconds_played > player.target_seconds + 60.0):
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
        remaining_seconds = max(0.0, fouled_player.target_seconds - fouled_player.seconds_played)
        fouled_player.target_seconds = fouled_player.seconds_played 
        
        # 時間重分配
        if remaining_seconds > 0:
            # 讀取重分配設定
            redis_config = config.get('match_engine', {}).get('general', {}).get('substitution', {}).get('redistribution', {})
            SubstitutionSystem._redistribute_minutes(team, remaining_seconds, redis_config)

        # 強制換人
        p_in = SubstitutionSystem._pick_best_available(team, fouled_player.position)
        
        if p_in:
            SubstitutionSystem.execute_sub(team, fouled_player, p_in)
            return f"{fouled_player.name} 犯滿離場(剩餘{remaining_seconds:.1f}分已分配)，由 {p_in.name} 接替"
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
                p.target_seconds += unit_time

    @staticmethod
    def execute_sub(team: EngineTeam, p_out: EnginePlayer, p_in: EnginePlayer):
        """執行換人"""
        if p_out in team.on_court:
            team.on_court.remove(p_out)
            team.bench.append(p_out)
        
        if p_in in team.bench:
            team.bench.remove(p_in)
            team.on_court.append(p_in)
        elif p_in not in team.on_court:
            # 防呆: 如果 p_in 既不在 bench 也不在 on_court (理論上不應發生)
            team.on_court.append(p_in)

    @staticmethod
    def _pick_bench_player(team: EngineTeam, target_position: str, current_stamina_threshold: float) -> Optional[EnginePlayer]:
        """常規替補選擇"""
        candidates = [
            p for p in team.bench 
            if not p.is_fouled_out 
            and p.current_stamina > current_stamina_threshold
            and p.seconds_played < p.target_seconds
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
    
    @staticmethod
    def enforce_best_lineup(team: EngineTeam, config: Dict) -> List[str]:
        """
        [Spec 2.5 Revised] 關鍵時刻強制調度 (Clutch Override)
        邏輯：
        1. 以賽前決定的 Best 5 為基礎。
        2. 若 Best 5 有人犯滿，則依據該位置評分順序，選出下一位可用球員遞補。
        3. 確保遞補者不是「其他位置的 Best 5 成員」(避免挖東牆補西牆)。
        4. 強制換人。
        """
        logs = []
        
        # 1. 取得基礎 Best 5 (對應索引 0:C, 1:PF, 2:SF, 3:SG, 4:PG)
        # 注意: 這裡必須複製一份 list，避免修改到原始的 team.best_five
        if not team.best_five: return logs
        
        target_lineup = list(team.best_five) 
        positions_order = ["C", "PF", "SF", "SG", "PG"]
        
        # 2. 建立「已鎖定名單」集合
        # 先將 Best 5 中「未犯滿」的球員鎖定，確保他們不會被當作替補去補別的位置
        locked_ids: Set[str] = {p.id for p in target_lineup if not p.is_fouled_out}
        
        # 3. 檢查並修復陣容 (填補犯滿缺口)
        for i, player in enumerate(target_lineup):
            if player.is_fouled_out:
                target_pos = positions_order[i]
                
                # 尋找替補：
                # 條件 A: 未犯滿
                # 條件 B: 不在 locked_ids 中 (不是其他位置的主力)
                candidates = [
                    p for p in team.roster 
                    if not p.is_fouled_out and p.id not in locked_ids
                ]
                
                # 排序：依據該位置 (target_pos) 的評分由高至低
                candidates.sort(key=lambda p: p.pos_scores.get(target_pos, 0), reverse=True)
                
                if candidates:
                    replacement = candidates[0]
                    target_lineup[i] = replacement
                    locked_ids.add(replacement.id) # 鎖定這位替補，避免他被重複選用
                    # logs.append(f"Debug: {team.name} {target_pos} 由 {replacement.name} 遞補 (原: {player.name} 犯滿)")
                else:
                    # 極端情況：全隊都犯滿或無人可用，保持原樣 (避免程式崩潰)
                    pass

        # 4. 執行換人 (Diff & Swap)
        # 比較 target_lineup 與 team.on_court
        
        # 找出「該上場但不在場上」的球員 (In)
        current_court_ids = {p.id for p in team.on_court}
        players_in = [p for p in target_lineup if p.id not in current_court_ids]
        
        # 找出「在場上但不該上場」的球員 (Out)
        target_ids = {p.id for p in target_lineup}
        players_out = [p for p in team.on_court if p.id not in target_ids]
        
        # 執行替換 (一進一出)
        # 由於人數一定相等 (都是5人)，直接配對替換
        for p_in, p_out in zip(players_in, players_out):
            SubstitutionSystem.execute_sub(team, p_out, p_in)
            
            # 設定上場球員的位置 (依照他在 target_lineup 中的索引決定)
            # 找出 p_in 在 target_lineup 的 index 以決定位置
            idx = target_lineup.index(p_in)
            p_in.position = positions_order[idx]
            
            logs.append(f"{team.name} 關鍵時刻調度: {p_in.name} ({p_in.position}) 替換 {p_out.name}")
        
        return logs