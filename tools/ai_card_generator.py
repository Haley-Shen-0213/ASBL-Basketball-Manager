# tools/ai_card_generator.py
# -*- coding: utf-8 -*-
"""
專案名稱：ASBL-Basketball-Manager
模組名稱：AI 球員卡牌批量生成器 (極速版 + 網頁報告)
硬體優化：針對 NVMe SSD + 128GB RAM 優化
功能新增：執行後自動開啟瀏覽器展示成果
"""

import json
import base64
import requests
import os
import time
import random
import sys
import webbrowser  # 新增：用於開啟瀏覽器

# ==========================================
# ⚙️ 設定區域
# ==========================================

BASE_URL = "http://127.0.0.1:7860"

MODEL_LIST = [
    "JANKUTrained NoobaiRouwei_v69.safetensors",
    "furrytoonmix_xlIllustriousV2.safetensors",
    "prefectiousXLNSFW_v10.safetensors"
]

LORA_CONFIG = {
    "name": "CharacterDesign-IZT",
    "filename": "CharacterDesign-IZT-V1.safetensors", 
    "trigger_word": "CharacterDesignIZT",
    "weight": 0.8
}

OUTPUT_DIR = os.path.join("frontend", "public", "assets", "player_cards_test")

# ==========================================

class StableDiffusionClient:
    def __init__(self):
        self.url = BASE_URL
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR, exist_ok=True)

    def get_current_model(self):
        try:
            res = requests.get(f"{self.url}/sdapi/v1/options", timeout=5)
            return res.json().get('sd_model_checkpoint', '')
        except:
            return None

    def switch_model(self, target_model):
        current = self.get_current_model()
        
        def clean(n): return os.path.basename(n).split('.')[0] if n else ""
        
        if current and clean(target_model) in clean(current):
            return current

        print(f"⚡ [系統] 切換模型: {clean(target_model)} ...")
        
        try:
            requests.post(f"{self.url}/sdapi/v1/options", json={"sd_model_checkpoint": target_model})
        except:
            pass

        start = time.time()
        while True:
            if time.time() - start > 60:
                print("⚠️ 切換超時")
                break
                
            new_model = self.get_current_model()
            if new_model and clean(target_model) in clean(new_model):
                print(f"✅ 模型就緒！耗時: {time.time() - start:.2f}s")
                time.sleep(0.5)
                return new_model
            
            time.sleep(1)

    def generate_image(self, payload, output_filename):
        try:
            res = requests.post(f"{self.url}/sdapi/v1/txt2img", json=payload)
            if res.status_code == 200:
                data = base64.b64decode(res.json()['images'][0])
                with open(os.path.join(OUTPUT_DIR, output_filename), 'wb') as f:
                    f.write(data)
                return True
            return False
        except Exception as e:
            print(f"❌: {e}")
            return False

class PromptBuilder:
    @staticmethod
    def build(player_data, model_name, use_lora):
        prompts = []
        if "Noobai" in model_name:
            prompts.append("masterpiece, best quality, anime style, cel shading")
        elif "furrytoon" in model_name.lower():
            prompts.append("masterpiece, best quality, furry, kemono, fluffy, detailed fur")
        elif "prefectious" in model_name.lower():
            prompts.append("masterpiece, best quality, photorealistic, 8k, cinematic lighting")
        else:
            prompts.append("masterpiece, best quality")

        prompts.append("1boy, solo, anthropomorphic cat, cat ears, cat tail, basketball uniform, holding basketball")
        prompts.append(f"{player_data['color']} fur, {player_data['eyes']} eyes, action: {player_data['action']}")

        if use_lora:
            prompts.append(LORA_CONFIG['trigger_word'])
            prompts.append(f"<lora:{LORA_CONFIG['name']}:{LORA_CONFIG['weight']}>")

        return ", ".join(prompts)

def generate_html_report(history, output_dir):
    """生成 HTML 報告並儲存"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ASBL AI 生成報告</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }
            h1 { text-align: center; color: #ff9800; margin-bottom: 30px; }
            .gallery { 
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); 
                gap: 20px; 
            }
            .card { 
                background: #2d2d2d; 
                border-radius: 10px; 
                overflow: hidden; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
                transition: transform 0.2s;
            }
            .card:hover { transform: translateY(-5px); }
            .card img { 
                width: 100%; 
                height: auto; 
                display: block; 
                border-bottom: 2px solid #444;
            }
            .info { padding: 15px; font-size: 0.9em; }
            .row { display: flex; justify-content: space-between; margin-bottom: 5px; }
            .label { color: #888; }
            .val { font-weight: bold; }
            .model-name { color: #4fc3f7; word-break: break-all; font-size: 0.85em; margin-bottom: 8px;}
            .tag-lora { background: #e91e63; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
            .tag-no-lora { background: #555; color: #aaa; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
        </style>
    </head>
    <body>
        <h1>🏀 ASBL 球員卡生成報告</h1>
        <div class="gallery">
    """

    for item in history:
        lora_tag = '<span class="tag-lora">LoRA: ON</span>' if item['use_lora'] else '<span class="tag-no-lora">LoRA: OFF</span>'
        # 簡化模型名稱顯示
        model_display = os.path.basename(item['model'])
        
        html_content += f"""
            <div class="card">
                <a href="{item['filename']}" target="_blank">
                    <img src="{item['filename']}" alt="Player Card" loading="lazy">
                </a>
                <div class="info">
                    <div class="model-name">🧩 {model_display}</div>
                    <div class="row">
                        <span class="val">ID: {item['id']}</span>
                        {lora_tag}
                    </div>
                    <div class="row">
                        <span class="label">動作:</span>
                        <span class="val">{item['player_data']['action']}</span>
                    </div>
                    <div class="row">
                        <span class="label">毛色:</span>
                        <span class="val">{item['player_data']['color']}</span>
                    </div>
                </div>
            </div>
        """

    html_content += """
        </div>
        <p style="text-align:center; margin-top:30px; color:#666;">Generated by ASBL Tools</p>
    </body>
    </html>
    """

    report_path = os.path.join(output_dir, "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return report_path

def main():
    client = StableDiffusionClient()
    actions = ["dunking", "shooting", "dribbling", "defense", "resting"]
    colors = ["white", "black", "orange", "grey", "calico"]
    
    print("🚀 [ASBL] 啟動極速生成 (128GB RAM Optimized)...")
    
    tasks = []
    for i in range(1, 11):
        tasks.append({
            "id": i,
            "model": random.choice(MODEL_LIST),
            "use_lora": random.choice([True, False]),
            "player_data": {"color": random.choice(colors), "eyes": "yellow", "action": random.choice(actions)}
        })

    tasks.sort(key=lambda x: x['model'])
    
    print(f"📋 任務已排序，準備執行 {len(tasks)} 張圖...")

    history = []
    for t in tasks:
        client.switch_model(t['model'])
        
        prompt = PromptBuilder.build(t['player_data'], t['model'], t['use_lora'])
        payload = {
            "prompt": prompt,
            "negative_prompt": "lowres, bad anatomy, error, worst quality, low quality",
            "steps": 20,
            "cfg_scale": 7,
            "width": 832,
            "height": 1216,
            "sampler_name": "Euler a"
        }
        
        fname = f"test_{t['id']:02d}_{t['model'].split(' ')[0]}.png"
        
        # 將檔名存回 task 物件，供報告使用
        t['filename'] = fname
        
        print(f"   🎨 [{t['id']:02d}] {t['model'][:10]}... {'+LoRA' if t['use_lora'] else ''} -> ", end="")
        sys.stdout.flush()
        
        s = time.time()
        if client.generate_image(payload, fname):
            print(f"OK ({time.time()-s:.1f}s)")
            history.append(t)
        else:
            print("Failed")

    print("\n🎉 生成完成！正在製作網頁報告...")
    
    # 生成並開啟報告
    report_file = generate_html_report(history, OUTPUT_DIR)
    print(f"📄 報告已儲存: {report_file}")
    
    # 轉換為絕對路徑以確保瀏覽器能正確開啟
    abs_path = os.path.abspath(report_file)
    webbrowser.open(f"file://{abs_path}")

if __name__ == "__main__":
    main()
