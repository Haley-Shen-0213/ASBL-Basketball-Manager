// frontend/src/components/SchedulesPage.tsx
import React, { useState, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Trophy, Users, Eye } from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';

interface TeamInfo {
  id: number;
  name: string;
}

interface MatchInfo {
  home_score: number;
  away_score: number;
  is_ot: boolean;
}

interface ScheduleItem {
  id: number;
  day: number;
  game_type: number;
  status: string;
  match_id: number | null;
  home_team: TeamInfo;
  away_team: TeamInfo;
  match: MatchInfo | null;
}

interface SeasonInfo {
  id: number;
  season_number: number;
  current_day: number;
  phase: string;
}

const SchedulesPage = ({ teamId }: { teamId: number }) => {
  const [season, setSeason] = useState<SeasonInfo | null>(null);
  const [currentDay, setCurrentDay] = useState<number>(1);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modal State
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);

  useEffect(() => {
    const fetchSeason = async () => {
      try {
        const res = await fetch('/api/league/season/info');
        if (res.ok) {
          const data = await res.json();
          setSeason(data);
          setCurrentDay(data.current_day || 1);
        }
      } catch (e) {
        console.error("Failed to fetch season info", e);
      }
    };
    fetchSeason();
  }, []);

  useEffect(() => {
    if (!season) return;

    const fetchSchedule = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/league/schedule?season_id=${season.id}&day=${currentDay}`);
        if (res.ok) {
          const data = await res.json();
          setSchedules(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchSchedule();
  }, [season, currentDay]);

  const handlePrevDay = () => {
    if (currentDay > 1) setCurrentDay(currentDay - 1);
  };

  const handleNextDay = () => {
    if (currentDay < 91) setCurrentDay(currentDay + 1);
  };

  // 排序邏輯：將與自己相關的比賽排在最前面
  const sortGames = (games: ScheduleItem[]) => {
    return [...games].sort((a, b) => {
      const isMyGameA = a.home_team.id === teamId || a.away_team.id === teamId;
      const isMyGameB = b.home_team.id === teamId || b.away_team.id === teamId;
      
      if (isMyGameA && !isMyGameB) return -1;
      if (!isMyGameA && isMyGameB) return 1;
      return 0;
    });
  };

  const officialGames = sortGames(schedules.filter(s => s.game_type === 1));
  const expansionGames = sortGames(schedules.filter(s => s.game_type === 2));

  const GameCard = ({ game }: { game: ScheduleItem }) => {
    const isFinished = game.status === 'FINISHED' && game.match;
    const homeWin = isFinished && game.match!.home_score > game.match!.away_score;
    const awayWin = isFinished && game.match!.away_score > game.match!.home_score;
    
    const isMyHome = game.home_team.id === teamId;
    const isMyAway = game.away_team.id === teamId;
    const isMyGame = isMyHome || isMyAway;

    return (
      <div 
        onClick={() => {
          if (isFinished && game.match_id) setSelectedMatchId(game.match_id);
        }}
        className={`backdrop-blur-md border rounded-xl p-4 flex items-center justify-between shadow-lg group relative overflow-hidden transition-all
          ${isMyGame ? 'bg-violet-900/40 border-violet-500/50 ring-1 ring-violet-500/30' : 'bg-gray-900/40 border-white/10'}
          ${isFinished ? 'cursor-pointer hover:bg-gray-900/60 hover:border-blue-500/30' : ''}`}
      >
        {/* Hover Effect Hint */}
        {isFinished && (
          <div className="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
            <div className="bg-black/50 px-3 py-1 rounded-full text-xs text-white font-bold flex items-center gap-2 backdrop-blur-sm">
              <Eye size={12} /> 查看數據
            </div>
          </div>
        )}

        {/* Home Team (Left) */}
        <div className="flex-1 flex items-center gap-3 overflow-hidden z-10">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border shadow-inner shrink-0
            ${homeWin ? 'bg-yellow-500 text-black border-yellow-400' : 'bg-white/10 border-white/10 text-gray-300'}
            ${isMyHome ? 'ring-2 ring-white' : ''}`}>
            {game.home_team.name.charAt(0)}
          </div>
          
          <div className="flex items-center gap-2 min-w-0">
             {/* 主場標籤 */}
             <span className="text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1.5 py-0.5 rounded shrink-0">主</span>
             
             <div className={`font-bold text-sm truncate ${homeWin ? 'text-white' : 'text-gray-300'} ${isMyHome ? 'text-yellow-300' : ''}`}>
               {game.home_team.name}
             </div>
             {isMyHome && <span className="text-[10px] bg-white/20 px-1 rounded shrink-0 text-white/80">YOU</span>}
          </div>
        </div>

        {/* Score / VS (Center) */}
        <div className="px-2 flex flex-col items-center min-w-[100px] shrink-0 z-10">
          {isFinished ? (
            <>
              <div className="text-2xl font-black font-mono text-white tracking-widest flex items-center gap-2 drop-shadow-md">
                <span className={homeWin ? 'text-yellow-400' : 'text-gray-400'}>{game.match!.home_score}</span>
                <span className="text-gray-600 text-sm">:</span>
                <span className={awayWin ? 'text-yellow-400' : 'text-gray-400'}>{game.match!.away_score}</span>
              </div>
              {game.match!.is_ot && (
                <span className="text-[10px] font-bold text-orange-300 bg-orange-500/20 px-1.5 py-0.5 rounded mt-1 border border-orange-500/30">OT</span>
              )}
            </>
          ) : (
            <div className="text-xl font-black text-gray-500 font-mono">VS</div>
          )}
          
          <div className={`text-[10px] font-bold mt-1.5 px-2 py-0.5 rounded border backdrop-blur-sm
            ${game.status === 'FINISHED' ? 'bg-green-500/20 text-green-400 border-green-500/30' : 
              game.status === 'PUBLISHED' ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : 'bg-gray-600/30 text-gray-400 border-gray-600/30'}`}>
            {game.status === 'FINISHED' ? '已完賽' : game.status === 'PUBLISHED' ? '未開賽' : '待定'}
          </div>
        </div>

        {/* Away Team (Right) */}
        <div className="flex-1 flex items-center gap-3 justify-end overflow-hidden z-10">
          <div className="flex items-center gap-2 justify-end min-w-0">
             {isMyAway && <span className="text-[10px] bg-white/20 px-1 rounded shrink-0 text-white/80">YOU</span>}
             
             <div className={`font-bold text-sm text-right truncate ${awayWin ? 'text-white' : 'text-gray-300'} ${isMyAway ? 'text-yellow-300' : ''}`}>
               {game.away_team.name}
             </div>
             
             {/* 客場標籤 */}
             <span className="text-[10px] font-bold bg-red-500/20 text-red-300 border border-red-500/30 px-1.5 py-0.5 rounded shrink-0">客</span>
          </div>
          
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border shadow-inner shrink-0
            ${awayWin ? 'bg-yellow-500 text-black border-yellow-400' : 'bg-white/10 border-white/10 text-gray-300'}
            ${isMyAway ? 'ring-2 ring-white' : ''}`}>
            {game.away_team.name.charAt(0)}
          </div>
        </div>
      </div>
    );
  };

  if (!season) return <div className="p-8 text-center text-white/50">載入賽季資訊中...</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 h-full flex flex-col">
      {/* Header & Navigation */}
      <div className="flex justify-between items-center bg-gray-900/60 backdrop-blur-md p-5 rounded-2xl border border-white/10 shadow-xl">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <Calendar className="text-asbl-violet" /> 
          <span>Season {season.season_number}</span>
          <span className="text-xs font-bold text-gray-300 bg-white/10 px-2 py-1 rounded border border-white/5 tracking-wider">{season.phase}</span>
        </h2>

        <div className="flex items-center gap-4 bg-black/40 p-1.5 rounded-xl border border-white/10 shadow-inner">
          <button 
            onClick={handlePrevDay}
            disabled={currentDay <= 1}
            className="p-2 hover:bg-white/10 rounded-lg text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
          >
            <ChevronLeft size={20} />
          </button>
          <div className="text-center min-w-[100px]">
            <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-0.5">DAY</div>
            <div className="text-2xl font-black text-white font-mono leading-none drop-shadow-md">{currentDay}</div>
          </div>
          <button 
            onClick={handleNextDay}
            disabled={currentDay >= 91}
            className="p-2 hover:bg-white/10 rounded-lg text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto space-y-8 pr-2 pb-4 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
        {loading ? (
          <div className="text-center py-20 text-white/50 flex flex-col items-center gap-2">
            <div className="w-6 h-6 border-2 border-asbl-violet border-t-transparent rounded-full animate-spin"></div>
            載入賽程中...
          </div>
        ) : schedules.length === 0 ? (
          <div className="text-center py-20 text-gray-400 bg-gray-900/30 rounded-2xl border border-dashed border-white/10">
            本日無賽程
          </div>
        ) : (
          <>
            {/* Official League */}
            {officialGames.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-white/70 flex items-center gap-2 px-2 uppercase tracking-wider">
                  <Trophy size={14} className="text-yellow-400" /> 正式聯賽 (Official League)
                </h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  {officialGames.map(g => <GameCard key={g.id} game={g} />)}
                </div>
              </div>
            )}

            {/* Expansion League */}
            {expansionGames.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-white/70 flex items-center gap-2 px-2 mt-6 uppercase tracking-wider">
                  <Users size={14} className="text-blue-400" /> 擴充聯賽 (Expansion League)
                </h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  {expansionGames.map(g => <GameCard key={g.id} game={g} />)}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Match Detail Modal */}
      {selectedMatchId && (
        <MatchDetailModal 
          matchId={selectedMatchId} 
          onClose={() => setSelectedMatchId(null)} 
        />
      )}
    </div>
  );
};

export default SchedulesPage;