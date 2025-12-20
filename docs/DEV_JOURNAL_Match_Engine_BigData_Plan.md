# 路徑：docs/DEV_JOURNAL_Match_Engine_BigData_Plan.md
# 專案開發日誌：ASBL 比賽引擎大數據測試參數規劃 (10M+ Scale)
**Project Journal: ASBL Match Engine - Big Data Simulation Strategy (10M+ Scale)**

**日期**: 2025-12-18 04:30
**參與者**: Product Owner (User), Lead Architect (Monica)
**主題**: 定義達成 1,000 萬至 1 億場次模擬的參數設定與數據蒐集架構

## 1. 測試目標與範疇 (Objectives & Scope)

### 1.1 核心需求
本次測試旨在驗證 **Match Engine v1.6** 的數值平衡性與極限邊界。
*   **模擬規模**: 累積 **1,000 萬 (10M)** 至 **1 億 (100M)** 場有效比賽數據。
*   **賽制結構**: 模擬標準職業聯賽結構（每隊單季約 70 場），以蒐集具有統計意義的賽季數據（如勝率、場均得分、MVP 歸屬）。
*   **機制限制**: 目前尚未實作「跨場次」的賽季疲勞累積與傷病系統。因此，本次測試採用 **「無狀態賽季模擬 (Stateless Season Simulation)」** 模式——即每場比賽開始時，球員體力與狀態皆為滿值，但比賽產生的數據（PTS/REB/AST）會被累計。

### 1.2 策略選擇：平行宇宙法 (Parallel Seasons Method)
為了在有限的運算資源下達成千萬級別場次，同時保持賽季結構的合理性，我們不採用單一超大型聯賽，而是採用 **「標準聯賽參數 x 大量平行迭代」** 的方式進行蒙地卡羅模擬 (Monte Carlo Simulation)。

## 2. 參數模型設計 (Parameter Modeling)

為了滿足「每隊單季出賽 70 場」且「循環賽制 (Round-Robin)」的數學限制，我們推導出以下最佳參數組合：

### 2.1 變數定義
*   **$N$**: 聯盟球隊數量 (Number of Teams)
*   **$X$**: 對戰循環次數 (Head-to-Head Games)
*   **$G_{team}$**: 單隊單季出賽數 (Games per Team)
*   **$G_{total}$**: 單季聯盟總場次 (Total Games per Season)

### 2.2 最佳參數解
若目標 $G_{team} = 70$，且必須滿足每隊彼此對戰：
\[ G_{team} = (N - 1) \times X \]

設定 **$X = 2$** (主客場各一，最標準的公平賽制)，則：
\[ 70 = (N - 1) \times 2 \Rightarrow N - 1 = 35 \Rightarrow N = 36 \]

因此，我們將採用以下設定：
*   **球隊數 ($N$)**: **36 隊**
*   **對戰數 ($X$)**: **2 場** (主/客各 1)
*   **單隊場次**: **70 場** (完美符合需求)
*   **單季總場次 ($G_{total}$)**: 
    \[ \frac{36 \times 35}{2} \times 2 = 1,260 \text{ 場} \]

### 2.3 規模擴展計算 (Scaling)
基於單季 1,260 場的基礎，達成目標所需的賽季迭代次數 ($S$) 如下：

| 測試層級 (Tier) | 目標總場次 | 需模擬賽季數 ($S$) | 預估耗時 (20 Cores) | 備註 |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1: 壓力測試** | 10,000,000 (10M) | **7,937** | ~1.5 小時 | 驗證數值收斂性 |
| **Phase 2: 極限驗證** | 100,000,000 (100M) | **79,366** | ~15 小時 | 檢測極端離群值 (Outliers) |

## 3. 數據蒐集架構 (Data Collection Schema)

我們將透過 ETL Pipeline 產出四份關鍵的 Parquet 資料表，用於後續的數據分析：

### 3.1 賽季戰績表 (League Standings)
*用途：驗證強弱隊伍的勝率分佈，確認 SSR 球員對戰績的影響力。*
*   `season_id`: UUID
*   `team_id`: String
*   `wins`: Int (勝場)
*   `losses`: Int (敗場)
*   `win_pct`: Float (勝率)
*   `avg_point_diff`: Float (平均分差 / Net Rating)

### 3.2 球隊攻守統計 (Team Aggregates)
*用途：驗證比賽節奏與比分是否符合現代籃球常態。*
*   `season_id`: UUID
*   `team_id`: String
*   `ppg`: Float (場均得分)
*   `oppg`: Float (場均失分)
*   `pace`: Float (場均回合數)
*   `fg_pct`: Float (團隊命中率)

### 3.3 球員賽季數據 (Player Season Stats)
*用途：驗證球員卡等級 (Grade) 與實際表現的相關性 (Correlation)。*
*   `season_id`: UUID
*   `player_id`: String
*   `grade`: Category (SSR/SS/S/A/B/C/G)
*   `role`: Category (Star/Starter/Rotation...)
*   `mpg`: Float (場均上場時間)
*   `ppg`: Float (場均得分)
*   `rpg`: Float (場均籃板)
*   `apg`: Float (場均助攻)
*   `usage_rate`: Float (球權佔有率)

### 3.4 體能極限監測 (Stamina Stress Log)
*用途：針對單場比賽的體力消耗模型進行壓力測試。*
*   `match_id`: String
*   `player_id`: String
*   `end_game_stamina`: Float (終場剩餘體力)
*   `is_fatigued`: Boolean (是否在體力 < 30 狀態下結束比賽)
*   *註：此數據僅記錄單場狀態，不進行跨場次累計。*

## 4. 執行計畫 (Execution Roadmap)

1.  **初始化 (Initialization)**:
    *   建立一個包含 1,000 支球隊的 **Team Pool** (符合常態分佈)。
    *   每次賽季開始前，從 Pool 中隨機抽取 36 支球隊組成聯盟。

2.  **並行運算 (Parallel Processing)**:
    *   利用 Python `multiprocessing` 模組。
    *   每個 Worker Process 負責執行一個完整的 **Season Context** (1,260 場比賽)。
    *   Worker 僅回傳聚合後的統計數據 (Aggregated Stats)，大幅減少 I/O 開銷。

3.  **驗收標準 (Acceptance Criteria)**:
    *   **勝率分佈**: 強隊 (SSR核心) 勝率應 > 60%，弱隊 < 40%。
    *   **數據合理性**: 聯盟平均得分應落在 90-110 區間。
    *   **體力模型**: 應有 5%-15% 的球員在比賽結束時處於疲勞狀態 (Stamina < 30)，證明體力限制有效。

## 5. 結論 (Conclusion)
本計畫透過 **$N=36, X=2$** 的參數設定，精確模擬了單季 70 場的職業賽制。透過平行執行約 8,000 個賽季，我們將能以極高的效率完成 1,000 萬場次的數值驗證，為 ASBL 的平衡性提供堅實的數據支撐。

---

## 2025-12-18 05:00 - 實作架構與腳本設計 (Implementation Architecture)

**參與者**: Product Owner, Lead Architect
**變更摘要**: 確立 `scripts/simulate_bigdata.py` 的程式結構，定義並行運算中的記憶體管理與數據聚合策略。

### 1. 核心腳本設計 (`scripts/simulate_bigdata.py`)

為了落實 $N=36, X=2$ 的平行宇宙模擬，我們將程式邏輯拆解為三個主要類別，以確保在 i9-14900K 上的執行效率：

#### A. `TeamPoolManager` (球隊池管理器)
*   **職責**: 負責在主程序 (Main Process) 初始化 1,000 支球隊。
*   **記憶體策略**: 
    *   由於 1,000 支球隊物件 (包含球員) 大約佔用 200-500MB 記憶體，我們決定**不使用 Shared Memory** (太複雜且序列化成本高)。
    *   **策略**: 在主程序生成後，透過 `copy.deepcopy` 或 `pickle` 將「選中的 36 支球隊」傳遞給 Worker。這能確保每個賽季的狀態獨立 (Stateless)。

#### B. `SeasonWorker` (賽季執行器)
*   **職責**: 這是 `multiprocessing` 的執行單元。
*   **輸入**: 36 支球隊物件 (List[Team])。
*   **流程**:
    1.  建立賽程表 (Schedule): Round-Robin x 2 (共 1,260 場)。
    2.  執行比賽 (Match Execution): 呼叫 `MatchEngine.run_headless()`。
    3.  **數據暫存 (In-Memory Buffer)**: 將該賽季產生的數據暫存於 Dict，不進行磁碟 I/O。
*   **輸出**: 回傳一個包含 `standings`, `player_stats`, `team_stats` 的壓縮資料包 (Data Class)。

#### C. `BigDataAggregator` (數據聚合器)
*   **職責**: 接收 Worker 回傳的結果，並進行批次寫入。
*   **I/O 優化**: 
    *   設定 `FLUSH_INTERVAL = 100 Seasons`。
    *   每累積 100 個賽季的數據，才呼叫一次 `pyarrow.parquet.write_table`，避免 SSD 頻繁寫入造成瓶頸。

### 2. 資料流與 ID 追蹤 (Data Flow & ID Tracking)

為了達成「統計特定球隊奪冠率」的需求，我們必須確保 ID 的一致性：

*   **Team ID**: 在 `TeamPoolManager` 初始化時生成 UUID (e.g., `T-001` to `T-1000`)，並在所有平行宇宙中保持不變。
*   **Season ID**: 每次 Worker 啟動新賽季時動態生成 UUID。
*   **Match ID**: 僅在比賽執行當下生成，用於關聯 `stamina_log`。

### 3. 例外處理與斷點續傳 (Error Handling & Checkpoint)

考慮到跑 1 億場 (Phase 2) 可能耗時 15 小時，必須設計防呆機制：
*   **Crash Protection**: 若單一 Worker 發生 Exception (如數值溢出)，主程序僅記錄 Error Log 並丟棄該賽季數據，**不中斷整體測試**。
*   **Progress Bar**: 使用 `tqdm` 顯示進度 (e.g., `Season 5430/7937 [======>...]`)。
*   **Checkpoint**: 每完成 10% 進度，強制 Flush 所有 Parquet 檔案，確保斷電時僅損失最後一小部分的數據。

### 4. 下一步 (Next Steps)
*   **Action**: 開始撰寫 `scripts/simulate_bigdata.py`。
*   **Check**: 先用 `Tier 1` (10 賽季) 進行 Dry Run，確認記憶體峰值是否穩定在 128GB 安全範圍內。

---

## 2025-12-18 05:15 - 最終測試計畫確認 (Finalized Test Plan)

**參與者**: Product Owner, Lead Architect
**變更摘要**: 根據硬體規格與測試需求，確立最終執行細節、目錄結構與配置管理方式。

### 1. 測試概述 (Executive Summary)
本計畫旨在透過高併發運算，驗證 ASBL 比賽引擎在長週期、大規模樣本下的數值穩定性。
*   **Phase 0 (Pilot)**: 執行 **30 個賽季**，驗證 Pipeline 穩定性與資源消耗。
*   **Phase 1 (Production)**: 執行 **80,000 個賽季** (累積約 **1.008 億場**)，產出終極平衡性報告。

### 2. 測試環境 (Test Environment)
*   **CPU**: Intel Core i9-14900K (24 Cores / 32 Threads) -> 分配 20-22 Cores 給 Worker。
*   **RAM**: 128GB DDR5 -> 預留 64GB 作為 In-Memory Buffer。
*   **Storage**: 2TB NVMe SSD (RAID 5) -> 專用 Parquet 寫入。

### 3. 專案結構與配置 (Project Structure & Config)
測試程式碼將獨立於 `tests/` 目錄下，並透過 YAML 管理所有變數。

tests/bigdata_sim/
├── config.yaml            # 核心設定檔 (資源、賽季數、閾值)
├── simulate_main.py       # 主程式 (Entry Point)
├── worker.py              # 單一賽季執行邏輯
├── analytics.py           # 數據驗證與 KPI 計算
└── requirements.txt       # 測試專用依賴

### 4. 測試內容細節 (Test Scope Details)

#### 4.1 模擬參數 (Simulation Parameters)
*   **Team Generation**: 
    *   使用專案內建服務 `app.services.team_creator.py`。
    *   生成 1,000 支球隊存入 Pool (ID 固定)。
*   **League Structure**:
    *   **$N=36$** (球隊數)
    *   **$X=2$** (循環次數)
    *   **$G_{team}=70$** (單隊場次)
    *   **$G_{total}=1,260$** (單季總場次)
*   **Engine Mode**: Stateless (無疲勞累積), Headless.

#### 4.2 驗證項目 (Validation Items)
1.  **數值分佈**: 勝率常態分佈檢定、SSR/G 級球員數據顯著性差異、Outliers 檢測。
2.  **機率統計**: 
    *   統計全體球隊的奪冠機率分佈 (Max/Min/Avg Title Probability)。
    *   統計全體球隊進入前三名的機率分佈。
3.  **系統效能**: 單季/總耗時、記憶體洩漏、Parquet Schema 驗證。

### 5. 關鍵績效指標 (KPIs)

#### 5.1 系統效能 (System Performance)
*   **CPU**: 85% - 95% (滿載運行)。
*   **RAM**: Peak < 100GB。
*   **Speed**: 單季模擬 < 15 秒。
*   **Stability**: Phase 0 (0% Crash), Phase 1 (<0.1% Crash)。

#### 5.2 數據品質 (Data Quality)
*   **Integrity**: 無 NaN 值，Pandas 可讀取。
*   **Logic**: `Total Wins == Total Losses`, `Total Points Scored == Total Points Allowed`.

### 6. 測試流程 (Test Workflow)

#### Step 1: 初始化 (Initialization)
*   讀取 `tests/bigdata_sim/config.yaml`。
*   呼叫 `team_creator` 生成 1,000 支球隊並快取。
*   初始化 Output 目錄。

#### Step 2: 任務分派 (Dispatch)
*   建立 `multiprocessing.Pool(processes=Config.CORES)`。
*   派發任務：Phase 0 (30 tasks) 或 Phase 1 (80,000 tasks)。

#### Step 3: 執行與監控 (Execution)
*   **Worker**: 執行 1,260 場比賽 -> 暫存數據。
*   **Main**: 監控 CPU/RAM，更新 `tqdm` 進度條。

#### Step 4: 數據持久化 (Persist)
*   每累積 `Config.FLUSH_INTERVAL` (e.g., 100) 個賽季，寫入一次 Parquet。

#### Step 5: 驗收 (Verification)
*   執行 `analytics.py` 產出 KPI 報告。

### 7. Phase 0 前導測試規格 (Pilot Specs)
*   **Config**: `total_seasons: 30`, `cores: 22`
*   **Goal**: 總耗時 < 60 秒，產出檔案無誤。

---

## 2025-12-20 09:00 - Phase 1 檢討與 Phase 2 架構重整 (Post-Mortem & Phase 2 Re-Architecture)

**參與者**: Product Owner, Lead Architect
**狀態**: Phase 1 (Failed), Phase 2 (Planning)

### 1. Phase 1 測試結果檢討 (Post-Mortem)

雖然 Phase 1 成功在硬體層面跑完了 1 億場次（耗時約 42 小時），但在數據有效性上被判定為**失敗**。主要原因如下：

*   **身分識別災難 (Identity Crisis)**:
    *   **問題**: 依賴隨機姓名作為 Key，但 Mock 姓名庫過小導致嚴重的碰撞（Collision）。
    *   **後果**: `MillerRichard` 代表了 20 個不同能力的球員，導致無法分析個別球員（如 SSR vs C 級）的真實表現。
*   **數值模型崩壞 (Model Collapse)**:
    *   **問題**: 勝率分佈呈現極端的「啞鈴狀」而非「常態分佈」。
    *   **後果**: 強隊勝率接近 100%，弱隊接近 0%。顯示引擎缺乏隨機變異數 (Variance)，導致比賽結果過於決定論 (Deterministic)。
*   **統計異常 (Statistical Anomalies)**:
    *   **問題**: 三分球命中率 (46.7%) 高於兩分球命中率 (45.4%)。
    *   **後果**: 破壞了進攻期望值模型，顯示防守干擾係數或投籃難度計算有誤。

### 2. Phase 2 測試目標：結構化重啟 (Structured Reset)

為了修正上述問題，Phase 2 將進行「外科手術式」的架構調整。目標是驗證**隨機生成的初始球隊**在大量樣本下，是否呈現合理的常態分佈，並確保長期模擬的公平性。

#### 2.1 核心變更策略：固定樣本池
*   **Phase 1 缺陷**: 從 1,000 支球隊池中，每季隨機抽取 36 隊。這導致每支球隊參與的賽季數不一致，難以追蹤特定球隊的長期表現。
*   **Phase 2 修正**: 
    1.  一次性生成 **360 支固定球隊**。
    2.  這 360 支球隊將**全勤參與所有 8,000 個賽季**。
    3.  透過分組機制解決單季對戰規模問題。

### 3. Phase 2 參數模型 (Revised Parameters)

#### 3.1 硬體與環境
*   **CPU**: Intel Core i9-14900K (24 Cores / 32 Threads)。
*   **RAM**: 128GB DDR5。
*   **Storage**: 2TB NVMe SSD (RAID 5)。

#### 3.2 聯盟結構
*   **總球隊數 ($N_{total}$)**: **360 隊** (一次生成，ID 固定)。
*   **分組結構**: 每個賽季開始時，將 360 隊隨機拆分為 **10 組 (Groups)**，每組 36 隊。
*   **賽制**: 組內雙循環 (Intra-group Double Round-Robin)。
    *   每隊場次: $35 \times 2 = 70$ 場。
    *   單組總場次: $1,260$ 場。
    *   **單季總場次 ($G_{season}$)**: $1,260 \times 10 = 12,600$ 場。

#### 3.3 模擬規模
*   **目標總場次**: **1 億場 (100M+)**。
*   **需模擬賽季數 ($S$)**: 
    \[ \frac{100,000,000}{12,600} \approx \mathbf{8,000} \text{ Seasons} \]
    *(註：Phase 1 為 80,000 賽季，Phase 2 因單季場次擴大 10 倍，故賽季數縮減為 1/10，總運算量不變)*

### 4. 數據驗證重點 (Analytics Focus)

本次測試將產出六個維度的深度分析報告：

#### 4.1 球隊勝率偏差 (Win Rate Deviation)
*   **假設**: 所有球隊皆由相同邏輯隨機生成（初始狀態），理論上勝率應呈現**標準常態分佈**。
*   **觀測指標**: 
    *   勝率標準差 (Standard Deviation)。
    *   是否有極端強/弱隊出現（檢驗 Team Creator 的隨機性是否均勻）。
    *   驗證 360 支球隊的長期平均勝率是否收斂於 50% 附近。

#### 4.2 球員能力與表現相關性 (Attribute-Performance Correlation)
*   **背景**: 目前球員位置 (Position) 為隨機分配，尚未與能力值掛鉤。因此不進行位置別的數據驗證。
*   **驗證目標**: 確認「數值越高，表現越好」的**正相關性 (Positive Correlation)**。
*   **觀測指標**: 
    *   建立散佈圖 (Scatter Plot): X軸為 `Total Attribute Sum`，Y軸為 `PER` 或 `PPG`。
    *   統計不同能力區間 (如 400-450, 450-500) 的平均數據表現。

#### 4.3 體力系統驗證 (Stamina System)
*   **關聯性分析**: 建立回歸模型 $y = f(x_1, x_2, x_3)$
    *   $y$: 終場剩餘體力 (End Game Stamina)
    *   $x_1$: 體能屬性 (Attribute: Stamina)
    *   $x_2$: 上場時間 (Minutes Played)
    *   $x_3$: 比賽節奏 (Pace)
*   **目標**: 確認體力消耗是否線性合理，以及是否出現「體力無限」或「開場即累」的 Bug。

#### 4.4 節奏與環境數據 (Pace & Environment)
*   **平均回合數 (Pace)**: 目標值 95-105 (符合現代籃球節奏)。
*   **進攻效率**: 驗證 3PT% 是否修正為低於 2PT%，且罰球命中率 (FT%) 符合預期。

#### 4.5 長期公平性驗證 (Long-term Fairness)
*   **目標**: 統計 360 支球隊在 8,000 個賽季中的極端表現。
*   **觀測指標**:
    *   **最佳/最差戰績**: 單季最高勝場與最低勝場紀錄。
    *   **排名機率**: 進入前三名 (Top 3) 與落入後三名 (Bottom 3) 的機率分佈。
    *   **奪冠/墊底次數**: 統計每支球隊獲得分組冠軍與分組墊底的總次數。
    *   **偏差檢定**: 理應所有球隊的奪冠次數應在一定誤差範圍內，若某隊奪冠次數異常高，則代表 Team Generation 存在偏差。

#### 4.6 犯規系統驗證 (Foul System Verification)
*   **球隊層級**: 
    *   平均每場犯規次數 (Avg Fouls per Game)。
    *   平均每場罰球次數 (Avg FT Attempts per Game)。
*   **球員層級**:
    *   平均犯規次數。
    *   **最大犯規次數 (Max Fouls)**: 必須嚴格小於 6 (犯滿離場機制)。
    *   驗證防守屬性較低的球員是否更容易犯規。

### 5. 技術執行計畫 (Execution Plan)

1.  **Refactor `TeamCreator`**: 注入 UUID 生成邏輯，確保 360 隊的 ID 永久唯一。
2.  **Rewrite `Worker`**: 
    *   實作「分組邏輯」：接收 360 隊 -> Shuffle -> Split into 10 groups -> Run 10 sub-leagues.
    *   加入 `Random Seed` 控制。
3.  **Schema Update**:
    *   `player_stats` 新增欄位: `grade`, `position`, `attr_sum`, `attr_stamina`, `fouls`.
    *   `team_stats` 新增欄位: `fouls`, `ft_attempts`.
    *   `stamina_log` (抽樣記錄): 每 100 場紀錄一次詳細體力變化，避免硬碟爆炸。

---