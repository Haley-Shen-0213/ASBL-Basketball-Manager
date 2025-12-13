# tests/big_data/verify_kpi_v2_6_final_release.py
import os
import sys
import time
import re
import polars as pl
from scipy.stats import norm
import numpy as np
from pathlib import Path
from datetime import datetime

# ================= 路徑修正 =================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
# ===========================================

# ================= 設定 =================
DATA_DIR = os.path.join(current_dir, 'output', 'run_v2_6_dataset_20251212')
LOG_FILE = os.path.join(current_dir, 'logs', 'execution_history.log')

# 修改報告輸出路徑至 docs 資料夾
DOCS_DIR = os.path.join(project_root, 'docs')
REPORT_FILE = os.path.join(DOCS_DIR, 'KPI_Validation_Report_v2_6.md')

# 確保 docs 資料夾存在
if not os.path.exists(DOCS_DIR):
    os.makedirs(DOCS_DIR)
# =======================================

# 欄位定義
UNTRAINABLE_COLS = [
    'physical_stamina', 'physical_strength', 'physical_speed', 'physical_jumping', 'physical_health',
    'offense_touch', 'offense_release', 
    'mental_off_iq', 'mental_def_iq', 'mental_luck'
]

TRAINABLE_COLS = [
    'offense_accuracy', 'offense_range', 
    'offense_passing', 'offense_dribble', 'offense_handle', 'offense_move',
    'defense_rebound', 'defense_boxout', 'defense_contest', 'defense_disrupt'
]

# ================= 工具類別：雙向輸出 Logger =================
class ReportLogger(object):
    """將 print 內容同時輸出到終端機與 Markdown 檔案"""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")
        
        # 寫入 Markdown 檔頭
        header = f"# ASBL v2.6 Big Data Validation Report\n"
        header += f"> Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        header += "```text\n"
        self.log.write(header)

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def close(self):
        # 寫入 Markdown 結尾
        self.log.write("\n```\n")
        self.log.close()

# ================= 格式化函式 =================
def fmt_pct(count, total):
    """通用格式化：若小於 0.01% 且不為 0，顯示數量"""
    if total == 0: return "0.00%"
    pct = (count / total) * 100
    pct_str = f"{pct:6.4f}%"
    if pct < 0.01 and count > 0:
        return f"{pct_str} (n={count})"
    return pct_str

def fmt_matrix_cell(count, total, width=18):
    """矩陣表格專用格式化"""
    if count == 0: return "0.0000%".rjust(width)
    pct = (count / total) * 100
    if pct < 0.01:
        s = f"{pct:.4f}% (n={int(count)})"
    else:
        s = f"{pct:.4f}%"
    return s.rjust(width)

def analyze_execution_log():
    """解析 Log 檔案產生執行報告"""
    print("📊 [執行摘要報告] Execution Summary Report")
    print("-" * 100)
    
    if not os.path.exists(LOG_FILE):
        print(f"⚠️ 找不到 Log 檔: {LOG_FILE}，跳過 Log 分析。")
        return

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        start_time = None
        end_time = None
        total_count = 0
        peak_ram = 0.0
        peak_cpu = 0.0
        
        for line in lines:
            if "[START" in line:
                parts = line.split(']')
                try:
                    start_time = datetime.strptime(parts[0].strip('['), "%Y-%m-%d %H:%M:%S")
                except: pass
            if "[COMPLETE" in line:
                parts = line.split(']')
                try:
                    end_time = datetime.strptime(parts[0].strip('['), "%Y-%m-%d %H:%M:%S")
                except: pass
                # 解析 Count
                if "Count:" in line:
                    try:
                        total_count = int(line.split("Count:")[1].split("|")[0].strip())
                    except: pass
            
            # 解析資源使用
            if "RAM:" in line:
                try:
                    ram_str = line.split("RAM:")[1].split("GB")[0].strip()
                    peak_ram = max(peak_ram, float(ram_str))
                except: pass
            if "CPU:" in line:
                try:
                    cpu_str = line.split("CPU:")[1].split("%")[0].strip()
                    peak_cpu = max(peak_cpu, float(cpu_str))
                except: pass

        print(f"• Log 檔案:      {LOG_FILE}")
        if start_time and end_time:
            duration = end_time - start_time
            total_seconds = duration.total_seconds()
            print(f"• 執行時間:      {start_time} ~ {end_time}")
            print(f"• 總耗時:        {duration}")
            if total_count > 0:
                print(f"• 總生成筆數:    {total_count:,}")
                print(f"• 平均速度:      {total_count / total_seconds:.2f} 筆/秒")
        
        print(f"• 記憶體峰值:    {peak_ram:.2f} GB")
        print(f"• CPU 峰值:      {peak_cpu:.1f}%")
        print("-" * 100)
        print()

    except Exception as e:
        print(f"⚠️ Log 解析失敗: {e}")
        print("-" * 100)

def verify_kpi_final():
    # 0. 顯示執行報告
    analyze_execution_log()

    print(f"🚀 [ASBL v2.6] 啟動最終版 KPI 驗收程序 (Final Release)")
    print(f"📂 資料來源: {DATA_DIR}")
    print("-" * 120)
    
    start_time = time.time()
    
    # 1. 載入資料
    try:
        lf = pl.scan_parquet(os.path.join(DATA_DIR, "*.parquet"))
        
        lf = lf.with_columns([
            # 身高區間
            pl.when(pl.col("height") < 190).then(pl.lit("< 190"))
              .when((pl.col("height") >= 190) & (pl.col("height") <= 199)).then(pl.lit("190-199"))
              .when((pl.col("height") >= 200) & (pl.col("height") <= 209)).then(pl.lit("200-209"))
              .otherwise(pl.lit(">= 210")).alias("pos_height_bin"),
            
            # 身高切片
            (pl.col("height") // 10 * 10).cast(pl.Int32).alias("height_slice"),

            # 屬性總和
            pl.sum_horizontal(UNTRAINABLE_COLS).alias("untrainable_sum"),
            pl.sum_horizontal(TRAINABLE_COLS).alias("trainable_sum"),
            
            # 技術屬性切片
            (pl.sum_horizontal(TRAINABLE_COLS) // 100 * 100).cast(pl.Int32).alias("trainable_slice")
        ])
        
        print("⏳ 正在掃描並聚合 1 億筆資料 (這可能需要幾分鐘)...")
        df = lf.collect()
        
    except Exception as e:
        print(f"❌ 讀取失敗: {e}")
        return

    total_count = len(df)
    print(f"✅ 資料載入完成: {total_count:,} 筆 (耗時 {time.time()-start_time:.2f}s)\n")

    # ==========================================
    # KPI 3.1 A: 身高分佈 (4位小數)
    # ==========================================
    print("📊 [KPI 3.1 A] 身高分佈與極端值監測")
    print("   理論模型: Mean=195, SD=10")
    print("-" * 120)
    
    height_dist = df.group_by('height_slice').len().sort('height_slice')
    height_dist = height_dist.with_columns((pl.col('len') / total_count).alias('actual_prob'))
    
    print(f"{'Slice (cm)':<12} | {'Actual %':<12} | {'Theory %':<12} | {'Diff %':<12} | {'Status'}")
    print("-" * 120)

    mean, std = 195, 10
    slices = range(160, 240, 10) 
    
    for s_start in slices:
        s_end = s_start + 10
        if s_start >= 230: continue 
        actual_row = height_dist.filter(pl.col('height_slice') == s_start)
        actual_prob = actual_row['actual_prob'][0] if not actual_row.is_empty() else 0.0
        prob_theory = norm(mean, std).cdf(s_end) - norm(mean, std).cdf(s_start)
        diff = actual_prob - prob_theory
        status = "✅" if abs(diff) < 0.015 else "❌" 
        print(f"{s_start}-{s_end-1}cm    | {actual_prob*100:>8.4f}%   | {prob_theory*100:>8.4f}%   | {diff*100:>+8.4f}%   | {status}")

    # 極端值逐公分詳細監測
    print("-" * 120)
    print("🔍 極端值逐公分詳細監測 (Per cm Breakdown):")
    
    height_counts_df = df.group_by('height').len()
    h_map = dict(height_counts_df.iter_rows())

    def print_cm_detail(start, end, label):
        print(f"\n   >>> {label} ({start}-{end} cm)")
        print(f"   {'Height':<8} | {'Count':<10} | {'Actual %':<12} | {'Theory %':<12} | {'Diff %':<12}")
        print(f"   {'-'*70}")
        
        total_in_range = 0
        
        for h in range(start, end + 1):
            count = h_map.get(h, 0)
            total_in_range += count
            pct = count / total_count
            theory = norm(mean, std).cdf(h + 1) - norm(mean, std).cdf(h)
            diff = pct - theory
            print(f"   {h:<3} cm   | {count:>8,} | {pct*100:>9.4f}%  | {theory*100:>9.4f}%  | {diff*100:>+9.4f}%")
        
        print(f"   {'-'*70}")
        print(f"   Total    | {total_in_range:>8,} | {(total_in_range/total_count)*100:>9.4f}%")

    print_cm_detail(160, 169, "Low Extreme")
    print_cm_detail(221, 230, "High Extreme")

    # ==========================================
    # KPI 3.1 B: 位置判定 (4位小數)
    # ==========================================
    print("\n📊 [KPI 3.1 B] 位置判定矩陣 (Position Assignment)")
    print(f"{'Height Bin':<10} | {'Pos':<4} | {'Target %':<10} | {'Actual %':<22} | {'Diff %':<10} | {'Check'}")
    print("-" * 120)
    
    bin_counts = df['pos_height_bin'].value_counts()
    bin_map = {r['pos_height_bin']: r['count'] for r in bin_counts.to_dicts()}
    pos_counts = df.group_by(['pos_height_bin', 'position']).len()
    
    specs = [
        ('< 190', {'PG': 60, 'SG': 40}),
        ('190-199', {'PG': 35, 'SG': 45, 'SF': 20}),
        ('200-209', {'PF': 50, 'SF': 20, 'C': 15, 'SG': 10, 'PG': 5}),
        ('>= 210', {'C': 45, 'PF': 30, 'SF': 10, 'SG': 10, 'PG': 5}),
    ]
    
    for h_bin, targets in specs:
        bin_total = bin_map.get(h_bin, 0)
        if bin_total == 0: continue
        print(f"[{h_bin}] (Total: {bin_total:,})")
        for pos, target_pct in targets.items():
            actual_row = pos_counts.filter((pl.col('pos_height_bin') == h_bin) & (pl.col('position') == pos))
            actual_count = actual_row['len'][0] if not actual_row.is_empty() else 0
            actual_pct = (actual_count / bin_total) * 100
            diff = actual_pct - target_pct
            status = "✅" if abs(diff) < 1.0 else "❌"
            
            actual_str = f"{actual_pct:>8.4f}% ({actual_count})"
            print(f"{'':<10} | {pos:<4} | {target_pct:>8.4f}% | {actual_str:<22} | {diff:>+8.4f}% | {status}")
        print("-" * 120)

    # ==========================================
    # KPI 3.3: 天賦生成詳細驗證 (整數顯示)
    # ==========================================
    print("\n📊 [KPI 3.3] 天賦生成詳細驗證 (Untrainable Stats)")
    print("-" * 120)
    
    print("🔍 (A) 總分區間合規性 (Total Sum Check):")
    untrainable_specs = {
        'G': (10, 400), 'C': (399, 600), 'B': (599, 700),
        'A': (699, 800), 'S': (799, 900), 'SS': (900, 950), 'SSR': (951, 990)
    }
    u_stats = df.group_by('grade').agg([
        pl.col('untrainable_sum').min().alias('min'),
        pl.col('untrainable_sum').max().alias('max'),
        pl.col('untrainable_sum').mean().alias('avg')
    ]).to_pandas().set_index('grade')
    
    print(f"{'Grade':<6} | {'Spec Range':<15} | {'Actual Range':<15} | {'Avg':<6} | {'Status'}")
    for g in ['G', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
        spec_min, spec_max = untrainable_specs[g]
        row = u_stats.loc[g]
        status = "✅"
        if row['min'] < spec_min or row['max'] > spec_max:
            status = f"❌ (Violated)"
        print(f"{g:<6} | {spec_min}-{spec_max:<15} | {int(row['min'])}-{int(row['max']):<15} | {int(row['avg']):<6} | {status}")

    # ==========================================
    # KPI 3.3 B: 單項極值分佈
    # ==========================================
    print("\n🔍 (B) 單項屬性全量分佈 (Full Stat Distribution):")
    print("   目標: 驗證所有 20 個屬性是否均勻分佈。")
    print(f"{'Stat Name':<20} | {'1-10':<15} | {'11-40':<15} | {'41-60':<15} | {'61-89':<15} | {'90-99':<15}")
    print("-" * 120)
    
    all_stats_cols = UNTRAINABLE_COLS + TRAINABLE_COLS
    for col in all_stats_cols:
        counts = df.select([
            pl.col(col).filter((pl.col(col) >= 1) & (pl.col(col) <= 10)).len().alias('c1'),
            pl.col(col).filter((pl.col(col) >= 11) & (pl.col(col) <= 40)).len().alias('c2'),
            pl.col(col).filter((pl.col(col) >= 41) & (pl.col(col) <= 60)).len().alias('c3'),
            pl.col(col).filter((pl.col(col) >= 61) & (pl.col(col) <= 89)).len().alias('c4'),
            pl.col(col).filter((pl.col(col) >= 90) & (pl.col(col) <= 99)).len().alias('c5')
        ]).to_dicts()[0]
        
        print(f"{col:<20} | {fmt_pct(counts['c1'], total_count):<15} | {fmt_pct(counts['c2'], total_count):<15} | {fmt_pct(counts['c3'], total_count):<15} | {fmt_pct(counts['c4'], total_count):<15} | {fmt_pct(counts['c5'], total_count):<15}")

    # ==========================================
    # KPI 3.4: 技術生成驗證
    # ==========================================
    print("\n📊 [KPI 3.4] 技術生成驗證 (Trainable Stats)")
    print("-" * 120)
    
    caps = {'G': 800, 'C': 700, 'B': 650, 'A': 600, 'S': 550, 'SS': 550, 'SSR': 550}
    
    print("🔍 (A) 切片分佈 (每 100 分):")
    slice_matrix = df.group_by(['grade', 'trainable_slice']).len()
    grade_totals = df.group_by('grade').len().rename({'len': 'g_total'})
    
    slice_pivot_count = slice_matrix.to_pandas().pivot(index='grade', columns='trainable_slice', values='len').fillna(0)
    cols = sorted(slice_pivot_count.columns)
    slice_pivot_count = slice_pivot_count[cols]
    slice_pivot_count = slice_pivot_count.reindex(['G', 'C', 'B', 'A', 'S', 'SS', 'SSR'])
    
    g_total_map = {row['grade']: row['g_total'] for row in grade_totals.to_dicts()}
    
    col_width = 18
    header = "Grade  | " + " | ".join([f"{c}-{c+99}".center(col_width) for c in cols])
    print(header)
    print("-" * len(header))
    
    for g, row in slice_pivot_count.iterrows():
        g_total = g_total_map.get(g, 0)
        vals_str = []
        for count in row:
            vals_str.append(fmt_matrix_cell(count, g_total, width=col_width))
        print(f"{g:<6} | {' | '.join(vals_str)}")

    print("\n🔍 (B) 極值監測 (Extreme Values):")
    print(f"{'Grade':<6} | {'Cap':<5} | {'Trash (<100)':<20} | {'Elite (>Cap-50)':<20} | {'Max Val':<8}")
    print("-" * 120)
    
    t_stats = df.group_by('grade').agg([
        pl.col('trainable_sum').max().alias('max_val'),
        pl.col('trainable_sum').filter(pl.col('trainable_sum') < 100).len().alias('trash_cnt'),
    ]).to_pandas().set_index('grade')
    
    for g in ['G', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
        cap = caps[g]
        row = t_stats.loc[g]
        g_total = g_total_map.get(g, 0)
        elite_cnt = len(df.filter((pl.col('grade') == g) & (pl.col('trainable_sum') > cap - 50)))
        
        print(f"{g:<6} | {cap:<5} | {fmt_pct(row['trash_cnt'], g_total):<20} | {fmt_pct(elite_cnt, g_total):<20} | {row['max_val']:<8}")

    # ==========================================
    # KPI 3.5: 年齡分佈 (移動至此)
    # ==========================================
    print("\n📊 [KPI 3.5] 年齡分佈驗證 (Age Distribution)")
    print("   規則: SSR=18(100%), SS=18-19(50%), S=18-20, A=18-21, B=18-22, C=18-23, G=18-24")
    print(f"{'Grade':<6} | {'Age Range':<10} | {'Target %':<10} | {'Check'}")
    print("-" * 120)

    age_rules = {
        'SSR': (18, 18), 'SS': (18, 19), 'S': (18, 20),
        'A': (18, 21), 'B': (18, 22), 'C': (18, 23), 'G': (18, 24)
    }

    for g, (min_a, max_a) in age_rules.items():
        g_total = len(df.filter(pl.col('grade') == g))
        if g_total == 0: continue

        num_choices = max_a - min_a + 1
        target_pct = 100.0 / num_choices
        
        outliers = len(df.filter((pl.col('grade') == g) & ((pl.col('age') < min_a) | (pl.col('age') > max_a))))
        
        is_uniform = True
        dist_lines = []
        for age in range(min_a, max_a + 1):
            cnt = len(df.filter((pl.col('grade') == g) & (pl.col('age') == age)))
            pct = (cnt / g_total) * 100
            dist_lines.append(f"       ↳ {age}歲: {pct:.4f}%")
            if abs(pct - target_pct) > 3.0:
                is_uniform = False
        
        status = "✅" if is_uniform and outliers == 0 else "❌"
        if outliers > 0: status += f" ({outliers} 異常)"

        print(f"{g:<6} | {min_a}-{max_a:<10} | ~{target_pct:.4f}%   | {status}")
        for line in dist_lines:
            print(line)
        print("-" * 60)

    # ==========================================
    # KPI 3.6: 違規與異常檢測 (順延至此)
    # ==========================================
    print("\n🚨 [KPI 3.6] 違規與異常檢測 (Violation Check)")
    print("   目標: 確保沒有任何一筆資料違反硬性規則。")
    print("-" * 120)
    
    violations = []
    
    for g, cap in caps.items():
        violation_cnt = len(df.filter((pl.col('grade') == g) & (pl.col('trainable_sum') > cap)))
        if violation_cnt > 0:
            violations.append(f"❌ [技術屬性上限] 等級 {g} 有 {violation_cnt} 名球員超過上限 {cap}!")
        else:
            print(f"✅ [技術屬性上限] 等級 {g}: 無違規 (最大值 <= {cap})")

    for g, (u_min, u_max) in untrainable_specs.items():
        violation_cnt = len(df.filter((pl.col('grade') == g) & ((pl.col('untrainable_sum') < u_min) | (pl.col('untrainable_sum') > u_max))))
        if violation_cnt > 0:
            violations.append(f"❌ [天賦屬性總和區間] 等級 {g} 有 {violation_cnt} 名球員超出區間 {u_min}-{u_max}!")
        else:
            print(f"✅ [天賦屬性總和區間] 等級 {g}: 無違規")

    for col in all_stats_cols:
        out_of_bound = len(df.filter((pl.col(col) < 1) | (pl.col(col) > 99)))
        if out_of_bound > 0:
            violations.append(f"❌ [單項屬性邊界] 欄位 {col} 有 {out_of_bound} 個數值超出 1-99 範圍!")
    
    if not violations:
        # 修正：使用正確的變數名稱 all_stats_cols
        print(f"✅ [單項屬性邊界] 所有 {len(all_stats_cols)} 個屬性皆在 1-99 範圍內。")
    
    print("-" * 120)
    if len(violations) == 0:
        print("🎉 完美！1 億筆資料全部通過硬性規則檢查。")
    else:
        print(f"⚠️ 發現 {len(violations)} 項違規：")
        for v in violations:
            print(v)

if __name__ == "__main__":
    try:
        from scripts.terminal import clear_terminal
        clear_terminal()
    except ImportError:
        pass
    except Exception:
        pass
    
    # 啟動雙向 Logger
    original_stdout = sys.stdout
    logger = ReportLogger(REPORT_FILE)
    sys.stdout = logger
    
    try:
        verify_kpi_final()
    finally:
        # 恢復 stdout 並關閉檔案
        sys.stdout = original_stdout
        logger.close()
        print(f"\n📄 報告已生成: {REPORT_FILE}")
