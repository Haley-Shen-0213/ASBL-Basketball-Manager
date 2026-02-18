// frontend/src/components/MatchDetailModal.tsx
import React, { useState, useEffect } from 'react';
import { X, Activity, List, Trophy, Clock } from 'lucide-react';

interface PlayerStat {
  id: number;
  name: string;
  pos: string;
  grade: string;
  min: number;
  pts: number;
  reb: number;
  ast: number;
  stl: number;
  blk: number;
  tov: number;
  pf: number;
  pm: number;
  fg: string;
  '3pt': string;
  ft: string;
  is_starter: boolean;
  is_played: boolean;
}

interface MatchDetail {
  id: number;
  home_team: { id: number; name: string; score: number };
  away_team: { id: number; name: string; score: number };
  is_ot: boolean;
  pace: number;
  box_score: {
    home: PlayerStat[];
    away: PlayerStat[];
  };
  pbp_logs: string[];
}

const MatchDetailModal = ({ matchId, onClose }: { matchId: number; onClose: () => void }) => {
  const [data, setData] = useState<MatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'box' | 'pbp'>('box');

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const res = await fetch(`/api/league/match/${matchId}`);
        if (res.ok) {
          setData(await res.json());
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [matchId]);

  if (!data && !loading) return null;

  // 樣式輔助
  const getGradeColor = (g: string) => {
    if (['SSR', 'SS'].includes(g)) return 'text-yellow-400 font-black';
    if (g === 'S') return 'text-red-400 font-bold';
    return 'text-gray-400';
  };

  const StatTable = ({ players }: { players: PlayerStat[] }) => {
    // [修改 1] 過濾未出賽 (is_played) 並排序 (先發優先 -> 上場時間)
    const activePlayers = players
      .filter(p => p.is_played)
      .sort((a, b) => {
        if (a.is_starter !== b.is_starter) return a.is_starter ? -1 : 1;
        return b.min - a.min;
      });

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left border-collapse">
          <thead className="bg-white/5 text-gray-400 border-b border-white/10">
            <tr>
              <th className="p-2 w-8">POS</th>
              <th className="p-2">Name</th>
              <th className="p-2 text-center">MIN</th>
              <th className="p-2 text-center text-white font-bold">PTS</th>
              <th className="p-2 text-center">REB</th>
              <th className="p-2 text-center">AST</th>
              <th className="p-2 text-center">STL</th>
              <th className="p-2 text-center">BLK</th>
              <th className="p-2 text-center text-gray-500">TO</th>
              <th className="p-2 text-center">FG</th>
              <th className="p-2 text-center">3PT</th>
              <th className="p-2 text-center">FT</th>
              <th className="p-2 text-center">+/-</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {activePlayers.map((p) => (
              <tr key={p.id} className={`hover:bg-white/5 transition-colors ${p.is_starter ? 'bg-white/[0.02]' : ''}`}>
                <td className="p-2 text-gray-500 font-mono">{p.pos}</td>
                <td className="p-2">
                  <div className="flex items-center gap-2">
                    {/* [修改 2] 先發標記 GS (Game Starter) */}
                    {p.is_starter && (
                      <span className="text-[9px] bg-blue-600 text-white px-1 rounded font-bold tracking-tighter shadow-sm" title="Starter">
                        GS
                      </span>
                    )}
                    
                    <span className={`text-[10px] ${getGradeColor(p.grade)}`}>{p.grade}</span>
                    <span className={`font-bold ${p.is_starter ? 'text-white' : 'text-gray-400'}`}>{p.name}</span>
                  </div>
                </td>
                <td className="p-2 text-center font-mono text-gray-400">{p.min}</td>
                <td className="p-2 text-center font-mono font-black text-yellow-400 text-sm">{p.pts}</td>
                <td className="p-2 text-center font-mono text-gray-300">{p.reb}</td>
                <td className="p-2 text-center font-mono text-gray-300">{p.ast}</td>
                <td className="p-2 text-center font-mono text-gray-400">{p.stl}</td>
                <td className="p-2 text-center font-mono text-gray-400">{p.blk}</td>
                <td className="p-2 text-center font-mono text-gray-500">{p.tov}</td>
                <td className="p-2 text-center font-mono text-gray-400">{p.fg}</td>
                <td className="p-2 text-center font-mono text-gray-400">{p['3pt']}</td>
                <td className="p-2 text-center font-mono text-gray-500">{p.ft}</td>
                <td className={`p-2 text-center font-mono font-bold ${p.pm > 0 ? 'text-green-400' : p.pm < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                  {p.pm > 0 ? '+' : ''}{p.pm}
                </td>
              </tr>
            ))}
            {activePlayers.length === 0 && (
              <tr>
                <td colSpan={13} className="p-4 text-center text-gray-600 italic">無出賽數據</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-gray-900 border border-white/10 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="relative p-6 bg-gradient-to-r from-gray-900 to-gray-800 border-b border-white/10 shrink-0">
          <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-white transition-colors">
            <X size={24} />
          </button>
          
          {loading ? (
            <div className="text-center text-white py-4">載入數據中...</div>
          ) : (
            <div className="flex justify-between items-center px-4">
              {/* Home */}
              <div className="text-center w-1/3">
                <div className="text-2xl font-bold text-white mb-1">{data!.home_team.name}</div>
                <div className="text-5xl font-black text-yellow-400 font-mono drop-shadow-lg">{data!.home_team.score}</div>
              </div>
              
              {/* VS / Info */}
              <div className="flex flex-col items-center gap-2">
                <div className="text-gray-500 font-black text-xl italic">VS</div>
                <div className="flex items-center gap-2 bg-black/30 px-3 py-1 rounded-full border border-white/5">
                  <Clock size={12} className="text-blue-400" />
                  <span className="text-xs text-blue-200 font-mono">Pace: {data!.pace.toFixed(1)}</span>
                </div>
                {data!.is_ot && <span className="text-xs font-bold text-orange-500 border border-orange-500/30 px-2 py-0.5 rounded">OT</span>}
              </div>

              {/* Away */}
              <div className="text-center w-1/3">
                <div className="text-2xl font-bold text-white mb-1">{data!.away_team.name}</div>
                <div className="text-5xl font-black text-yellow-400 font-mono drop-shadow-lg">{data!.away_team.score}</div>
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        {!loading && (
          <div className="flex border-b border-white/10 bg-black/20 shrink-0">
            <button 
              onClick={() => setActiveTab('box')}
              className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 transition-colors
                ${activeTab === 'box' ? 'text-white bg-white/5 border-b-2 border-blue-500' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <Activity size={16} /> 數據統計 (Box Score)
            </button>
            <button 
              onClick={() => setActiveTab('pbp')}
              className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 transition-colors
                ${activeTab === 'pbp' ? 'text-white bg-white/5 border-b-2 border-blue-500' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <List size={16} /> 文字轉播 (Play-by-Play)
            </button>
          </div>
        )}

        {/* Body */}
        {!loading && (
          <div className="flex-1 overflow-y-auto bg-gray-900/50 p-6 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            {activeTab === 'box' ? (
              <div className="space-y-8">
                {/* Home Box */}
                <div>
                  <h3 className="text-sm font-bold text-gray-400 mb-3 uppercase tracking-wider flex items-center gap-2">
                    <Trophy size={14} className="text-yellow-500" /> {data!.home_team.name}
                  </h3>
                  <StatTable players={data!.box_score.home} />
                </div>
                
                {/* Away Box */}
                <div>
                  <h3 className="text-sm font-bold text-gray-400 mb-3 uppercase tracking-wider flex items-center gap-2">
                    <Trophy size={14} className="text-blue-500" /> {data!.away_team.name}
                  </h3>
                  <StatTable players={data!.box_score.away} />
                </div>
              </div>
            ) : (
              <div className="space-y-1 font-mono text-sm">
                {data!.pbp_logs.map((log, idx) => (
                  <div key={idx} className={`p-2 rounded border-l-2 ${log.includes('Good') ? 'border-green-500 bg-green-900/10 text-green-100' : 
                    log.includes('Miss') ? 'border-red-500 bg-red-900/10 text-red-200' : 
                    log.includes('Start') || log.includes('End') ? 'border-blue-500 bg-blue-900/20 text-blue-100 font-bold text-center' :
                    'border-gray-700 text-gray-400'}`}>
                    {log}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MatchDetailModal;