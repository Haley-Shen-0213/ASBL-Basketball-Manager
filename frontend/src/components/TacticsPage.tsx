// frontend/src/components/TacticsPage.tsx
// 專案路徑: frontend/src/components/TacticsPage.tsx
// 模組名稱: 戰術與陣容設定頁面
// 描述: 提供球隊登錄名單 (Active Roster) 的管理介面，樣式已與 PlayerRoster 對齊。

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Users, ShieldAlert, CheckCircle, Save, RotateCcw, 
  Wand2, AlertTriangle, UserPlus, Loader2
} from 'lucide-react';

// ==========================================
// 型別定義
// ==========================================

interface PlayerLite {
  id: number | string;
  name: string;
  position: string;
  role: string; // Star, Starter, Rotation, Role, Bench
  grade: string;
  rating: number;
  is_active: boolean;
}

interface TacticsConfig {
  roster_size: number;
  constraints: {
    tier_1: { max: number; roles: string[] };
    tier_2: { max: number; roles: string[] };
    tier_3: { max: number; roles: string[] };
  };
}

// ==========================================
// 樣式與常數 (與 PlayerRoster.tsx 對齊)
// ==========================================

const ROLE_ORDER = ['Star', 'Starter', 'Rotation', 'Role', 'Bench'];

const ROLE_TRANSLATION: Record<string, string> = { 
  'Star': '明星', 'Starter': '先發', 'Rotation': '綠葉', 'Role': '功能', 'Bench': '板凳' 
};

const getGradeStyle = (grade: string) => {
  switch (grade) {
    case 'SSR': return 'bg-yellow-400 text-red-600 border-yellow-500 font-black';
    case 'SS':  return 'bg-pink-400 text-white border-pink-500 font-bold';
    case 'S':   return 'bg-red-600 text-white border-red-700 font-bold';
    case 'A':   return 'bg-blue-600 text-white border-blue-700 font-bold';
    case 'B':   return 'bg-green-600 text-white border-green-700 font-bold';
    case 'C':   return 'bg-white text-black border-gray-300 font-bold';
    case 'G':   return 'bg-black text-white border-gray-600 font-bold';
    default:    return 'bg-gray-200 text-gray-800';
  }
};

const getPosColor = (pos: string) => {
  switch (pos) {
    case 'C': return 'text-red-500'; // 在深色背景稍微調亮一點點，或保持原樣
    case 'PF': return 'text-orange-500';
    case 'SF': return 'text-blue-500';
    case 'SG': return 'text-green-500';
    case 'PG': return 'text-yellow-500';
    default: return 'text-gray-500';
  }
};

const getRoleStyle = (role: string) => {
  switch (role) {
    case 'Star': return 'bg-purple-100 text-purple-800 border-purple-200';
    case 'Starter': return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'Rotation': return 'bg-green-100 text-green-800 border-green-200';
    case 'Role': return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'Bench': return 'bg-gray-100 text-gray-600 border-gray-200';
    default: return 'bg-gray-50 text-gray-500';
  }
};

// ==========================================
// 主組件
// ==========================================
const TacticsPage: React.FC<{ teamId: number }> = ({ teamId }) => {
  // --- 狀態管理 ---
  const [allPlayers, setAllPlayers] = useState<PlayerLite[]>([]);
  const [config, setConfig] = useState<TacticsConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{type: 'success'|'error'|'warning', text: string} | null>(null);

  // --- 1. 初始化：載入規則與球員 ---
  useEffect(() => {
    const initPage = async () => {
      setLoading(true);
      try {
        const defaultConfig: TacticsConfig = {
          roster_size: 15,
          constraints: {
            tier_1: { max: 3, roles: ['Star'] },
            tier_2: { max: 7, roles: ['Star', 'Starter'] },
            tier_3: { max: 12, roles: ['Star', 'Starter', 'Rotation', 'Role'] }
          }
        };

        const [configRes, rosterRes] = await Promise.all([
           fetch('/api/system/config/tactics').catch(() => ({ ok: false, json: async () => defaultConfig })), 
           fetch(`/api/team/${teamId}/roster`)
        ]);

        let configData = defaultConfig;
        if (configRes.ok) {
           configData = await configRes.json();
        }

        if (!rosterRes.ok) {
          throw new Error('無法讀取球員名單');
        }

        const rosterData = await rosterRes.json();

        setConfig(configData);

        const mapped: PlayerLite[] = rosterData.map((p: any) => ({
          id: p.id,
          name: p.name,
          position: p.position,
          role: p.role,
          grade: p.grade,
          rating: p.rating,
          is_active: p.is_active
        })).sort((a: PlayerLite, b: PlayerLite) => b.rating - a.rating);
        
        setAllPlayers(mapped);

      } catch (e) {
        console.error("初始化失敗:", e);
        setMessage({ type: 'error', text: '系統載入失敗，請確認伺服器連線。' });
      } finally {
        setLoading(false);
      }
    };

    if (teamId) initPage();
  }, [teamId]);

  // --- 2. 即時計算與檢核邏輯 ---
  
  const activeRoster = useMemo(() => allPlayers.filter(p => p.is_active), [allPlayers]);
  const availablePool = useMemo(() => allPlayers.filter(p => !p.is_active), [allPlayers]);

  const stats = useMemo(() => {
    if (!config) return null;

    const counts = { Star: 0, Starter: 0, Rotation: 0, Role: 0, Bench: 0 };
    
    activeRoster.forEach(p => {
      if (counts[p.role as keyof typeof counts] !== undefined) {
        counts[p.role as keyof typeof counts]++;
      }
    });

    const tier1 = counts.Star;
    const tier2 = counts.Star + counts.Starter;
    const tier3 = counts.Star + counts.Starter + counts.Rotation + counts.Role;
    const total = activeRoster.length;

    return {
      tier1, 
      tier1Valid: tier1 <= config.constraints.tier_1.max,
      tier2, 
      tier2Valid: tier2 <= config.constraints.tier_2.max,
      tier3, 
      tier3Valid: tier3 <= config.constraints.tier_3.max,
      total,
      totalValid: total <= config.roster_size,
      counts
    };
  }, [activeRoster, config]);

  const isRulesValid = stats ? (stats.tier1Valid && stats.tier2Valid && stats.tier3Valid && stats.totalValid) : false;

  // --- 3. 操作處理函式 ---

  const togglePlayer = (id: number | string) => {
    if (!config) return;

    setAllPlayers(prev => prev.map(p => {
      if (p.id !== id) return p;
      if (!p.is_active && activeRoster.length >= config.roster_size) {
        setMessage({ type: 'warning', text: `登錄名單已滿 ${config.roster_size} 人，請先移除球員。` });
        return p;
      }
      return { ...p, is_active: !p.is_active };
    }));
    if (message?.type === 'warning') setMessage(null);
  };

  const handleAutoFill = () => {
    if (!config) return;

    const pool = [...allPlayers].sort((a, b) => b.rating - a.rating);
    const newActiveIds = new Set<number|string>();
    
    let t1Count = 0;
    let t2Count = 0;
    let t3Count = 0;
    let totalCount = 0;

    const tryAdd = (p: PlayerLite) => {
      if (totalCount >= config.roster_size) return false;
      
      const isStar = p.role === 'Star';
      const isStarter = p.role === 'Starter';
      const isRotRole = p.role === 'Rotation' || p.role === 'Role';
      
      if (isStar && t1Count >= config.constraints.tier_1.max) return false;
      if ((isStar || isStarter) && t2Count >= config.constraints.tier_2.max) return false;
      if ((isStar || isStarter || isRotRole) && t3Count >= config.constraints.tier_3.max) return false;

      newActiveIds.add(p.id);
      totalCount++;
      
      if (isStar) t1Count++;
      if (isStar || isStarter) t2Count++;
      if (isStar || isStarter || isRotRole) t3Count++;
      
      return true;
    };

    for (const p of pool) {
      if (p.role === 'Bench') continue;
      tryAdd(p);
    }

    for (const p of pool) {
      if (p.role !== 'Bench') continue;
      if (totalCount < config.roster_size) {
        newActiveIds.add(p.id);
        totalCount++;
      }
    }

    setAllPlayers(prev => prev.map(p => ({
      ...p,
      is_active: newActiveIds.has(p.id)
    })));
    
    const missing = config.roster_size - totalCount;
    if (missing > 0) {
      setMessage({ type: 'warning', text: `已填入最佳陣容，尚缺 ${missing} 人 (將由幽靈球員補位)。` });
    } else {
      setMessage({ type: 'success', text: '已自動產生符合規則的最佳陣容。' });
    }
  };

  const handleClear = () => {
    setAllPlayers(prev => prev.map(p => ({ ...p, is_active: false })));
    setMessage(null);
  };

  const handleSave = async () => {
    if (!config) return;
    if (!isRulesValid) {
      setMessage({ type: 'error', text: '陣容違反階層限制規則，無法提交！' });
      return;
    }
    
    const missingCount = config.roster_size - activeRoster.length;
    let confirmMsg = '確定提交目前的戰術名單嗎？';
    
    if (missingCount > 0) {
      confirmMsg += `\n注意：目前名單不足 ${config.roster_size} 人，系統將自動生成 ${missingCount} 名 G 級幽靈球員填補空缺。`;
      if (!window.confirm(confirmMsg)) return;
    }
    
    setSaving(true);
    try {
      const activeIds = activeRoster.map(p => p.id);
      
      const res = await fetch(`/api/team/${teamId}/roster/active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_ids: activeIds })
      });

      if (res.ok) {
        setMessage({ type: 'success', text: '戰術名單已成功提交並儲存！' });
        setTimeout(() => setMessage(null), 3000);
      } else {
        const errData = await res.json();
        throw new Error(errData.error || '提交失敗');
      }
    } catch (e: any) {
      console.error(e);
      setMessage({ type: 'error', text: `儲存失敗: ${e.message}` });
    } finally {
      setSaving(false);
    }
  };

  // --- UI 子組件 ---
  
  const StatCard = ({ label, current, max, valid }: { label: string, current: number, max: number, valid: boolean }) => (
    <div className={`flex flex-col items-center p-3 rounded-xl border transition-all duration-300
      ${valid ? 'bg-white/5 border-white/10' : 'bg-red-500/10 border-red-500/50 shadow-[0_0_10px_rgba(239,68,68,0.2)]'}`}>
      <span className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">{label}</span>
      <div className={`text-2xl font-black font-mono mt-1 ${valid ? 'text-white' : 'text-red-400'}`}>
        {current} <span className="text-sm text-gray-500 font-normal">/ {max}</span>
      </div>
    </div>
  );

  // 球員列表項目 (樣式已對齊 PlayerRoster)
  const PlayerRow = ({ p, actionIcon, onClick }: { p: PlayerLite, actionIcon: React.ReactNode, onClick: () => void }) => (
    <div 
      onClick={onClick}
      className={`flex items-center justify-between p-2 rounded-lg border mb-2 cursor-pointer transition-all hover:scale-[1.01] group
        ${p.is_active 
          ? 'bg-violet-600/10 border-violet-500/30 hover:bg-violet-600/20' 
          : 'bg-white/5 border-white/10 hover:bg-white/10'
        }`}
    >
      <div className="flex items-center gap-3">
        {/* 等級 (Grade) - 使用標準樣式 */}
        <div className="w-10 flex justify-center">
          <span className={`inline-block w-full py-0.5 rounded text-[10px] text-center border shadow-sm ${getGradeStyle(p.grade)}`}>
            {p.grade}
          </span>
        </div>

        {/* 位置 (Position) - 使用標準顏色文字 */}
        <div className={`w-8 text-center font-black text-lg ${getPosColor(p.position)}`}>
          {p.position}
        </div>
        
        {/* 球員資訊 */}
        <div>
          <div className="font-bold text-sm text-white">
            {p.name}
          </div>
          <div className="flex gap-2 text-[10px] items-center mt-0.5">
            {/* 定位 (Role) - 使用標準樣式與翻譯 */}
            <span className={`px-2 py-0.5 rounded text-[10px] border ${getRoleStyle(p.role)}`}>
              {ROLE_TRANSLATION[p.role] || p.role}
            </span>
            <span className={`font-mono font-bold ${p.rating >= 1200 ? 'text-amber-400' : 'text-gray-400'}`}>
              RTG: {p.rating}
            </span>
          </div>
        </div>
      </div>
      
      {/* 操作圖示 */}
      <div className="text-gray-500 transition-colors px-2">
        {actionIcon}
      </div>
    </div>
  );

  if (loading || !config || !stats) {
    return (
      <div className="h-96 flex flex-col items-center justify-center text-gray-400 gap-3">
        <Loader2 className="animate-spin" size={32} />
        <span className="text-sm font-mono">LOADING TACTICS BOARD...</span>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-4 animate-in fade-in duration-500 p-4">
      
      {/* Header Section */}
      <div className="bg-gray-900/50 border-b border-white/10 pb-6 rounded-2xl p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <ShieldAlert className="text-pink-500" size={28} /> 
            <span>戰術與陣容設定</span>
          </h2>
          
          {/* Action Buttons */}
          <div className="flex gap-3">
            <button 
              onClick={handleAutoFill} 
              className="px-4 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-violet-900/20 active:scale-95"
            >
              <Wand2 size={16} /> 自動填補
            </button>
            
            <button 
              onClick={handleClear} 
              className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-sm font-bold flex items-center gap-2 transition-all border border-white/10 active:scale-95"
            >
              <RotateCcw size={16} /> 清空
            </button>
            
            <button 
              onClick={handleSave} 
              disabled={!isRulesValid || saving}
              className={`px-6 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 transition-all active:scale-95
                ${isRulesValid 
                  ? 'bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-900/20' 
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-white/5'}`}
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              {saving ? '儲存中...' : '提交名單'}
            </button>
          </div>
        </div>

        {/* Stats Dashboard */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Tier 1 (Star)" current={stats.tier1} max={config.constraints.tier_1.max} valid={stats.tier1Valid} />
          <StatCard label="Tier 2 (Main)" current={stats.tier2} max={config.constraints.tier_2.max} valid={stats.tier2Valid} />
          <StatCard label="Tier 3 (Rotation)" current={stats.tier3} max={config.constraints.tier_3.max} valid={stats.tier3Valid} />
          <StatCard label="Total Players" current={stats.total} max={config.roster_size} valid={stats.totalValid} />
        </div>

        {/* Status Message */}
        {message && (
          <div className={`mt-4 p-3 rounded-xl flex items-center gap-3 text-sm font-bold animate-in slide-in-from-top-2 duration-300
            ${message.type === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/30' : 
              message.type === 'warning' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30' :
              'bg-green-500/10 text-green-400 border border-green-500/30'}`}>
            {message.type === 'error' ? <AlertTriangle size={18} /> : <CheckCircle size={18} />}
            {message.text}
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 min-h-0">
        
        {/* Left Column: Available Pool */}
        <div className="bg-black/20 rounded-2xl border border-white/10 flex flex-col overflow-hidden h-[600px]">
          <div className="p-4 bg-white/5 border-b border-white/10 flex justify-between items-center">
            <span className="font-bold text-gray-300 text-sm uppercase tracking-wider flex items-center gap-2">
              <Users size={16} /> 可用球員 ({availablePool.length})
            </span>
            <span className="text-xs text-gray-500">點擊加入名單</span>
          </div>
          <div className="flex-1 overflow-y-auto p-3 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
            {availablePool.map(p => (
              <PlayerRow 
                key={p.id} 
                p={p} 
                onClick={() => togglePlayer(p.id)}
                actionIcon={<CheckCircle size={20} className="text-gray-600 group-hover:text-green-500 transition-colors" />} 
              />
            ))}
            {availablePool.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-gray-600 gap-2">
                <Users size={32} className="opacity-20" />
                <span className="text-sm">無可用球員</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Active Roster */}
        <div className={`rounded-2xl border flex flex-col overflow-hidden transition-colors duration-300 h-[600px]
          ${isRulesValid ? 'bg-green-900/5 border-green-500/20' : 'bg-red-900/5 border-red-500/20'}`}>
          <div className="p-4 bg-black/20 border-b border-white/10 flex justify-between items-center">
            <span className="font-bold text-white text-sm uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert size={16} className={isRulesValid ? 'text-green-400' : 'text-red-400'} />
              登錄名單 ({activeRoster.length}/{config.roster_size})
            </span>
            {!isRulesValid && (
              <span className="text-[10px] font-bold text-red-400 bg-red-900/30 px-2 py-1 rounded border border-red-500/30">
                規則不符
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
            {activeRoster
              .sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role) || b.rating - a.rating)
              .map(p => (
              <PlayerRow 
                key={p.id} 
                p={p} 
                onClick={() => togglePlayer(p.id)}
                actionIcon={<RotateCcw size={20} className="text-gray-600 group-hover:text-red-400 transition-colors" />} 
              />
            ))}
            
            {/* Empty State / Ghost Player Placeholder */}
            {activeRoster.length < config.roster_size && (
              <div className="mt-2 p-4 border border-dashed border-gray-700 rounded-xl bg-white/5 flex flex-col items-center justify-center gap-2 text-center opacity-70 hover:opacity-100 transition-opacity">
                <UserPlus size={24} className="text-gray-500" />
                <div>
                  <div className="text-gray-400 text-sm font-bold">
                    尚缺 {config.roster_size - activeRoster.length} 個名額
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    提交時將自動生成 <span className="text-gray-400 font-mono">G</span> 級幽靈球員補齊
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default TacticsPage;
