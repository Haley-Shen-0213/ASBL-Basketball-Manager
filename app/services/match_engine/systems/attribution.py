# app/services/match_engine/systems/attribution.py

from typing import List, Optional, Tuple, Dict
from ..structures import EnginePlayer, EngineTeam
from ..utils.rng import rng

class AttributionSystem:
    """
    數據歸屬系統 (Level 3) - Config Driven
    對應 Spec v1.5 Section 6
    
    [Fix Log]
    - Aligned method signatures with MatchEngine core calls.
    - record_block now accepts (blocker, shooter).
    - Renamed record_shot_attempt -> record_attempt.
    - Renamed determine_assister -> determine_assist_provider.
    - Added record_assist method.
    """

    @staticmethod
    def _get_val(player: EnginePlayer, attr_name: str) -> float:
        """取得經體力修正後的屬性值"""
        val = getattr(player, attr_name, 0.0)
        if attr_name == 'height': return val
        return val * player.stamina_coeff

    @staticmethod
    def _get_attrs_from_config(config: Dict, key: str) -> List[str]:
        """
        Helper: 解析 Config 中的屬性列表引用
        """
        me_config = config.get('match_engine', {})
        attr_pools = me_config.get('attr_pools', {})
        
        # 嘗試從 attribution.formulas 讀取 key
        formulas = me_config.get('attribution', {}).get('formulas', {})
        val = formulas.get(key)
        
        if isinstance(val, list):
            return val
        elif isinstance(val, str):
            # 若是字串，代表引用 attr_pools
            return attr_pools.get(val, [])
        return []

    @staticmethod
    def determine_shooter(team: EngineTeam, is_3pt_attempt: bool, config: Dict) -> EnginePlayer:
        """
        [Spec 6.1] 決定投籃出手者
        """
        candidates = team.on_court
        weights = []
        total_weight = 0.0
        
        me_config = config.get('match_engine', {})
        attr_params = me_config.get('attribution', {}).get('params', {})

        # 1. 讀取屬性列表
        base_attrs = AttributionSystem._get_attrs_from_config(config, 'shot_weight_base')
        bonus_3pt_attrs = AttributionSystem._get_attrs_from_config(config, 'shot_3pt_bonus')
        
        # 2. 讀取加成係數
        star_bonus = attr_params.get('shot_star_bonus', 1.5)
        starter_bonus = attr_params.get('shot_starter_bonus', 1.2)

        for p in candidates:
            # 基礎權重
            w = sum(AttributionSystem._get_val(p, a) for a in base_attrs)

            # 3分球特殊加成
            if is_3pt_attempt:
                w += sum(AttributionSystem._get_val(p, a) for a in bonus_3pt_attrs)

            # 戰術加成
            role = getattr(p, 'role', 'Bench')
            if role == 'Star': w *= star_bonus
            elif role == 'Starter': w *= starter_bonus
            
            weights.append((p, w))
            total_weight += w

        # 分配邏輯: 權重佔比最小者優先 (Spec 6.1)
        weights.sort(key=lambda x: x[1])
        r = rng.get_float(0.0, 1.0)
        current_prob = 0.0
        
        if total_weight == 0: return candidates[0]

        for p, w in weights:
            prob = w / total_weight
            current_prob += prob
            if r <= current_prob: return p
        return weights[-1][0]

    @staticmethod
    def determine_rebounder(off_team: EngineTeam, def_team: EngineTeam, is_defensive: bool, config: Dict) -> EnginePlayer:
        """
        [Spec 6.3] 決定籃板球歸屬
        """
        candidates = def_team.on_court if is_defensive else off_team.on_court
        weights = []
        total_weight = 0.0
        
        me_config = config.get('match_engine', {})
        attr_params = me_config.get('attribution', {}).get('params', {})
        
        # 讀取參數
        base_attrs = AttributionSystem._get_attrs_from_config(config, 'rebound_base')
        bonus_attrs = AttributionSystem._get_attrs_from_config(config, 'rebound_bonus')
        iq_off_attrs = AttributionSystem._get_attrs_from_config(config, 'rebound_iq_off')
        iq_def_attrs = AttributionSystem._get_attrs_from_config(config, 'rebound_iq_def')
        
        height_weight = attr_params.get('rebound_height_weight', 1.5)

        for p in candidates:
            # 通用屬性
            w = sum(AttributionSystem._get_val(p, a) for a in base_attrs)
            
            # 加權屬性 (包含身高)
            w += sum(AttributionSystem._get_val(p, a) for a in bonus_attrs) * height_weight
            w += AttributionSystem._get_val(p, 'height') * height_weight

            # 智商屬性
            if is_defensive:
                w += sum(AttributionSystem._get_val(p, a) for a in iq_def_attrs)
            else:
                w += sum(AttributionSystem._get_val(p, a) for a in iq_off_attrs)
            
            weights.append((p, w))
            total_weight += w

        weights.sort(key=lambda x: x[1])
        r = rng.get_float(0.0, 1.0)
        current_prob = 0.0
        
        if total_weight == 0: return candidates[0]

        for p, w in weights:
            prob = w / total_weight
            current_prob += prob
            if r <= current_prob: return p
        return weights[-1][0]

    @staticmethod
    def determine_assist_provider(off_team: EngineTeam, shooter: EnginePlayer, config: Dict) -> Optional[EnginePlayer]:
        """
        [Spec 6.4] 決定助攻者 (原名 determine_assister)
        """
        candidates = [p for p in off_team.on_court if p.id != shooter.id]
        if not candidates: return None

        weights = []
        total_weight = 0.0
        
        # 讀取權重屬性
        assist_attrs = AttributionSystem._get_attrs_from_config(config, 'assist_weight')

        for p in candidates:
            w = sum(AttributionSystem._get_val(p, a) for a in assist_attrs)
            weights.append((p, w))
            total_weight += w
        
        # 判定順序: C -> PF -> SF -> SG -> PG
        pos_order_list = config.get('match_engine', {}).get('general', {}).get('substitution', {}).get('redistribution', {}).get('positions', ["C", "PF", "SF", "SG", "PG"])
        pos_order_map = {pos: idx for idx, pos in enumerate(pos_order_list)}
        
        weights.sort(key=lambda x: pos_order_map.get(x[0].position, -1))

        r = rng.get_float(0.0, 1.0)
        current_prob = 0.0
        
        if total_weight == 0: return candidates[-1]

        for p, w in weights:
            prob = w / total_weight
            current_prob += prob
            if r <= current_prob: return p
        return weights[-1][0]

    @staticmethod
    def determine_stealer(def_team: EngineTeam, config: Dict) -> EnginePlayer:
        """
        [Spec 6.5] 決定抄截者
        """
        candidates = def_team.on_court
        weights = []
        total_weight = 0.0
        
        steal_attrs = AttributionSystem._get_attrs_from_config(config, 'steal_weight')

        for p in candidates:
            w = sum(AttributionSystem._get_val(p, a) for a in steal_attrs)
            weights.append((p, w))
            total_weight += w
        
        r = rng.get_float(0.0, 1.0) * total_weight
        upto = 0.0
        for p, w in weights:
            if upto + w >= r: return p
            upto += w
        return candidates[-1]

    # =========================================================================
    # Recording Methods (Aligned with MatchEngine Core)
    # =========================================================================

    @staticmethod
    def get_position_matchup(target_player: EnginePlayer, opponent_team: EngineTeam) -> EnginePlayer:
        """Helper: 尋找對位球員"""
        target_pos = target_player.position
        for p in opponent_team.on_court:
            if p.position == target_pos: return p
        return opponent_team.on_court[0]

    @staticmethod
    def record_attempt(player: EnginePlayer, is_3pt: bool):
        """記錄出手 (原名 record_shot_attempt)"""
        player.stat_fga += 1
        if is_3pt: player.stat_3pa += 1

    @staticmethod
    def record_score(team: EngineTeam, scorer: EnginePlayer, points: int, is_3pt: bool, assister: Optional[EnginePlayer] = None):
        """
        記錄得分 (進球)
        [Critical Fix] 進球必須同時增加 FGA 與 FGM
        """
        # 1. 團隊得分
        team.score += points
        
        # 2. 個人得分
        scorer.stat_pts += points
        
        # 3. 命中數
        scorer.stat_fgm += 1
        if is_3pt: 
            scorer.stat_3pm += 1
        
        # 4. [Fix] 出手數 (進球也算一次出手)
        scorer.stat_fga += 1
        if is_3pt:
            scorer.stat_3pa += 1

        # 5. 助攻
        if assister: 
            assister.stat_ast += 1

    @staticmethod
    def record_assist(passer: EnginePlayer):
        """[New] 記錄助攻 (Core 獨立呼叫)"""
        passer.stat_ast += 1

    @staticmethod
    def record_rebound(player: EnginePlayer, is_offensive: bool):
        """記錄籃板"""
        player.stat_reb += 1
        if is_offensive: player.stat_orb += 1
        else: player.stat_drb += 1

    @staticmethod
    def record_steal(stealer: EnginePlayer, victim_team: EngineTeam):
        """記錄抄截"""
        stealer.stat_stl += 1
        # 尋找受害者記錄失誤
        victim = AttributionSystem.get_position_matchup(stealer, victim_team)
        victim.stat_tov += 1

    @staticmethod
    def record_block(blocker: EnginePlayer, shooter: EnginePlayer):
        """
        記錄封阻 [Fix: 接收 (blocker, shooter)]
        """
        blocker.stat_blk += 1
        # 籃球規則: 被蓋火鍋算一次出手 (FGA)
        # 由於 Core 在封蓋後直接返回 'turnover'，不會進入投籃結算，
        # 因此必須在這裡補上記錄 FGA。
        shooter.stat_fga += 1

    @staticmethod
    def record_team_turnover(team: EngineTeam):
        """記錄團隊失誤 (如 8秒違例)"""
        if hasattr(team, 'stat_tov'): team.stat_tov += 1

    @staticmethod
    def record_foul(player: EnginePlayer):
        """記錄犯規"""
        player.fouls += 1

    @staticmethod
    def record_free_throw(player: EnginePlayer, made: bool):
        """記錄罰球"""
        player.stat_fta += 1
        if made:
            player.stat_ftm += 1
            player.stat_pts += 1