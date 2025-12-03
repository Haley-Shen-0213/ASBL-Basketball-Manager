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