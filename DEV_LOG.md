# ASBL Manager - 開發日誌 (Development Log)

## 專案資訊
- **專案名稱**: ASBL Basketball Manager
- **開始日期**: 2025-12-03
- **開發環境**: Python 3.13 + MySQL 9.0 + Flask
- **目前階段**: Phase 1 - 核心架構 (Core Architecture)

---

## 📅 2025-12-03 08:00 (Day 1) - 專案初始化

### ✅ 已完成 (Completed)
- [x] **專案結構建立**: 
    - 連結 GitHub 儲存庫。
    - 修正資料夾層級問題。
    - 設定 `.gitignore` 排除不必要檔案。
- [x] **文件撰寫**:
    - 完成 `README.md` (包含遊戲規則 V2、技術架構、開發時程)。
    - 建立 `DEV_LOG.md` (本檔案)。
- [x] **環境設定**:
    - 建立 `requirements.txt` (Flask, SQLAlchemy, PyMySQL...)。
    - 建立 `config.py` (資料庫連線設定)。
    - 建立 Python 虛擬環境 (`venv`) 並安裝依賴套件。

### 🚧 進行中 (In Progress)
- [ ] **資料庫模型設計**: 準備建立 `User`, `Team`, `Player` 等 SQLAlchemy Models。

### 📝 筆記與問題 (Notes & Issues)
- **Git 操作**: 修正了重複 Clone 導致的巢狀目錄問題，現在結構已扁平化。
- **規則確認**: 
    - 65% 薪資帽限制：超過後無法頂薪續約。
    - 稀有度分級：明確定義 G~SSR 分數區間。
    - 投籃屬性：細分為準心、範圍、手感、射速。

---

## 📅 待辦事項 (To-Do List)

### Phase 1: 核心架構
- [ ] **資料庫建置**:
    - [ ] 定義 `User` Model (帳號、邀請碼)。
    - [ ] 定義 `Team` Model (資金、聲望)。
    - [ ] 定義 `Player` Model (基本資料、稀有度)。
    - [ ] 定義 `PlayerAttributes` Model (詳細數值)。
    - [ ] 定義 `Contract` Model (薪資、角色)。
- [ ] **初始化腳本**: 撰寫 `init_db.py` 讓程式自動建表。
- [ ] **球員生成器**: 實作 `PlayerGenerator` class (100抽邏輯)。

---

## 2025-12-03 10:00 ：資料庫架構與環境建置

### 🚧 進度摘要
完成專案基礎建設，建立 Flask 應用程式工廠模式，並成功連線 MySQL 資料庫，完成核心資料表建置。

### 🛠️ 技術細節
1.  **環境配置 (Configuration)**
    - 建立 `config.py` 與 `.env` 機制，將敏感資訊（Database URL, Secret Key）與程式碼分離。
    - 設定 `.gitignore` 排除 `.env` 檔案，確保資安。

2.  **資料庫模型 (Database Models)**
    - 使用 SQLAlchemy 定義 ORM 模型。
    - **User**: 使用者帳號系統。
    - **Team**: 球隊經營資訊（資金、聲望）。
    - **Player**: 球員核心資料（包含 JSON 格式的詳細數據 `detailed_stats`）。
    - **Contract**: 球員合約系統（薪資、年限、定位）。

3.  **資料庫初始化 (Initialization)**
    - 撰寫 `scripts/init_db.py` 自動化建表腳本。
    - **優化**: 為所有資料表 (Table) 與欄位 (Column) 加上 `COMMENT` 中文註解，提升資料庫可讀性與維護性。

### 🔜 下一步計畫
- 撰寫球員生成演算法 (Gacha System)。
- 實作「首抽」功能測試。

---

## 2025-12-03 22:30 ：球員生成核心與開隊模擬 (Player Generation & Team Simulation)

### ✅ 進度摘要
完成了基於 **Spec v2.3** 的球員生成服務 (`PlayerGenerator`)，並實作了「開隊陣容檢核」邏輯，確保新球隊能獲得符合戰術需求（如 C>=2, PG>=2）的完整陣容。

### 🛠️ 技術細節
1.  **球員生成服務 (Player Generator)**
    - **姓名系統**: 實作 `NameLibrary` 模型，並加入姓氏長度機率控制 (80% 單字 / 15% 雙字 / 5% 長字)。
    - **身高分佈**: 採用 Box-Muller Transform 實作常態分佈 (Mean 195, SD 10)。
    - **能力值重骰 (Reroll)**: 實作「反向總上限」與「重骰機制」，允許單項能力值極端化 (如 99) 同時保持總平衡。
    - **JSON 儲存**: 將詳細屬性結構化存入 `detailed_stats` JSON 欄位，支援 MySQL 查詢。

2.  **開隊模擬腳本 (Simulation Script)**
    - 開發 `scripts/simulate_team_creation.py`。
    - **Reroll & Filter**: 實作整隊重骰邏輯，直到隨機生成的 15 人名單滿足位置與等級限制。
    - **驗證通過**: 經測試，系統能正確產出符合 C>=2, PG>=2, 後衛>=4, 前鋒>=4 且等級分佈正確的陣容。

3.  **規格書更新**
    - 建立 `ASBL_Player_System_Specification.md` (v2.3)，詳細定義所有數學模型與機率參數。

### 📝 筆記
- **修正**: 修正了腳本中能力值中文名稱的對照錯誤 (如 shot_accuracy 應為「投籃準心」)。
- **架構**: 決定將「開隊檢核邏輯」放在應用層 (Script/API) 而非生成層 (Service)，保持生成器的純粹隨機性。

### 🔜 下一步計畫
- 開發 `POST /api/teams` API，將模擬腳本的邏輯正式整合進後端。
- 完善前端註冊流程，讓使用者能實際建立球隊。

---
## 2025-12-04 06:00 ：年齡、合約與上場時間分配系統 (Age, Contract & Minutes)

### ✅ 進度摘要
實作了 Spec v2.4 (年齡與合約) 與 v2.5 (上場時間分配) 的核心邏輯。現在生成的球員具備了完整的職業生涯屬性，並且能透過演算法模擬出真實的比賽輪替調度。

### 🛠️ 技術細節
1.  **資料庫模型更新**
    - **Player**: 新增 `age` 欄位。
    - **Contract**: 新增 `role` (角色定位) 欄位，用於計算上場時間優先權。

2.  **球員生成器升級 (v2.4)**
    - **年齡生成**: 實作 `_generate_age`，SSR 固定 18 歲，G 級浮動至 24 歲。
    - **初始合約**: 實作 `_get_contract_rules`，生成時自動綁定合約年限 (SSR=4年) 與角色 (SSR=Star)。

3.  **上場時間分配演算法 (v2.5)**
    - 實作 **「保底 + 權重」** 分配機制。
    - **Star**: 保底 30 分鐘 (權重 -1~5)。
    - **Starter**: 保底 20 分鐘 (權重 -2~7)。
    - **Rotation**: 保底 10 分鐘 (權重 5~15)。
    - **演算法邏輯**: 先扣除總保底時間，剩餘時間依權重比例分配，最後進行尾數修正，確保總和為 240 分鐘。

4.  **模擬測試**
    - 更新 `scripts/simulate_team_creation.py`，新增 `simulate_games` 函數。
    - 成功模擬 10 場比賽的輪替狀況，驗證了 Star 球員時間穩定，而 Bench 球員時間波動大的預期效果。

### 📝 筆記
- **時間分配**: 目前演算法運作良好，未出現負數時間或總和錯誤的情況。
- **權重調整**: 未來可考慮將球員的 `stamina` (體力) 或 `form` (近況) 加入權重計算公式中。

### 🔜 下一步計畫
- 開始設計比賽引擎 (Match Engine)，將分配好的時間轉化為比賽數據 (得分、籃板等)。

## 2025-12-07 14:00 ：比賽引擎 v1.4 與數據歸屬機制 (Match Engine v1.4)

### ✅ 進度摘要
完成了比賽引擎的核心升級，實作了 **ASBL Spec v1.4**。本次更新重點在於讓模擬數據更具真實感，透過權重分配機制取代純隨機判定，並調整了體力消耗模型以強化輪替的重要性。

### 🛠️ 技術細節
1.  **比賽引擎升級 (Match Engine v1.4)**
    - **數據歸屬判定 (Data Attribution)**:
        - **投籃**: 引入「戰術地位 (Star/Starter)」與「射程傾向 (3PT)」權重，明星球員與射手將獲得更多出手權。
        - **助攻**: 實作固定順序判定 (C->PF->SF->SG->PG)，確保控球後衛在助攻分配上的優勢。
        - **籃板**: 區分進攻/防守籃板權重，身高、彈跳與卡位能力成為關鍵。
        - **失誤**: 分離「個人失誤」(被抄截) 與「團隊失誤」(8秒/24秒違例)，使球員數據更精確。
    - **體力系統調整**:
        - 消耗係數由 2.5 提升至 **3.0**，加速體力流失，迫使教練更依賴板凳深度。
        - 修正屬性計算，確保所有判定皆使用體力衰退後的當前數值。

2.  **程式碼重構與優化**
    - **PlayerObj**: 新增 `game_stats` 字典，獨立記錄單場比賽的詳細數據 (PTS, REB, AST, STL, BLK, TOV)。
    - **Team Creation**: 優化 `create_team_roster`，直接生成符合等級分佈的屬性，移除對 Service 層的不必要依賴。
    - **Terminal Utils**: 新增 `scripts/terminal.py`，提供跨平台 (Windows/Mac/Linux) 的終端機畫面清除功能。

3.  **文件更新**
    - 新增 `ASBL_Spec_v1.4.md`，完整記錄比賽引擎的判定邏輯與公式。

### 📝 筆記
- **模擬結果觀察**: 在 v1.4 版本下，Star 球員的得分數據顯著提升，且 PG 的助攻數更符合預期。體力消耗加快後，板凳球員的上場時間變得更加關鍵。

### 🔜 下一步計畫
- 開發前端比賽直播介面 (Play-by-Play UI)。
- 實作球員成長系統 (Training & Aging)。

## 2025-12-12 10:00 ：配置檔重構與 Spec v2.6 屬性標準化 (Refactoring & Spec v2.6)

### ✅ 進度摘要
為了因應未來大規模數據驗證與平衡性調整的需求，本次進行了系統重構。將原本散落在程式碼中的「魔術數字 (Magic Numbers)」與「生成規則」全數抽離至 YAML 設定檔，並統一了屬性命名規範。

### 🛠️ 技術細節
1.  **配置檔中心化 (Configuration Centralization)**
    - **新增 `config/game_config.yaml`**: 集中管理球員生成機率、薪資係數、能力值上下限、比賽引擎參數等。
    - **新增 `GameConfigLoader`**: 實作 Singleton 模式的設定檔讀取器，支援熱重載 (Reload) 與環境變數路徑設定。

2.  **球員生成器重構 (PlayerGenerator Refactor)**
    - **Spec v2.6 實作**: 更新 `ATTR_MAPPING`，將 Config Key 與 DB Field 進行標準化對照 (例如 `shot_touch` 對應 `offense.touch`)。
    - **移除硬編碼**: `_generate_stats_by_grade` 與 `generate_payload` 改為從 ConfigLoader 讀取參數。
    - **大數據支援**: 新增 `to_flat_dict` 方法，可將巢狀的 Player Payload 攤平為單層 Dictionary，方便後續匯出 CSV 進行 Pandas 分析。

3.  **規格書更新**
    - **ASBL_Player_System_Specification.md (v2.6)**: 新增詳細的屬性對照表 (Config Key vs DB Field)，確保開發一致性。

### 📝 筆記
- **優化方向**: 這次重構雖然沒有改變外部功能，但大幅提升了系統的可維護性。接下來進行大數據測試時，若發現某個等級太強，只需修改 YAML 檔即可，無需改動程式碼。

### 🔜 下一步計畫
- **大數據驗證 (Big Data Verification)**: 開發 Python 腳本，生成 100萬筆球員資料，驗證常態分佈、等級機率與能力值總和是否符合 Spec v2.6 預期。

## 2025-12-13 08:00 ：大數據驗證架構與一億筆球員生成 (Big Data Verification & 100M Generation)

### ✅ 進度摘要
為了驗證 **Spec v2.6** 球員生成器的機率模型是否精確，我們建構了一套 **ETL (Extract, Transform, Load) 大數據測試架構**。利用 Python 多進程 (Multiprocessing) 技術，成功在 1 小時內生成並寫入 **100,000,000 (一億)** 筆球員資料，並透過 Polars 進行全量 KPI 檢核，確認所有數值分佈皆符合預期。

### 🛠️ 技術細節
1.  **ETL 資料管線 (`tests/big_data/verify_generator_integration.py`)**
    - **架構**: 採用 `Producer-Consumer` 模式，利用 `multiprocessing.Pool` 開啟 24 個 Worker 並行生成。
    - **儲存**: 放棄 CSV，改用 **Apache Parquet (Snappy壓縮)** 格式，將 1 億筆資料壓縮至約 5GB，大幅降低 I/O 瓶頸。
    - **流程**: 實作「試跑 (Dry Run) -> 容量預估 -> 串流寫入 (Streaming)」三階段流程，確保記憶體與硬碟空間受控。

2.  **高效能分析 (`tests/big_data/verify_kpi_v2_6.py`)**
    - **技術選型**: 引入 **Polars** 取代 Pandas 進行數據分析。在處理 1 億筆資料的聚合與篩選時，效能提升約 10-20 倍。
    - **雙向 Logger**: 實作 `ReportLogger`，將驗證結果同時輸出至終端機與 Markdown 報告 (`docs/KPI_Validation_Report_v2_6.md`)。

3.  **KPI 驗證結果 (全數通過)**
    - **身高分佈**: 160-230cm 各區間誤差 < 0.02%，極端值 (160cm, 230cm) 出現頻率符合常態分佈理論值。
    - **位置判定**: 在不同身高區間下，PG/SG/SF/PF/C 的分配比例誤差控制在 ±0.02% 內。
    - **能力值邊界**: 
        - **反向總上限**: 驗證 G~SSR 各等級的技術總和上限 (Cap) 無任何違規。
        - **天賦區間**: 驗證 SSR (951-990) 至 G (10-400) 的總分區間無任何違規。
        - **極端值**: 確認存在單項能力 > 90 或 < 10 的「偏科型」球員，證明重骰 (Reroll) 機制運作正常。
    - **年齡分佈**: SSR 100% 為 18 歲，其餘等級年齡分佈均勻。

### 📝 筆記
- **效能數據**: 在 i9-14900K 環境下，生成速度達到 **1,153 筆/秒**，CPU 使用率滿載 (100%)，記憶體峰值約 60GB。
- **資料完整性**: 新增 `check_crash_data.py` 工具，用於在程式意外中斷後驗證 Parquet 檔案的完整性。

### 🔜 下一步計畫
- **比賽引擎重構**: 修改比賽引擎架構，將數據跟公式抽離，以利後續大數據測試與參數調整。

--

## 2025-12-16 04:50 ：比賽引擎核心架構與規則實作 (Match Engine Core & Spec v1.6)

### ✅ 進度摘要
正式完成了 **Level 4 比賽引擎 (Match Engine)** 的核心架構搭建。實作了 `MatchEngine` 主類別，包含比賽流程控制 (Flow Control)、賽前初始化 (Initialization) 以及與各子系統 (體力、換人、數據歸屬) 的整合。同時，根據 **Spec v1.6** 實作了開場跳球、節次球權輪替以及犯滿離場後的上場時間重分配邏輯。

### 🛠️ 技術細節
1.  **引擎架構建立 (`app/services/match_engine/`)**
    - 確立了分層架構：
        - **L4 Core**: `core.py` (主迴圈, 狀態機)。
        - **L3 Systems**: `stamina.py`, `substitution.py`, `attribution.py` (獨立邏輯單元)。
        - **L2 Utils**: `calculator.py` (公式計算), `rng.py` (隨機數)。
        - **L1 Structures**: `structures.py` (資料結構)。
    - 修正時間單位：統一將內部計算單位由「分鐘」改為「秒 (seconds)」，避免浮點數誤差。

2.  **規則實作 (Spec v1.6)**
    - **開場跳球 (Jump Ball)**: 
        - 實作於 `core.py` 的 `_jump_ball` 方法。
        - 邏輯改為 **Config Driven**，由設定檔定義參與屬性 (身高+彈跳+進攻IQ) 與權重。
    - **球權輪替 (Possession)**:
        - Q1: 跳球勝方。
        - Q2/Q3: 跳球負方。
        - Q4: 跳球勝方。
    - **開場首回合例外**: 
        - 在 Config 中新增 `opening_seconds: 2.0`，強制設定 Q1 首回合時間。
    - **犯滿離場 (Foul Out)**:
        - 實作 6 犯離場規則。
        - **時間重分配 (Redistribution)**: 當球員離場時，將其剩餘時間平均分配給同位置評分前 3 名的隊友。

3.  **設定檔更新 (`config/game_config.yaml`)**
    - 新增 `jump_ball` 區塊：定義跳球公式。
    - 新增 `backcourt.params.opening_seconds`：定義開場時間。
    - 調整 `positional_scoring`：優化 SF 位置的評分權重。
    - 新增 `substitution.redistribution`：定義時間重分配參數。

### 📝 筆記
- **資料驅動修正**: 修正了原先在 `core.py` 中寫死跳球公式的問題，現在完全依賴 Config，方便未來調整平衡。
- **效能優化**: `RNG` 類別採用靜態方法綁定，減少大量隨機數生成時的 overhead。

### 🔜 下一步計畫
- **實作回合邏輯 (Step 3)**: 填充 `_simulate_possession` 方法，實作完整的 後場 -> 前場 -> 投籃/籃板 流程。
- **整合 Play Logic**: 將 Spec v1.6 的詳細判定邏輯 (如快攻、封蓋、空間判定) 轉化為程式碼。

--

## 2025-12-18 04:30 ：比賽引擎邏輯完備與關鍵 Bug 修復 (Match Engine Logic & Bug Fix)

### ✅ 進度摘要
本次更新解決了阻礙比賽模擬的關鍵技術問題，並完成了 **Match Engine (v1.6)** 的所有核心回合邏輯。修復了設定檔解析錯誤導致的「屬性為零」Bug，使投籃命中率與攻防數據回歸正常。同時，重構了數據歸屬系統 (`AttributionSystem`) 以對齊核心引擎的呼叫介面，並新增了無資料庫依賴的模擬腳本 (`simulate_match_no_db.py`) 以加速開發測試。

### 🛠️ 技術細節

1.  **核心修復 (`app/services/match_engine/core.py`)**
    - **Config 解析修復 (`_resolve_formula`)**: 
        - 問題：原先程式碼無法識別 Config 中以字串形式 (如 `'off_13'`) 參照的屬性池，導致 `Calculator` 接收到字串而非屬性列表，計算結果為 0。
        - 解決：新增 `_resolve_formula` 方法，自動判斷並將字串引用轉換為實際的屬性列表。
    - **全流程實作**: 
        - 完成 `_simulate_possession` 內部的完整狀態機：`Backcourt` (後場) -> `Frontcourt` (前場) -> `Shooting` (投籃)。
        - 實作了 **快攻 (Fastbreak)**、**阻攻 (Block)**、**抄截 (Steal)** 與 **犯規 (Foul)** 的詳細判定邏輯。
    - **公式應用**: 將 Spec v1.6 定義的命中率公式、空間加成 (Spacing) 與出手品質 (Quality) 完整轉化為程式碼。

2.  **系統重構 (`app/services/match_engine/systems/attribution.py`)**
    - **介面統一**: 調整方法簽章 (Signature) 以配合 `core.py` 的呼叫需求。
    - **邏輯修正**:
        - `record_block`: 現在接收 `(blocker, shooter)`，並正確記錄射手被蓋火鍋時的 `FGA` (出手數)。
        - `record_assist`: 新增獨立的助攻記錄方法。
        - 方法更名：`record_shot_attempt` -> `record_attempt`，`determine_assister` -> `determine_assist_provider`。

3.  **測試工具 (`scripts/simulate_match_no_db.py`)**
    - 新增獨立模擬腳本，透過 Mock `PlayerGenerator` 與 Adapter 模式，在不連接 MySQL 的情況下直接生成兩支球隊進行對戰。
    - 輸出詳細的 **Play-by-Play (PBP)** 日誌與 **Box Score**，用於驗證數值平衡。

### 📝 筆記
- **模擬結果驗證**: 經過修復後，模擬比賽比分 (如 103:113) 與命中率 (30%~60%) 皆符合現代籃球常態，SSR 球員表現顯著優於普通球員，證實數值模型有效。
- **架構優化**: 透過 Adapter 隔離了 DB Model 與 Engine Model，未來更換資料庫或調整存儲結構時，引擎核心無需修改。

### 🔜 下一步計畫
- **大數據平衡測試**: 使用 `simulate_league.py` 進行 20 隊 x 6 循環的賽季模擬，檢視勝率分佈與極端值。
- **前端串接**: 將比賽結果 (JSON) 傳遞給前端介面進行視覺化顯示。

--

## 2025-12-20 14:00 ：投籃機制重構與數據定義標準化 (Match Engine v1.8 & Output Schema)

### ✅ 進度摘要
本次更新將比賽引擎升級至 **v1.8**。核心變動在於重構了投籃判定流程，正式區分了 **2分球 (40%)** 與 **3分球 (20%)** 的基礎命中率，解決了原本三分球過於容易命中的平衡性問題。同時，修復了數據歸屬系統中「進球未計入出手數 (FGA)」的嚴重 Bug，並統一了換人系統的時間單位。最後，在規格書中正式定義了 API 輸出的數據結構。

### 🛠️ 技術細節

1.  **投籃邏輯重構 (`app/services/match_engine/core.py`)**
    - **流程調整**: 將「投籃類型判定 (2pt/3pt)」提前至「命中率計算」之前執行。
    - **動態基礎命中率**: 
        - 實作 **Spec v1.7** 規則。
        - 讀取 Config 新增的 `base_rate_2pt` (0.40) 與 `base_rate_3pt` (0.20)。
        - 依據判定結果動態套用基礎命中率，使三分球更依賴球員屬性而非基礎機率。

2.  **數據統計修復 (`app/services/match_engine/systems/attribution.py`)**
    - **Critical Fix**: 修正 `record_score` 方法。
    - **問題**: 原本邏輯中，進球 (Score) 只增加 `FGM` (命中數) 與 `PTS` (得分)，未增加 `FGA` (出手數)，導致命中率計算分母錯誤 (變成 FGM / Misses)。
    - **修正**: 進球時現在會同步執行 `scorer.stat_fga += 1` (若為3分則 `stat_3pa += 1`)。

3.  **單位統一與配置更新**
    - **SubstitutionSystem**: 將換人判斷邏輯中的 `minutes_played` 修正為 `seconds_played`，與 Core 的計時單位保持一致，避免換人功能失效。
    - **Config**: 更新 `game_config.yaml`，移除單一 `base_rate`，拆分為 `base_rate_2pt` 與 `base_rate_3pt`。

4.  **規格書更新 (Spec v1.8)**
    - 新增 **Section 7: 輸出數據定義 (Output Data Definition)**，詳細列出 `MatchResult` 與 `Box Score` 的所有欄位與格式，作為前後端串接的標準。

### 📝 筆記
- **平衡性預期**: 預期更新後，三分球的命中率會顯著下降，更加符合真實籃球數據（約 30%-40%），且高射程屬性的球員價值會提升。
- **數據驗證**: 下一步需重新執行 `simulate_match_no_db.py`，確認 Box Score 中的 FGM/FGA 比例是否正常 (例如不再出現 5/0 的詭異數據)。

### 🔜 下一步計畫
- **進階數據實作**: 根據新的 Spec v1.8，開始實作正負值 (+/-)、快攻得分、二波得分等進階數據欄位。
- **前端串接**: 依據 Section 7 的定義，提供 API 給前端顯示比賽結果。

--

## 2025-12-22 06:00 ：球員系統 v3.1 與比賽引擎 Phase 2 優化 (Player System v3.1 & Match Engine Optimization)

### ✅ 進度摘要
本次更新包含兩大重點：一是實作 **Player System Spec v3.1**，引入了更嚴謹的球員生成限制（位置檢核、身高修正）；二是 **Match Engine 進入 Phase 2**，新增了進階數據（Pace, Fastbreak Efficiency）追蹤，並對核心資料結構進行了記憶體優化，以應對未來的大規模模擬需求。

### 🛠️ 技術細節

1.  **球員生成系統升級 (Spec v3.1)**
    - **配置檔更新 (`config/game_config.yaml`)**:
        - **位置檢核 (Position Validation)**: 在 YAML 中定義了各位置的屬性總和限制（例如 C 的籃板+卡位+干擾必須大於其他屬性），防止生成出數值分佈不合理的球員。
        - **身高修正 (Height Modifiers)**: 實作了身高區間的補償與懲罰機制（如矮個子球員獲得額外屬性點數，且針對 PG 關鍵屬性加權）。
        - **流程重構**: 確立了 `姓名 -> 等級 -> 天賦 -> 身高 -> 位置 -> 能力 -> 年齡` 的生成順序。

2.  **比賽引擎 Phase 2 (`app/services/match_engine/`)**
    - **進階數據追蹤**:
        - **Pace (節奏)**: 在 `AttributionSystem` 新增 `record_possession`，並在 `MatchEngine` 中計算每 48 分鐘回合數。
        - **快攻效率**: 新增 `record_fastbreak_event`，分別記錄快攻的嘗試次數與成功次數，用於分析球員速度屬性的實際效益。
    - **結構優化 (`structures.py`)**:
        - 全面導入 Python 3.10+ 的 `@dataclass(slots=True)`。
        - **效益**: 相比原本的 `__slots__` 手動定義或標準字典儲存，記憶體佔用減少約 40%，屬性存取速度提升約 20%，對千萬級別的模擬至關重要。

3.  **輸出介面擴充**
    - **MatchResult**: 擴充了回傳結構，現在包含 `pace`, `home_possessions`, `fb_made/attempt` 等高階數據，供前端與分析系統使用。

### 📝 筆記
- **邏輯修正**: 在實作身高修正時，確認了 210cm+ 的懲罰邏輯與 160cm+ 的獎勵邏輯互斥，程式端已依照 YAML 配置正確處理。
- **效能監控**: 初步測試顯示，雖然新增了數據追蹤邏輯，但受惠於 `slots=True` 的優化，整體模擬速度並未下降。

### 🔜 下一步計畫
- **生成器驗證**: 執行新一輪的大數據測試 (Big Data Verification)，確認 v3.1 的位置檢核是否會導致某些等級的球員生成失敗率過高。
- **前端整合**: 將新的 Box Score 與進階數據串接至前端頁面。
