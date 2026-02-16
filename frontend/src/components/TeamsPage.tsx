// ---------------------------------------------------------
// 1. frontend/src/components/TeamsPage.tsx
// ---------------------------------------------------------
import React, { useState, useEffect } from 'react';
import { Trophy, TrendingUp, Users, Star } from 'lucide-react';

interface TeamData {
  id: number;
  rank: number;
  name: string;
  reputation: number;
  season_wins: number;
  season_losses: number;
  total_rating: number;
  player_count: number;
}

const TeamsPage = () => {
  const [teams, setTeams] = useState<TeamData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/team/list')
      .then(res => res.json())
      .then(data => {
        setTeams(data);
        setLoading(false);
      })
      .catch(err => console.error(err));
  }, []);

  if (loading) return <div className="p-8 text-center text-white">載入聯盟資料中...</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-end">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Trophy className="text-amber-500" /> 聯盟球隊排行
        </h2>
      </div>

      <div className="bg-white/60 backdrop-blur-md border border-white/50 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 text-gray-700 font-bold text-xs border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-center w-16">排名</th>
                <th className="px-4 py-3">球隊名稱</th>
                <th className="px-4 py-3 text-center">戰績 (勝-敗)</th>
                <th className="px-4 py-3 text-center">聲望</th>
                <th className="px-4 py-3 text-center">球隊總評</th>
                <th className="px-4 py-3 text-center">球員數</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {teams.map((team) => (
                <tr key={team.id} className="hover:bg-white/80 transition-colors">
                  <td className="px-4 py-3 text-center font-black text-lg text-gray-500">
                    {team.rank <= 3 ? <span className="text-amber-500">#{team.rank}</span> : team.rank}
                  </td>
                  <td className="px-4 py-3 font-bold text-gray-900 text-base">
                    {team.name}
                  </td>
                  <td className="px-4 py-3 text-center font-mono">
                    <span className="text-green-600 font-bold">{team.season_wins}</span> - <span className="text-red-600 font-bold">{team.season_losses}</span>
                  </td>
                  <td className="px-4 py-3 text-center font-mono text-gray-700">
                    {team.reputation}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 px-2 py-1 rounded font-bold font-mono">
                      <TrendingUp size={14} /> {team.total_rating}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-500">
                    {team.player_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TeamsPage ;