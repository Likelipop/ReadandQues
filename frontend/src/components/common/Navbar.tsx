import React from 'react';
import { Compass, BookOpen, User as UserIcon, Star, LogIn, LogOut, Sparkles } from 'lucide-react';
import { OmniSearch } from './OmniSearch';
import { useAuth } from '../../store';
import { NavTheme } from '../../types';

interface NavbarProps {
  currentView: string;
  onNavigate: (view: string, articleId?: string) => void;
  onOpenAuth: (mode?: 'login' | 'register') => void;
  navThemes?: NavTheme[];
  selectedTheme?: string;
  onSelectTheme?: (themeId: string) => void;
  onShowToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  onNavigate,
  onOpenAuth,
  navThemes = [],
  selectedTheme = 'All',
  onSelectTheme,
  onShowToast,
}) => {
  const { user, logout } = useAuth();

  const formattedDate = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date());

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/10 bg-slate-950/85 backdrop-blur-xl shadow-lg shadow-black/20">
      {/* Main Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand Logo */}
        <button
          onClick={() => onNavigate('home')}
          className="flex items-center gap-3 hover:opacity-95 transition shrink-0 cursor-pointer focus:outline-none"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-cyan-400 flex items-center justify-center font-black text-white text-lg shadow-lg glow-violet">
            R
          </div>
          <div className="flex flex-col text-left">
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-base tracking-tight text-white">
                READ<span className="text-indigo-400">QUES</span>
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium tracking-wide">
              Academic Reading Engine
            </span>
          </div>
        </button>

        {/* Global OmniSearch Bar */}
        <div className="flex-1 max-w-lg hidden md:block">
          <OmniSearch
            onSelectArticle={(id) => onNavigate('readspace', id)}
            onShowToast={onShowToast}
          />
        </div>

        {/* Navigation & User Controls */}
        <div className="flex items-center gap-3">
          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1">
            <button
              onClick={() => onNavigate('home')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                currentView === 'home'
                  ? 'bg-white/10 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              Home
            </button>

            <button
              onClick={() => onNavigate('all-tests')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                currentView === 'all-tests'
                  ? 'bg-white/10 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Explore Tests</span>
            </button>
          </nav>

          {/* User Section */}
          {user?.is_authenticated ? (
            <div className="flex items-center gap-2.5">
              {/* Star Balance Badge */}
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-400/10 border border-amber-400/30 text-amber-300 text-xs font-bold shadow-sm">
                <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                <span className="font-mono">{user.stars}</span>
              </div>

              {/* Profile button */}
              <button
                onClick={() => onNavigate('profile')}
                className="flex items-center gap-2 p-1.5 pr-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition cursor-pointer text-xs font-bold text-slate-200"
              >
                <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[11px] font-black">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <span>{user.username}</span>
              </button>

              <button
                onClick={logout}
                title="Log out"
                className="p-2 text-slate-400 hover:text-rose-400 rounded-xl hover:bg-white/5 transition cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onOpenAuth('login')}
                className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-slate-300 hover:text-white hover:bg-white/5 transition cursor-pointer"
              >
                Sign In
              </button>

              <button
                onClick={() => onOpenAuth('register')}
                className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg glow-violet transition-transform active:scale-95 cursor-pointer flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
                <span>Get Started</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Search Bar Row */}
      <div className="px-4 pb-3 md:hidden">
        <OmniSearch
          onSelectArticle={(id) => onNavigate('readspace', id)}
          onShowToast={onShowToast}
        />
      </div>

      {/* Categories & Themes Filter Bar */}
      {navThemes && navThemes.length > 0 && (
        <div className="border-t border-white/5 bg-black/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center gap-2 overflow-x-auto scrollbar-none py-2">
            <button
              onClick={() => onSelectTheme && onSelectTheme('All')}
              className={`px-3 py-1 text-xs font-bold rounded-full transition shrink-0 cursor-pointer ${
                selectedTheme === 'All'
                  ? 'glass-pill-active'
                  : 'glass-pill'
              }`}
            >
              All Topics
            </button>
            {navThemes.map((cat) => (
              <button
                key={cat.id}
                onClick={() => onSelectTheme && onSelectTheme(cat.id)}
                className={`px-3 py-1 text-xs font-bold rounded-full transition shrink-0 uppercase tracking-wider cursor-pointer ${
                  selectedTheme === cat.id
                    ? 'glass-pill-active'
                    : 'glass-pill'
                }`}
              >
                {cat.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </header>
  );
};
