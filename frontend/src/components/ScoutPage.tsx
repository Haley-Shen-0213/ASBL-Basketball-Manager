// frontend/src/components/ScoutPage.tsx
// 專案路徑: frontend/src/components/ScoutPage.tsx
// 模組名稱: 球員球探中心 (Scout)
// 描述: 提供球探設定、抽卡機制、待簽名單管理及合約預估

import React, { useState, useEffect, useMemo } from 'react';
import { Search, Settings, UserPlus, Clock, Zap, DollarSign, AlertCircle, Sparkles, ArrowUpDown, ArrowUp, ArrowDown, Coins } from 'lucide-react';

// --- 型別定義 ---
interface ScoutSettings {
  daily_level: number;
  scout_chances: number;
  cost_per_level: number;
  max_level: number;
}

interface PendingPlayer {
  player_id: number;
  name: string;
  grade: string;
  position: string;
  height: number;
  age: number;
  rating: number;
  nationality: string;
  expire_in_hours: number;
  stats: any;
}

// --- 靜態資料與規則 ---
const GRADE_WEIGHTS: Record<string, number> = { 'SSR': 7, 'SS': 6, 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'G': 1 };
const POS_WEIGHTS: Record<string, number> = { 'PG': 5, 'SG': 4, 'SF': 3, 'PF': 2, 'C': 1 };

const SALARY_FACTORS: Record<string, number> = {
  'G': 1.0, 'C': 1.1, 'B': 1.3, 'A': 1.6, 'S': 2.0, 'SS': 2.5, 'SSR': 3.0
};

const CONTRACT_RULES: Record<string, { years: number, role: string }> = {
  'SSR': { years: 4, role: 'Star' },
  'SS':  { years: 4, role: 'Star' },
  'S':   { years: 4, role: 'Starter' },
  'A':   { years: 2, role: 'Rotation' },
  'B':   { years: 2, role: 'Rotation' },
  'C':   { years: 1, role: 'Role' },
  'G':   { years: 1, role: 'Bench' }
};

const ROLE_TRANSLATION: Record<string, string> = { 
  'Star': '明星', 'Starter': '先發', 'Rotation': '綠葉', 'Role': '功能', 'Bench': '板凳' 
};

// --- 樣式函式 (Standardized) ---
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
    case 'C': return 'text-red-600';
    case 'PF': return 'text-orange-600';
    case 'SF': return 'text-blue-600';
    case 'SG': return 'text-green-600';
    case 'PG': return 'text-yellow-600';
    default: return 'text-gray-600';
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

// --- 輔助函式 ---
const calculateContract = (grade: string, rating: number) => {
  const factor = SALARY_FACTORS[grade] || 1.0;
  const rule = CONTRACT_RULES[grade] || { years: 1, role: 'Bench' };
  const salary = Math.round(rating * factor);
  return { salary, years: rule.years, role: rule.role };
};

// --- 排序設定 ---
type SortKey = 'grade' | 'position' | 'name' | 'age' | 'height' | 'rating' | 'expire_in_hours' | 'salary';
type SortDirection = 'asc' | 'desc';

// --- 主組件 ---
const ScoutPage: React.FC<{ userId: number }> = ({ userId }) => {
  const [settings, setSettings] = useState<ScoutSettings | null>(null);
  const [pendingList, setPendingList] = useState<PendingPlayer[]>([]);
  const [sliderValue, setSliderValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState<{type: 'success'|'error', text: string} | null>(null);
  const [sortConfig, setSortConfig] = useState<{key: SortKey, direction: SortDirection}>({ key: 'rating', direction: 'desc' });

  const fetchData = async () => {
    try {
      const [setRes, listRes] = await Promise.all([
        fetch(`/api/scout/settings?user_id=${userId}`),
        fetch(`/api/scout/pending?user_id=${userId}`)
      ]);
      
      if (setRes.ok) {
        const data = await setRes.json();
        setSettings(data);
        setSliderValue(data.daily_level);
      }
      if (listRes.ok) {
        setPendingList(await listRes.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) fetchData();
  }, [userId]);

  const handleSaveSettings = async () => {
    setProcessing(true);
    try {
      const res = await fetch('/api/scout/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_id: userId, level: sliderValue })
      });
      if (res.ok) {
        setMessage({ type: 'success', text: '球探設定已更新' });
        fetchData();
      }
    } catch (e) {
      setMessage({ type: 'error', text: '更新失敗' });
    } finally {
      setProcessing(false);
    }
  };

  const handleUseChance = async (count: number) => {
    if (!settings || settings.scout_chances < count) return;
    setProcessing(true);
    try {
      const res = await fetch('/api/scout/use', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_id: userId, count: count })
      });
      const data = await res.json();
      if (res.ok) {
        setMessage({ type: 'success', text: data.message });
        fetchData();
      } else {
        setMessage({ type: 'error', text: data.error });
      }
    } catch (e) {
      setMessage({ type: 'error', text: '操作失敗' });
    } finally {
      setProcessing(false);
    }
  };

  const handleSign = async (playerId: number) => {
    if (!confirm('確定要簽下這名球員嗎？')) return;
    setProcessing(true);
    try {
      const res = await fetch('/api/scout/sign', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_id: userId, player_id: playerId })
      });
      const data = await res.json();
      if (res.ok) {
        setMessage({ type: 'success', text: data.message });
        fetchData();
      } else {
        setMessage({ type: 'error', text: data.error });
      }
    } catch (e) {
      setMessage({ type: 'error', text: '簽約失敗' });
    } finally {
      setProcessing(false);
    }
  };

  // --- 排序邏輯 ---
  const handleSort = (key: SortKey) => {
    let direction: SortDirection = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') direction = 'asc';
    setSortConfig({ key, direction });
  };

  const sortedList = useMemo(() => {
    const sorted = [...pendingList];
    sorted.sort((a, b) => {
      let valA: number | string = 0;
      let valB: number | string = 0;
      
      const contractA = calculateContract(a.grade, a.rating);
      const contractB = calculateContract(b.grade, b.rating);

      switch (sortConfig.key) {
        case 'grade': valA = GRADE_WEIGHTS[a.grade] || 0; valB = GRADE_WEIGHTS[b.grade] || 0; break;
        case 'position': valA = POS_WEIGHTS[a.position] || 0; valB = POS_WEIGHTS[b.position] || 0; break;
        case 'name': valA = a.name; valB = b.name; break;
        case 'age': valA = a.age; valB = b.age; break;
        case 'height': valA = a.height; valB = b.height; break;
        case 'rating': valA = a.rating; valB = b.rating; break;
        case 'expire_in_hours': valA = a.expire_in_hours; valB = b.expire_in_hours; break;
        case 'salary': valA = contractA.salary; valB = contractB.salary; break;
      }
      if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
      if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [pendingList, sortConfig]);

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortConfig.key !== column) return <ArrowUpDown size={14} className="text-gray-400 opacity-50" />;
    return sortConfig.direction === 'asc' ? <ArrowUp size={14} className="text-asbl-violet" /> : <ArrowDown size={14} className="text-asbl-violet" />;
  };

  const ThButton = ({ label, column, icon }: { label: string, column: SortKey, icon?: React.ReactNode }) => (
    <th className="px-3 py-3 cursor-pointer hover:bg-gray-100 transition-colors select-none whitespace-nowrap" onClick={() => handleSort(column)}>
      <div className="flex items-center gap-1 justify-center">
        {icon} <span>{label}</span> <SortIcon column={column} />
      </div>
    </th>
  );

  const renderActionButtons = () => {
    if (!settings) return null;
    const chances = settings.scout_chances;

    if (chances === 0) {
      return (
        <button disabled className="w-full py-3 bg-white/20 text-white/50 rounded-xl font-bold cursor-not-allowed border border-white/10">
          無法使用
        </button>
      );
    }

    return (
      <div className="flex gap-2 w-full">
        <button 
          onClick={() => handleUseChance(1)}
          disabled={processing}
          className="flex-1 py-3 bg-white text-blue-700 hover:bg-blue-50 rounded-xl font-black shadow-md transition-all active:scale-95 disabled:opacity-50 flex justify-center items-center gap-2"
        >
          <Zap size={18} className="text-yellow-500 fill-yellow-500" /> 1次
        </button>

        {chances >= 10 && (
          <button 
            onClick={() => handleUseChance(10)}
            disabled={processing}
            className="flex-1 py-3 bg-gradient-to-r from-yellow-400 to-orange-500 text-white hover:opacity-90 rounded-xl font-black shadow-md transition-all active:scale-95 disabled:opacity-50 flex justify-center items-center gap-2"
          >
            <Sparkles size={18} /> 10次
          </button>
        )}

        {chances >= 20 && (
          <button 
            onClick={() => handleUseChance(chances)}
            disabled={processing}
            className="flex-1 py-3 bg-black/30 hover:bg-black/40 text-white border border-white/30 rounded-xl font-bold transition-all active:scale-95 disabled:opacity-50"
          >
            全部 ({chances})
          </button>
        )}
      </div>
    );
  };

  if (loading || !settings) return <div className="p-8 text-center text-white">載入球探中心...</div>;

  const dailyCost = sliderValue * settings.cost_per_level;
  const chances = settings.scout_chances;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 h-full flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Search className="text-blue-600" /> 球探中心
        </h2>
        {message && (
          <div className={`px-4 py-2 rounded-lg text-sm font-bold ${message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {message.text}
          </div>
        )}
      </div>

      {/* Top Section: Merged Panel */}
      <div className="grid grid-cols-12 gap-6 bg-white/80 backdrop-blur border border-white/50 rounded-2xl shadow-sm overflow-hidden">
        
        {/* Left: Daily Settings */}
        <div className="col-span-12 lg:col-span-7 p-6 border-b lg:border-b-0 lg:border-r border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <Settings size={20} className="text-gray-600" />
            <div>
              <h3 className="text-lg font-bold text-gray-800">每日投入</h3>
              <p className="text-xs text-gray-500">自動尋找新球員</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div>
              <div className="flex justify-between text-sm font-bold text-gray-600 mb-2">
                <span>投入等級: <span className="text-blue-600 text-lg">{sliderValue}</span></span>
                <span className="text-xs text-gray-400">{settings.max_level} (Max)</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max={settings.max_level} 
                value={sliderValue} 
                onChange={(e) => setSliderValue(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>

            <div className="flex items-center justify-between md:justify-end gap-4">
              <div className="text-right">
                <div className="text-xs text-gray-500 font-bold">每日預估</div>
                <div className="text-lg font-black text-blue-600 flex items-center justify-end">
                  <DollarSign size={16} /> {dailyCost.toLocaleString()}
                </div>
              </div>
              <button 
                onClick={handleSaveSettings}
                disabled={processing}
                className="px-6 py-2.5 bg-gray-900 hover:bg-gray-800 text-white rounded-xl font-bold transition-colors disabled:opacity-50 whitespace-nowrap"
              >
                儲存
              </button>
            </div>
          </div>
        </div>

        {/* Right: Manual Scout */}
        <div className="col-span-12 lg:col-span-5 p-6 bg-gradient-to-br from-blue-600 to-violet-600 text-white flex flex-col justify-center">
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-3">
              <Zap size={20} className="text-yellow-300" />
              <div>
                <h3 className="text-lg font-bold">立即搜尋</h3>
                <p className="text-xs text-blue-100">剩餘 <span className="font-mono font-bold text-yellow-300 text-sm">{chances}</span> 次</p>
              </div>
            </div>
          </div>
          
          {renderActionButtons()}
        </div>
      </div>

      {/* Bottom Section: Pending List */}
      <div className="bg-white/60 backdrop-blur-md border border-white/50 rounded-xl overflow-hidden shadow-sm flex-1 flex flex-col min-h-[400px]">
        <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex justify-between items-center">
          <h3 className="font-bold text-gray-700 flex items-center gap-2">
            <UserPlus size={18} /> 待簽名單 ({pendingList.length})
          </h3>
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <AlertCircle size={12} /> 超過 7 天未簽約將自動釋出
          </span>
        </div>

        <div className="overflow-x-auto flex-1">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-gray-50 text-gray-700 font-bold text-xs border-b border-gray-200 sticky top-0 z-10">
              <tr>
                <ThButton label="等級" column="grade" />
                <ThButton label="位置" column="position" />
                <th className="px-4 py-3 text-left">姓名 (國籍)</th>
                <ThButton label="年齡" column="age" />
                <ThButton label="身高" column="height" />
                <ThButton label="總評" column="rating" />
                <th className="px-3 py-3 text-center">定位</th>
                <th className="px-3 py-3 text-center">年限</th>
                <ThButton label="薪資" column="salary" icon={<Coins size={14}/>} />
                <ThButton label="剩餘時間" column="expire_in_hours" icon={<Clock size={14}/>} />
                <th className="px-3 py-3 text-center">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white/40">
              {sortedList.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-gray-400">
                    <Search size={48} className="mx-auto opacity-20 mb-2" />
                    目前沒有待簽球員
                  </td>
                </tr>
              ) : (
                sortedList.map((p) => {
                  const contract = calculateContract(p.grade, p.rating);
                  return (
                    <tr key={p.player_id} className="hover:bg-white/80 transition-colors group">
                      <td className="px-3 py-3 text-center">
                        <span className={`inline-block w-10 py-0.5 rounded text-[10px] border shadow-sm ${getGradeStyle(p.grade)}`}>
                          {p.grade}
                        </span>
                      </td>
                      <td className={`px-3 py-3 text-center font-black text-base ${getPosColor(p.position)}`}>
                        {p.position}
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-bold text-gray-900">{p.name}</div>
                        <div className="text-[10px] text-gray-500 uppercase font-mono">{p.nationality}</div>
                      </td>
                      <td className="px-3 py-3 text-center font-mono text-gray-700">{p.age}</td>
                      <td className="px-3 py-3 text-center font-mono text-gray-700">{p.height} <span className="text-[10px] text-gray-400">cm</span></td>
                      <td className="px-3 py-3 text-center">
                        <span className={`font-bold font-mono text-base ${p.rating >= 1200 ? 'text-amber-600' : 'text-gray-800'}`}>{p.rating}</span>
                      </td>
                      
                      {/* 合約定位 (使用標準樣式) */}
                      <td className="px-3 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getRoleStyle(contract.role)}`}>
                          {ROLE_TRANSLATION[contract.role] || contract.role}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center font-mono font-bold text-gray-600">
                        {contract.years} 年
                      </td>
                      <td className="px-3 py-3 text-center font-mono font-black text-blue-700">
                        ${contract.salary.toLocaleString()}
                      </td>
                      
                      <td className="px-3 py-3 text-center">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${p.expire_in_hours < 24 ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'}`}>
                          {p.expire_in_hours}h
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <button 
                          onClick={() => handleSign(p.player_id)}
                          disabled={processing}
                          className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded shadow-sm transition-colors active:scale-95 disabled:opacity-50"
                        >
                          簽約
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};

export default ScoutPage;
