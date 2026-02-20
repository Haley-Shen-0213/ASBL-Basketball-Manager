# ASBL AI 球員卡牌生成規格書 (v1.0)

**版本**: 1.0
**文件類型**: 系統規格 (System Specification)
**狀態**: 已定案 (Confirmed)
**最後更新**: 2026-02-19
**核心邏輯**: **中上構圖 + 動作權重池 + 全屬性視覺映射**

---

## 1. 產出定義 (Output Contract)

### 1.1 基礎規格
*   **尺寸**: **768 x 1024** (直式 3:4)
*   **格式**: PNG (無損壓縮)
*   **主體**: 單一 Q 版擬人化貓咪 (Anthropomorphic Chibi Cat)。

### 1.2 嚴格內容限制 (Strict Constraints)
*   **❌ 禁止項目**:
    *   任何可讀文字、數字、Logo、隊名。
    *   場景物件 (籃框、觀眾席、地板標線)。
    *   **禁止重傷輔具**: 拐杖 (Crutches)、輪椅 (Wheelchair)、石膏 (Cast)。
*   **✅ 允許項目**:
    *   背景僅由 **光線**、**顏色**、**幾何圖形** 構成。
    *   **下方留白**: 預留空間給前端 CSS 疊加數據。

---

## 2. 構圖規範 (Composition - Bottom HUD Layout)

*   **角色佔比**: **70% ~ 80%**。
*   **位置**: **置中偏上 (Center-High)**。
    *   *目的*: 角色頭部接近頂端（保留少許邊距），**腳部下方保留 20% ~ 25% 的乾淨空間**，用於放置稀有度 (Grade) 與 總評 (Rating) 的 UI 面板。
*   **鏡頭焦段**: **中景 (Full Body Shot)**。
*   **安全區**: 左右邊緣 5% 空白，頭頂 5% 空白。

---

## 3. 屬性驅動動作權重 (Stat-Driven Action Weights)

程式碼需檢查球員屬性，將符合條件的動作加入 **權重池 (Weighted Pool)**，再進行隨機抽取。

| 關聯屬性 (>80) | 動作代碼 (Prompt) | 權重 | 描述 |
| :--- | :--- | :--- | :--- |
| **運球 (Dribble)** | `crossover` | 50 | 壓低重心，大幅度換手運球。 |
| **運球 (Dribble)** | `dribble_low` | 30 | 側身護球，眼神銳利。 |
| **投籃技巧 (Accuracy)** | `fadeaway` | 50 | 後仰跳投，單腳抬起。 |
| **投籃技巧 (Accuracy)** | `jump_shot` | 30 | 標準跳投姿勢。 |
| **彈跳 (Jump)** | `dunk_tomahawk` | 50 | 戰斧式扣籃 (單手後拉)。 |
| **彈跳 (Jump)** | `dunk_power` | 30 | 雙手掛框/扣籃。 |
| **籃板 (Rebound)** | `rebound_reach` | 50 | 雙手高舉爭搶空中的球。 |
| **干擾/抄截 (Defense)** | `defense_stance` | 40 | 張開雙臂，防守步伐。 |
| **傳球 (Pass)** | `no_look_pass` | 40 | 眼神看向別處，雙手傳球。 |
| **(無 / 通用)** | `holding_ball_hip` | 10 | 單手抱球於腰間 (預設)。 |
| **(無 / 通用)** | `finger_spin` | 5 | 手指轉球 (彩蛋動作)。 |

---

## 4. 稀有度特效字典 (Rarity FX Dictionary)

**G 與 C 正式拆分**，強調入門與普通的差異。

| 等級 | 關鍵詞 (Prompt Keywords) | 視覺效果 |
| :--- | :--- | :--- |
| **G (入門)** | `matte flat background, desaturated color, no particles, simple paper texture` | **消光/紙質感**：灰階或低飽和，無光效，像新手練習卡。 |
| **C (普通)** | `clean solid color background, minimal geometric shapes, soft lighting` | **乾淨色塊**：色彩飽和，簡單幾何，無雜訊。 |
| **B (非凡)** | `gradient background, layered geometry, subtle rim light` | **漸層/層次**：雙色漸層，幾何有前後層次。 |
| **A (稀有)** | `neon glowing lines, tech grid, vivid contrast, spotlight` | **霓虹線條**：科技感網格，強烈聚光燈。 |
| **S (史詩)** | `dynamic speed lines, motion blur, strong backlight, energy streaks` | **動態速度**：放射線，背光剪影，能量流動。 |
| **SS (傳說)** | `floating light particles, holographic shards, intense bloom, cinematic lighting` | **全像粒子**：漂浮光塵，全像折射，電影級光影。 |
| **SSR (神話)** | `golden divine aura, iridescent refraction, complex fractal geometry, god rays, masterpiece` | **神聖光環**：金色氣場，複雜碎形，神聖光芒。 |

---

## 5. 生理與能力特徵映射 (Full Attribute Mapping)

使用權重語法 `(keyword:weight)` 實現連續性變化。

### 5.1 身體素質 (Physical)

| 屬性 | 映射邏輯 | Prompt 注入 |
| :--- | :--- | :--- |
| **身高 (Height)** | **160~230cm** | `(tall stature:{w}), (long legs:{w})` <br> *w = 1.0 + (Height-195)*0.015* |
| **力量 (Strength)** | **1~99** | `(muscular build:{w}), (broad shoulders:{w})` <br> *w = 0.8 + (Strength*0.006)* |
| **年齡 (Age)** | **18~35** | `(young cute face:{w_y}), (mature serious expression:{w_o})` |

### 5.2 運動能力 (Ability - Continuous)

| 屬性 | 映射邏輯 | Prompt 注入 | 視覺效果 |
| :--- | :--- | :--- | :--- |
| **速度 (Speed)** | **1~99** <br> *w = 0.5 + (Speed * 0.01)* | `(wind blowing fur:{w}), (dynamic motion:{w})` | **風動感**：速度越快，毛髮飄動與殘影感越強。 |
| **彈跳 (Jump)** | **1~99** <br> *w = 0.8 + (Jump * 0.008)* | `(feet off ground:{w}), (mid-air suspension:{w})` | **滯空感**：彈跳越高，離地感與懸浮感越強。 |

### 5.3 狀態與健康 (Status)

| 屬性 | 觸發條件 | Prompt 注入 | 視覺效果 |
| :--- | :--- | :--- | :--- |
| **體力 (Stamina)** | **> 80** | `(energetic expression:1.2), (sparkles around:0.8)` | 精神奕奕，眼神發亮。 |
| **體力 (Stamina)** | **< 40** | `(sweating:1.2), (heavy breathing:1.0), (tired expression:1.0)` | 流汗，略顯疲態但堅持。 |
| **健康 (Health)** | **< 50** | `(bandages on legs:1.3), (kinesiology tape on shoulder:1.2), (athletic tape:1.2)` | **繃帶/肌貼**：暗示帶傷上陣 (無拐杖)。 |
| **健康 (Health)** | **> 80** | `(pristine condition:1.1)` | 無繃帶，身體狀態完美。 |

---

## 6. 提示詞工程 (Prompt Template)

```python
# Python f-string 範例

positive_prompt = f"""
(score_9, score_8_up, masterpiece, best quality, source_anime),

// 主體與生理特徵
(anthropomorphic chibi cat:1.2), full body, 
(tall stature:{h_weight:.2f}), (muscular build:{str_weight:.2f}),
{age_prompt}, 

// 運動能力特徵 (速度/彈跳)
(wind blowing fur:{spd_weight:.2f}), (dynamic motion:{spd_weight:.2f}),
(feet off ground:{jump_weight:.2f}), (mid-air suspension:{jump_weight:.2f}),

// 狀態特徵 (體力/健康)
{stamina_prompt}, {health_prompt},

// 動作與服裝 (由權重池選出)
{selected_action}, 
basketball uniform, {uniform_style}, {team_color} color scheme, sneakers,
simple geometric emblem on chest,

// 背景與稀有度
abstract geometric background, {rarity_fx}, 

// 構圖控制 (重要!)
(clean bottom background:1.3), (negative space at bottom:1.3),
no other objects, solo, centered composition, studio lighting
"""

negative_prompt = """
score_6, score_5, score_4,
text, logo, watermark, signature, jersey number, numbers, letters,
basketball hoop, net, bleachers, crowd, stadium, audience,
human face, human skin, bad anatomy, missing limbs, extra digits,
crutches, wheelchair, cast, // 禁止重傷輔具
cropped, cut off, out of frame, blurry, lowres
"""
```

---

## 7. 檔案命名 (Naming)

*   **格式**: `player_{id}.png`
*   **路徑**: `frontend/public/assets/cards/`