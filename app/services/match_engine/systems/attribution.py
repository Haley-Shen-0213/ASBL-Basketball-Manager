# app/services/match_engine/systems/attribution.py

from typing import List, Optional, Tuple, Dict
from ..structures import EnginePlayer, EngineTeam
from ..utils.rng import rng

class AttributionSystem:
    """
    數據歸屬系統 (Level 3) - Config Driven
    對應 Spec v1.5 Section 6
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
        例如: "off_13" -> 查 attr_pools -> 回傳 list
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
            # Spec: 身高(*1.5) + 彈跳(*1.5) ...
            # 這裡假設 bonus_attrs 裡的屬性都需要乘上 height_weight
            w += sum(AttributionSystem._get_val(p, a) for a in bonus_attrs) * height_weight
            
            # 身高單獨處理 (因為它在 attributes 裡可能沒有，是基本資料)
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
    def determine_assister(off_team: EngineTeam, shooter: EnginePlayer, config: Dict) -> Optional[EnginePlayer]:
        """
        [Spec 6.4] 決定助攻者
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
        # 這裡我們使用 Config 中的 substitution.redistribution.positions 作為參考順序
        # 因為通常這就是標準的位置順序
        pos_order_list = config.get('match_engine', {}).get('general', {}).get('substitution', {}).get('redistribution', {}).get('positions', ["C", "PF", "SF", "SG", "PG"])
        
        # 建立 lookup table: {'C': 0, 'PF': 1...}
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

    # ... (Record 方法與之前相同，略過不變的部分) ...
    # 為了完整性，以下保留 Helper 方法
    
    @staticmethod
    def get_position_matchup(target_player: EnginePlayer, opponent_team: EngineTeam) -> EnginePlayer:
        target_pos = target_player.position
        for p in opponent_team.on_court:
            if p.position == target_pos: return p
        return opponent_team.on_court[0]

    @staticmethod
    def record_shot_attempt(player: EnginePlayer, is_3pt: bool):
        player.stat_fga += 1
        if is_3pt: player.stat_3pa += 1

    @staticmethod
    def record_score(team: EngineTeam, scorer: EnginePlayer, points: int, is_3pt: bool, assister: Optional[EnginePlayer] = None):
        team.score += points
        scorer.stat_pts += points
        scorer.stat_fgm += 1
        if is_3pt: scorer.stat_3pm += 1
        if assister: assister.stat_ast += 1

    @staticmethod
    def record_rebound(player: EnginePlayer, is_offensive: bool):
        player.stat_reb += 1
        if is_offensive: player.stat_orb += 1
        else: player.stat_drb += 1

    @staticmethod
    def record_steal(stealer: EnginePlayer, victim_team: EngineTeam):
        stealer.stat_stl += 1
        victim = AttributionSystem.get_position_matchup(stealer, victim_team)
        victim.stat_tov += 1

    @staticmethod
    def record_block(shooter: EnginePlayer, def_team: EngineTeam):
        blocker = AttributionSystem.get_position_matchup(shooter, def_team)
        blocker.stat_blk += 1

    @staticmethod
    def record_team_turnover(team: EngineTeam):
        if hasattr(team, 'stat_tov'): team.stat_tov += 1

    @staticmethod
    def record_foul(player: EnginePlayer):
        player.fouls += 1

    @staticmethod
    def record_free_throw(player: EnginePlayer, made: bool):
        player.stat_fta += 1
        if made:
            player.stat_ftm += 1
            player.stat_pts += 1