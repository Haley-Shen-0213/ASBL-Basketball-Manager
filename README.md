# ASBL Basketball Manager (Advanced Simulation Basketball League)

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue?style=for-the-badge&logo=typescript)
![MySQL](https://img.shields.io/badge/MySQL-9.0-4479A1?style=for-the-badge&logo=mysql)
![Stable Diffusion](https://img.shields.io/badge/AI-Stable_Diffusion-orange?style=for-the-badge)

> **ASBL** 是一款基於高擬真數據模擬的現代化籃球經理遊戲。專案核心採用 **資料驅動 (Data-Driven)** 與 **配置化設計 (Config-Driven)** 架構，結合 Python 後端的高效運算與 React 前端的互動體驗，並引入 Stable Diffusion 進行 AI 球員卡牌生成。

---

## 📖 專案概述 (Overview)

本專案旨在打造一個具備高度策略深度與數值平衡的籃球模擬系統。不同於傳統遊戲，ASBL 的核心引擎經過 **上億次 (100M+)** 的大數據壓力測試驗證，確保常態分佈、極端值處理與比賽節奏 (Pace) 皆符合現代籃球規律。

### 核心特色
*   **高擬真比賽引擎 (L4 Match Engine)**: 支援 Play-by-Play 回合制模擬，包含體力衰退、8秒/24秒違例、快攻判定、空間 (Spacing) 計算與關鍵時刻 (Clutch) 強制調度。
*   **參數與邏輯分離**: 所有機率、權重、公式係數皆抽離至 `game_config.yaml`，實現不改動程式碼即可調整遊戲平衡。
*   **大數據驗證架構**: 內建 ETL 測試管線，利用 `Polars` 與 `Parquet` 處理千萬級別的球員生成與賽季模擬，產出詳細的 KPI 驗收報告。
*   **AI 生成整合**: 整合 Stable Diffusion WebUI API，根據球員特徵 (種族、毛色、動作) 自動生成獨一無二的視覺化卡牌。
*   **完整聯賽生態**: 包含正式聯賽 (36隊) 與擴充聯賽的升降機制、每日自動排程與戰績結算。

---

## 🛠️ 技術架構 (Tech Stack)

### Backend (後端)
*   **Framework**: Python 3.13 + Flask 3.0 (Application Factory Pattern)
*   **Database**: MySQL 9.0 (Production) / SQLite (Dev), SQLAlchemy ORM
*   **Simulation**: Custom Match Engine (Optimized with `__slots__` for memory efficiency)
*   **Scheduling**: APScheduler (Background tasks for daily simulation)
*   **Data Analysis**: Pandas, Polars, Apache Parquet (For big data testing)

### Frontend (前端)
*   **Framework**: React 19 + Vite
*   **Language**: TypeScript
*   **Styling**: Tailwind CSS (Responsive Design)
*   **State/API**: React Hooks, Fetch API (Proxy via Vite)

### AI & Tools
*   **Image Gen**: Stable Diffusion WebUI API (Text-to-Image with LoRA)
*   **DevOps**: Docker support, Python `multiprocessing` for stress testing.

---

## 🏗️ 系統模組設計 (System Modules)

專案採用模組化設計，確保各子系統低耦合高內聚：

### 1. 比賽引擎 (`app/services/match_engine`)
*   **Core**: 控制比賽狀態機 (跳球 -> 後場 -> 前場 -> 投籃 -> 結算)。
*   **Systems**: 
    *   `StaminaSystem`: 計算體力流失 (含年齡衰退) 與能力值動態懲罰。
    *   `AttributionSystem`: 基於權重 (Weight) 分配籃板、助攻與出手權。
    *   `SubstitutionSystem`: 處理自動輪替、犯滿離場與時間重分配 (Positional Top-K)。
*   **Physics**: 實作身高修正 (Height Correction) 與速度折扣 (Speed Discount) 機制。

### 2. 球員生成系統 (`app/services/player_generator.py`)
*   **演算法**: Box-Muller Transform (身高常態分佈)。
*   **檢核機制**: 
    *   **反向總上限 (Reverse Cap)**: 限制高潛力球員的初始能力。
    *   **位置檢核**: 確保生成的數值分佈符合位置特徵 (如 C 的籃板能力)。
    *   **開隊規則**: 強制高階球員 (SSR/SS) 覆蓋 5 個位置。

### 3. 聯賽營運系統 (`app/services/league_service.py`)
*   **排程**: 每日 00:00 自動生成賽程 (Round-Robin + 擴充配對)。
*   **模擬**: 每日 19:00 鎖定名單並執行比賽，更新戰績與聲望。
*   **球探**: 每日自動扣除資金並生成待簽球員。

---

## 📊 大數據驗證 (Big Data Verification)

為了確保數值模型的穩定性，專案包含一套完整的測試工具 (`tests/`)。

*   **球員生成測試**: 
    *   生成 **1 億筆 (100M)** 球員資料。
    *   驗證身高分佈誤差 < 0.02%。
    *   驗證稀有度 (SSR~G) 機率收斂。
*   **比賽平衡測試**:
    *   模擬 **1200 萬場** 比賽。
    *   分析勝率分佈、分差常態分佈、Pace 與真實命中率。
    *   產出 Markdown 格式的 KPI 驗收報告。

---

## 🚀 安裝與執行 (Installation)

### 前置需求
*   Python 3.13+
*   Node.js 18+
*   MySQL 8.0+ (Optional, default uses SQLite)
*   Stable Diffusion WebUI (Optional, for image generation)

### 1. 後端設定
```bash
# 1. Clone 專案
git clone https://github.com/your-repo/ASBL-Basketball-Manager.git
cd ASBL-Basketball-Manager

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 初始化資料庫
python scripts/init_db.py

# 5. 生成測試用的 CPU 球隊 (填充聯賽)
python scripts/generate_cpu_teams.py

# 6. 啟動伺服器
python run.py
```

### 2. 前端設定
```bash
cd frontend

# 1. 安裝依賴
npm install

# 2. 啟動開發伺服器
npm run dev
```

瀏覽器開啟 `http://localhost:5173` 即可進入遊戲。

---

## 📂 目錄結構 (Directory Structure)

ASBL-Basketball-Manager/
├── app/                                      # [後端核心] Flask 應用程式主目錄
│   ├── models/                               # [資料模型層] SQLAlchemy ORM 定義 (Schema)
│   │   ├── __init__.py                       # 匯出所有模型方便引用
│   │   ├── contract.py                       # 合約系統 (薪資、年限、角色定位)
│   │   ├── league.py                         # 聯賽系統 (賽季 Season、賽程 Schedule)
│   │   ├── match.py                          # 比賽數據 (Match, TeamStats, PlayerStats/BoxScore)
│   │   ├── player.py                         # 球員核心 (基本資料、JSON 詳細屬性、成長紀錄)
│   │   ├── scout.py                          # 球探系統 (待簽名單紀錄)
│   │   ├── system.py                         # 系統輔助表 (多國語系姓名庫)
│   │   ├── tactics.py                        # 戰術配置 (登錄名單、戰術參數)
│   │   ├── team.py                           # 球隊經營 (資金、聲望、戰績)
│   │   └── user.py                           # 使用者帳號 (權限、登入紀錄)
│   │
│   ├── routes/                               # [API 路由層] 處理 HTTP 請求與回應
│   │   ├── auth.py                           # 認證 API (註冊/登入、開局球隊建立)
│   │   ├── game.py                           # 比賽 API (單場模擬觸發)
│   │   ├── league.py                         # 聯賽 API (賽程查詢、賽季資訊)
│   │   ├── scout.py                          # 球探 API (搜尋、簽約)
│   │   └── team.py                           # 球隊 API (儀表板、名單管理)
│   │
│   ├── services/                             # [業務邏輯層] 封裝複雜運算與核心機制
│   │   ├── match_engine/                     # >> L4 高擬真比賽模擬引擎 (核心亮點) <<
│   │   │   ├── systems/                      # [子系統] 特定領域邏輯 (Config Driven)
│   │   │   │   ├── attribution.py            # 數據歸屬判定 (籃板/助攻/出手權重)
│   │   │   │   ├── stamina.py                # 體力系統 (消耗/恢復/年齡衰退)
│   │   │   │   └── substitution.py           # 換人系統 (自動輪替/犯滿重分配)
│   │   │   ├── utils/                        # [引擎工具]
│   │   │   │   ├── calculator.py             # 數值計算器 (屬性加總、命中率公式)
│   │   │   │   └── rng.py                    # 高效能隨機數生成器
│   │   │   ├── core.py                       # 引擎核心 (狀態機、PBP 流程控制)
│   │   │   ├── service.py                    # 適配器 (DB Model <-> Engine Struct 轉換)
│   │   │   └── structures.py                 # 引擎專用資料結構 (使用 __slots__ 優化記憶體)
│   │   │
│   │   ├── image_generation_service.py       # AI 圖片生成服務 (Stable Diffusion 串接)
│   │   ├── league_service.py                 # 聯賽營運 (每日排程、配對、戰績結算)
│   │   ├── player_generator.py               # 球員生成器 (常態分佈演算法、姓名生成)
│   │   ├── scout_service.py                  # 球探邏輯 (每日刷新、資金扣除)
│   │   └── team_creator.py                   # 球隊組建器 (開局陣容檢核邏輯)
│   │
│   ├── utils/                                # [通用工具]
│   │   └── game_config_loader.py             # 設定檔載入器 (Singleton 模式)
│   ├── scheduler.py                          # [排程系統] APScheduler (每日模擬任務)
│   └── __init__.py                           # App Factory 初始化
│
├── config/                                   # [配置層]
│   └── game_config.yaml                      # 遊戲核心平衡參數 (機率、權重、公式係數)
│
├── frontend/                                 # [前端] React + TypeScript + Vite
│   ├── src/
│   │   ├── components/                       # UI 組件 (Roster, Tactics, MatchModal...)
│   │   ├── App.tsx                           # 主應用程式與路由
│   │   └── ...
│   ├── tailwind.config.js                    # 樣式配置
│   └── vite.config.ts                        # 建置配置 (含 API Proxy)
│
├── scripts/                                  # [維運腳本]
│   ├── utils/                                # 腳本輔助工具
│   ├── batch_generate_images.py              # 批次補生成球員卡圖片
│   ├── generate_cpu_teams.py                 # 批量生成 NPC 球隊 (填充聯賽)
│   ├── init_db.py                            # 資料庫初始化
│   └── terminal.py                           # 終端機工具
│
├── tests/                                    # [大數據驗證] ETL 測試管線
│   ├── match_bigdata_test/                   # 比賽引擎平衡性測試
│   │   └── run_core_bigdata_test.py          # 執行千萬場次模擬與數據收集
│   ├── player_generator_big_data/            # 球員生成分佈驗證
│   │   ├── analyzer.py                       # 統計分析器 (Polars)
│   │   └── run_test.py                       # 執行一億筆生成測試
│   └── team_bigdata_test/                    # 隊伍生成壓力測試
│
├── tools/                                    # [開發輔助工具]
│   ├── ai_card_generator.py                  # AI 繪圖測試工具
│   └── code_merger.py                        # 代碼合併工具 (用於 LLM Context)
│
├── ASBL_AI_Card_Generation_Specification.md  # [規格書] AI 球員卡生成規範
├── ASBL_Database_Schema.md                   # [規格書] 資料庫架構設計 (ER Diagram)
├── ASBL_League_Simulation_Design.md          # [規格書] 大數據模擬驗證設計
├── ASBL_League_System_Specification.md       # [規格書] 聯賽營運系統規範
├── ASBL_Match_Engine_Specification.md        # [規格書] 比賽引擎核心邏輯 (v2.4)
├── ASBL_Player_System_Specification.md       # [規格書] 球員生成與成長系統 (v3.5)
├── ASBL_Tactics_System_Specification.md      # [規格書] 戰術與陣容管理規範
├── config.py                                 # Flask 環境設定 (Secret Key, DB URI)
├── manage.py                                 # 手動觸發排程指令
├── requirements.txt                          # Python 依賴套件
└── run.py                                    # 程式進入點 (Entry Point)

---

## 📝 開發規範 (Development Standards)

*   **註解**: 所有程式碼需包含清楚明確的繁體中文註解。
*   **檔案標頭**: 每個檔案首行需標註專案路徑與檔名。
*   **配置分離**: 禁止在程式碼中 Hardcode 數值，必須使用 `GameConfigLoader` 讀取 YAML。
*   **靜態方法**: 工具類方法應使用 `@staticmethod` 或 `@classmethod` 以利重用。

---

## 📜 授權 (License)

MIT License. Copyright (c) 2026 ASBL Dev Team.
```
