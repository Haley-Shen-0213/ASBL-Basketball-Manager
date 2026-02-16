import React, { useState, useEffect } from 'react';
import { 
  Users, Trophy, Calendar, ClipboardList, Search, 
  ShoppingBag, Repeat, MessageSquare, BookOpen, 
  LogOut, User as UserIcon
} from 'lucide-react';

// --- 型別定義 ---
interface UserState {
  id: number;
  username: string;
  teamId: number;
}

interface TeamDashboard {
  id: number;
  name: string;
  funds: number;
  reputation: number;
  arena_name: string;
  fanpage_name: string;
  scout_chances: number;
  player_count: number;
  roster_limit: number;
  season_wins: number;
  season_losses: number;
  rank: number;
  total_teams: number;
  owner: string;
}

// --- 元件：Sidebar ---
const Sidebar = ({ activeTab, setActiveTab }: { activeTab: string, setActiveTab: (t: string) => void }) => {
  const menuItems = [
    { id: 'dashboard', label: '首頁', icon: <Users size={18} /> },
    { id: 'players', label: '球員', icon: <Users size={18} /> },
    { id: 'teams', label: '球隊', icon: <Trophy size={18} /> },
    { id: 'scouts', label: '球探', icon: <Search size={18} /> },
    { id: 'schedules', label: '賽程', icon: <Calendar size={18} /> },
    { id: 'tactics', label: '戰術', icon: <ClipboardList size={18} /> },
    { id: 'market', label: '市場', icon: <ShoppingBag size={18} /> },
    { id: 'trades', label: '交換', icon: <Repeat size={18} /> },
    { id: 'community', label: '社群', icon: <MessageSquare size={18} /> },
    { id: 'guide', label: '指南', icon: <BookOpen size={18} /> },
  ];

  return (
    <aside className="w-64 bg-asbl-panel border-r border-black/20 flex flex-col p-4 text-[#1f093a] hidden md:flex">
      <div className="text-xs font-bold tracking-wider mb-2 text-[#2b0c60] uppercase">選單</div>
      <nav className="flex-1 space-y-1">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
              ${activeTab === item.id 
                ? 'bg-white/40 border border-black/20 text-[#14043a] font-bold shadow-sm' 
                : 'bg-white/20 border border-transparent hover:bg-white/30 hover:border-black/10'
              }`}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
};

// --- 元件：Header ---
const Header = ({ user, onLogout }: { user: UserState, onLogout: () => void }) => {
  const [time, setTime] = useState(new Date());
  const [playerStats, setPlayerStats] = useState({ active: 0, total: 0 });

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/api/system/stats');
        if (res.ok) {
          const data = await res.json();
          setPlayerStats({
            active: data.active_users,
            total: data.total_users
          });
        }
      } catch (error) {
        console.error("Failed to fetch system stats:", error);
      }
    };
    fetchStats();
    const statsTimer = setInterval(fetchStats, 60000);
    return () => clearInterval(statsTimer);
  }, []);

  return (
    <header className="h-[88px] bg-header-gradient px-6 flex items-center justify-between shadow-md relative z-10">
      {/* Left: Logo */}
      <div className="flex items-center gap-4">
        <div className="w-11 h-11 bg-white/20 rounded-lg border border-white/40 flex items-center justify-center overflow-hidden backdrop-blur-sm">
          <span className="text-2xl">🏀</span>
        </div>
        <div className="flex flex-col">
          <h1 className="text-2xl font-black tracking-wide uppercase bg-gold-text bg-clip-text text-transparent drop-shadow-sm" 
              style={{ WebkitTextStroke: '0.5px rgba(0,0,0,0.4)' }}>
            ASBL
          </h1>
          <span className="text-[10px] font-bold text-gray-800 tracking-wider -mt-1 opacity-70">
            BASKETBALL MANAGER
          </span>
        </div>
      </div>

      {/* Middle: Info */}
      <div className="hidden md:flex flex-col items-center text-sm text-gray-900 gap-0.5">
        <div>
          <span className="opacity-70 mr-2">日期:</span>
          <span className="font-bold">{time.toLocaleDateString('zh-TW')}</span>
        </div>
        <div>
          <span className="opacity-70 mr-2">時間:</span>
          <span className="font-bold font-mono">{time.toLocaleTimeString('zh-TW', { hour12: false })}</span>
        </div>
        <div className="text-xs">
          <span className="opacity-70 mr-2">活躍/總數:</span>
          <span className="font-bold text-blue-900">
            {playerStats.active} / {playerStats.total}
          </span>
        </div>
      </div>

      {/* Right: User */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 bg-white/20 px-3 py-1.5 rounded-full border border-white/30 backdrop-blur-sm">
          <div className="w-7 h-7 rounded-full bg-gray-800 text-white flex items-center justify-center text-xs font-bold border border-white/50">
            {user.username.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm font-bold text-gray-900">{user.username}</span>
        </div>
        <button onClick={onLogout} className="bg-gray-900 hover:bg-gray-800 text-white text-xs px-3 py-2 rounded-lg transition-colors flex items-center gap-2">
          <LogOut size={14} />
          登出
        </button>
      </div>
    </header>
  );
};

// --- 頁面：Dashboard (首頁) ---
const Dashboard = ({ teamId, username }: { teamId: number, username: string }) => {
  const [data, setData] = useState<TeamDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`/api/team/${teamId}/dashboard`);
        if (res.ok) {
          setData(await res.json());
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [teamId]);

  if (loading) return <div className="p-6 text-white">載入中...</div>;
  if (!data) return <div className="p-6 text-white">無法讀取球隊資料</div>;

  const stats = [
    { label: "球隊名稱", value: data.name },
    { label: "球隊資金", value: `$${data.funds.toLocaleString()}` },
    { label: "球隊聲望", value: data.reputation },
    { label: "場館名稱", value: data.arena_name || "未命名" },
    { label: "粉絲團", value: data.fanpage_name || "未命名" },
    { label: "球探次數", value: data.scout_chances },
    { label: "球員人數", value: `${data.player_count} / ${data.roster_limit}` },
    { label: "聯賽戰績", value: `${data.season_wins}勝 - ${data.season_losses}敗 (第${data.rank}名)` },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="bg-asbl-panel/20 border border-asbl-panel p-6 rounded-2xl backdrop-blur-sm">
        <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          歡迎回來，{username}！
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, idx) => (
            <div key={idx} className="bg-white/40 border border-white/50 p-4 rounded-xl shadow-sm hover:bg-white/60 transition-colors">
              <div className="text-xs text-gray-600 mb-1">{stat.label}</div>
              <div className="text-lg font-bold text-gray-900 truncate">{stat.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 快速操作區 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white/30 border border-white/40 p-6 rounded-2xl shadow-sm">
          <h3 className="font-bold text-gray-800 mb-3">球隊動態</h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              系統初始化完成，球隊已建立。
            </li>
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              初始 15 人名單已生成。
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

// --- 頁面：Auth (登入/註冊) ---
const AuthPage = ({ onLogin }: { onLogin: (user: UserState) => void }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    team_name: '' // Optional
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
    
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || '操作失敗');
      }

      // 登入/註冊成功
      onLogin({
        id: data.user_id,
        username: isLogin ? data.username : formData.username,
        teamId: data.team_id
      });

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-asbl-bg p-4">
      <div className="w-full max-w-md bg-white/10 backdrop-blur-md border border-white/20 p-8 rounded-2xl shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-black text-white mb-2">ASBL</h1>
          <p className="text-gray-300 text-sm">BASKETBALL MANAGER</p>
        </div>

        <div className="flex mb-6 bg-black/20 p-1 rounded-lg">
          <button
            onClick={() => setIsLogin(true)}
            className={`flex-1 py-2 rounded-md text-sm font-bold transition-all ${isLogin ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400 hover:text-white'}`}
          >
            登入
          </button>
          <button
            onClick={() => setIsLogin(false)}
            className={`flex-1 py-2 rounded-md text-sm font-bold transition-all ${!isLogin ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-400 hover:text-white'}`}
          >
            註冊
          </button>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500/50 text-red-200 text-sm p-3 rounded-lg mb-4 text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-300 mb-1">使用者名稱</label>
            <input
              type="text"
              required
              className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-asbl-pink transition-all"
              placeholder="Manager Name"
              value={formData.username}
              onChange={e => setFormData({...formData, username: e.target.value})}
            />
          </div>

          {!isLogin && (
            <>
              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">電子信箱</label>
                <input
                  type="email"
                  required
                  className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-asbl-pink transition-all"
                  placeholder="email@example.com"
                  value={formData.email}
                  onChange={e => setFormData({...formData, email: e.target.value})}
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-300 mb-1">球隊名稱 (選填)</label>
                <input
                  type="text"
                  className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-asbl-pink transition-all"
                  placeholder="預設為 Team_{ID}"
                  value={formData.team_name}
                  onChange={e => setFormData({...formData, team_name: e.target.value})}
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-bold text-gray-300 mb-1">密碼</label>
            <input
              type="password"
              required
              className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-asbl-pink transition-all"
              placeholder="••••••••"
              value={formData.password}
              onChange={e => setFormData({...formData, password: e.target.value})}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-asbl-pink to-asbl-violet hover:opacity-90 text-white font-bold py-3 rounded-xl shadow-lg transform active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4"
          >
            {loading ? '處理中...' : (isLogin ? '進入遊戲' : '建立球隊')}
          </button>
        </form>
      </div>
    </div>
  );
};

// --- 主程式入口 ---
function App() {
  const [user, setUser] = useState<UserState | null>(null);
  const [activeTab, setActiveTab] = useState('dashboard');

  // 檢查 LocalStorage 是否有登入狀態 (簡易持久化)
  useEffect(() => {
    const savedUser = localStorage.getItem('asbl_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  const handleLogin = (userData: UserState) => {
    setUser(userData);
    localStorage.setItem('asbl_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('asbl_user');
  };

  if (!user) {
    return <AuthPage onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-asbl-bg text-gray-900 font-sans selection:bg-asbl-pink selection:text-white">
      <Header user={user} onLogout={handleLogout} />
      <div className="flex min-h-[calc(100vh-88px)]">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        
        <main className="flex-1 bg-asbl-main p-6 overflow-y-auto">
          {activeTab === 'dashboard' && <Dashboard teamId={user.teamId} username={user.username} />}
          {activeTab === 'players' && <div className="text-center mt-20 text-gray-600">球員列表開發中...</div>}
          {activeTab === 'scouts' && <div className="text-center mt-20 text-gray-600">球探中心開發中...</div>}
          {/* 其他頁面... */}
        </main>
      </div>
    </div>
  );
}

export default App;