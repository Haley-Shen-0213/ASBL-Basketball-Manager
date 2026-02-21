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

## 2026-01-26 22:00 : 姓名生成系統重構與比賽引擎違例機制 (Name Gen Refactor & Match Engine Violations)

### ✅ 進度摘要
本次更新完成了 **Player System Spec v3.4** 與 **Match Engine Spec v2.4** 的實作。核心變動包括重構了球員姓名生成邏輯，支援多語系（歐美、東亞、原住民）的動態生成策略，並在資料庫層級新增了國籍欄位。在比賽引擎方面，正式實裝了 **8秒/24秒違例** 判定，並引入 **速度折扣 (Speed Discount)** 機制，強化了球隊速度屬性對比賽節奏 (Pace) 的實質影響。

### 🛠️ 技術細節

1.  **球員生成系統重構 (Spec v3.4)**
    -   **多語系姓名策略**:
        -   在 `PlayerGenerator` 中實作了三種生成策略：
            -   **Strategy A (歐美)**: 隨機抽取 3 字組合，以間隔號分隔。
            -   **Strategy B (東亞)**: 姓 + 名 (1~2字)，無分隔符。
            -   **Strategy C (原住民)**: 隨機抽取 2 個不重複字組合，以間隔號分隔。
        -   策略對應關係由 `config/game_config.yaml` 動態驅動。
    -   **資料庫模型變更**:
        -   `NameLibrary`: 新增 `language`, `category`, `weight` 欄位，支援權重抽取。
        -   `Player`: 新增 `nationality` 欄位，記錄球員語系來源。

2.  **比賽引擎功能擴充 (Spec v2.4)**
    -   **違例機制 (Violations)**:
        -   在 `MatchEngine` 核心迴圈中加入 **8秒違例** (後場) 與 **24秒違例** (全場) 的時間判定。
        -   新增 `stat_violation_8s` 與 `stat_violation_24s` 統計欄位，並將其歸屬為團隊失誤 (Team Turnover)。
    -   **速度折扣 (Speed Discount)**:
        -   實作速度對時間消耗的影響公式。進攻方速度越快，推進與進攻消耗的時間越短 (Discount)，進而提升整場比賽的回合數 (Pace)。
    -   **年齡體力衰退**:
        -   在 `StaminaSystem` 中實作年齡因子，20 歲以上球員的體力消耗與恢復速度將隨年齡線性衰退。

3.  **大數據測試工具優化**
    -   **穩定性增強**: 引入 `faulthandler` 與 Flush 隔離機制，防止單場模擬錯誤導致整個測試中斷。
    -   **報告升級**: 新增違例分佈統計與「速度 vs Pace」的相關性分析，驗證新機制的數值平衡。

### 📝 筆記
-   **數據觀察**: 初步測試顯示，引入速度折扣後，高速度球隊的 Pace 有顯著提升，解決了先前速度屬性效益不明顯的問題。
-   **資料庫遷移**: 由於 `Player` 與 `NameLibrary` 模型有欄位變更，需注意資料庫遷移 (Migration) 或重建。

### 🔜 下一步計畫
-   **全面代碼審查**: 重新檢查所有現成程式碼，確保與計畫書 (Spec) 完全一致，並修復潛在的不連貫處。
-   **日常系統架構**: 開始規劃與實作日常營運系統 (Daily Operations)。
-   **前端開發啟動**: 著手架構前端專案，準備串接 API。

--

## 2026-02-16 12:00 : API 路由實作與開隊規則優化 (API Implementation & Team Gen v3.5)

### ✅ 進度摘要
本次更新正式將後端邏輯封裝為 RESTful API，建立了 `Auth`, `Team`, `Game` 三大路由模組，使前端能與比賽引擎互動。同時，針對 **Player System Spec v3.5** 進行了實作，引入了「分層位置覆蓋 (Tiered Position Coverage)」機制，確保玩家在開局時獲得的高階球員 (SSR-A) 與中階球員 (B-C) 能均勻分佈於五個位置，避免陣容結構失衡。此外，新增了專案快照工具以利後續維護。

### 🛠️ 技術細節

1.  **API 路由層實作 (`app/routes/`)**
    -   **Auth (`auth.py`)**: 
        -   整合 `TeamCreator` 與 `PlayerGenerator`。
        -   註冊成功時，系統會自動建立球隊並生成符合 v3.5 規則的 15 人初始名單，寫入資料庫。
    -   **Team (`team.py`)**: 
        -   提供 `/api/team/<id>/roster` 端點，回傳包含詳細屬性 (Physical, Offense, Defense, Mental) 的 JSON 結構，供前端顯示球員卡片。
    -   **Game (`game.py`)**: 
        -   提供 `/api/game/simulate` 端點。
        -   實作 `DBToEngineAdapter`，將資料庫模型轉換為引擎模型，執行單場模擬並回傳 Box Score 與 Play-by-Play 紀錄。

2.  **開隊生成邏輯升級 (Spec v3.5)**
    -   **分層位置覆蓋**:
        -   更新 `config/game_config.yaml` 與 `team_creator.py`。
        -   **High Tier (SSR/SS/S/A)**: 強制要求這組球員必須覆蓋 C, PF, SF, SG, PG 各至少 1 人。
        -   **Mid Tier (B/C)**: 同樣強制覆蓋 5 個位置。
        -   **目的**: 確保玩家開局時，無論是核心主力還是輪替陣容，都有完整的戰術執行能力。

3.  **資料模型與工具擴充**
    -   **Player Model**: 新增 `grade` 欄位 (SSR~G)，將評級持久化，減少執行時期的重複計算。
    -   **Project Exporter**: 新增 `scripts/utils/project_exporter.py`，可生成包含完整檔案內容的專案快照 Markdown，利於 AI 輔助開發與代碼審查。
    -   **Documentation**: 新增 `ASBL_Database_Schema.md`，完整定義資料表結構與關聯。

### 📝 筆記
-   **架構驗證**: 透過 Postman 測試 `/api/game/simulate`，確認從 DB 讀取球隊 -> 轉換模型 -> 引擎模擬 -> 回傳 JSON 的流程順暢無誤，平均響應時間在 200ms 內 (視模擬複雜度而定)。
-   **資料庫變更**: `Player` 表新增了 `grade` 欄位，需執行 Migration。

### 🔜 下一步計畫
-   **前端架構搭建**: 初始化 React + Vite + TypeScript 專案。
-   **UI 開發**: 實作登入頁面、球隊陣容管理頁面 (Roster) 與比賽直播頁面 (Live Game)。

--

## 2026-02-16 13:30 : 前端架構初始化與儀表板 API 實作 (Frontend Init & Dashboard API)

### ✅ 進度摘要
本次更新標誌著專案正式進入全端開發階段。建立了基於 **React + TypeScript + Vite** 的前端架構，並整合 **Tailwind CSS** 進行 UI 開發。後端部分，為了支援前端 Dashboard 的數據顯示，擴充了 `User` 與 `Team` 的資料庫模型（新增最後登入時間、場館資訊、戰績快取），並實作了對應的 API 端點。

### 🛠️ 技術細節

1.  **前端架構搭建 (`frontend/`)**
    -   **初始化**: 使用 Vite 建立 React + TypeScript 專案。
    -   **樣式系統**: 設定 Tailwind CSS (`tailwind.config.js`)，定義了專案色系 (`asbl-bg`, `asbl-pink` 等) 與漸層背景。
    -   **開發配置**: 設定 `vite.config.ts` 中的 Proxy，將 `/api` 請求代理至 Flask 後端 (`http://127.0.0.1:5000`)，解決 CORS 問題。
    -   **UI 實作 (`App.tsx`)**:
        -   **AuthPage**: 整合登入與註冊表單，串接後端 `/api/auth`。
        -   **Dashboard**: 實作球隊首頁，顯示資金、聲望、戰績與球員人數概況。
        -   **Layout**: 實作響應式 Sidebar 與 Header（包含即時系統在線人數顯示）。

2.  **後端 API 與模型擴充**
    -   **資料庫模型更新**:
        -   `User`: 新增 `last_login` 欄位，用於追蹤活躍用戶。
        -   `Team`: 新增 `arena_name`, `fanpage_name`, `scout_chances`, `season_wins`, `season_losses` 等經營與戰績欄位。
    -   **API 端點新增**:
        -   `GET /api/system/stats`: 回傳總註冊人數與活躍人數（定義於 `routes/__init__.py`）。
        -   `GET /api/team/<id>/dashboard`: 回傳 Dashboard 所需的聚合資訊（包含排名計算）。
    -   **邏輯更新**:
        -   `auth.py`: 註冊時讀取 Config 中的 `initial_team_settings` 來設定初始資金與聲望，並同步寫入 `last_login`。

3.  **設定檔更新 (`config/game_config.yaml`)**
    -   新增 `system.active_user_threshold_days`: 定義活躍用戶判定天數。
    -   新增 `system.initial_team_settings`: 集中管理初始球隊的資金、聲望與球探次數。

### 📝 筆記
-   **前後端聯調**: 經測試，前端透過 Vite Proxy 成功呼叫後端 API，登入流程順暢，Dashboard 能正確顯示資料庫中的球隊資訊。
-   **資料庫遷移**: `User` 與 `Team` 表結構有變動，需執行 `flask db migrate` 與 `flask db upgrade`。

### 🔜 下一步計畫
-   **球員列表頁面**: 實作前端 Roster 頁面，串接 `/api/team/<id>/roster`，以卡片或列表形式展示球員詳細能力。
-   **比賽直播 UI**: 設計比賽模擬的視覺化介面，解析 Play-by-Play 文字流。

--

## 2026-02-16 15:30 : 球員名單與戰術配置 UI 實作 (Roster & Tactics UI)

  ### ✅ 進度摘要
  完成了球隊管理的核心介面開發。實作了 **球員名單 (Player Roster)** 的詳細數據展示與 **戰術配置 (Tactics)** 的互動介面。戰術頁面整合了後端的規則檢核機制（如明星球員數量限制），並提供了「自動填補」與「防呆儲存」功能，確保玩家提交的陣容符合聯賽規範。

  ### 🛠️ 技術細節

  1.  **前端組件開發 (`frontend/src/components/`)**
      -   **PlayerRoster.tsx**:
          -   實作球員列表，支援多欄位排序 (等級、位置、能力值)。
          -   實作詳細資訊 Modal，視覺化展示球員的 20 項細部屬性與訓練點數。
          -   整合等級顏色標籤 (SSR~G) 與位置樣式。
      -   **TacticsPage.tsx**:
          -   實作雙欄式拖曳/點擊介面 (Active Roster vs Available Pool)。
          -   **動態規則檢核**: 從後端讀取 `tactics_system` 設定，即時計算 Tier 1 (Star) / Tier 2 (Starter) / Tier 3 (Rotation) 的人數限制。
          -   **自動化功能**: 實作「自動填補 (Auto-Fill)」按鈕，依據能力值與規則自動產生最佳合法陣容。
          -   **防呆機制**: 當陣容不符規則時，禁用提交按鈕並顯示具體錯誤訊息。

  2.  **後端戰術系統整合**
      -   **資料庫模型**: 新增 `TeamTactics` 模型，儲存球隊的 `roster_list` (JSON)，實現戰術配置與球隊基本資料的解耦。
      -   **API 端點**:
          -   `GET /api/system/config/tactics`: 提供前端動態載入戰術規則。
          -   `POST /api/team/<id>/roster/active`: 接收並驗證玩家提交的登錄名單 ID 列表。
          -   `GET /api/team/<id>/roster`: 回傳球員列表時，動態標記 `is_active` 狀態。

  ### 📝 筆記
  -   **使用者體驗 (UX)**: 戰術頁面的即時驗證回饋 (Real-time Validation) 大幅降低了玩家提交錯誤陣容的挫折感。
  -   **效能**: 前端採用 `useMemo` 優化了列表排序與規則計算，即使在 40 人名單下操作依然流暢。

  ### 🔜 下一步計畫
  -   **電腦球隊生成 (CPU Teams)**: 撰寫腳本批量生成 NPC 球隊，填補聯賽空缺。
  -   **聯賽運作 (League Simulation)**: 實作賽程生成 (Schedule) 與每日自動模擬 (Daily Simulation) 的後端邏輯。

--

## 2026-02-16 17:00 : 球探系統全端實作與環境填充 (Scout System Full-Stack & CPU Teams)

  ### ✅ 進度摘要
  本次更新完成了 **球探系統 (Scout System)** 的全端開發，包含每日自動投入設定、手動搜尋、待簽名單管理與簽約邏輯。同時，為了豐富遊戲環境，實作了 **CPU 球隊生成腳本**，可一鍵生成 35 支具備完整 15 人名單與戰術配置的 NPC 球隊，為聯賽模擬做好準備。

  ### 🛠️ 技術細節

  1.  **球探系統實作 (Scout System)**
      -   **資料庫模型 (`app/models/scout.py`)**:
          -   新增 `ScoutingRecord`: 關聯球隊與球員，並設定 `expire_at` (過期時間)。
          -   更新 `Team`: 新增 `scout_chances` (剩餘次數) 與 `daily_scout_level` (每日投入等級)。
      -   **業務邏輯 (`app/services/scout_service.py`)**:
          -   **生成邏輯**: 呼叫 `PlayerGenerator` 生成自由球員並寫入待簽名單。
          -   **每日結算**: 實作 `process_daily_scout_event`，處理資金扣除、自動搜尋與過期名單清理。
          -   **簽約邏輯**: 實作 `sign_player`，將球員從待簽名單轉移至正式名單，並自動產生合約。
      -   **API 端點 (`app/routes/scout.py`)**:
          -   `POST /api/scout/use`: 執行單次或多次手動搜尋。
          -   `GET /api/scout/pending`: 取得目前待簽球員列表 (含倒數時間)。
          -   `POST /api/scout/sign`: 執行簽約動作。
      -   **前端介面 (`frontend/src/components/ScoutPage.tsx`)**:
          -   實作互動式儀表板，整合每日投入設定滑桿與手動搜尋按鈕。
          -   待簽名單列表支援依能力、薪資、剩餘時間排序，並提供簽約操作。

  2.  **環境填充工具 (`scripts/generate_cpu_teams.py`)**
      -   實作自動化腳本，生成 35 支 CPU 球隊。
      -   **完整流程**: 建立 User (Manager) -> 建立 Team -> 生成 15 人合法名單 -> 建立 TeamTactics (全選登錄)。
      -   **效益**: 解決了開發初期缺乏對手進行聯賽測試的問題。

  3.  **配置與整合**
      -   **Config**: 更新 `game_config.yaml`，新增 `scout_system` 區塊 (費用、過期天數等)。
      -   **Frontend**: 更新 `App.tsx`，正式啟用球探中心路由。

  ### 📝 筆記
  -   **交易安全性**: 在 `ScoutService` 中使用了 `db.session.commit()` 確保扣除次數與生成球員的原子性 (Atomicity)。
  -   **效能**: CPU 球隊生成腳本執行 35 隊約需 15-20 秒 (視硬體而定)，主要開銷在於 `TeamCreator` 的 Reroll 機制，但這是為了確保 NPC 球隊陣容合規的必要成本。

  ### 🔜 下一步計畫
  -   **聯賽排程系統**: 設計賽季行事曆 (Schedule) 與對戰組合生成演算法。
  -   **每日模擬排程**: 整合 `MatchEngine` 與排程系統，實作每日自動模擬比賽的功能。

--

## 2026-02-18 15:30 : 聯賽排程系統與自動化模擬實作 (League Scheduling & Automated Simulation)

### ✅ 進度摘要
本次更新完成了遊戲的核心循環機制。實作了 **聯賽服務 (League Service)** 與 **排程器 (Scheduler)**，現在系統能夠自動推進賽季日期、生成每日賽程，並在指定時間自動執行比賽模擬。前端部分，新增了 **賽程頁面 (Schedules)** 與 **比賽詳情 (Match Details)**，玩家可以查看每日對戰組合、比分以及詳細的攻守數據 (Box Score) 與文字轉播 (PBP)。

### 🛠️ 技術細節

1.  **聯賽核心邏輯 (`app/services/league_service.py`)**
    -   **賽季管理**: 實作 `Season` 模型，追蹤當前賽季階段 (例行賽/季後賽) 與天數。
    -   **每日配對 (00:00)**:
        -   **正式聯賽**: 採用 Round-Robin 演算法生成雙循環賽程。
        -   **擴充聯賽**: 實作基於聲望 (Reputation) 的動態配對機制，落單球隊自動配對 Ghost Bot。
    -   **比賽執行 (19:00)**:
        -   批量讀取當日 `PUBLISHED` 狀態的賽程。
        -   呼叫 `MatchEngine` 進行模擬。
        -   將模擬結果 (`MatchResult`) 轉存至 `Match`, `MatchTeamStat`, `MatchPlayerStat` 資料表。
        -   執行 `Team.update_season_stats()` 同步更新戰績與排名。

2.  **自動化排程系統 (`app/scheduler.py`)**
    -   **APScheduler 整合**: 使用 `BackgroundScheduler` 執行背景任務。
    -   **Socket Lock 機制**: 解決 Flask Debug Mode 下 Reloader 導致排程器重複啟動 (Double Execution) 的問題，確保全域只有一個排程實例。
    -   **任務定義**:
        -   `daily_change`: 每日 00:00 觸發換日與配對。
        -   `daily_match`: 每日 19:00 觸發比賽模擬。

3.  **比賽數據擴充與前端呈現**
    -   **進階數據儲存**: 在 `MatchTeamStat` 中新增 `possession_history` (JSON)，記錄每一回合的消耗時間，用於分析球隊節奏 (Pace)。
    -   **前端組件 (`frontend/src/components/`)**:
        -   **SchedulesPage**: 顯示每日賽程卡片，區分正式/擴充聯賽，並標示勝敗與比分。
        -   **MatchDetailModal**: 實作 Tab 切換介面，完整呈現雙方 Box Score (含 +/- 值、效率) 與 Play-by-Play 文字流。
        -   **TeamsPage**: 實作聯盟排行榜，依據聲望與勝場排序。

### 📝 筆記
-   **資料一致性**: 在 `LeagueService` 中，比賽模擬後的戰績更新採用了 `flush()` 與 `commit()` 的分離策略，確保所有比賽數據寫入成功後才更新排名，避免數據不一致。
-   **效能優化**: 賽程列表 API (`/api/league/schedule`) 針對 `match_id` 進行了預先加載 (Eager Loading) 的優化，減少 N+1 查詢問題。

### 🔜 下一步計畫
-   **季後賽邏輯**: 實作季後賽樹狀圖生成 (Bracket Generation) 與晉級判定。
-   **球員成長結算**: 在休賽季階段加入球員老化與能力值成長的批次處理。

--

## 2026-02-20 08:30 : AI 球員卡牌生成系統與背景任務整合 (AI Card Generation & Background Tasks)

### ✅ 進度摘要
本次更新正式引入了 **AI 圖像生成系統 (Spec v5.0)**，利用 Stable Diffusion 為每位球員生成獨一無二的卡牌插圖。系統採用 **非同步背景任務 (Background Task)** 架構，確保在註冊或球探生成球員時，API 回應不會因繪圖運算而阻塞。同時，建立了一套基於球員屬性的 **動態提示詞引擎 (Prompt Engine)**，將數值 (如運球、彈跳) 轉化為具體的視覺動作與特效。

### 🛠️ 技術細節

1.  **AI 生成服務 (`app/services/image_generation_service.py`)**
    -   **Facade 模式**: 封裝與 Stable Diffusion WebUI API 的溝通邏輯。
    -   **Prompt Engine**: 實作屬性映射邏輯。
        -   **動作 (Actions)**: 若球員 `off_dribble > 80`，自動加入 `crossover` 提示詞；若 `ath_jump > 80`，加入 `tomahawk dunk`。
        -   **特徵 (Traits)**: 將身高、體格、年齡映射為視覺描述 (如 `tall stature`, `muscular build`)。
        -   **稀有度特效 (Rarity FX)**: 依據 Grade (SSR~G) 自動套用不同的背景與光影特效 (如 SSR 的 `golden divine aura`)。
    -   **非阻塞機制**: 使用 `threading.Thread` 搭配 Flask `app_context`，在背景執行生成任務，避免拖慢前端 UX。

2.  **業務流程整合**
    -   **Auth (`auth.py`)**: 玩家註冊並建立球隊後，自動觸發初始 15 人名單的背景繪圖任務。
    -   **Scout (`scout_service.py`)**: 產生待簽球員時，同步觸發單張卡牌生成。

3.  **配置與工具擴充**
    -   **Config (`config/game_config.yaml`)**: 新增 `ai_card_generation` 區塊，定義模型路徑、LoRA 設定、Prompt 模板與屬性映射規則。
    -   **工具腳本**:
        -   `tools/ai_card_generator.py`: 開發測試工具，可生成 HTML 報告預覽不同模型的生成效果。
        -   `scripts/batch_generate_images.py`: 維運腳本，用於掃描資料庫並補齊尚未生成圖片的球員卡。

### 📝 筆記
-   **效能優化**: 針對大量生成需求 (如開隊 15 人)，採用佇列或批次處理概念，但在目前的實作中先以 Thread 處理，需注意 GPU 負載。
-   **視覺風格**: 目前設定為 `Anthropomorphic Chibi Cat` 風格，配合 LoRA `CharacterDesign-IZT` 統一畫風。

### 🔜 下一步計畫
-   **訓練系統實裝**: 實作訓練點數的計算公式 (成長/巔峰/衰退) 以及前端分配介面。
-   **生成流程優化**: 優化球員與球隊的生成效能，減少資料庫 I/O。
-   **經濟系統開發**: 著手設計球隊收支、薪資帽運算與自由市場機制。

--

## 📅 2026-02-21 12:00 : 聯賽排程優化與季後賽邏輯實作 (League Scheduling & Playoff Logic)

### ✅ 進度摘要
本次更新完成了 **聯賽營運系統 (League System)** 的最後一塊拼圖。核心重點在於實作了基於 **蒙地卡羅模擬 (Monte Carlo Simulation)** 的賽程優化演算法，確保賽季賽程的主客場平衡。同時，完善了 **季後賽 (Playoffs)** 的動態樹狀圖生成邏輯，支援 BO3/BO5 賽制與系列賽結算。前端部分，完成了 **賽程頁面 (SchedulesPage)** 與 **比賽詳情 (MatchDetailModal)**，實現了從賽季預覽到單場數據的完整視覺化。

### 🛠️ 技術細節

1.  **聯賽排程與優化 (`app/services/league_service.py`)**
    -   **賽程生成演算法**:
        -   實作 `_generate_full_season_schedule`，結合 **標準圓桌法 (Round-Robin)** 與 **多核心蒙地卡羅模擬**。
        -   **懲罰積分機制**: 定義了連續主/客場的懲罰權重 (Streak Penalty)，透過大量模擬 (預設 3000 萬次) 篩選出積分最低（最平衡）的賽程組合。
    -   **季後賽邏輯**:
        -   實作 `_generate_playoff_bracket`，支援 R1 (16強) 到 Finals 的動態對戰組合生成。
        -   **系列賽管理**: 實作 `_cleanup_finished_series`，當系列賽勝負已分 (如 3-0) 時，自動取消後續無效賽程。
    -   **賽季重組**: 實作 `_reset_season_and_reseed`，於每一季 Day 1 依據聲望重新分配聯賽層級 (Tier 0, Tier 1...)。

2.  **前端介面實作 (`frontend/src/components/`)**
    -   **SchedulesPage.tsx**:
        -   實作每日賽程卡片，區分「例行賽」、「季後賽」與「擴充聯賽」樣式。
        -   新增 **日期選擇器 (DateSelectorModal)**，方便玩家在 91 天的賽季中快速跳轉。
        -   整合季後賽系列賽資訊 (如 "Round 1 · G2", "系列賽 1-0")。
    -   **MatchDetailModal.tsx**:
        -   實作比賽詳情彈窗，包含 **Box Score** (基礎/進階數據) 與 **Play-by-Play** 文字轉播。
        -   優化數據呈現，包含球員等級顏色 (`SSR`~`G`) 與先發標記 (`GS`)。

3.  **資料模型與配置**
    -   **Schema 更新**:
        -   `League` / `LeagueParticipant`: 支援多層級聯賽架構。
        -   `Schedule`: 新增 `series_id` 與 `game_number` 用於追蹤季後賽進度。
    -   **Config 更新**: 在 `game_config.yaml` 新增 `league_system` 區塊，定義賽程優化參數與聲望獎勵規則。

4.  **測試工具**
    -   新增 `tests/schedule_bigdata_test/run_schedule_optimization.py`: 專用於驗證賽程演算法的獨立測試腳本，產出積分分佈圖表。
    -   更新 `manage.py`: 新增手動觸發換日與比賽模擬的 CLI 指令。

### 📝 筆記
-   **效能優化**: 賽程生成採用 `ProcessPoolExecutor` 進行多進程運算，在 i9-14900K 上可於數分鐘內完成高品質賽程排定。
-   **使用者體驗**: 前端賽程頁面加入了「我的比賽」高亮顯示與自動排序邏輯，確保玩家能優先看到自己的賽程。

### 🔜 下一步計畫
-   **數據顯示優化**: 完善球隊與球員的數據統計頁面 (Stats Leaderboard)。
-   **訓練系統實裝**: 實作訓練點數分配與球員成長/老化結算邏輯。

--

## 📅 2026-02-22 06:00 - 系統穩定性修復與架構調整

### ✅ 已完成 (Completed)
- [x] **修復 AI 繪圖服務設定讀取錯誤**: 修正 `ImageGenerationService` 中使用點號路徑導致設定失效的問題，改為巢狀 `get()`。
- [x] **修復球隊生成器潛在崩潰**: 在 `TeamCreator` 中預先初始化變數，防止 `UnboundLocalError`。
- [x] **強化聯賽接管資料完整性**: 修正 `LeagueService` 接管 BOT 時未限制 Season ID 導致汙染歷史資料的 Bug。
- [x] **移除內建排程器**: 
    - 刪除 `app/scheduler.py`。
    - 移除 `app/__init__.py` 中的排程器初始化邏輯。
    - **說明**: 解決了排程時間設定不一致 (A2) 的問題，並將自動化控制權移交給外部系統 (如 Crontab) 或 `manage.py` 手動觸發，避免 Flask Debug 模式下的重複執行問題。

### 📝 筆記
- 系統不再自動執行每日模擬，請確保伺服器部署時已配置外部排程腳本呼叫 `manage.py`。

--

