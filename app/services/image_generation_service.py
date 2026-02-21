# app/services/image_generation_service.py
# -*- coding: utf-8 -*-
"""
專案名稱：ASBL-Basketball-Manager
模組名稱：AI 圖片生成服務 (Image Generation Service)
功能描述：
    提供單一球員卡牌生成的邏輯封裝。
    包含 Prompt 組裝引擎與 Stable Diffusion API 客戶端。
    [Update] 新增背景非同步生成功能，避免阻塞 API 回應。
    [Fix] 修正 YAML 設定檔讀取邏輯，解決巢狀字典存取失效問題。
"""

import os
import time
import random
import requests
import base64
import threading
from flask import current_app
from app import db
from app.models.player import Player
from app.utils.game_config_loader import GameConfigLoader

class ImageGenerationService:
    """
    圖片生成服務外觀類別 (Facade)
    """
    def __init__(self):
        self.config = GameConfigLoader.get('ai_card_generation')
        if not self.config:
            raise ValueError("無法讀取 ai_card_generation 設定，請檢查 game_config.yaml")
        
        self.client = _SDClient(self.config)
        self.engine = _PromptEngine(self.config)
        
        # [修正] 字典不支援 'output.directory' 語法，需改為巢狀 get
        output_conf = self.config.get('output', {})
        self.output_dir = output_conf.get('directory', 'frontend/public/assets/cards')
        self.filename_pattern = output_conf.get('filename_pattern', 'player_{id}.png')
        
        # 確保絕對路徑
        if not os.path.isabs(self.output_dir):
            # 假設執行位置在專案根目錄
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
            self.output_dir = os.path.join(base_dir, self.output_dir)
            
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def ensure_model_ready(self):
        """確保 SD WebUI 載入正確的模型 (建議在批次執行前呼叫)"""
        self.client.switch_model()

    def generate_card_for_player(self, player) -> bool:
        """
        為指定球員生成卡牌並存檔
        :param player: Player 資料庫物件
        :return: Boolean (成功/失敗)
        """
        try:
            # 1. 檢查是否已存在 (避免重複生成)
            img_path = self.get_image_path(player.id)
            if os.path.exists(img_path):
                print(f"⚠️ [ImageService] ID {player.id} 圖片已存在，跳過。")
                return True

            # 2. 組裝 Prompt
            prompt = self.engine.build_prompt(player)
            
            # [修正] 巢狀讀取 negative_base
            prompts_conf = self.config.get('prompts', {})
            neg_prompt = prompts_conf.get('negative_base', "")
            
            params = self.config.get('params', {})
            
            # 3. 呼叫 API 生成
            print(f"🎨 [ImageService] Generating for {player.name} (ID: {player.id})...")
            success = self.client.txt2img(prompt, neg_prompt, params, img_path)
            
            return success
        except Exception as e:
            print(f"❌ [ImageService] 生成失敗 (ID: {player.id}): {e}")
            return False

    def get_image_path(self, player_id):
        """取得預期的圖片路徑 (用於檢查是否存在)"""
        filename = self.filename_pattern.format(id=player_id)
        return os.path.join(self.output_dir, filename)

    # ==========================================
    # [New] 背景執行緒管理 (Background Task)
    # ==========================================
    @staticmethod
    def start_background_generation(app, player_ids):
        """
        啟動一個背景執行緒來生成圖片，避免阻塞主程式。
        :param app: Flask App 實例 (用於在執行緒中建立 Context)
        :param player_ids: 待生成的球員 ID 列表
        """
        def task(app_obj, ids):
            # 必須手動推入 App Context 才能使用 DB 與 Config
            with app_obj.app_context():
                service = ImageGenerationService()
                service.ensure_model_ready()
                
                print(f"🚀 [BgTask] 開始背景生成 {len(ids)} 張圖片...")
                count = 0
                for pid in ids:
                    # 重新查詢球員 (避免 Detached Instance 錯誤)
                    player = Player.query.get(pid)
                    if player:
                        if service.generate_card_for_player(player):
                            count += 1
                    else:
                        print(f"⚠️ [BgTask] 找不到球員 ID: {pid}")
                
                print(f"✅ [BgTask] 背景生成結束。成功: {count}/{len(ids)}")

        # 啟動執行緒
        # 注意: 這裡傳入的是 app 的實例，而非 current_app proxy
        # 在 Flask 路由中呼叫時，需傳入 `current_app._get_current_object()`
        thread = threading.Thread(target=task, args=(app, player_ids))
        thread.daemon = True # 設為 Daemon，主程式結束時自動結束
        thread.start()


# ==========================================
# 內部輔助類別 (Internal Helpers)
# ==========================================

class _SDClient:
    """負責與 Stable Diffusion WebUI API 溝通"""
    def __init__(self, config):
        # [修正] 巢狀讀取 base_url
        conn_conf = config.get('connection', {})
        self.base_url = conn_conf.get('base_url', "http://127.0.0.1:7860")
        self.model_config = config.get('model', {})
        
    def switch_model(self):
        """切換至設定檔指定的模型"""
        target_checkpoint = self.model_config.get('checkpoint')
        if not target_checkpoint:
            return

        try:
            # 1. 檢查當前模型
            opts = requests.get(f"{self.base_url}/sdapi/v1/options", timeout=5).json()
            current = opts.get('sd_model_checkpoint', '')
            
            # 簡單比對檔名
            if target_checkpoint.split('.')[0] in current:
                # print(f"✅ [SD] 模型已就緒: {current}")
                return

            # 2. 切換模型
            print(f"🔄 [SD] 切換模型中: {target_checkpoint}...")
            payload = {"sd_model_checkpoint": target_checkpoint}
            requests.post(f"{self.base_url}/sdapi/v1/options", json=payload, timeout=30)
            
            # 等待切換
            time.sleep(3)
            print(f"✅ [SD] 模型切換指令已發送")
            
        except Exception as e:
            print(f"⚠️ [SD] 模型檢查失敗 (API 可能未連線): {e}")

    def txt2img(self, prompt, negative_prompt, params, output_path):
        """發送生成請求並存檔"""
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": params.get('steps', 28),
            "cfg_scale": params.get('cfg_scale', 7.0),
            "width": params.get('width', 768),
            "height": params.get('height', 1024),
            "sampler_name": params.get('sampler_name', "Euler a"),
            "clip_skip": params.get('clip_skip', 2)
        }

        try:
            response = requests.post(f"{self.base_url}/sdapi/v1/txt2img", json=payload, timeout=120)
            if response.status_code == 200:
                r = response.json()
                image_data = base64.b64decode(r['images'][0])
                
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                return True
            else:
                print(f"❌ [SD] API 回傳錯誤: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ [SD] 連線錯誤: {e}")
            raise e


class _PromptEngine:
    """負責將球員資料轉換為 Prompt"""
    def __init__(self, config):
        # 這裡的 key 是第一層，直接 get 沒問題
        self.mappings = config.get('mappings', {})
        self.prompts = config.get('prompts', {})

    def _get_stat(self, player, key):
        """從 Player 物件解析屬性值 (支援扁平與巢狀 JSON)"""
        # 1. 直接屬性
        if hasattr(player, key):
            return getattr(player, key)
        
        # 2. JSON 屬性 (detailed_stats)
        stats = player.detailed_stats or {}
        
        # 簡易搜尋邏輯：遍歷所有分類尋找 key
        # 例如 key='off_dribble', 在 stats['offense']['dribble']
        for cat in ['physical', 'offense', 'defense', 'mental']:
            if cat in stats:
                for sub_k, val in stats[cat].items():
                    # 建立可能的鍵名變體進行比對
                    candidates = [
                        sub_k,                      # dribble
                        f"{cat}_{sub_k}",           # offense_dribble
                        f"off_{sub_k}" if cat == 'offense' else None,
                        f"def_{sub_k}" if cat == 'defense' else None,
                        f"ath_{sub_k}" if cat == 'physical' else None,
                        f"talent_{sub_k}" if cat == 'mental' else None,
                        f"shot_{sub_k}" if cat == 'offense' else None
                    ]
                    if key in candidates:
                        return val
        return 0

    def _select_action(self, player):
        """選擇動作 Prompt"""
        pool = self.mappings.get('actions', {}).get('pool', [])
        candidates = []
        weights = []

        for item in pool:
            condition = item.get('condition')
            is_valid = True
            
            if condition:
                attr_val = self._get_stat(player, condition['attr'])
                if attr_val < condition['min']:
                    is_valid = False
            
            if is_valid:
                candidates.append(item['prompt'])
                weights.append(item['weight'])
        
        if not candidates:
            return "holding basketball, standing pose"
            
        return random.choices(candidates, weights=weights, k=1)[0]

    def _calc_continuous_trait(self, player, trait_name, rule):
        """計算連續特徵 Prompt (如身高、肌肉)"""
        val = self._get_stat(player, trait_name)
        base = rule.get('base', 1.0)
        ref_val = rule.get('ref_val', 0)
        coeff = rule.get('coeff', 0.0)
        fmt = rule.get('prompt_fmt', "")
        
        w = base + (val - ref_val) * coeff
        try:
            return fmt.format(w=w)
        except:
            return ""

    def _calc_age_trait(self, player, rule):
        """計算年齡特徵 Prompt"""
        age = player.age
        base_age = rule.get('base_age', 18)
        w_young = rule.get('young_base', 1.0) + (age - base_age) * rule.get('young_coeff', -0.03)
        w_old = rule.get('old_base', 0.8) + (age - base_age) * rule.get('old_coeff', 0.03)
        
        try:
            return rule.get('prompt_fmt', "").format(w_young=w_young, w_old=w_old)
        except:
            return ""

    def build_prompt(self, player):
        """主入口：產生完整 Prompt"""
        base_prompt = self.prompts.get('positive_base', "")
        action_prompt = self._select_action(player)
        
        rarity_map = self.mappings.get('rarity_fx', {})
        rarity_prompt = rarity_map.get(player.grade, "")
        
        trait_prompts = []
        c_traits = self.mappings.get('continuous_traits', {})
        for trait_name, rule in c_traits.items():
            p_str = self._calc_continuous_trait(player, trait_name, rule)
            if p_str: trait_prompts.append(p_str)
            
        age_rule = self.mappings.get('age_traits', {})
        age_prompt = self._calc_age_trait(player, age_rule)
        
        # 視覺隨機化 (固定 Seed 確保同一球員長相一致)
        colors = ["white", "black", "orange", "grey", "calico", "tabby"]
        eye_colors = ["yellow", "blue", "green", "heterochromia"]
        random.seed(player.id) 
        fur_color = random.choice(colors)
        eye_color = random.choice(eye_colors)
        visual_prompt = f"{fur_color} fur, {eye_color} eyes, basketball uniform, sneakers"

        full_prompt = (
            f"{base_prompt}, "
            f"{action_prompt}, "
            f"{visual_prompt}, "
            f"{', '.join(trait_prompts)}, "
            f"{age_prompt}, "
            f"{rarity_prompt}, "
            f"(clean bottom background:1.3), (negative space at bottom:1.3), solo"
        )
        return full_prompt