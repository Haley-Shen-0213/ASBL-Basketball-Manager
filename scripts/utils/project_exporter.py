# scripts/utils/project_exporter.py
# -*- coding: utf-8 -*-
"""
專案名稱：ASBL-Basketball-Manager (籃球數據遊戲)
模組名稱：專案代碼匯出工具 (Project Exporter) - Full Stack Version
功能描述：
    整合檔案樹生成與代碼合併功能，支援前後端完整架構。
    1. 掃描專案目錄，根據設定的副檔名過濾檔案 (包含 Python 後端與 React/TS 前端)。
    2. 生成專案結構樹狀圖 (自動排除 node_modules, venv 等非核心目錄)。
    3. 合併所有符合條件的檔案內容至單一 Markdown 文件。
    4. 用於提供 LLM 完整的專案上下文或進行代碼備份。

使用說明：
    於專案根目錄執行：
    python scripts/utils/project_exporter.py

    輸出檔案預設位於：docs/PROJECT_CONTEXT_YYYYMMDD_HHMMSS.md

作者：Monica (AI Assistant)
日期：2026-02-06
"""

import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Set, List, Tuple, Optional

class ProjectExporter:
    """
    專案匯出器類別
    負責掃描目錄、生成樹狀圖及合併檔案內容
    """

    # ==========================================
    # 靜態配置參數 (Configuration)
    # ==========================================
    
    # 輸出目錄
    OUTPUT_DIR: str = "docs/PROJECT_CONTEXT"
    
    # 輸出的檔案前綴
    OUTPUT_FILENAME_PREFIX: str = "PROJECT_CONTEXT"
    
    # 要包含的檔案副檔名 (白名單) - [已擴充前端支援]
    TARGET_EXTENSIONS: Set[str] = {
        # Backend & Config
        '.py', '.env', '.md', '.yaml', '.yml', '.sql',
        # Frontend (React + TypeScript + Vite)
        '.ts', '.tsx',   # 核心邏輯與組件
        '.js', '.jsx',   # 設定檔或舊代碼
        '.json',         # tsconfig, package.json 等設定
        '.html',         # index.html 入口
        '.css', '.scss'  # Tailwind 或全域樣式
    }

    # [新增] 強制包含的特定檔案名稱 (不論副檔名為何)
    INCLUDE_FILES: Set[str] = {
        'requirements.txt',
        'Dockerfile',
        'Procfile'
    }
    
    # 要排除的目錄名稱 (黑名單)
    EXCLUDE_DIRS: Set[str] = {
        # General / IDE
        '.git', '.idea', '.vscode',
        # Backend
        '__pycache__', '.venv', 'venv', 'env', '.pytest_cache', 'htmlcov',
        # Frontend / Build
        'node_modules', 'site-packages', 
        'build', 'dist', '.vite', 'coverage', 'public', # public 通常放圖檔，不需讀取代碼
        # Output / Logs
        'docs', 'backup', 'output', 'data', 'reports', 'logs'
    }
    
    # 要排除的特定檔案名稱 (黑名單)
    EXCLUDE_FILES: Set[str] = {
        '.DS_Store', 'Thumbs.db',
        # Lock files (通常太長且無助於理解邏輯)
        'poetry.lock', 'Pipfile.lock', 'yarn.lock', 'package-lock.json', 'pnpm-lock.yaml',
        'LICENSE', '.gitignore', 'favicon.ico', 'logo.png'
    }

    # ==========================================
    # 核心邏輯方法 (Core Logic)
    # ==========================================

    @staticmethod
    def run() -> None:
        """
        主執行入口
        """
        # 1. 初始化路徑
        # 假設此腳本在 scripts/utils/ 下，回退兩層至根目錄
        root_path = Path(__file__).resolve().parents[2] 
        
        # 解析命令列參數
        parser = argparse.ArgumentParser(description="ASBL 專案代碼匯出工具")
        parser.add_argument('--out', type=str, help='自定義輸出路徑 (可選)')
        args = parser.parse_args()

        # 2. 準備輸出路徑
        output_file_path = ProjectExporter._get_output_path(root_path, args.out)
        
        print(f"🚀 [ASBL] 開始執行專案匯出 (Full Stack Mode)...")
        print(f"📂 專案根目錄: {root_path}")
        print(f"🎯 目標副檔名: {len(ProjectExporter.TARGET_EXTENSIONS)} 種類型")
        print(f"📄 強制包含檔案: {ProjectExporter.INCLUDE_FILES}")
        print(f"🚫 排除目錄: {ProjectExporter.EXCLUDE_DIRS}")

        # 3. 掃描專案並構建資料
        # collected_files 儲存 (相對路徑, 絕對路徑) 的列表
        tree_str, collected_files = ProjectExporter._scan_and_build_tree(root_path)

        # 4. 寫入檔案
        ProjectExporter._write_export_file(output_file_path, tree_str, collected_files, root_path)

        print(f"✅ 匯出完成！")
        print(f"📊 總計處理檔案: {len(collected_files)} 個")
        print(f"💾 檔案已儲存至: {output_file_path}")

    @staticmethod
    def _get_output_path(root_path: Path, custom_out: Optional[str]) -> Path:
        """
        生成帶有時間戳記的輸出路徑
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if custom_out:
            p = Path(custom_out)
            if p.is_dir() or custom_out.endswith(('/', '\\')):
                return p / f"{ProjectExporter.OUTPUT_FILENAME_PREFIX}_{ts}.md"
            return p
        
        # 預設路徑
        docs_dir = root_path / ProjectExporter.OUTPUT_DIR
        docs_dir.mkdir(parents=True, exist_ok=True)
        return docs_dir / f"{ProjectExporter.OUTPUT_FILENAME_PREFIX}_{ts}.md"

    @staticmethod
    def _scan_and_build_tree(root: Path) -> Tuple[str, List[Tuple[str, Path]]]:
        """
        掃描目錄，同時生成樹狀圖字串與收集符合條件的檔案
        """
        collected_files: List[Tuple[str, Path]] = []
        
        def _recursive_build(current_path: Path, prefix: str = '') -> str:
            """內部遞迴函數"""
            try:
                # 取得當前目錄下的所有項目，並排序 (目錄優先，然後是檔案名)
                entries = sorted(
                    current_path.iterdir(),
                    key=lambda p: (p.is_file(), p.name.lower())
                )
            except PermissionError:
                return ""

            # 過濾掉排除的目錄和檔案
            valid_entries = []
            for e in entries:
                if e.name in ProjectExporter.EXCLUDE_FILES:
                    continue
                if e.is_dir() and e.name in ProjectExporter.EXCLUDE_DIRS:
                    continue
                
                # [修改] 檔案過濾邏輯：檢查副檔名 OR 強制包含的檔名
                if e.is_file():
                    is_valid_extension = e.suffix in ProjectExporter.TARGET_EXTENSIONS
                    is_included_file = e.name in ProjectExporter.INCLUDE_FILES
                    
                    if not (is_valid_extension or is_included_file):
                        continue
                
                valid_entries.append(e)

            lines = []
            count = len(valid_entries)
            
            for i, entry in enumerate(valid_entries):
                is_last = (i == count - 1)
                connector = '└─ ' if is_last else '├─ '
                
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    ext_prefix = f"{prefix}{'   ' if is_last else '│  '}"
                    subtree = _recursive_build(entry, ext_prefix)
                    if subtree: # 只有當子目錄有內容時才加入，避免空目錄佔版面
                        lines.append(subtree)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
                    # 收集檔案資訊
                    rel_path = entry.relative_to(root)
                    collected_files.append((str(rel_path), entry))
            
            return '\n'.join(lines)

        # 開始遞迴
        tree_body = _recursive_build(root)
        full_tree = f"{root.name}/\n{tree_body}"
        return full_tree, collected_files

    @staticmethod
    def _write_export_file(output_path: Path, tree_str: str, files: List[Tuple[str, Path]], root_path: Path) -> None:
        """
        將樹狀圖與檔案內容寫入目標文件
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # 1. 寫入檔頭與專案資訊
                f.write(f"# \n\n")
                f.write(f"# ASBL Basketball Manager - 專案全景快照\n\n")
                f.write(f"- **生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- **專案路徑**: `{root_path}`\n")
                f.write(f"- **包含格式**: `{', '.join(sorted(ProjectExporter.TARGET_EXTENSIONS))}`\n")
                f.write(f"- **強制包含**: `{', '.join(sorted(ProjectExporter.INCLUDE_FILES))}`\n")
                f.write(f"- **檔案總數**: {len(files)}\n\n")
                
                # 2. 寫入專案結構樹
                f.write("## 1. 專案結構樹 (Project Tree)\n\n")
                f.write("```text\n")
                f.write(tree_str)
                f.write("\n```\n\n")
                
                f.write("---\n\n")
                f.write("## 2. 檔案內容詳情 (File Contents)\n\n")

                # 3. 遍歷並寫入檔案內容
                for rel_path, full_path in files:
                    f.write(f"### 📄 File: `{rel_path}`\n\n")
                    
                    # 根據副檔名決定 Markdown 的代碼區塊語言標籤 (Syntax Highlighting)
                    ext = full_path.suffix.lower().replace('.', '')
                    
                    # 映射表
                    lang_map = {
                        'py': 'python',
                        'js': 'javascript',
                        'jsx': 'javascript',
                        'ts': 'typescript',
                        'tsx': 'tsx',
                        'json': 'json',
                        'html': 'html',
                        'css': 'css',
                        'scss': 'scss',
                        'yaml': 'yaml',
                        'yml': 'yaml',
                        'env': 'bash',
                        'md': 'markdown',
                        'txt': 'text',
                        'sql': 'sql'
                    }
                    
                    code_block_lang = lang_map.get(ext, '')
                    
                    # 特殊處理 requirements.txt
                    if full_path.name == 'requirements.txt':
                        code_block_lang = 'text'

                    f.write(f"```{code_block_lang}\n")
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            # 處理檔案結尾沒有換行的情況，避免 Markdown 格式跑掉
                            if content and not content.endswith('\n'):
                                content += '\n'
                            f.write(content)
                    except UnicodeDecodeError:
                        f.write(f"# [ERROR] 無法以 UTF-8 格式讀取此檔案 (可能是二進制文件)\n")
                    except Exception as e:
                        f.write(f"# [ERROR] 讀取檔案時發生異常: {str(e)}\n")
                        
                    f.write("```\n\n")
                    f.write("---\n\n")
                    
        except Exception as e:
            print(f"❌ 寫入輸出檔案時發生錯誤: {str(e)}")

if __name__ == '__main__':
    ProjectExporter.run()
