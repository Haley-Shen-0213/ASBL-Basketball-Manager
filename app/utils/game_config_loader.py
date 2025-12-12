# app/utils/game_config_loader.py
import yaml
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

class GameConfigLoader:
    """
    負責讀取 config/game_config.yaml 的單例類別。
    優先順序:
    1. 環境變數 'GAME_CONFIG_PATH'
    2. 專案根目錄下的 config/game_config.yaml (自動推導)
    """
    _config = None

    @classmethod
    def load(cls):
        """
        載入設定檔 (Singleton 模式)
        """
        if cls._config is None:
            config_path = None
            
            # 1. 優先嘗試從環境變數讀取路徑
            env_path = os.getenv('GAME_CONFIG_PATH')
            if env_path:
                # 支援相對路徑與絕對路徑
                if os.path.isabs(env_path):
                    potential_path = env_path
                else:
                    potential_path = os.path.abspath(env_path)
                
                if os.path.exists(potential_path):
                    config_path = potential_path
                else:
                    print(f"[Warning] .env 設定的 GAME_CONFIG_PATH ({env_path}) 找不到檔案，將嘗試自動搜尋。")

            # 2. 若環境變數未設定或找不到，使用預設相對路徑搜尋
            if not config_path:
                # 定位到 app/utils/game_config_loader.py
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # 往上兩層: app/utils -> app -> root
                project_root = os.path.dirname(os.path.dirname(current_dir))
                
                # 預設路徑: root/config/game_config.yaml
                default_path = os.path.join(project_root, 'config', 'game_config.yaml')
                
                if os.path.exists(default_path):
                    config_path = default_path
                else:
                    # 最後嘗試: 當前工作目錄 (CWD) 下的 config
                    cwd_path = os.path.join(os.getcwd(), 'config', 'game_config.yaml')
                    if os.path.exists(cwd_path):
                        config_path = cwd_path

            # 3. 最終檢查
            if not config_path or not os.path.exists(config_path):
                raise FileNotFoundError(
                    "Game config file not found. \n"
                    "Please set 'GAME_CONFIG_PATH' in .env or ensure 'config/game_config.yaml' exists in project root."
                )

            # 4. 讀取 YAML
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cls._config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing YAML config at {config_path}: {e}")

        return cls._config

    @classmethod
    def get(cls, key_path=None, default=None):
        """
        取得設定值，支援點號路徑存取。
        Example: GameConfigLoader.get('match_engine.backcourt.params.time_coeff', 0.01)
        """
        try:
            cfg = cls.load()
        except Exception as e:
            print(f"[Error] Failed to load config: {e}")
            return default

        if not key_path:
            return cfg
        
        keys = key_path.split('.')
        val = cfg
        
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None:
                    return default
            else:
                return default
            
        return val

    @classmethod
    def reload(cls):
        """強制重新讀取 (用於熱更或測試)"""
        cls._config = None
        return cls.load()