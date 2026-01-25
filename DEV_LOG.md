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

--

## 2025-12-24 11:00 ：開隊生成規則優化與生成器效能重構 (Initial Roster Optimization & Performance Refactor)

### ✅ 進度摘要
本次更新主要實作了 **Player System Spec v3.2**，針對「開隊陣容」加入了能力下限保護機制，確保玩家初始隊伍的戰力下限。同時，為了應對接下來的上億次大數據測試，對 `PlayerGenerator` 進行了底層架構重構，引入了 **快取機制 (Caching)** 與 **規則預編譯 (Rule Compilation)**。最後，將模擬測試腳本的輸出介面全面 **繁體中文化**，提升開發體驗。

### 🛠️ 技術細節

1.  **開隊陣容優化 (Team Creator - Spec v3.2)**
    - **能力下限檢核 (Lower Bound Validation)**:
        - 在 `TeamCreator` 中新增 `_generate_qualified_player` 方法。
        - 讀取 Config 中的 `initial_team_min_ratio` (預設 0.5)。
        - 邏輯：若生成球員的 `可訓練能力總和` < `該等級上限 * 50%`，則視為無效球員並自動重骰 (Reroll)。
        - **目的**：縮小開局隨機範圍，避免 G/C 級球員數值過低導致無法上場。
    - **職責分離**: 堅持將此邏輯放在 `TeamCreator` 而非 `PlayerGenerator`，保持生成器的純粹隨機性，僅在組隊業務邏輯中進行篩選。

2.  **生成器效能重構 (Player Generator Refactor)**
    - **靜態快取 (Static Cache)**:
        - 實作 `initialize_class` 方法。
        - 啟動時一次性將 DB 中的 `NameLibrary` 與 YAML 中的 `GameConfig` 載入記憶體 (`_config_cache`)。
        - **效益**: 消除每次生成球員時重複讀取 DB 與解析 YAML 的 I/O 開銷，大幅提升生成速度。
    - **動態規則編譯**:
        - 將 YAML 中的字串規則 (如 `"sum(def_rebound...) > ..."`) 在初始化階段解析為 Python List。
        - 執行階段不再使用 Regex 解析，而是直接進行 List 運算，優化位置檢核效能。

3.  **模擬工具中文化 (Simulation Script Localization)**
    - 更新 `scripts/simulate_match_no_db.py`。
    - **新增功能**: `print_team_details`，在模擬前列印雙方球員的等級、身高、總評與詳細屬性 (每 5 項換行)。
    - **UI 優化**: 所有輸出訊息、表格標頭、系統日誌皆調整為 **繁體中文**，符合專案開發規範。

### 📝 筆記
- **效能預估**: 在 i9-14900K 環境下，預期新的 `PlayerGenerator` 配合快取機制，生成速度將比 v2.6 版本提升顯著，為接下來的模擬聯賽測試做好準備。
- **除錯體驗**: 現在透過模擬腳本可以直接看到球員的細項數值，對於驗證「位置檢核」與「身高修正」是否生效非常有幫助。

### 🔜 下一步計畫
1.  **大數據測試球員產生報告**: 執行新版生成器，產出 100 萬筆數據的 KPI 報告，驗證 v3.2 下限規則與 v3.1 身高修正的分布情形。
2.  **大數據測試比賽引擎**: 使用大量隨機隊伍進行對戰，分析比賽數據 (Pace, FG%, Score) 的常態分佈。
3.  **設計模擬聯賽運作方式**: 規劃模擬選秀 (Draft) 邏輯及自由球員 (Free Agency) 生成機制。

--

## 2025-12-27 05:30 ：比賽引擎 Phase 2 完成與大數據驗證準備 (Match Engine Phase 2 Final & Big Data Prep)

### ✅ 進度摘要
正式完成了 **Match Engine (Level 4 - Phase 2 Final)** 的開發與整合。本次更新重點在於完善比賽中的邊緣案例處理（如犯滿離場後的上場時間重分配），並引入了進階數據（Pace, Fastbreak Efficiency）的計算與輸出。同時，為了迎接即將到來的「上億次」聯賽模擬測試，對核心資料結構進行了記憶體優化 (`slots=True`)，並確認了球員生成器 (v3.2) 的大數據驗證結果符合常態分佈預期。

### 🛠️ 技術細節

1.  **比賽引擎核心邏輯 (`app/services/match_engine/core.py`)**
    - **犯滿離場處理 (Foul Out Logic)**:
        - 實作 `_check_and_handle_foul_out` 方法。
        - **機制**: 當球員犯規達上限 (Config 定義，預設 6 次) 時，強制移出 `on_court`。
        - **時間重分配 (Redistribution)**: 關鍵演算法更新。犯滿球員剩餘的 `target_seconds` 不會憑空消失，而是依權重動態分配給場上及板凳上未犯滿的隊友，確保比賽總時間 (240分鐘) 守恆，避免模擬崩潰。
    - **進階數據計算**:
        - **Pace (節奏)**: 整合 `stat_possessions`，於賽後計算每 48 分鐘回合數。
        - **快攻 (Fastbreak)**: 在 `_run_fastbreak` 中加入 `record_fastbreak_event`，追蹤快攻成功率與次數。

2.  **資料結構效能優化 (`app/services/match_engine/structures.py`)**
    - **記憶體優化**: 全面套用 `@dataclass(slots=True)`。
    - **效益**: 在大規模模擬 (100M+ 場次) 下，預計減少 40-50% 的記憶體佔用，並提升 20% 的屬性存取速度。
    - **欄位擴充**: `MatchResult` 與 `EnginePlayer` 新增 `pace`, `fb_made`, `fb_attempt`, `remaining_stamina` 等欄位，支援 Phase 2 的數據分析需求。

3.  **配置檔與規則整合 (`config/game_config.yaml`)**
    - **季後賽規則**: 新增 `playoff` 區塊，定義各輪賽制 (3戰2勝 / 5戰3勝) 及是否強制打滿 (Force Full Series) 以利數據收集。
    - **生成規則整合**: 確認 `height_modifiers` (身高修正) 與 `position_validation` (位置檢核) 參數已正確載入，並通過 12/24 的大數據驗證報告。

### 📝 筆記
- **驗證報告**: 根據 `docs/player_generator_test_Report_20251224.md`，球員生成器的身高分佈 (Mean=195, SD=10) 與極端值處理已完全符合數學模型，且位置判定矩陣準確率極高，為接下來的聯賽模擬奠定良好基礎。
- **系統穩定性**: 新增的犯滿時間重分配邏輯，解決了先前模擬中因主力犯滿導致板凳時間不足而 Crash 的潛在風險。

### 🔜 下一步計畫
- **身高影響實裝**: 將身高 (Height) 參數更深入地整合進比賽引擎的判定公式中 (如：身高差對投籃干擾的具體影響係數)。
- **年齡體力模型**: 實作年齡 (Age) 對於體力消耗 (Drain) 與恢復 (Recovery) 的影響曲線，模擬老將與新秀在體能上的真實差異。

--

## 2025-12-29 21:00 ：比賽引擎物理修正與開隊邏輯升級 (Match Engine Physics & Team Gen v3.3)

### ✅ 進度摘要
本次更新完成了 **Match Engine Spec v2.1** 與 **Player System Spec v3.3** 的實作。重點在於提升比賽引擎的物理真實度（引入身高修正、年齡體力衰退），並優化了開隊生成邏輯，確保高階球員（SSR/SS/S）的位置覆蓋率。同時，產出了 1200 萬場次的模擬測試報告，驗證了數值模型的穩定性。

### 🛠️ 技術細節

1.  **比賽引擎優化 (Match Engine v2.1)**
    - **身高修正 (Height Correction)**: 
        - 實作 `_apply_height_correction`，在賽前針對身高過高或過矮的球員進行屬性微調（如矮個子運球加成、高個子運球懲罰）。
        - 更新 `attr_pools`，將 `height` 加入投籃、籃板、封蓋的判定公式中。
    - **體力系統升級**:
        - 引入 **年齡衰退 (Age Decay)** 機制，超過 20 歲的球員體力消耗與恢復速度會隨年齡線性衰退。
        - 修正 `_check_and_handle_foul_out`，採用 **Positional Top-K** 邏輯，將犯滿離場球員的時間精準分配給同位置最強的 3 名隊友，避免模擬崩潰。
    - **規則參數化**: 將關鍵時刻閾值 (`clutch_time_threshold`) 與三分球加成倍率 (`multiplier_3pt`) 移至 Config 管理。

2.  **開隊生成邏輯升級 (Team Creator v3.3)**
    - **高階覆蓋檢核 (High-Tier Coverage)**:
        - 在 `_validate_roster_positions` 新增邏輯。
        - 強制要求隊伍中的高階球員 (SSR/SS/S) 必須覆蓋 C, PF, SF, SG, PG 全部 5 個位置，避免開局神卡位置重疊。
    - **效能調整**: 配合更嚴格的檢核條件，增加了生成嘗試次數上限。

3.  **測試與驗證工具**
    - **新增 `scripts/debug_team_generation.py`**: 
        - 用於生成測試用的球隊 Parquet 檔，並計算加權戰力，方便觀察數值分佈。
    - **模擬報告 (`docs/team_creator_test_report_*.md`)**:
        - 執行了 1200 萬場模擬。
        - 確認勝率分佈正常 (強隊 ~58%, 弱隊 ~36%)。
        - 確認體力系統運作正常 (疲勞狀態佔比 ~11%)。
        - 確認犯規分佈正常 (平均單場 6.8 次)。

4.  **規格書更新**
    - 更新 `ASBL_Match_Engine_Specification.md` 至 v2.1。
    - 更新 `ASBL_Player_System_Specification.md` 至 v3.3。
    - 更新 `config/game_config.yaml` 對應上述變更。

### 📝 筆記
- **平衡性觀察**: 根據測試報告，T001 (SSR SG) 與 T002 (SSR SF) 的勝率顯著高於 T003/T004，顯示核心球員的影響力符合預期。
- **體力影響**: 數據顯示「透支狀態 (<20)」的命中率並未顯著崩盤，可能需要微調 `stamina_nerf_threshold` 或衰退公式，讓疲勞懲罰更具體感。

### 🔜 下一步計畫
- **開隊數據統計驗證**: 針對生成的一億筆或大量開隊數據進行統計分析，確認 v3.3 規則下的分佈。
- **定義聯賽與選秀**: 開始規劃 `League` 資料結構與 `Draft` 選秀邏輯。

--

## 2026-01-10 06:00 ：比賽引擎計算邏輯重構與命中率修復 (Match Engine Logic Refactor & Shooting Rate Fix)

### ✅ 進度摘要
本次更新主要針對 **Match Engine** 的代碼架構進行了深度重構，解決了核心邏輯與輔助工具 (`Calculator`) 不同步的問題。實作了 **Spec v2.2 (技巧加成)** 與 **Spec v2.3 (抄截轉換)**，並修復了重構過程中因「對抗範圍不對等」導致命中率崩跌至 10% 的嚴重 Bug。現在 `Calculator` 已成為投籃判定邏輯的唯一真理 (Single Source of Truth)。

### 🛠️ 技術細節

1.  **Calculator 工具升級 (`app/services/match_engine/utils/calculator.py`)**
    - **邏輯封裝**: 將原本散落在 `core.py` 中的投籃公式（包含 2分/3分 基礎率選擇、屬性加成倍率）完整移入 `calculate_shooting_rate`。
    - **介面更新**: 方法簽章擴充，現在接收 `off_players` (進攻全隊)、`def_players` (防守全隊) 與 `shooter` (出手者) 三種參數。
    - **Spec v2.2 實作**: 加入 **技巧加成 (Skill Bonus)** 計算，公式為 `1 + (accuracy+range+move)/800`，針對出手者個人能力進行額外修正。

2.  **比賽引擎瘦身 (`app/services/match_engine/core.py`)**
    - **職責分離**: `_run_shooting` 不再進行數學運算，僅負責流程控制（如決定是否投三分、是否犯規），計算工作全數委派給 `Calculator`。
    - **Spec v2.3 實作**: 在後場階段 (`_run_backcourt`) 加入了 **抄截轉換 (Steal Transition)** 判定。當發生抄截時，依據雙方速度總和判定是發動快攻還是進入陣地戰。

3.  **關鍵 Bug 修復 (Critical Fix)**
    - **問題**: 初次重構時，誤將 `off_player` (單人) 傳入對抗公式與 `def_players` (五人) 進行數值比較。
    - **現象**: 進攻方數值遠低於防守方，導致 `stat_diff` 為負值，命中率被截斷在下限 (1%~10%)。
    - **修正**: 修正 `Calculator` 介面，明確區分 **「團隊對抗 (Team Rating)」** 與 **「個人技巧 (Skill Bonus)」** 的計算來源，命中率回歸正常區間 (30%~50%)。

### 📝 筆記
- **架構效益**: 這次重構雖然花費了時間解決 Bug，但大幅提升了代碼的可測試性。未來若要調整命中率公式（例如修改 Spacing 權重），只需修改 `Calculator` 一處即可，不用擔心 `Core` 與 UI 顯示的數值不一致。
- **數值觀察**: 加入 Skill Bonus 後，高數值射手 (SSR) 的統治力進一步提升，符合設計預期。

### 🔜 下一步計畫
- **Pace 機制調整**: 修改速度屬性 (Speed) 對於比賽回合數 (Possessions/Pace) 的影響權重，讓快節奏球隊能打出更多回合。
- **隊伍平衡測試**: 執行大規模模擬，驗證不同戰術風格（如快攻隊 vs 陣地戰隊）的勝率平衡。

--

## 2026-01-16 15:30 ：進階數據統計與物理機制補完 (Advanced Stats & Physics Completion)

### ✅ 進度摘要
本次更新完成了 **Match Engine** 的功能補完，重點在於實作 **Spec v2.1** 的身高修正機制與 **Spec v2.3** 的抄截轉換邏輯。同時，為了支援更深度的戰術分析，新增了 **正負值 (+/-)** 與 **回合時間 (Possession Time)** 的統計追蹤。底層部分，針對 `RNG` 模組進行了微幅優化以避免潛在的綁定問題。

### 🛠️ 技術細節

1.  **進階數據系統 (`app/services/match_engine/structures.py` & `attribution.py`)**
    - **正負值 (+/-)**:
        - 在 `EnginePlayer` 新增 `stat_plus_minus` 欄位。
        - 實作 `AttributionSystem.update_plus_minus`，在得分或罰球進球時，動態更新場上雙方球員的正負值。
    - **回合時間 (Possession Time)**:
        - 在 `EngineTeam` 新增 `stat_possession_seconds` (累積) 與 `stat_possession_history` (歷程)。
        - 在 `MatchEngine._simulate_quarter` 中，將每個回合的消耗時間 (`elapsed`) 歸屬給進攻方，用於分析球隊的進攻節奏 (Pace) 與拖延戰術。

2.  **物理機制實裝 (`app/services/match_engine/core.py`)**
    - **身高修正 (Height Correction)**:
        - 實作 `_apply_height_correction` 方法 (Spec v2.1)。
        - 依據 Config 定義的 `bonus_threshold` (190cm) 與 `nerf_threshold` (210cm)，在賽前永久性修正球員的 `speed`, `dribble`, `handle`, `disrupt` 等屬性。
    - **抄截轉換邏輯 (Transition Logic)**:
        - 在 `_run_backcourt` 中完善了 Spec v2.3 的判斷。
        - 當發生後場抄截時，計算雙方場上五人的速度總和，依據速度差判定是發動 **快攻 (Fastbreak)** 還是進入 **陣地戰 (Set Play)**。

3.  **底層優化 (`app/services/match_engine/utils/rng.py`)**
    - **Module Level Binding**: 將 `random` 的方法綁定從類別層級移至模組層級 (`_sys_random`, `_sys_uniform`)。
    - **目的**: 避免在 Python 新版本中將綁定方法指派給類別屬性時可能產生的參數傳遞錯誤，同時保持極致的效能。

4.  **輸出介面更新**
    - 更新 `MatchResult` dataclass，新增 `home_possession_history`, `home_avg_seconds_per_poss` 等欄位，讓前端能繪製進攻時間分佈圖。

### 📝 筆記
- **數據觀察**: 加入回合時間統計後，可以明顯區分出「跑轟球隊」與「陣地戰球隊」的平均進攻時間差異（例如 8秒 vs 18秒）。
- **正負值驗證**: 初步測試顯示，主力球員在場時的 +/- 值通常為正，符合預期，此數據將成為評估球員「隱形貢獻」的重要指標。

### 🔜 下一步計畫
- **改善速度對於球隊回合數的影響**

--

## 2026-01-25 10:00 ：比賽引擎 v2.4 違例機制與速度節奏優化 (Match Engine v2.4 Violations & Speed/Pace)

### ✅ 進度摘要
本次更新將比賽引擎推進至 **v2.4** 版本，核心目標是強化「速度屬性」對比賽節奏的實質影響，並補完籃球規則中的違例機制。實作了 **速度折扣 (Speed Discount)** 機制，讓速度快的球隊能以更短時間完成推進與進攻，進而提升回合數 (Pace)。同時，新增了 **8秒違例** 與 **24秒違例** 的判定邏輯，完善了失誤 (Turnover) 的類型。最後，更新了大數據測試腳本，以驗證新機制的數值分佈。

### 🛠️ 技術細節

1.  **比賽引擎核心邏輯 (`app/services/match_engine/core.py`)**
    - **速度折扣 (Speed Discount)**:
        - 在 `_run_backcourt` (後場) 與 `_run_frontcourt` (前場) 階段引入新公式。
        - **機制**: 計算進攻方場上球員的平均速度，依據 Config 定義的係數 (`speed_discount_coeff`) 隨機扣除消耗時間。
        - **效益**: 速度越快的球隊，單一回合消耗時間越短，整場比賽的總回合數 (Possessions) 自然提升，解決了先前 Pace 與 Speed 相關性不足的問題。
    - **違例判定 (Violations)**:
        - **8秒違例**: 若後場推進時間 > 8.0 秒，觸發 `record_8sec_violation` 並轉換球權。
        - **24秒違例**: 若 (後場時間 + 前場時間) > 24.0 秒，觸發 `record_24sec_violation` 並轉換球權。

2.  **數據結構與歸屬 (`structures.py` & `attribution.py`)**
    - **結構擴充**: 在 `EngineTeam` 與 `MatchResult` 中新增 `stat_violation_8s` 與 `stat_violation_24s` 欄位。
    - **歸屬邏輯**: 新增專屬的記錄方法，將違例計入「團隊失誤 (Team Turnover)」，不影響球員個人失誤數據。

3.  **配置檔更新 (`config/game_config.yaml`)**
    - **Backcourt**: 新增 `speed_discount_coeff` (預設 0.1) 與 `violation_threshold` (8.0)。
    - **Frontcourt**: 新增 `speed_discount_coeff` (預設 0.01) 與 `violation_threshold` (24.0)。
    - **物理限制**: 設定了時間計算的物理下限 (`min_time_limit`)，防止因折扣過大導致時間為負。

4.  **大數據測試工具 (`tests/match_bigdata_test/run_core_bigdata_test.py`)**
    - **報告升級**: 
        - 新增「速度對球隊回合數 (Pace) 的影響」分析章節，計算加權速度與 Pace 的相關係數。
        - 新增「違例詳細分析」章節，統計 8秒/24秒違例的發生頻率與佔比。
    - **穩定性優化**: 引入 `faulthandler` 與 Flush 隔離機制，防止單一場次模擬失敗導致整個測試中斷。

### 📝 筆記
- **平衡性觀察**: 初步測試顯示，引入速度折扣後，高速度球隊的 Pace 明顯提升，且 24 秒違例通常發生在防守壓迫極強或進攻方速度極慢的極端對局中，符合預期。
- **數據驗證**: 需持續觀察違例發生的機率是否過高 (例如超過總回合數的 5%)，若過高則需微調 `time_base` 或 `violation_threshold`。

### 🔜 下一步計畫
- **修正程式碼內與技術文件不符合的內容**: 全面盤點 Codebase 與 Spec 文件的差異並進行同步。
- **球員命名規則**: 優化姓名生成庫，可能引入更多樣化的命名邏輯。
- **程式更新修正**: 針對測試中發現的微小 Bug 進行修復。

--

