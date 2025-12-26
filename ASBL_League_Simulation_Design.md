# ASBL 聯賽賽季模擬系統設計文件 (League Simulation Design Document)

**版本**: 1.7 (Final with Spec-Compliant Attributes)
**日期**: 2025-12-24
**狀態**: 待實作 (Ready for Implementation)

---

## 1. 系統概述 (Overview)
本系統旨在利用現有的 `TeamCreator` (球員生成) 與 `MatchEngine` (比賽引擎)，模擬 ASBL 聯盟 36 支球隊的完整賽季運作。

**核心目標**：
1.  驗證比賽引擎在大規模樣本下的數據穩定性 (Pace, FG%, Score)。
2.  建立長期追蹤機制，觀察球員能力值分佈對比賽數據的影響。
3.  **驗證體力系統平衡性**：分析個別球員的上場時間與剩餘體力之關聯。
4.  **追蹤球員流動**：記錄球員的加入與離開（選秀、裁員）。

---

## 2. 變更歷程 (Change Log)
記錄從初版需求到定案的討論過程。

### v1.0 ~ v1.3 (前期規劃)
*   確立 36 隊、1307 場比賽 (例行賽+季後賽) 的規模。
*   確立球員 8 位數隨機編號機制。
*   確立季後賽強制打滿、休賽季裁人 (Drop) 機制。
*   加入回合數 (Possessions) 與體力追蹤。

### v1.4 (體力追蹤修正)
*   修正體力追蹤維度至「球員層級」，驗證上場時間與剩餘體力的關係。

### v1.5 (交易記錄與中文化)
*   新增 `roster_transactions.parquet`。
*   欄位說明全面中文化。

### v1.6 (詳細能力值)
*   在 `player_stats.parquet` 中加入詳細能力值。

### v1.7 (能力值規格對齊 - Current)
*   **修正欄位**: 依據 ASBL v3.2 規格書，將能力值欄位精確拆分為 10 項可訓練能力與 10 項不可訓練能力。

---

## 3. 執行流程 (Execution Flow)

### Phase 1: 聯盟初始化 (Initialization)
*(僅在模擬開始時執行一次)*

1.  **建立球隊**: 產生 `TEAM_01` ~ `TEAM_36` 共 36 個球隊物件。
2.  **生成球員**:
    *   呼叫 `TeamCreator.create_valid_roster()` 生成 15 人名單。
    *   **注入 ID**: 為每位球員生成唯一 `8位數隨機編號` (Key)。
    *   **物件轉換**: 將 Payload 轉為 `EnginePlayer`。
    *   **記錄異動**: 寫入 `INITIAL` 類型的交易紀錄。
3.  **名單確認**: 依 `attr_sum` (能力總和) 排序，提交最強 15 人名單給引擎。

### Phase 2: 例行賽模擬 (Regular Season)
*(共 1260 場比賽)*

1.  **賽程產生**: 36 隊雙循環 (Double Round-Robin)，隨機打亂順序。
2.  **比賽執行**:
    *   逐場呼叫 `MatchEngine.simulate()`。
    *   **數據寫入**:
        *   更新球隊戰績 (Wins, Losses, PF, PA, Possessions)。
        *   累積球員 **例行賽數據** (Regular Stats)。
        *   **累積體力數據**: 記錄每位球員該場比賽結束時的 `current_stamina`。

### Phase 3: 季後賽模擬 (Playoffs)
*(共 47 場比賽 - 強制打滿)*

1.  **種子排序**: 依 `勝率 > 淨分差` 取前 16 名。
2.  **系列賽執行**:
    *   **R1 (16強)**: 8 組 x 3 場。
    *   **R2 (8強)**: 4 組 x 3 場。
    *   **R3 (4強)**: 2 組 x 3 場。
    *   **Finals**: 1 組 x 5 場。
3.  **數據寫入**:
    *   累積球員 **季後賽數據** (Playoff Stats)。

### Phase 4: 休賽季演練 (Offseason - Future Prep)
*(為多賽季測試做準備)*

1.  **選秀 (Draft)**:
    *   生成 36 名新秀。
    *   依例行賽戰績 **倒序** 分配。
    *   **記錄異動**: 寫入 `DRAFT` 類型的交易紀錄。
2.  **名單調整 (Roster Cut)**:
    *   全隊排序 (16人)。
    *   保留前 15 強。
    *   **強制合規檢查**: 若 Star > 3 或 Star+Starter > 5，直接**拋棄**能力最低的違規球員，由第 16 人遞補。
    *   **記錄異動**: 針對被拋棄的球員，寫入 `DROP` 類型的交易紀錄。

---

## 4. 檔案輸出規格 (Output Schema)
所有檔案皆輸出為 `.parquet` 格式 (Snappy Compression)。

### A. 賽季總結報告 (`season_summary.parquet`)
*   **用途**: 追蹤聯盟整體的趨勢變化 (Macro Level)。
*   **欄位說明**:
    *   `season_id`: **賽季編號** (例如: 1, 2, 3...)
    *   `total_games`: **總場次** (該季進行的總比賽場數)
    *   `avg_attr_sum`: **平均能力總和** (全聯盟所有球員的能力值平均)
    *   `avg_pace`: **平均節奏** (全聯盟每 48 分鐘的平均回合數)
    *   `avg_pts`: **場均得分** (全聯盟平均每場得分)
    *   `avg_fg_pct`: **平均投籃命中率** (全聯盟 FG%)
    *   `avg_3p_pct`: **平均三分命中率** (全聯盟 3P%)
    *   `avg_end_stamina`: **平均賽後剩餘體力** (全聯盟比賽結束時的平均體力，用於監控體力消耗)

### B. 球隊戰績表 (`team_standings.parquet`)
*   **用途**: 記錄各隊賽季表現。
*   **欄位說明**:
    *   `season_id`: **賽季編號**
    *   `team_id`: **隊伍代碼** (例如: TEAM_01)
    *   `wins`: **勝場數**
    *   `losses`: **敗場數**
    *   `win_pct`: **勝率**
    *   `pf`: **總得分** (Points For)
    *   `pa`: **總失分** (Points Against)
    *   `diff`: **淨分差** (PF - PA)
    *   `possessions`: **賽季總回合數** (用於計算進階數據)
    *   `rank_seed`: **例行賽排名** (1-36)
    *   `playoff_result`: **季後賽最終成績** (Champion, Finals, R2, R1, None)

### C. 球員賽季數據表 (`player_stats.parquet`)
*   **用途**: 記錄球員個人數據 (Micro Level)，含詳細能力值與體力追蹤。
*   **欄位說明**:
    *   `season_id`: **賽季編號**
    *   `player_id`: **球員識別碼** (8位數隨機編號, Key)
    *   `name`: **球員姓名**
    *   `team_id`: **所屬球隊**
    *   `grade`: **球員等級** (SSR, SS, S, A, B)
    *   `role`: **球隊角色** (Star, Starter, Rotation, Bench)
    *   `attr_sum`: **能力總和** (Trainable + Untrainable)
    *   **[Trainable Stats - 可訓練能力]** (v3.2 Spec):
        *   `attr_shot_accuracy`: **投籃準心**
        *   `attr_shot_range`: **射程**
        *   `attr_off_pass`: **傳球**
        *   `attr_off_dribble`: **運球**
        *   `attr_off_handle`: **控球**
        *   `attr_off_move`: **跑位**
        *   `attr_def_rebound`: **籃板**
        *   `attr_def_boxout`: **卡位**
        *   `attr_def_contest`: **干擾**
        *   `attr_def_disrupt`: **抄截**
    *   **[Untrainable Stats - 不可訓練能力]** (v3.2 Spec):
        *   `attr_ath_stamina`: **體力**
        *   `attr_ath_strength`: **力量**
        *   `attr_ath_speed`: **速度**
        *   `attr_ath_jump`: **彈跳**
        *   `attr_talent_health`: **健康**
        *   `attr_shot_touch`: **手感**
        *   `attr_shot_release`: **出手速度**
        *   `attr_talent_offiq`: **進攻智商**
        *   `attr_talent_defiq`: **防守智商**
        *   `attr_talent_luck`: **運氣**
    *   **[Regular Season Stats - 例行賽數據]**:
        *   `reg_gp`: **出賽場次**
        *   `reg_min`: **總上場時間**
        *   `reg_avg_min`: **平均上場時間**
        *   `reg_avg_end_stamina`: **平均賽後剩餘體力** (驗證高工時是否導致低體力)
        *   `reg_pts`: **總得分**
        *   `reg_reb`: **總籃板**
        *   `reg_ast`: **總助攻**
        *   `reg_stl`: **總抄截**
        *   `reg_blk`: **總火鍋**
        *   `reg_fgm`: **投籃命中數**
        *   `reg_fga`: **投籃出手數**
        *   `reg_3pm`: **三分命中數**
        *   `reg_3pa`: **三分出手數**
    *   **[Playoff Stats - 季後賽數據]**:
        *   `po_gp`: **出賽場次**
        *   `po_min`: **總上場時間**
        *   `po_avg_end_stamina`: **平均賽後剩餘體力**
        *   `po_pts` ~ `po_3pa`: (同上，季後賽版本)

### D. 比賽結果明細表 (`match_results.parquet`)
*   **用途**: 1307 場比賽的流水帳。
*   **欄位說明**:
    *   `season_id`: **賽季編號**
    *   `game_id`: **比賽識別碼** (例如: S1_REG_0001)
    *   `stage`: **比賽階段** (Regular / Playoff)
    *   `home_team`: **主隊代碼**
    *   `away_team`: **客隊代碼**
    *   `home_score`: **主隊得分**
    *   `away_score`: **客隊得分**
    *   `winner`: **勝方代碼**
    *   `pace`: **比賽節奏** (該場比賽每 48 分鐘回合數)
    *   `possessions`: **總回合數** (該場比賽實際回合數)
    *   `is_ot`: **是否延長賽** (True/False)

### E. 球員流動記錄表 (`roster_transactions.parquet`)
*   **用途**: 追蹤球員的進出狀況。
*   **欄位說明**:
    *   `season_id`: **賽季編號**
    *   `team_id`: **相關球隊代碼**
    *   `player_id`: **球員識別碼**
    *   `player_name`: **球員姓名**
    *   `transaction_type`: **異動類型**
        *   `INITIAL`: 聯盟創立時的初始分配
        *   `DRAFT`: 選秀會選中加入
        *   `DROP`: 因名單限制被裁員/拋棄
    *   `timestamp`: **發生時間點** (例如: "Pre-Season", "Offseason")