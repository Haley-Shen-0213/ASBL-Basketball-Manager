// frontend/src/components/PlayerRoster.tsx
// 專案路徑: frontend/src/components/PlayerRoster.tsx
// 模組名稱: 球員名單列表組件 (Final)
// 描述: 包含列表排序、數據聚合以及詳細資訊彈窗 (Modal)

import React, { useState, useEffect, useMemo } from 'react';
import { User, ArrowUpDown, ArrowUp, ArrowDown, Activity, Zap, Shield, X, Dumbbell } from 'lucide-react';

// --- 型別定義 ---
interface PlayerStats {
  physical: {
    stamina: number; strength: number; speed: number; jumping: number; health: number;
  };
  offense: {
    touch: number; release: number; accuracy: number; range: number;
    passing: number; dribble: number; handle: number; move: number;
  };
  defense: {
    rebound: number; boxout: number; contest: number; disrupt: number;
  };
  mental: {
    off_iq: number; def_iq: number; luck: number;
  };
}

interface PlayerData {
  id: string | number;
  name: string;
  nationality: string;
  position: string;
  role: string;
  grade: string;
  height: number;
  age: number;
  rating: number;
  training_points: number; // 新增
  stats: PlayerStats;
}

// --- 排序設定 ---
type SortKey = 'grade' | 'position' | 'name' | 'age' | 'height' | 'rating' | 'role' | 'physical' | 'offense' | 'defense';
type SortDirection = 'asc' | 'desc';

interface SortConfig {
  key: SortKey;
  direction: SortDirection;
}

// --- 靜態對照表 ---
const GRADE_WEIGHTS: Record<string, number> = { 'SSR': 7, 'SS': 6, 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'G': 1 };
const POS_WEIGHTS: Record<string, number> = { 'PG': 5, 'SG': 4, 'SF': 3, 'PF': 2, 'C': 1 };
const ROLE_WEIGHTS: Record<string, number> = { 'Star': 5, 'Starter': 4, 'Rotation': 3, 'Role': 2, 'Bench': 1 };
const ROLE_TRANSLATION: Record<string, string> = { 'Star': '明星', 'Starter': '先發', 'Rotation': '綠葉', 'Role': '功能', 'Bench': '板凳' };

// --- 樣式函式 ---
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

// --- 輔助函式：計算平均 ---
const calculateAverages = (p: PlayerData) => {
  const s = p.stats;
  const phySum = s.physical.stamina + s.physical.strength + s.physical.speed + s.physical.jumping;
  const offSum = s.offense.touch + s.offense.release + s.mental.off_iq + s.offense.accuracy + s.offense.range + s.offense.passing + s.offense.dribble + s.offense.handle + s.offense.move;
  const defSum = s.defense.rebound + s.defense.boxout + s.defense.contest + s.defense.disrupt + s.mental.def_iq;
  return { phyAvg: phySum / 4, offAvg: offSum / 9, defAvg: defSum / 5 };
};

// --- 子組件：詳細資訊 Modal ---
const PlayerDetailModal = ({ player, onClose }: { player: PlayerData, onClose: () => void }) => {
  if (!player) return null;

  // 定義可訓練能力 (10項)
  const trainableStats = [
    { label: '投籃技巧', value: player.stats.offense.accuracy, cat: 'offense' },
    { label: '射程', value: player.stats.offense.range, cat: 'offense' },
    { label: '傳球', value: player.stats.offense.passing, cat: 'offense' },
    { label: '運球', value: player.stats.offense.dribble, cat: 'offense' },
    { label: '控球', value: player.stats.offense.handle, cat: 'offense' },
    { label: '跑位', value: player.stats.offense.move, cat: 'offense' },
    { label: '籃板', value: player.stats.defense.rebound, cat: 'defense' },
    { label: '卡位', value: player.stats.defense.boxout, cat: 'defense' },
    { label: '干擾', value: player.stats.defense.contest, cat: 'defense' },
    { label: '抄截', value: player.stats.defense.disrupt, cat: 'defense' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header: 球員卡片風格 */}
        <div className="relative p-6 bg-gradient-to-br from-gray-900 to-gray-800 text-white flex gap-6 items-center shrink-0">
          <button onClick={onClose} className="absolute top-4 right-4 text-white/50 hover:text-white transition-colors">
            <X size={24} />
          </button>
          
          {/* 圖像預留區 */}
          <div className="w-24 h-24 rounded-full bg-gray-700 border-4 border-white/10 flex items-center justify-center shrink-0 shadow-lg">
            <User size={40} className="text-gray-500" />
          </div>
          
          {/* 基本資料 */}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <span className={`px-2 py-0.5 rounded text-xs font-black border ${getGradeStyle(player.grade)}`}>
                {player.grade}
              </span>
              <span className={`font-black text-xl ${getPosColor(player.position)}`}>{player.position}</span>
              <h2 className="text-2xl font-bold">{player.name}</h2>
              <span className="text-sm text-gray-400 font-mono bg-black/30 px-2 py-0.5 rounded">{player.nationality}</span>
            </div>
            
            <div className="flex gap-6 text-sm text-gray-300 mt-2">
              <div>年齡: <span className="text-white font-bold font-mono">{player.age}</span></div>
              <div>身高: <span className="text-white font-bold font-mono">{player.height} cm</span></div>
              <div>定位: <span className="text-white font-bold">{ROLE_TRANSLATION[player.role] || player.role}</span></div>
            </div>

            {/* 訓練點數 */}
            <div className="mt-4 inline-flex items-center gap-2 bg-asbl-violet/20 px-3 py-1.5 rounded-lg border border-asbl-violet/50">
              <Dumbbell size={16} className="text-asbl-violet" />
              <span className="text-xs text-asbl-violet font-bold uppercase">現有訓練點數</span>
              <span className="text-white font-black font-mono text-lg ml-1">{player.training_points ?? 0}</span>
            </div>
          </div>
        </div>

        {/* Body: 可訓練能力 */}
        <div className="p-6 overflow-y-auto bg-gray-50 flex-1">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Activity size={16} /> 可訓練能力 (Trainable Stats)
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {trainableStats.map((stat, idx) => (
              <div key={idx} className="bg-white border border-gray-200 p-3 rounded-xl flex flex-col items-center justify-center shadow-sm hover:border-asbl-violet/50 transition-colors group">
                <span className={`text-xs font-bold mb-1 ${stat.cat === 'offense' ? 'text-orange-600' : 'text-green-600'}`}>
                  {stat.label}
                </span>
                <span className="text-2xl font-black font-mono text-gray-800 group-hover:text-asbl-violet">
                  {stat.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer: 按鈕 */}
        <div className="p-4 bg-white border-t border-gray-200 shrink-0 flex justify-end gap-3">
          <button onClick={onClose} className="px-5 py-2.5 rounded-xl text-sm font-bold text-gray-600 hover:bg-gray-100 transition-colors">
            關閉
          </button>
          <button className="px-6 py-2.5 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-asbl-violet to-asbl-blue hover:opacity-90 shadow-lg shadow-asbl-violet/30 flex items-center gap-2 transform active:scale-95 transition-all">
            <Dumbbell size={18} />
            前往訓練
          </button>
        </div>

      </div>
    </div>
  );
};

// --- 主組件 ---
const PlayerRoster: React.FC<{ teamId: number }> = ({ teamId }) => {
  const [players, setPlayers] = useState<PlayerData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'grade', direction: 'desc' });
  
  // Modal State
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerData | null>(null);

  useEffect(() => {
    const fetchRoster = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/team/${teamId}/roster`);
        if (res.ok) {
          const data = await res.json();
          setPlayers(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    if (teamId) fetchRoster();
  }, [teamId]);

  const handleSort = (key: SortKey) => {
    let direction: SortDirection = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') direction = 'asc';
    setSortConfig({ key, direction });
  };

  const sortedPlayers = useMemo(() => {
    const sorted = [...players];
    sorted.sort((a, b) => {
      let valA: number | string = 0;
      let valB: number | string = 0;

      switch (sortConfig.key) {
        case 'grade': valA = GRADE_WEIGHTS[a.grade] || 0; valB = GRADE_WEIGHTS[b.grade] || 0; break;
        case 'position': valA = POS_WEIGHTS[a.position] || 0; valB = POS_WEIGHTS[b.position] || 0; break;
        case 'role': valA = ROLE_WEIGHTS[a.role] || 0; valB = ROLE_WEIGHTS[b.role] || 0; break;
        case 'physical': valA = calculateAverages(a).phyAvg; valB = calculateAverages(b).phyAvg; break;
        case 'offense': valA = calculateAverages(a).offAvg; valB = calculateAverages(b).offAvg; break;
        case 'defense': valA = calculateAverages(a).defAvg; valB = calculateAverages(b).defAvg; break;
        case 'age': case 'height': case 'rating': valA = a[sortConfig.key]; valB = b[sortConfig.key]; break;
        default: return 0;
      }
      if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
      if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [players, sortConfig]);

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortConfig.key !== column) return <ArrowUpDown size={14} className="text-gray-400 opacity-50" />;
    return sortConfig.direction === 'asc' ? <ArrowUp size={14} className="text-asbl-violet" /> : <ArrowDown size={14} className="text-asbl-violet" />;
  };

  const ThButton = ({ label, column, icon }: { label: string, column: SortKey, icon?: React.ReactNode }) => (
    <th className="px-3 py-3 cursor-pointer hover:bg-gray-100 transition-colors select-none" onClick={() => handleSort(column)}>
      <div className="flex items-center gap-1 justify-center">
        {icon} <span>{label}</span> <SortIcon column={column} />
      </div>
    </th>
  );

  if (loading) return <div className="p-8 text-center text-white">載入中...</div>;

  return (
    <div className="space-y-4 animate-in fade-in duration-500">
      <div className="flex justify-between items-end">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <User className="text-asbl-violet" />
          球隊名單 ({players.length}人)
        </h2>
        <span className="text-xs text-gray-600 italic"></span>
      </div>

      <div className="bg-white/60 backdrop-blur-md border border-white/50 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-gray-50 text-gray-700 font-bold text-xs border-b border-gray-200">
              <tr>
                <ThButton label="等級" column="grade" />
                <ThButton label="位置" column="position" />
                <th className="px-4 py-3 text-left">姓名 (國籍)</th>
                <ThButton label="年齡" column="age" />
                <ThButton label="身高" column="height" />
                <ThButton label="總評" column="rating" />
                <ThButton label="定位" column="role" />
                <ThButton label="體能" column="physical" icon={<Activity size={14} className="text-blue-600"/>} />
                <ThButton label="進攻" column="offense" icon={<Zap size={14} className="text-orange-600"/>} />
                <ThButton label="防守" column="defense" icon={<Shield size={14} className="text-green-600"/>} />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedPlayers.map((p) => {
                const avgs = calculateAverages(p);
                return (
                  <tr key={p.id} className="hover:bg-white/80 transition-colors group">
                    <td className="px-3 py-3 text-center">
                      <span className={`inline-block w-10 py-0.5 rounded text-[10px] border shadow-sm ${getGradeStyle(p.grade)}`}>{p.grade}</span>
                    </td>
                    <td className={`px-3 py-3 text-center font-black text-base ${getPosColor(p.position)}`}>{p.position}</td>
                    <td className="px-4 py-3">
                      {/* 點擊姓名開啟 Modal */}
                      <button 
                        onClick={() => setSelectedPlayer(p)}
                        className="text-left font-bold text-gray-900 hover:text-asbl-violet hover:underline decoration-2 underline-offset-2 transition-all"
                      >
                        {p.name}
                      </button>
                      <div className="text-[10px] text-gray-500 uppercase font-mono">{p.nationality}</div>
                    </td>
                    <td className="px-3 py-3 text-center font-mono text-gray-700">{p.age}</td>
                    <td className="px-3 py-3 text-center font-mono text-gray-700">{p.height} <span className="text-[10px] text-gray-400">cm</span></td>
                    <td className="px-3 py-3 text-center">
                      <span className={`font-bold font-mono text-base ${p.rating >= 1200 ? 'text-amber-600' : 'text-gray-800'}`}>{p.rating}</span>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getRoleStyle(p.role)}`}>{ROLE_TRANSLATION[p.role] || p.role}</span>
                    </td>
                    <td className="px-3 py-3 text-center"><span className="font-bold text-blue-700 text-lg">{Math.round(avgs.phyAvg)}</span></td>
                    <td className="px-3 py-3 text-center"><span className="font-bold text-orange-700 text-lg">{Math.round(avgs.offAvg)}</span></td>
                    <td className="px-3 py-3 text-center"><span className="font-bold text-green-700 text-lg">{Math.round(avgs.defAvg)}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 詳細資訊 Modal */}
      {selectedPlayer && (
        <PlayerDetailModal 
          player={selectedPlayer} 
          onClose={() => setSelectedPlayer(null)} 
        />
      )}
    </div>
  );
};

export default PlayerRoster;