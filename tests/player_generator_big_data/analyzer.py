# tests/player_generator_big_data/analyzer.py
import pandas as pd
import numpy as np
import os
import json
import math
import pyarrow.dataset as ds
from datetime import datetime, timedelta
import time

# ==========================================
# 欄位名稱映射表
# ==========================================
FIELD_MAP = {
    # Untrainable
    'physical_stamina': '體力',
    'physical_strength': '力量',
    'physical_speed': '速度',
    'physical_jumping': '彈跳',
    'physical_health': '健康',
    'offense_touch': '手感',
    'offense_release': '出手速度',
    'mental_off_iq': '進攻智商',
    'mental_def_iq': '防守智商',
    'mental_luck': '運氣',
    
    # Trainable
    'offense_accuracy': '投籃準心',
    'offense_range': '射程',
    'offense_passing': '傳球',
    'offense_dribble': '運球',
    'offense_handle': '控球',
    'offense_move': '跑位',
    'defense_rebound': '籃板',
    'defense_boxout': '卡位',
    'defense_contest': '干擾',
    'defense_disrupt': '抄截'
}

# Base Caps Definition for Validation
BASE_CAPS = {'G': 800, 'C': 700, 'B': 650, 'A': 600, 'S': 550, 'SS': 550, 'SSR': 550}

class BigDataAnalyzer:
    def __init__(self, config, data_path):
        self.config = config
        self.data_path = data_path
        self.report_lines = []
        self.meta = {}
        
        # 統計容器 (Aggregators)
        self.stats = {
            'total_rows': 0,
            'grade_counts': {},
            
            # Height
            'height_counts': {}, 
            'height_sum': 0.0,
            'height_sq_sum': 0.0,
            
            # Position Matrix
            'pos_matrix': {}, 
            
            # KPI 3.1.C: Rating by Detailed Height & Grade
            'rating_matrix': {},

            # Untrainable (Sum Ranges)
            'untrainable_sum_ranges': {}, 
            
            # Histograms
            'stat_histograms_by_grade': {}, 
            'stat_histograms_by_pos': {},
            
            # Trainable (Slices & Caps)
            'trainable_slices': {}, 
            'trainable_caps': {}, 
            
            # Age
            'age_dist': {}, 
            
            # Violations & Monitors
            'violations': [],
            
            # KPI 3.6 Small Player Monitor by Grade
            # Key: grade -> {'max': 0, 'count': 0, 'overflow_count': 0}
            'small_player_stats': {} 
        }

    def _log(self, text):
        self.report_lines.append(text)

    def _load_metadata(self):
        meta_path = os.path.join(self.data_path, "execution_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                self.meta = json.load(f)
        else:
            self.meta = {
                "start_time": "N/A", "end_time": "N/A", "duration_seconds": 0,
                "total_rows": 0, "peak_cpu": 0, "peak_ram_gb": 0, "avg_speed": 0
            }

    def run_analysis(self):
        """執行分析並生成報告"""
        self._load_metadata()
        self._write_project_journal()
        self._process_stream()
        
        self._write_execution_summary()
        self._write_height_analysis() 
        self._write_position_matrix() 
        self._write_rating_matrix()   
        self._write_grade_distribution() 
        self._write_untrainable_analysis() 
        self._write_trainable_analysis()   
        self._write_age_analysis()    
        self._write_violations()      
        
        return "\n".join(self.report_lines)

    def _write_project_journal(self):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        self._log(f"# {now_str} 專案開發日誌：ASBL 球員生成系統大數據驗證架構 (v2.6)")
        self._log(f"**Project Journal: ASBL Player Generation System - Big Data Verification Architecture (v2.6)**\n")
        self._log(f"**日期**: {now_str}")
        self._log(f"**參與者**: Product Owner (User), Lead Architect (Monica)")
        self._log(f"**主題**: 定義球員生成器 (v2.6) 的重構動機、測試目標與詳細 KPI 驗收標準\n")
        self._log(f"## 1. 前言：重構動機與測試一致性 (Preface)")
        self._log(f"為了確保程式設計與測試驗證的一致性與效率，我們在進入大數據測試前，對 `PlayerGenerator` 進行了核心重構 (Refactoring to v2.6)。")
        self._log(f"本次測試的核心目標，即是驗證重構後的生成器，其**機率分佈**與**隨機性**是否完全符合數學模型設定。\n")

    def _process_stream(self):
        print("[Analyzer] 開始串流掃描數據 (Aggregation Mode)...")
        t0 = time.time()
        
        files = [
            os.path.join(self.data_path, f) 
            for f in os.listdir(self.data_path) 
            if f.endswith('.parquet')
        ]
        
        if not files:
            print("[Error] 目錄中找不到任何 .parquet 檔案！")
            return

        dataset = ds.dataset(files, format="parquet")
        
        # Bins Definitions
        pos_h_bins = [0, 189, 199, 209, 300]
        pos_h_labels = ['< 190', '190-199', '200-209', '>= 210']
        
        det_h_bins = [0, 169, 179, 189, 199, 209, 219, 300]
        det_h_labels = ['< 170', '170-179', '180-189', '190-199', '200-209', '210-219', '>= 220']
        
        stat_bins = [0, 10, 40, 60, 89, 99]
        
        # Columns
        cols = [
            'grade', 'position', 'height', 'age', 'name', 'rating',
            # Untrainable
            'physical_stamina', 'physical_strength', 'physical_speed', 'physical_jumping', 'physical_health',
            'offense_touch', 'offense_release', 'mental_off_iq', 'mental_def_iq', 'mental_luck',
            # Trainable
            'offense_accuracy', 'offense_range', 'offense_passing', 'offense_dribble', 'offense_handle', 'offense_move',
            'defense_rebound', 'defense_boxout', 'defense_contest', 'defense_disrupt'
        ]
        
        schema_names = dataset.schema.names
        scan_cols = [c for c in cols if c in schema_names]
        
        untrainable_cols = [c for c in scan_cols if c in [
            'physical_stamina', 'physical_strength', 'physical_speed', 'physical_jumping', 'physical_health',
            'offense_touch', 'offense_release', 'mental_off_iq', 'mental_def_iq', 'mental_luck'
        ]]
        trainable_cols = [c for c in scan_cols if c in [
            'offense_accuracy', 'offense_range', 'offense_passing', 'offense_dribble', 'offense_handle', 'offense_move',
            'defense_rebound', 'defense_boxout', 'defense_contest', 'defense_disrupt'
        ]]

        for batch in dataset.to_batches(columns=scan_cols, batch_size=100000):
            df = batch.to_pandas()
            self.stats['total_rows'] += len(df)
            
            # 1. Grade Counts
            g_counts = df['grade'].value_counts()
            for g, c in g_counts.items():
                self.stats['grade_counts'][g] = self.stats['grade_counts'].get(g, 0) + c
                
            # 2. Height Stats
            h_counts = df['height'].value_counts()
            for h, c in h_counts.items():
                self.stats['height_counts'][h] = self.stats['height_counts'].get(h, 0) + c
            
            h_vals = df['height'].values
            self.stats['height_sum'] += np.sum(h_vals)
            self.stats['height_sq_sum'] += np.sum(h_vals ** 2)
            
            # 3. Position Matrix
            pos_h_cuts = pd.cut(df['height'], bins=pos_h_bins, labels=pos_h_labels)
            pos_grp = df.groupby([pos_h_cuts, 'position'], observed=True).size()
            for (h_grp, pos), count in pos_grp.items():
                self.stats['pos_matrix'][(h_grp, pos)] = self.stats['pos_matrix'].get((h_grp, pos), 0) + count
            
            # 3.1.C Rating Matrix
            if 'rating' in df.columns:
                det_h_cuts = pd.cut(df['height'], bins=det_h_bins, labels=det_h_labels)
                rating_grp = df.groupby([det_h_cuts, 'grade'], observed=True)['rating'].agg(['sum', 'count'])
                for (h_grp, grade), row in rating_grp.iterrows():
                    key = (h_grp, grade)
                    if key not in self.stats['rating_matrix']:
                        self.stats['rating_matrix'][key] = {'sum': 0, 'count': 0}
                    self.stats['rating_matrix'][key]['sum'] += row['sum']
                    self.stats['rating_matrix'][key]['count'] += row['count']

            # 4. Histograms by Grade
            grouped_g = df.groupby('grade')
            for grade, sub_df in grouped_g:
                if grade not in self.stats['stat_histograms_by_grade']:
                    self.stats['stat_histograms_by_grade'][grade] = {}
                
                target_cols = untrainable_cols + trainable_cols
                for col in target_cols:
                    counts, _ = np.histogram(sub_df[col], bins=stat_bins)
                    if col not in self.stats['stat_histograms_by_grade'][grade]:
                        self.stats['stat_histograms_by_grade'][grade][col] = np.zeros(len(stat_bins)-1, dtype=int)
                    self.stats['stat_histograms_by_grade'][grade][col] += counts
                    
                    # Check bounds
                    c_min, c_max = sub_df[col].min(), sub_df[col].max()
                    if c_min < 1 or c_max > 99:
                        self.stats['violations'].append(f"等級 {grade} 屬性 {FIELD_MAP.get(col, col)} 超出範圍 1-99 (Val: {c_min}-{c_max})")

            # 5. Histograms by Position
            grouped_p = df.groupby('position')
            for pos, sub_df in grouped_p:
                if pos not in self.stats['stat_histograms_by_pos']:
                    self.stats['stat_histograms_by_pos'][pos] = {}
                for col in trainable_cols:
                    counts, _ = np.histogram(sub_df[col], bins=stat_bins)
                    if col not in self.stats['stat_histograms_by_pos'][pos]:
                        self.stats['stat_histograms_by_pos'][pos][col] = np.zeros(len(stat_bins)-1, dtype=int)
                    self.stats['stat_histograms_by_pos'][pos][col] += counts

            # Untrainable Sum Check
            if untrainable_cols:
                batch_u_sums = df[untrainable_cols].sum(axis=1)
                temp_df = pd.DataFrame({'grade': df['grade'], 'u_sum': batch_u_sums})
                grp_stats = temp_df.groupby('grade')['u_sum'].agg(['min', 'max'])
                for g in grp_stats.index:
                    g_min, g_max = grp_stats.loc[g, 'min'], grp_stats.loc[g, 'max']
                    if g not in self.stats['untrainable_sum_ranges']:
                        self.stats['untrainable_sum_ranges'][g] = {'min': 9999, 'max': 0}
                    curr = self.stats['untrainable_sum_ranges'][g]
                    curr['min'] = min(curr['min'], g_min)
                    curr['max'] = max(curr['max'], g_max)

            # Trainable Stats (Slices & Caps & Small Player Monitor)
            if trainable_cols:
                t_sum = df[trainable_cols].sum(axis=1)
                t_bins = list(range(0, 1001, 100))
                t_cuts = pd.cut(t_sum, bins=t_bins, right=False, labels=False)
                
                slice_grp = df.groupby(['grade', t_cuts], observed=True).size()
                for (g, bin_idx), count in slice_grp.items():
                    if g not in self.stats['trainable_slices']: self.stats['trainable_slices'][g] = {}
                    self.stats['trainable_slices'][g][bin_idx] = self.stats['trainable_slices'][g].get(bin_idx, 0) + count
                    
                temp_t_df = pd.DataFrame({'grade': df['grade'], 't_sum': t_sum})
                grp_max = temp_t_df.groupby('grade')['t_sum'].max()
                trash_mask = temp_t_df['t_sum'] < 100
                grp_trash = temp_t_df[trash_mask].groupby('grade').size()
                
                all_grades = set(grp_max.index) | set(grp_trash.index)
                for g in all_grades:
                    if g not in self.stats['trainable_caps']: 
                        self.stats['trainable_caps'][g] = {'max': 0, 'trash': 0}
                    if g in grp_max:
                        self.stats['trainable_caps'][g]['max'] = max(self.stats['trainable_caps'][g]['max'], grp_max[g])
                    if g in grp_trash:
                        self.stats['trainable_caps'][g]['trash'] += grp_trash[g]
                        
                # Monitor 3.6: Small Player Overflow Check
                is_small = df['height'] <= 189
                if is_small.any():
                    # Create a mini DF for calculation
                    small_df = pd.DataFrame({
                        'grade': df.loc[is_small, 'grade'],
                        't_sum': t_sum[is_small]
                    })
                    
                    # Group by grade to calc stats
                    for grade, sub_df in small_df.groupby('grade'):
                        cap = BASE_CAPS.get(grade, 9999)
                        max_val = sub_df['t_sum'].max()
                        count = len(sub_df)
                        overflow_count = (sub_df['t_sum'] > cap).sum()
                        
                        if grade not in self.stats['small_player_stats']:
                            self.stats['small_player_stats'][grade] = {'max': 0, 'count': 0, 'overflow_count': 0}
                        
                        s = self.stats['small_player_stats'][grade]
                        s['max'] = max(s['max'], max_val)
                        s['count'] += count
                        s['overflow_count'] += overflow_count

            # 6. Age Distribution
            age_grp = df.groupby(['grade', 'age']).size()
            for (g, age), count in age_grp.items():
                if g not in self.stats['age_dist']: self.stats['age_dist'][g] = {}
                self.stats['age_dist'][g][age] = self.stats['age_dist'][g].get(age, 0) + count
                
            if self.stats['total_rows'] % 5000000 == 0:
                print(f"  Processed {self.stats['total_rows']/1000000:.0f}M rows...")
                
        print(f"[Analyzer] 掃描完成。耗時: {time.time() - t0:.2f} 秒")

    def _write_execution_summary(self):
        m = self.meta
        duration_str = str(timedelta(seconds=int(m['duration_seconds'])))
        
        self._log("📊 [執行摘要報告] Execution Summary Report")
        self._log("-" * 100)
        self._log(f"• Log 檔案:      {os.path.join(self.data_path, 'execution_meta.json')}")
        self._log(f"• 執行時間:      {m['start_time']} ~ {m['end_time']}")
        self._log(f"• 總耗時:        {duration_str}")
        self._log(f"• 總生成筆數:    {m['total_rows']:,}")
        self._log(f"• 平均速度:      {m['avg_speed']:.2f} 筆/秒")
        self._log(f"• 記憶體峰值:    {m['peak_ram_gb']:.2f} GB")
        self._log(f"• CPU 峰值:      {m['peak_cpu']:.1f}%")
        self._log("-" * 100 + "\n")

    def _get_normal_prob(self, start, end, mean=195, std=10):
        cdf_end = 0.5 * (1 + math.erf((end - mean) / (std * 2**0.5)))
        cdf_start = 0.5 * (1 + math.erf((start - mean) / (std * 2**0.5)))
        return cdf_end - cdf_start

    def _write_height_analysis(self):
        self._log("📊 [KPI 3.1 A] 身高分佈與極端值監測")
        self._log("   理論模型: Mean=195, SD=10")
        self._log("-" * 120)
        self._log(f"{'Slice (cm)':<12} | {'Actual %':<12} | {'Theory %':<12} | {'Diff %':<12} | Status")
        self._log("-" * 120)
        
        slices = [
            (160, 169), (170, 179), (180, 189), (190, 199),
            (200, 209), (210, 219), (220, 229)
        ]
        total = self.stats['total_rows']
        if total == 0: return

        for s_min, s_max in slices:
            count = sum(self.stats['height_counts'].get(h, 0) for h in range(s_min, s_max + 1))
            actual_pct = count / total
            theory_pct = self._get_normal_prob(s_min - 0.5, s_max + 0.5)
            diff = actual_pct - theory_pct
            status = "✅" if abs(diff) < 0.015 else "❌"
            self._log(f"{s_min}-{s_max}cm    | {actual_pct:10.4%} | {theory_pct:10.4%} | {diff:+10.4%} | {status}")
        
        self._log("-" * 120)
        self._log("🔍 極端值逐公分詳細監測 (Per cm Breakdown):")
        self._log("\n   >>> Low Extreme (160-169 cm)")
        self._write_height_detail(160, 169)
        self._log("\n   >>> High Extreme (221-230 cm)")
        self._write_height_detail(221, 230)
        self._log("\n")

    def _write_height_detail(self, start, end):
        self._log(f"   {'Height':<8} | {'Count':<10} | {'Actual %':<10} | {'Theory %':<10} | {'Diff %':<10}")
        self._log("   " + "-" * 70)
        total_sub = 0
        for h in range(start, end + 1):
            c = self.stats['height_counts'].get(h, 0)
            total_sub += c
            act = c / self.stats['total_rows']
            theory = self._get_normal_prob(h - 0.5, h + 0.5)
            diff = act - theory
            self._log(f"   {h} cm   | {c:10,} | {act:9.4%} | {theory:9.4%} | {diff:+.4%}")
        self._log("   " + "-" * 70)
        self._log(f"   Total    | {total_sub:10,} | {total_sub/self.stats['total_rows']:9.4%}")

    def _write_position_matrix(self):
        self._log("📊 [KPI 3.1 B] 位置判定矩陣 (Position Assignment)")
        labels = ['< 190', '190-199', '200-209', '>= 210']
        targets = {
            '< 190': {'PG': 0.60, 'SG': 0.40},
            '190-199': {'PG': 0.35, 'SG': 0.45, 'SF': 0.20},
            '200-209': {'PF': 0.50, 'SF': 0.20, 'C': 0.15, 'SG': 0.10, 'PG': 0.05},
            '>= 210': {'C': 0.45, 'PF': 0.30, 'SG': 0.10, 'SF': 0.10, 'PG': 0.05}
        }
        self._log(f"{'Height Bin':<10} | {'Pos':<4} | {'Target %':<10} | {'Actual % (Count)':<22} | {'Diff %':<8} | Check")
        self._log("-" * 120)
        for label in labels:
            row_total = sum(self.stats['pos_matrix'].get((label, p), 0) for p in ['PG', 'SG', 'SF', 'PF', 'C'])
            if row_total == 0: continue
            self._log(f"[{label}] (Total: {row_total:,})")
            t_map = targets.get(label, {})
            sorted_pos = sorted(t_map.keys(), key=lambda x: t_map[x], reverse=True)
            for pos in sorted_pos:
                target = t_map[pos]
                count = self.stats['pos_matrix'].get((label, pos), 0)
                actual = count / row_total
                diff = actual - target
                check = "✅" if abs(diff) < 0.01 else "❌"
                self._log(f"{'':<10} | {pos:<4} | {target:9.4%} | {actual:9.4%} ({count})   | {diff:+.4%} | {check}")
            self._log("-" * 120)
        self._log("\n")

    def _write_rating_matrix(self):
        self._log("📊 [KPI 3.1 C] 身高級距內各等級平均能力值 (Average Rating by 10cm)")
        labels = ['< 170', '170-179', '180-189', '190-199', '200-209', '210-219', '>= 220']
        grades = ['G', 'C', 'B', 'A', 'S', 'SS', 'SSR']
        
        header = f"{'Height Bin':<10} | " + " | ".join([f"{g:^8}" for g in grades])
        self._log("-" * len(header))
        self._log(header)
        self._log("-" * len(header))
        
        for label in labels:
            vals = []
            for g in grades:
                key = (label, g)
                data = self.stats['rating_matrix'].get(key, {'sum': 0, 'count': 0})
                if data['count'] > 0:
                    avg = data['sum'] / data['count']
                    vals.append(f"{avg:^8.1f}")
                else:
                    vals.append(f"{'-':^8}")
            self._log(f"{label:<10} | " + " | ".join(vals))
        self._log("-" * len(header) + "\n")

    def _write_grade_distribution(self):
        self._log("📊 [KPI 3.2] 等級機率分佈 (Grade Drop Rates)")
        targets = {
            'G':   {'target': 0.280, 'tol': 0.010},
            'C':   {'target': 0.260, 'tol': 0.010},
            'B':   {'target': 0.220, 'tol': 0.010},
            'A':   {'target': 0.140, 'tol': 0.010},
            'S':   {'target': 0.070, 'tol': 0.005},
            'SS':  {'target': 0.025, 'tol': 0.005},
            'SSR': {'target': 0.005, 'tol': 0.001}
        }
        self._log(f"{'Grade':<6} | {'Target':<8} | {'Actual':<10} | {'Diff':<10} | {'Tolerance':<10} | Status")
        self._log("-" * 80)
        total = self.stats['total_rows']
        for g in ['G', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
            count = self.stats['grade_counts'].get(g, 0)
            actual = count / total if total > 0 else 0
            t_data = targets[g]
            target = t_data['target']
            tol = t_data['tol']
            diff = actual - target
            status = "✅" if abs(diff) <= tol else f"❌"
            self._log(f"{g:<6} | {target:8.1%} | {actual:10.4%} | {diff:+.4%} | ±{tol:.1%}   | {status}")
        self._log("-" * 80 + "\n")

    def _write_generic_histograms(self, title, data_source, keys, target_cols):
        self._log(title)
        self._log("-" * 120)
        self._log(f"{'Stat Name':<12} | {'1-10':<12} | {'11-40':<12} | {'41-60':<12} | {'61-89':<12} | {'90-99':<12}")
        
        for key in keys:
            if key not in data_source: continue
            self._log(f"\n[Group: {key}]")
            self._log("-" * 80)
            
            group_data = data_source[key]
            for col in target_cols:
                if col not in group_data: continue
                counts = group_data[col]
                total = counts.sum()
                if total == 0: continue
                pcts = counts / total
                cn_name = FIELD_MAP.get(col, col)
                row = f"{cn_name:<12} | " + " | ".join([f"{p:10.4%}" for p in pcts])
                self._log(row)
        self._log("\n")

    def _write_untrainable_analysis(self):
        self._log("📊 [KPI 3.3] 天賦生成詳細驗證 (Untrainable Stats)")
        self._log("-" * 120)
        
        self._log("🔍 (A) 總分區間合規性 (Total Sum Check):")
        self._log(f"{'Grade':<6} | {'Spec Range':<15} | {'Actual Range':<15} | Status")
        specs = {
            'G': (10, 400), 'C': (399, 600), 'B': (599, 700),
            'A': (699, 800), 'S': (799, 900), 'SS': (900, 950), 'SSR': (951, 990)
        }
        for g in ['G', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
            if g not in self.stats['untrainable_sum_ranges']: continue
            data = self.stats['untrainable_sum_ranges'][g]
            spec = specs.get(g, (0,0))
            status = "✅"
            if data['min'] < spec[0] or data['max'] > spec[1]:
                status = f"❌ (Out: {data['min']}~{data['max']})"
            self._log(f"{g:<6} | {spec[0]}-{spec[1]:<10} | {data['min']}-{data['max']:<10} | {status}")
        self._log("\n")

        cols = [
            'physical_stamina', 'physical_strength', 'physical_speed', 'physical_jumping', 'physical_health',
            'offense_touch', 'offense_release', 'mental_off_iq', 'mental_def_iq', 'mental_luck'
        ]
        self._write_generic_histograms(
            "🔍 (B) 天賦屬性分佈 (Untrainable Distribution by Grade)",
            self.stats['stat_histograms_by_grade'],
            ['SSR', 'SS', 'S', 'A', 'B', 'C', 'G'],
            cols
        )

    def _write_trainable_analysis(self):
        self._log("📊 [KPI 3.4] 技術生成驗證 (Trainable Stats)")
        self._log("-" * 120)
        
        self._log("🔍 (A) 總分切片分佈 (Total Score Slices):")
        slices = [f"{i}-{i+99}" for i in range(0, 900, 100)]
        header = f"{'Grade':<6} | " + " | ".join([f"{s:^12}" for s in slices])
        self._log(header)
        self._log("-" * len(header))
        for g in ['G', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
            if g not in self.stats['trainable_slices']: continue
            row_data = self.stats['trainable_slices'][g]
            g_total = sum(row_data.values())
            vals = []
            for i in range(len(slices)):
                c = row_data.get(i, 0)
                if c == 0: vals.append(f"{'0.00%':^12}")
                else:
                    pct = c / g_total
                    if pct < 0.0001: vals.append(f"{pct:.4%} (n={c})")
                    else: vals.append(f"{pct:^12.4%}")
            self._log(f"{g:<6} | " + " | ".join(vals))
        self._log("\n")
        
        self._log("🔍 (B) 極值監測 (Extreme Values):")
        self._log(f"{'Grade':<6} | {'Max Val':<10} | {'Trash (<100)':<15}")
        self._log("-" * 60)
        for g in ['G', 'C', 'B', 'A', 'S', 'SS', 'SSR']:
            if g in self.stats['trainable_caps']:
                d = self.stats['trainable_caps'][g]
                g_total = self.stats['grade_counts'].get(g, 1)
                trash_pct = d['trash'] / g_total
                self._log(f"{g:<6} | {d['max']:<10} | {trash_pct:.4%} (n={d['trash']})")
        self._log("\n")

        cols = [
            'offense_accuracy', 'offense_range', 'offense_passing', 'offense_dribble', 'offense_handle', 'offense_move',
            'defense_rebound', 'defense_boxout', 'defense_contest', 'defense_disrupt'
        ]
        self._write_generic_histograms(
            "🔍 (C) 技術屬性分佈 (Trainable Distribution by Grade)",
            self.stats['stat_histograms_by_grade'],
            ['SSR', 'SS', 'S', 'A', 'B', 'C', 'G'],
            cols
        )
        
        self._write_generic_histograms(
            "🔍 (D) 技術屬性分佈 (Trainable Distribution by Position)",
            self.stats['stat_histograms_by_pos'],
            ['PG', 'SG', 'SF', 'PF', 'C'],
            cols
        )

    def _write_age_analysis(self):
        self._log("📊 [KPI 3.5] 年齡分佈驗證 (Age Distribution)")
        self._log("-" * 120)
        targets = {
            'SSR': [18], 'SS': [18, 19], 'S': [18, 19, 20],
            'A': [18, 19, 20, 21], 'B': range(18, 23), 'C': range(18, 24), 'G': range(18, 25)
        }
        for g, allowed_ages in targets.items():
            if g not in self.stats['age_dist']: continue
            dist = self.stats['age_dist'][g]
            total = sum(dist.values())
            expected_pct = 1.0 / len(allowed_ages)
            self._log(f"{g:<4} | Target: {list(allowed_ages)}")
            for age in sorted(dist.keys()):
                pct = dist[age] / total
                diff = pct - expected_pct
                status = "✅" if abs(diff) < 0.03 else "⚠️"
                self._log(f"       ↳ {age}歲: {pct:.4%} (Diff: {diff:+.4%}) {status}")
            self._log("-" * 60)
        self._log("\n")

    def _write_violations(self):
        self._log("🚨 [KPI 3.6] 違規與異常檢測 (Violation Check)")
        self._log("   目標: 確保沒有任何一筆資料違反硬性規則。")
        self._log("-" * 120)
        
        # 3.6.A Basic Violations
        if not self.stats['violations']:
            self._log("✅ [單項屬性邊界] 所有屬性皆在 1-99 範圍內。")
        else:
            unique_v = list(set(self.stats['violations']))
            for v in unique_v[:20]:
                self._log(f"❌ {v}")
            if len(unique_v) > 20:
                self._log(f"... (還有 {len(unique_v)-20} 項錯誤)")
                
        # 3.6.B Small Player Monitor by Grade
        self._log("\n🔍 [矮個子監控] 身高 <= 189cm 球員能力值檢測 (依等級):")
        self._log("   說明: 檢查是否因身高紅利導致突破該等級的 Base Cap。")
        
        self._log(f"   {'Grade':<6} | {'Total Small (n)':<16} | {'Max Val':<8} | {'Base Cap':<8} | {'Overflow (n)':<12} | {'Overflow %':<10} | Check")
        self._log("   " + "-" * 100)
        
        # Sort by Grade Priority
        for g in ['SSR', 'SS', 'S', 'A', 'B', 'C', 'G']:
            if g not in self.stats['small_player_stats']:
                self._log(f"   {g:<6} | {'0':<16} | {'-':<8} | {BASE_CAPS.get(g,0):<8} | {'-':<12} | {'-':<10} | -")
                continue
                
            data = self.stats['small_player_stats'][g]
            max_val = data['max']
            count = data['count']
            overflow_count = data['overflow_count']
            base_cap = BASE_CAPS.get(g, 0)
            
            overflow_pct = overflow_count / count if count > 0 else 0
            
            diff = max_val - base_cap
            status = "✅"
            if diff > 50: status = "⚠️ (High)"
            if diff < 0: status = "✅ (Under)"
            
            self._log(f"   {g:<6} | {count:<16,} | {max_val:<8} | {base_cap:<8} | {overflow_count:<12,} | {overflow_pct:<10.2%} | {status}")
            
        self._log("-" * 120)