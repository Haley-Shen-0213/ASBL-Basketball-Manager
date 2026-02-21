// frontend/src/components/SchedulesPage.tsx
import React, { useState, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Trophy, Users, Crown, Grid3X3, X, Zap } from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';

// =========================================================================
// 介面定義
// =========================================================================

interface TeamInfo {
  id: number;
  name: string;
  wins: number;
  losses: number;
}

interface MatchInfo {
  home_score: number;
  away_score: number;
  is_ot: boolean;
}

interface SeriesInfo {
  round_label: string;
  game_number: number;
  home_wins: number;
  away_wins: number;
}

interface ScheduleItem {
  id: number;
  day: number;
  game_type: number; // 1: Regular, 2: Provisional, 3: Playoff
  status: string;
  match_id: number | null;
  home_team: TeamInfo;
  away_team: TeamInfo;
  match: MatchInfo | null;
  series_info?: SeriesInfo;
}

interface SeasonInfo {
  id: number;
  season_number: number;
  current_day: number;
  phase: string;
}

// =========================================================================
// 輔助函式
// =========================================================================

const getPhaseLabel = (day: number) => {
  if (day === 1) return '季前熱身 / 聯賽重組';
  if (day >= 2 && day <= 71) return '例行賽';
  if (day === 72) return '季後賽名單確認';
  if (day >= 73 && day <= 89) return '季後賽';
  return '休賽季';
};

// 權重計算：用於排序季後賽卡片
const getRoundWeight = (label: string) => {
  switch (label) {
    case 'Finals': return 100;      // 總冠軍賽最優先
    case 'Conf. Finals': return 80;
    case 'Conf. Semis': return 60;
    case 'Round 1': return 40;
    case '3rd Place': return 20;    // 季軍賽權重較低
    default: return 0;
  }
};

// =========================================================================
// 組件：全螢幕置中日期選擇器
// =========================================================================

const DateSelectorModal = ({ 
  currentDay, 
  maxDay, 
  onSelect, 
  onClose 
}: { 
  currentDay: number, 
  maxDay: number, 
  onSelect: (d: number) => void, 
  onClose: () => void 
}) => {
  const days = Array.from({ length: 91 }, (_, i) => i + 1);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose}>
      <div 
        className="bg-gray-900 border border-white/20 rounded-2xl shadow-2xl w-[90%] max-w-[400px] p-6 animate-in zoom-in-95 duration-200"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-5 pb-3 border-b border-white/10">
          <span className="text-xl font-bold text-white flex items-center gap-2">
            <Calendar className="text-asbl-violet" size={24} /> 快速跳轉日期
          </span>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>
        
        <div className="grid grid-cols-7 gap-2 max-h-[60vh] overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 pr-2">
          {days.map(d => {
            let bgClass = "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white";
            if (d === currentDay) bgClass = "bg-asbl-violet text-white font-black ring-2 ring-white/30 shadow-lg scale-105 z-10";
            else if (d > maxDay) bgClass = "bg-black/40 text-gray-700 cursor-not-allowed";
            
            const isPlayoff = d >= 73 && d <= 89;
            
            return (
              <button
                key={d}
                onClick={() => onSelect(d)}
                className={`text-sm py-3 rounded-lg transition-all flex flex-col items-center justify-center relative ${bgClass}`}
              >
                {d}
                {isPlayoff && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1"></span>}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// =========================================================================
// 主頁面組件
// =========================================================================

const SchedulesPage = ({ teamId }: { teamId: number }) => {
  const [season, setSeason] = useState<SeasonInfo | null>(null);
  const [currentDay, setCurrentDay] = useState<number>(1);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDatePicker, setShowDatePicker] = useState(false);
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

  const handlePrevDay = () => { if (currentDay > 1) setCurrentDay(currentDay - 1); };
  const handleNextDay = () => { if (currentDay < 91) setCurrentDay(currentDay + 1); };

  // 排序邏輯修正：總冠軍賽絕對優先 > 我的比賽 > 其他輪次權重
  const sortGames = (games: ScheduleItem[]) => {
    return [...games].sort((a, b) => {
      // 1. 總冠軍賽絕對置頂 (Finals always top)
      const isFinalsA = a.series_info?.round_label === 'Finals';
      const isFinalsB = b.series_info?.round_label === 'Finals';
      if (isFinalsA && !isFinalsB) return -1;
      if (!isFinalsA && isFinalsB) return 1;

      // 2. 我的比賽優先 (My Game priority)
      const isMyGameA = a.home_team.id === teamId || a.away_team.id === teamId;
      const isMyGameB = b.home_team.id === teamId || b.away_team.id === teamId;
      if (isMyGameA && !isMyGameB) return -1;
      if (!isMyGameA && isMyGameB) return 1;

      // 3. 其他季後賽輪次權重 (Round Weight)
      if (a.game_type === 3 && b.game_type === 3 && a.series_info && b.series_info) {
        const weightA = getRoundWeight(a.series_info.round_label);
        const weightB = getRoundWeight(b.series_info.round_label);
        return weightB - weightA; // 權重大的排前面
      }

      return 0;
    });
  };

  const activeSchedules = schedules.filter(s => s.status !== 'CANCELLED');
  const playoffGames = sortGames(activeSchedules.filter(s => s.game_type === 3));
  const officialGames = sortGames(activeSchedules.filter(s => s.game_type === 1));
  const expansionGames = sortGames(activeSchedules.filter(s => s.game_type === 2));
  const hasActiveGames = playoffGames.length > 0 || officialGames.length > 0 || expansionGames.length > 0;

  // =========================================================================
  // 萬用遊戲卡片組件
  // =========================================================================
  const GameCard = ({ game }: { game: ScheduleItem }) => {
    const isFinished = game.status === 'FINISHED' && game.match;
    const homeWin = isFinished && game.match!.home_score > game.match!.away_score;
    const awayWin = isFinished && game.match!.away_score > game.match!.home_score;
    const isMyHome = game.home_team.id === teamId;
    const isMyAway = game.away_team.id === teamId;
    const isMyGame = isMyHome || isMyAway;
    
    const handleClick = () => { if (isFinished && game.match_id) setSelectedMatchId(game.match_id); };
    const cursorClass = isFinished ? 'cursor-pointer hover:scale-[1.01] transition-transform' : '';

    // -----------------------------------------------------------------------
    // 樣式 1: 🧊 冰藍極光 (Ice Aurora) - [例行賽]
    // -----------------------------------------------------------------------
    if (game.game_type === 1 || game.game_type === 2) {
      return (
        <div onClick={handleClick} className={`relative rounded-xl overflow-hidden flex flex-col mb-3 border shadow-lg transition-all
          ${isMyGame ? 'bg-slate-900 border-cyan-500/50 shadow-cyan-500/10' : 'bg-slate-950 border-cyan-900/30'} ${cursorClass}`}>
          
          <div className={`py-2 px-4 flex justify-between items-center text-xs font-bold tracking-wider border-b 
            ${isMyGame ? 'bg-cyan-950/40 border-cyan-500/20 text-cyan-300' : 'bg-slate-900 border-white/5 text-slate-500'}`}>
            <span>{game.game_type === 1 ? '例行賽' : '擴充聯賽'}</span>
            <span>第 {game.day - 1} 場</span>
          </div>

          <div className="p-4 flex items-center justify-between relative h-24">
            {isMyGame && <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-24 bg-cyan-500/10 blur-3xl rounded-full pointer-events-none"></div>}

            <div className="flex items-center gap-3 flex-1 z-10">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold shadow-lg
                 ${homeWin ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-500'}`}>
                 {game.home_team.name.charAt(0)}
              </div>
              <div className="flex flex-col">
                <span className={`font-bold text-sm ${homeWin ? 'text-white' : 'text-gray-500'} ${isMyHome ? 'text-cyan-300' : ''}`}>
                  {game.home_team.name}
                </span>
                <span className="text-[11px] text-yellow-400 font-black font-mono mt-0.5 tracking-wide">
                  {game.home_team.wins}W-{game.home_team.losses}L
                </span>
              </div>
            </div>

            <div className="z-10 flex flex-col items-center">
              {isFinished ? (
                <div className="text-3xl font-bold font-mono text-white tracking-tight">
                  {game.match!.home_score} <span className="text-gray-600 text-xl">:</span> {game.match!.away_score}
                </div>
              ) : ( <span className="text-xl font-bold text-gray-700">VS</span> )}
            </div>

            <div className="flex items-center gap-3 flex-1 justify-end text-right z-10">
              <div className="flex flex-col">
                <span className={`font-bold text-sm ${awayWin ? 'text-white' : 'text-gray-500'} ${isMyAway ? 'text-cyan-300' : ''}`}>
                  {game.away_team.name}
                </span>
                <span className="text-[11px] text-yellow-400 font-black font-mono mt-0.5 tracking-wide">
                  {game.away_team.wins}W-{game.away_team.losses}L
                </span>
              </div>
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold shadow-lg
                 ${awayWin ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-500'}`}>
                 {game.away_team.name.charAt(0)}
              </div>
            </div>
          </div>
        </div>
      );
    }

    const roundLabel = game.series_info?.round_label || '';

    // -----------------------------------------------------------------------
    // 樣式 2: 🛡️ 鈦金裝甲 (Titanium Armor) - [季後賽首輪 R1]
    // -----------------------------------------------------------------------
    if (roundLabel === 'Round 1') {
      return (
        <div onClick={handleClick} className={`relative rounded-lg overflow-hidden flex flex-col mb-4 shadow-lg border-t border-white/10
          ${isMyGame ? 'bg-[#1e293b]' : 'bg-[#0f172a]'} ${cursorClass}`}>
          <div className={`absolute top-0 left-0 w-1.5 h-full ${isMyGame ? 'bg-orange-500' : 'bg-slate-600'}`}></div>
          
          <div className="py-2 px-4 pl-6 flex justify-between items-center text-xs font-bold tracking-wider bg-white/5 text-gray-300">
            <span>季後賽首輪 · G{game.series_info?.game_number}</span>
            <span className="text-[10px] bg-black/30 px-2 py-0.5 rounded">系列賽 {game.series_info?.home_wins}-{game.series_info?.away_wins}</span>
          </div>

          <div className="p-4 pl-6 flex items-center justify-between h-24 bg-gradient-to-b from-transparent to-black/20">
            <div className={`text-xl font-black italic ${homeWin ? 'text-white' : 'text-gray-500'} ${isMyHome ? 'text-orange-400' : ''}`}>
              {game.home_team.name}
            </div>
            <div className="flex flex-col items-center">
              {isFinished ? (
                <>
                  <div className="text-3xl font-black text-white tracking-widest">
                    {game.match!.home_score}-{game.match!.away_score}
                  </div>
                  <div className="text-[10px] text-orange-500/70 font-bold uppercase tracking-widest mt-1">終場比數</div>
                </>
              ) : ( <span className="text-xl font-black text-gray-700">VS</span> )}
            </div>
            <div className={`text-xl font-black italic ${awayWin ? 'text-white' : 'text-gray-500'} ${isMyAway ? 'text-orange-400' : ''}`}>
              {game.away_team.name}
            </div>
          </div>
        </div>
      );
    }

    // -----------------------------------------------------------------------
    // 樣式 3: 🌋 熔岩裂變 (Magma Fracture) - [分區準決賽 R2]
    // -----------------------------------------------------------------------
    if (roundLabel === 'Conf. Semis') {
      return (
        <div onClick={handleClick} className={`relative rounded-xl overflow-hidden flex flex-col mb-4 border-l-8 
          ${isMyGame ? 'bg-gray-900 border-orange-600' : 'bg-gray-950 border-gray-700'} ${cursorClass}`}>
          <div className="absolute right-0 top-0 w-32 h-full bg-gradient-to-l from-orange-900/10 to-transparent skew-x-[-20deg] pointer-events-none"></div>
          
          <div className="py-2 px-4 flex justify-between items-center relative z-10 w-full">
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${isMyGame ? 'bg-orange-500' : 'bg-gray-600'}`}></span>
              <span className="text-[10px] font-bold text-orange-200/70 uppercase tracking-wider">分區準決賽 · G{game.series_info?.game_number}</span>
            </div>
            <span className="text-[10px] bg-black/40 px-2 py-0.5 rounded text-orange-400 font-mono font-bold">
               系列賽 {game.series_info?.home_wins}-{game.series_info?.away_wins}
            </span>
          </div>

          <div className="p-4 flex items-center justify-between h-24 relative z-10">
            <div className="flex-1">
              <div className={`text-2xl font-black uppercase italic tracking-tighter transform -skew-x-6 
                ${homeWin ? 'text-white' : 'text-gray-600'} ${isMyHome ? 'text-orange-500' : ''}`}>
                {game.home_team.name}
              </div>
            </div>
            <div className="flex flex-col items-center px-4">
              {isFinished ? (
                <>
                  <div className="text-4xl font-black text-orange-500 italic leading-none">{game.match!.home_score}</div>
                  <div className="w-full h-0.5 bg-gray-800 my-1"></div>
                  <div className="text-2xl font-black text-gray-600 italic leading-none">{game.match!.away_score}</div>
                </>
              ) : ( <span className="text-xl font-black text-gray-700 italic">VS</span> )}
            </div>
            <div className="flex-1 text-right">
              <div className={`text-2xl font-black uppercase italic tracking-tighter transform -skew-x-6 
                ${awayWin ? 'text-white' : 'text-gray-600'} ${isMyAway ? 'text-orange-500' : ''}`}>
                {game.away_team.name}
              </div>
            </div>
          </div>
        </div>
      );
    }

    // -----------------------------------------------------------------------
    // 樣式 4: ⚡ 雷霆風暴 (Thunder Storm) - [分區決賽 R3]
    // -----------------------------------------------------------------------
    if (roundLabel === 'Conf. Finals') {
      return (
        <div onClick={handleClick} className={`relative rounded-xl overflow-hidden flex flex-col mb-4 border-2 shadow-[0_0_20px_rgba(250,204,21,0.15)]
          ${isMyGame ? 'bg-slate-900 border-yellow-400' : 'bg-slate-950 border-yellow-900/50'} ${cursorClass}`}>
          
          <div className={`py-1.5 px-4 flex justify-center items-center text-black font-black uppercase tracking-widest text-xs
            ${isMyGame ? 'bg-yellow-400' : 'bg-yellow-900/50 text-yellow-200'}`}>
            <Zap size={12} className="mr-2 fill-black" /> 分區決賽 <Zap size={12} className="ml-2 fill-black" />
          </div>

          <div className="p-5 flex items-center justify-between h-32 relative">
            {isMyGame && (
              <>
                <div className="absolute top-0 left-1/3 w-[1px] h-full bg-yellow-400/20 rotate-12 pointer-events-none"></div>
                <div className="absolute top-0 right-1/3 w-[1px] h-full bg-yellow-400/20 -rotate-12 pointer-events-none"></div>
              </>
            )}

            <div className="flex items-center gap-4 flex-1 z-10">
              <div className={`w-14 h-14 rounded-full border-2 flex items-center justify-center text-2xl font-black shadow-lg
                ${homeWin ? 'bg-yellow-100 text-black border-yellow-400' : 'bg-slate-800 text-slate-600 border-slate-700'}`}>
                {game.home_team.name.charAt(0)}
              </div>
              <div className="flex flex-col">
                <span className={`font-black text-xl italic ${homeWin ? 'text-yellow-100' : 'text-gray-500'}`}>
                  {game.home_team.name}
                </span>
                {isMyHome && <span className="text-[9px] bg-yellow-400/20 text-yellow-300 px-1 rounded w-fit">MY TEAM</span>}
              </div>
            </div>

            <div className="z-10 flex flex-col items-center">
              {isFinished ? (
                <>
                  <div className="text-5xl font-black italic text-white drop-shadow-[2px_2px_0px_rgba(250,204,21,0.8)]">
                    {game.match!.home_score}-{game.match!.away_score}
                  </div>
                  <div className="mt-2 bg-black/60 border border-red-500/50 px-3 py-0.5 rounded text-red-500 font-black text-xs tracking-wider shadow-[0_0_10px_rgba(239,68,68,0.3)]">
                    系列賽 {game.series_info?.home_wins}-{game.series_info?.away_wins}
                  </div>
                </>
              ) : ( <span className="text-2xl font-black text-gray-700">VS</span> )}
            </div>

            <div className="flex items-center gap-4 flex-1 justify-end z-10 text-right">
              <div className="flex flex-col items-end">
                <span className={`font-black text-xl italic ${awayWin ? 'text-yellow-100' : 'text-gray-500'}`}>
                  {game.away_team.name}
                </span>
                {isMyAway && <span className="text-[9px] bg-yellow-400/20 text-yellow-300 px-1 rounded w-fit">MY TEAM</span>}
              </div>
               <div className={`w-14 h-14 rounded-full border-2 flex items-center justify-center text-2xl font-black shadow-lg
                ${awayWin ? 'bg-yellow-100 text-black border-yellow-400' : 'bg-slate-800 text-slate-600 border-slate-700'}`}>
                {game.away_team.name.charAt(0)}
              </div>
            </div>
          </div>
        </div>
      );
    }

    // -----------------------------------------------------------------------
    // 樣式 5: ⚜️ 皇家黑曜石 (Royal Obsidian) - [季軍賽 3rd Place]
    // （維持你現在的大小/輸出內容，只改「顏色呈現」成你給的款式）
    // -----------------------------------------------------------------------
    if (roundLabel === '3rd Place') {
      return (
        <div
          onClick={handleClick}
          className={`relative rounded-lg overflow-hidden flex flex-col mb-4 border lg:col-span-2 ${cursorClass}
            bg-[#111] border-[#d4af37]/30`}
        >
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#d4af37] to-transparent"></div>

          <div className="py-2 px-4 flex justify-center items-center">
            <span className="text-[12px] font-serif italic text-[#d4af37] tracking-widest">季軍賽</span>
          </div>

          {/* 高度設定: h-32 (約 128px) */}
          <div className="p-5 flex items-center justify-between h-32 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-[#222] to-[#000]">
            <div className="flex flex-col items-center flex-1 border-r border-white/5">
              {/* 顏色：依你款式，贏家白、輸家灰 */}
              <span className={`text-2xl font-serif ${homeWin ? 'text-white' : 'text-gray-600'}`}>
                {game.home_team.name}
              </span>
              {homeWin && <span className="text-xs text-[#d4af37] mt-1">勝者</span>}
            </div>

            <div className="px-6 flex flex-col items-center">
              <div className="text-4xl font-serif text-[#f3e5ab] drop-shadow-md">
                {isFinished ? `${game.match!.home_score} - ${game.match!.away_score}` : 'VS'}
              </div>

              {!!game.series_info && (
                <div className="mt-2 text-lg text-red-500 font-bold tracking-[0.2em] uppercase">
                  系列賽 {game.series_info?.home_wins}-{game.series_info?.away_wins}
                </div>
              )}
            </div>
            <div className="flex flex-col items-center flex-1 border-l border-white/5">
              <span className={`text-2xl font-serif ${awayWin ? 'text-white' : 'text-gray-600'}`}>
                {game.away_team.name}
              </span>
              {awayWin && <span className="text-xs text-[#d4af37] mt-1">勝者</span>}
            </div>
          </div>
        </div>
      );
    }

    // -----------------------------------------------------------------------
    // 樣式 6: 🔥 熱血對決 (Intense Red) - [總冠軍賽 Finals] (預設)
    // （維持你現在的大小/輸出內容，只改「顏色呈現」成你給的款式）
    // -----------------------------------------------------------------------
    return (
      <div
        onClick={handleClick}
        className={`relative rounded-2xl overflow-hidden shadow-2xl flex flex-col mb-4 border lg:col-span-2 ${cursorClass}
          bg-gradient-to-br from-red-950 to-black border-red-600/40`}
      >
        <div className="py-3 px-4 flex justify-center items-center text-sm font-black uppercase tracking-[0.3em] bg-red-600 text-white">
          總冠軍賽 · 第 {game.series_info?.game_number} 戰
        </div>

        {/* 高度加大至 h-48 (約 192px)，比季軍賽大 1.5 倍 */}
        <div className="p-8 flex items-center justify-between h-36">
          {/* 顏色：依你款式，贏家白、輸家灰（Finals 款式右邊偏灰） */}
          <div className={`flex-1 font-black text-4xl ${homeWin ? 'text-white' : 'text-gray-600'}`}>
            {game.home_team.name}
          </div>

          <div className="flex flex-col items-center">
            <div className="text-6xl font-black italic text-white skew-x-[-10deg] drop-shadow-[4px_4px_0px_rgba(220,38,38,0.5)]">
              {isFinished ? (
                <>
                  {game.match!.home_score}{' '}
                  <span className="text-red-600 text-4xl mx-2">vs</span>{' '}
                  {game.match!.away_score}
                </>
              ) : (
                <span className="text-red-600">VS</span>
              )}
            </div>

            <div className="mt-4 text-lg text-red-500 font-bold tracking-[0.2em] uppercase border-t-2 border-red-900 pt-2">
              系列賽 {game.series_info?.home_wins}-{game.series_info?.away_wins}
            </div>
          </div>

          <div className={`flex-1 text-right font-black text-4xl ${awayWin ? 'text-white' : 'text-gray-500'}`}>
            {game.away_team.name}
          </div>
        </div>
      </div>
    );
  };

  if (!season) return <div className="p-8 text-center text-white/50">載入賽季資訊中...</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 h-full flex flex-col relative">
      
      {/* Header */}
      <div className="flex justify-between items-center bg-gray-900/60 backdrop-blur-md p-5 rounded-2xl border border-white/10 shadow-xl shrink-0 z-20">
        <div className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Calendar className="text-asbl-violet" /> 
            <span>第 {season.season_number} 賽季</span>
          </h2>
          <div className="flex items-center gap-2 ml-9">
            <span className={`text-xs font-bold px-2 py-0.5 rounded border tracking-wider
              ${getPhaseLabel(currentDay).includes('季後賽') ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-blue-500/20 text-blue-300 border-blue-500/30'}`}>
              {getPhaseLabel(currentDay)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-black/40 p-1.5 rounded-xl border border-white/10 shadow-inner relative">
          <button 
            onClick={handlePrevDay}
            disabled={currentDay <= 1}
            className="p-2 hover:bg-white/10 rounded-lg text-white disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
          >
            <ChevronLeft size={20} />
          </button>
          
          <button 
            onClick={() => setShowDatePicker(true)}
            className="text-center min-w-[100px] hover:bg-white/5 rounded-lg px-2 py-1 transition-colors group"
          >
            <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-0.5 flex items-center justify-center gap-1 group-hover:text-asbl-violet">
              DAY <Grid3X3 size={10} />
            </div>
            <div className="text-2xl font-black text-white font-mono leading-none drop-shadow-md">{currentDay}</div>
          </button>

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
        ) : !hasActiveGames ? (
          <div className="text-center py-20 text-gray-400 bg-gray-900/30 rounded-2xl border border-dashed border-white/10 flex flex-col items-center gap-3">
            <Calendar size={48} className="opacity-20" />
            <span>本日無賽程</span>
          </div>
        ) : (
          <>
            {/* Playoff League */}
            {playoffGames.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-white/90 flex items-center gap-2 px-2 uppercase tracking-wider">
                  <Crown size={14} className="text-amber-500" /> 季後賽 (Playoffs)
                </h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {playoffGames.map(g => <GameCard key={g.id} game={g} />)}
                </div>
              </div>
            )}

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

      {/* Modals */}
      {selectedMatchId && (
        <MatchDetailModal 
          matchId={selectedMatchId} 
          onClose={() => setSelectedMatchId(null)} 
        />
      )}
      
      {showDatePicker && (
        <DateSelectorModal 
          currentDay={currentDay} 
          maxDay={season.current_day} 
          onSelect={(d) => {
            setCurrentDay(d);
            setShowDatePicker(false);
          }}
          onClose={() => setShowDatePicker(false)}
        />
      )}
    </div>
  );
};

export default SchedulesPage;