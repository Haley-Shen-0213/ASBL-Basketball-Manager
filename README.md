# ASBL Basketball Manager (ASBL)

ASBL 是一款基於網頁的文字策略經營遊戲 (Web-based Text Strategy Game)。玩家扮演球隊經理，在嚴格的薪資限制下，透過選秀、交易、培養與戰術調度，打造屬於自己的冠軍王朝。

本專案採用 **Python 3.13 (Flask)** 作為後端框架，搭配 **MySQL 9.0** 資料庫進行開發，並引入 **Polars** 與 **Parquet** 進行大數據級別的數值平衡驗證。

---

## 📚 遊戲核心規則 (Game Rules)

### 1. 球員系統 (Player System)

> ⚠️ **詳細技術規格**：關於球員生成演算法、常態分佈參數、開隊陣容檢核邏輯，請參閱 [ASBL_Player_System_Specification.md](ASBL_Player_System_Specification.md)。

#### 屬性 (Attributes) - Spec v2.6
球員能力值範圍為 **1~99**，分為五大類：
*   **運動 (Physical)**: 體力、力量、速度、彈跳、健康(隱藏)。
*   **投籃 (Offense - Shooting)**: 投籃準心、射程、手感(不可訓)、出手速度(不可訓)。
*   **進攻 (Offense - Skill)**: 傳球、運球、控球、跑位。
*   **防守 (Defense)**: 籃板、卡位、干擾、抄截。
*   **天賦 (Mental)**: 進攻智商、防守智商、運氣(隱藏)。(永不改變)

#### 年齡生成 (Age Generation)
*   **SSR**: 固定 18 歲 (極具培養價值)。
*   **G~SS**: 等級越低，初始年齡浮動範圍越大 (G級可能高達 24 歲)。

#### 稀有度分級 (Rarity)
基於「不可訓練項目」的數值總和進行分級：
*   **SSR**: > 950
*   **SS**: 900 - 950
*   **S**: 800 - 899
*   **A**: 700 - 799
*   **B**: 600 - 699
*   **C**: 400 - 599
*   **G**: < 400

#### 成長與退化 (Growth & Decline)
*   **成長期 (18-25歲)**: 每上場 48 分鐘獲得 1 訓練點。
*   **巔峰期 (26-29歲)**: 每上場 144 分鐘獲得 1 訓練點。
*   **退化期 (30歲+)**: 隨上場時間與年齡增長，有機率扣除能力點數。

---

### 2. 薪資與合約 (Salary & Contract)

#### 薪資帽 (Salary Cap)
*   **硬上限**: 團隊總薪資不可超過 **100%** (底薪合約例外)。
*   **豪華稅**: 超過 100% 需支付倍率罰款。
*   **簽約限制**: 若薪資已達 65%，必須先完成頂薪續約 (35%)，才可簽署底薪合約。**否則一旦超過 65% 空間，即無法完成頂薪續約。**

#### 角色定位與上場時間 (Role & Minutes)
比賽總時間 240 分鐘。系統採用 **「保底時間 + 權重浮動」** 演算法分配時間。

| 角色定位 | 保底時間 (Base) | 權重範圍 (Weight) | 說明 |
| :--- | :--- | :--- | :--- |
| **明星 (Star)** | **30 min** | **-1 ~ 5** | 核心主力，極其穩定。 |
| **先發 (Starter)** | **20 min** | **-2 ~ 7** | 主力，有機會爆發獲得高時數。 |
| **綠葉 (Rotation)** | **10 min** | **5 ~ 15** | 輪替核心，競爭剩餘時間。 |
| **功能 (Role)** | **0 min** | **5 ~ 12** | 無保底，靠狀態爭取上場。 |
| **板凳 (Bench)** | **0 min** | **0 ~ 10** | 邊緣人，可能 DNP。 |

---

### 3. 比賽引擎 (Match Engine) - v1.4

本系統採用純文字模擬引擎，依據 **ASBL Spec v1.4** 進行開發。

#### 核心機制
*   **體力系統 (Stamina)**: 
    *   球員能力值隨體力下降而線性衰退。
    *   消耗公式：`3.0 * [1 + (1 - 體能%)] + (1 - 健康%)`。
*   **數據歸屬 (Data Attribution)**:
    *   **非隨機分配**：得分、籃板、助攻等數據依據球員能力值（如身高、智商、運球）進行權重分配。
    *   **戰術地位**：明星球員 (Star) 擁有更高的出手權重。
    *   **真實性優化**：控球後衛更容易獲得助攻，中鋒更容易獲得籃板與封蓋。
*   **關鍵時刻 (Clutch)**: 第四節最後 3 分鐘與延長賽強制換上最強陣容 (Best 5)。

---

## 🧪 大數據驗證架構 (Big Data Verification)

為了確保遊戲數值平衡，我們建立了千萬級別的 ETL 測試管線。

*   **技術核心**: Python Multiprocessing + Apache Parquet + Polars。
*   **驗證規模**: 100,000,000 (一億) 筆球員資料生成驗收。
*   **KPI 報告**: 自動化生成 Markdown 報告，詳見 `docs/KPI_Validation_Report_v2_6.md`。
*   **驗證項目**:
    *   常態分佈 (Normal Distribution) 檢核 (身高、體重)。
    *   稀有度 (Rarity) 出現機率收斂檢核。
    *   能力值邊界 (Stat Caps) 與重骰機制 (Reroll) 有效性。

---

## 📅 開發時程 (Development Roadmap)

### Phase 1: 核心架構 (Foundation) - [已完成]
*   [x] **資料庫建置**: 設計 User, Team, Player, Contract 等核心 Table。
*   [x] **球員生成引擎**: 實作 100 抽邏輯、G~SSR 分級演算法、屬性隨機生成。
*   [x] **合約系統**: 實作角色定位、薪資計算與簽約邏輯。
*   [x] **時間分配演算法**: 實作 `calculate_minutes(roster)` 函數。
*   [x] **大數據驗證**: 完成 1 億筆球員生成測試與 KPI 驗收報告。

### Phase 2: 比賽與成長 (Game Loop) - [進行中]
*   [x] **比賽引擎 (v1.6)**: 實作完整回合制判定、快攻、犯規、罰球與詳細數據紀錄。
*   [x] **單場模擬測試**: 完成無 DB 依賴的快速模擬腳本驗證。
*   [ ] **聯賽大數據測試**: 驗證賽季數據 (PTS/REB/AST) 的分佈平衡性。
*   [ ] **成長系統**: 實作年齡檢查、點數計算 (成長/巔峰/退化公式)。
*   [ ] **排程系統**: 每日自動結算比賽、更新球員年齡/合約天數。

### Phase 3: 經濟與交易 (Economy) - [預計 4 週]
*   [ ] **交易系統**: 實作掛單介面與條件匹配演算法。
*   [ ] **自由市場**: 實作競標系統與 RFA (受限自由球員) 機制。
*   [ ] **介面優化**: 完善前端顯示與操作體驗。

---

## 🛠 技術架構 (Tech Stack)

*   **Backend**: Python 3.13 (Flask)
*   **Database**: MySQL 9.0
*   **Data Analysis**: Polars, Pandas, Apache Parquet
*   **Frontend**: HTML5, CSS3, Jinja2 Templates
*   **ORM**: SQLAlchemy

## 📂 目錄結構 (Directory Structure)

ASBL-Basketball-Manager/
├─ app/                                   # 核心應用程式目錄
│  ├─ models/                             # [資料庫模型層] 定義 SQL Table 結構
│  │  ├─ __init__.py                      # 匯出 User, Team, Player, Contract, NameLibrary 方便引用
│  │  ├─ contract.py                      # (保留) 若合約邏輯過於複雜可獨立，目前定義在 player.py 內
│  │  ├─ match.py                         # 定義比賽賽程 (Match) 與比賽數據紀錄 (MatchStats)
│  │  ├─ player.py                        # 定義球員 (Player) 基本資料、JSON 詳細數據與合約 (Contract)
│  │  ├─ system.py                        # 定義系統輔助資料表，如姓名庫 (NameLibrary)
│  │  ├─ team.py                          # (保留) 若球隊邏輯複雜可獨立，目前定義在 user.py 內
│  │  └─ user.py                          # 定義使用者 (User) 帳號驗證與球隊 (Team) 資金/聲望
│  │
│  ├─ routes/                             # [API 路由層] 處理 HTTP 請求
│  │  ├─ __init__.py
│  │  └─ auth.py                          # 認證 API: 處理註冊 (/register) 與登入 (/login)，並自動建立球隊
│  │
│  ├─ services/                           # [業務邏輯層] 處理複雜運算，不直接碰觸 HTTP
│  │  ├─ match_engine/                    # >> 比賽模擬引擎 (Level 4 Simulation) <<
│  │  │  ├─ systems/                      # [引擎子系統] 負責特定領域的邏輯判斷 (Config Driven)
│  │  │  │  ├─ init.py
│  │  │  │  ├─ attribution.py             # [歸屬判定系統] 決定誰投籃、誰抓籃板、誰助攻 (依據權重與屬性)
│  │  │  │  ├─ play_logic.py              # (預留) 戰術邏輯
│  │  │  │  ├─ stamina.py                 # [體力系統] 計算體力流失/回復，並動態更新屬性懲罰係數
│  │  │  │  └─ substitution.py            # [換人系統] 執行自動換人、處理犯滿離場與時間重分配
│  │  │  ├─ utils/                        # [引擎工具]
│  │  │  │  ├─ init.py
│  │  │  │  ├─ calculator.py              # [數值計算器] 處理屬性加總、遞迴解析 Config、命中率公式計算
│  │  │  │  └─ rng.py                     # [隨機亂數] 極致效能優化的 RNG 類別 (綁定 random 底層函式)
│  │  │  ├─ init.py
│  │  │  ├─ core.py                       # 引擎核心: 控制比賽流程 (跳球 -> 節次 -> 回合 -> 結算)
│  │  │  ├─ service.py                    # 橋接服務: 負責 DB 資料 <-> Engine 物件轉換
│  │  │  └─ structures.py                 # [引擎專用結構] EnginePlayer/EngineTeam (使用 slots 優化效能)
│  │  │
│  │  ├─ init.py
│  │  ├─ player_generator.py              # 球員生成器: 產生符合常態分佈的身高、位置、SSR~G 級能力值
│  │  └─ team_creator.py                  # 球隊組建器: 呼叫生成器湊滿 15 人，並檢核陣容完整性 (如至少2個PG)
│  ├─ templates/                          # (目前無內容)
│  ├─ utils/
│  │  └─ game_config_loader.py            # [設定載入器] Singleton 模式讀取 YAML，支援環境變數路徑
│  └─ __init__.py
│
├─ config/
│  └─ game_config.yaml                    # [遊戲平衡檔] 定義所有機率、權重、薪資公式 (Spec v2.5 & v1.6)
│
├─ docs/                                  # [專案文件]
│  ├─ DEV_JOURNAL_BigData_Architecture.md # [架構日誌] 記錄從單機到 ETL Pipeline 的演進
│  └─  KPI_Validation_Report_v2_6.md       # [驗收報告] 1億筆資料生成的統計結果 (極端值、分佈檢核)
├─ scripts/
│  ├─ utils/
│  │  └─ tree.py # 專案檔案樹產生器
│  ├─ __init__.py
│  ├─ init_db.py # 舊檔案
│  ├─ simulate_match_no_db.py # 測試建立兩支球隊並且執行比賽
│  ├─ terminal.py # 清空終端顯示
│  └─ test_auth.py # 舊檔案
├─ tests/
│  ├─ big_data/                           # >> 大數據驗證架構 (ETL Pipeline) <<
│  │  ├─ output/                          # [資料輸出] (自動建立) 存放生成的 .parquet 檔案
│  │  │  ├─ dry_run/                      # 試跑產生的暫存檔
│  │  │  └─ run_v2_6_dataset_*/           # 正式測試產生的分片資料集
│  │  │
│  │  ├─ logs/                            # [執行紀錄] (自動建立) 存放 execution_history.log
│  │  │
│  │  ├─ __init__.py
│  │  ├─ test_config.yaml                 # [測試配置] 設定 Worker 數量、Batch Size、輸出路徑
│  │  │
│  │  ├─ verify_generator_integration.py  # [生產者 (Producer)] **主執行腳本**
│  │  │                                   # 1. 負責啟動 Multiprocessing Pool
│  │  │                                   # 2. 呼叫 PlayerGenerator 生成數據
│  │  │                                   # 3. 將數據寫入 Parquet 檔案 (ETL)
│  │  │
│  │  ├─ verify_kpi_v2_6.py               # [驗證者 (Validator)] **KPI 驗收腳本**
│  │  │                                   # 1. 使用 Polars 高速讀取 Parquet
│  │  │                                   # 2. 執行統計分析 (身高分佈、等級機率、極端值)
│  │  │                                   # 3. 輸出 Markdown 報告與 Log
│  │  │
│  │  ├─ analyze_data.py                  # [檢視器 (Viewer)]
│  │  │                                   # 使用 Pandas 快速預覽 dry_run.parquet 的內容與欄位
│  │  │
│  │  └─ check_crash_data.py              # [災難恢復 (Recovery)]
│  │                                      # 若測試中斷，此腳本可掃描 output 目錄，檢查哪些 Parquet 檔是完好的
│  └─ __init__.py
├── ASBL_Match_Engine_Specification.md # [Updated] 比賽引擎規格書 (v1.6)
├── ASBL_Player_System_Specification.md # 球員系統規格書 (v2.6)
├── config.py                # App Configuration (Flask 設定)
└── run.py                   # Entry Point (程式入口)
