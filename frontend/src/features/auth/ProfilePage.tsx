import React, { useState } from 'react';
import {
  User,
  Star,
  BookOpen,
  CheckCircle2,
  Lock,
  Flame,
  Trophy,
  Loader2,
  Settings,
  ArrowLeft,
  ShieldCheck,
  KeyRound,
  X,
} from 'lucide-react';
import { useAuth } from '../../store';
import { api } from '../../api/client';

interface ProfilePageProps {
  onShowToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
  onOpenAuth?: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  onShowToast,
  onOpenAuth,
}) => {
  const { user } = useAuth();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user || !user.is_authenticated) {
    return (
      <div className="max-w-md mx-auto my-20 p-8 glass-card text-center space-y-4">
        <User className="w-12 h-12 text-slate-500 mx-auto" />
        <h3 className="text-base font-bold text-white">Sign In Required</h3>
        <p className="text-xs text-slate-400">
          Please log in to view your learning progress, star balance, and account settings.
        </p>
        <button
          onClick={onOpenAuth}
          className="px-6 py-2.5 bg-cyber-violet text-white text-xs font-bold rounded-xl shadow-lg glow-violet cursor-pointer"
        >
          Sign In
        </button>
      </div>
    );
  }

  const accuracy =
    user.total_questions_solved > 0
      ? Math.round((user.correct_answers_count / user.total_questions_solved) * 100)
      : 0;

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.auth.changePassword(oldPassword, newPassword);
      if (onShowToast) onShowToast(res.message || 'Password changed successfully', 'success');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setIsSettingsOpen(false);
    } catch (err: any) {
      setError(err.message || 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSettings = () => {
    setIsSettingsOpen(false);
    setError(null);
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-8">
      {/* Profile Overview Card */}
      <div className="glass-card glow-violet p-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-cyber-violet to-cyber-cyan flex items-center justify-center font-black text-2xl text-white shadow-xl glow-violet shrink-0">
            {user.username.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-2xl font-black text-white">{user.username}</h1>
            <p className="text-xs text-slate-400 mt-0.5">{user.email}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-400/10 border border-amber-400/30 text-amber-300">
            <Star className="w-5 h-5 fill-amber-400" />
            <div>
              <div className="text-[10px] uppercase font-bold text-amber-400/80">Star Balance</div>
              <div className="text-lg font-black font-mono">{user.stars} Stars</div>
            </div>
          </div>

          <button
            onClick={() => setIsSettingsOpen((prev) => !prev)}
            aria-label="Settings"
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition cursor-pointer text-xs font-bold ${
              isSettingsOpen
                ? 'bg-cyber-violet text-white border-cyber-violet shadow-lg glow-violet'
                : 'bg-white/5 hover:bg-white/10 border-white/10 text-slate-200 hover:text-white'
            }`}
          >
            <Settings className="w-4 h-4 text-cyan-400" />
            <span>Settings</span>
          </button>
        </div>
      </div>

      {isSettingsOpen ? (
        /* Settings View: Security, Password & Preferences */
        <div className="space-y-6 animate-in fade-in zoom-95 duration-200">
          <div className="flex items-center justify-between">
            <button
              onClick={handleCloseSettings}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-slate-300 hover:text-white transition cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Overview</span>
            </button>
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Account Settings</span>
          </div>

          <div className="glass-card p-8 space-y-6 border border-white/15 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-cyber-violet/20 border border-cyber-violet/40 flex items-center justify-center text-cyber-violet">
                  <ShieldCheck className="w-5 h-5 text-indigo-300" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">Security & Password</h2>
                  <p className="text-xs text-slate-400">Update your account password to ensure maximum security.</p>
                </div>
              </div>
              <button
                onClick={handleCloseSettings}
                aria-label="Close Settings"
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {error && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Current Password</span>
                </label>
                <input
                  type="password"
                  placeholder="Enter current password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                  className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:outline-none transition"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-cyan-400" />
                  <span>New Password</span>
                </label>
                <input
                  type="password"
                  placeholder="Enter new password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:outline-none transition"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Confirm New Password</span>
                </label>
                <input
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2.5 px-3.5 text-xs text-white placeholder-slate-500 focus:outline-none transition"
                />
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="py-2.5 px-6 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg glow-violet transition flex items-center gap-2 cursor-pointer"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Update Password</span>}
                </button>
                <button
                  type="button"
                  onClick={handleCloseSettings}
                  className="py-2.5 px-4 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white font-bold text-xs transition cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : (
        /* Standard Overview: Learning Stats & Progress */
        <div className="space-y-8 animate-in fade-in duration-200">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="glass-card p-5 space-y-1">
              <div className="flex items-center gap-2 text-cyber-cyan text-xs font-bold uppercase">
                <BookOpen className="w-4 h-4" />
                <span>Imported</span>
              </div>
              <div className="text-2xl font-black text-white font-mono">
                {user.total_articles_imported || 0}
              </div>
              <span className="text-[10px] text-slate-400">Articles crawled</span>
            </div>

            <div className="glass-card p-5 space-y-1">
              <div className="flex items-center gap-2 text-cyber-emerald text-xs font-bold uppercase">
                <CheckCircle2 className="w-4 h-4" />
                <span>Questions</span>
              </div>
              <div className="text-2xl font-black text-white font-mono">
                {user.total_questions_solved || 0}
              </div>
              <span className="text-[10px] text-slate-400">Total solved</span>
            </div>

            <div className="glass-card p-5 space-y-1">
              <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase">
                <Trophy className="w-4 h-4" />
                <span>Accuracy</span>
              </div>
              <div className="text-2xl font-black text-white font-mono">{accuracy}%</div>
              <span className="text-[10px] text-slate-400">Correct answers</span>
            </div>

            <div className="glass-card p-5 space-y-1">
              <div className="flex items-center gap-2 text-red-400 text-xs font-bold uppercase">
                <Flame className="w-4 h-4" />
                <span>Streak</span>
              </div>
              <div className="text-2xl font-black text-white font-mono">
                {user.streak || 0} Days
              </div>
              <span className="text-[10px] text-slate-400">Reading continuity</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
