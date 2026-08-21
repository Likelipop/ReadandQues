import React, { useState } from 'react';
import { Modal } from '../../components/common/Modal';
import { useAuth } from '../../store';
import { api } from '../../api/client';
import { Loader2, Mail, Lock, User as UserIcon, KeyRound, ArrowRight, CheckCircle2 } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: 'login' | 'register' | 'verify';
  onShowToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialTab = 'login',
  onShowToast,
}) => {
  const [tab, setTab] = useState<'login' | 'register' | 'verify'>(initialTab);
  const { setUser } = useAuth();

  // Login form state
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');

  // Verify form state
  const [verifyCode, setVerifyCode] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Honeypot anti-bot
  const [honeypot, setHoneypot] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (honeypot) return;
    setLoading(true);
    setError(null);

    try {
      const res = await api.auth.login(loginUsername, loginPassword);
      if (res.user) {
        setUser(res.user);
        if (onShowToast) onShowToast(res.message || 'Login successful', 'success');
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (honeypot) return;
    setLoading(true);
    setError(null);

    try {
      const res = await api.auth.register({
        username: regUsername,
        email: regEmail,
        password: regPassword,
        confirm_password: regConfirmPassword,
      });
      if (onShowToast) onShowToast(res.message || 'Verification code sent to your email', 'success');
      setTab('verify');
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await api.auth.verify(verifyCode);
      if (res.user) {
        setUser(res.user);
        if (onShowToast) onShowToast('Account verified and logged in! Welcome.', 'success');
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Incorrect or expired verification code.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    try {
      const res = await api.auth.resend();
      if (onShowToast) onShowToast(res.message, 'info');
    } catch (err: any) {
      if (onShowToast) onShowToast(err.message, 'error');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        tab === 'login'
          ? 'Sign in to ReadQues'
          : tab === 'register'
          ? 'Create a ReadQues Account'
          : 'Verify Email Address'
      }
    >
      {/* Honeypot hidden input */}
      <input
        type="text"
        name="website_url"
        value={honeypot}
        onChange={(e) => setHoneypot(e.target.value)}
        className="hidden"
        tabIndex={-1}
        autoComplete="off"
      />

      {/* Tabs */}
      {tab !== 'verify' && (
        <div className="flex rounded-xl bg-white/[0.04] p-1 border border-white/10 text-xs font-bold mb-4">
          <button
            type="button"
            onClick={() => {
              setTab('login');
              setError(null);
            }}
            className={`flex-1 py-2 rounded-lg transition cursor-pointer ${
              tab === 'login'
                ? 'bg-cyber-violet text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => {
              setTab('register');
              setError(null);
            }}
            className={`flex-1 py-2 rounded-lg transition cursor-pointer ${
              tab === 'register'
                ? 'bg-cyber-violet text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs font-medium">
          {error}
        </div>
      )}

      {/* 1. Login Form */}
      {tab === 'login' && (
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
              Username or Email
            </label>
            <div className="relative">
              <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                placeholder="Enter your username or email"
                required
                className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2.5 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:outline-none transition"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2.5 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:outline-none transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-cyber-violet hover:bg-purple-600 disabled:opacity-50 text-white font-bold text-xs shadow-lg transition flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Sign In</span>}
          </button>
        </form>
      )}

      {/* 2. Register Form */}
      {tab === 'register' && (
        <form onSubmit={handleRegister} className="space-y-3">
          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
              Username
            </label>
            <div className="relative">
              <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                placeholder="Choose a username"
                required
                className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:outline-none transition"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="name@example.com"
                required
                className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2 pl-10 pr-4 text-xs text-white placeholder-slate-500 focus:outline-none transition"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                placeholder="••••••"
                required
                className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2 px-3 text-xs text-white placeholder-slate-500 focus:outline-none transition"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                Confirm
              </label>
              <input
                type="password"
                value={regConfirmPassword}
                onChange={(e) => setRegConfirmPassword(e.target.value)}
                placeholder="••••••"
                required
                className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-violet rounded-xl py-2 px-3 text-xs text-white placeholder-slate-500 focus:outline-none transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-cyber-violet hover:bg-purple-600 disabled:opacity-50 text-white font-bold text-xs shadow-lg transition flex items-center justify-center gap-2 cursor-pointer mt-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <span className="flex items-center gap-1.5">
                <span>Create Account</span>
                <ArrowRight className="w-4 h-4" />
              </span>
            )}
          </button>
        </form>
      )}

      {/* 3. Verify Form */}
      {tab === 'verify' && (
        <form onSubmit={handleVerify} className="space-y-4 text-center">
          <p className="text-xs text-slate-300">
            We sent a 6-digit verification OTP code to your registered email address.
          </p>

          <div className="relative max-w-[200px] mx-auto">
            <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              maxLength={6}
              value={verifyCode}
              onChange={(e) => setVerifyCode(e.target.value)}
              placeholder="000000"
              required
              className="w-full bg-white/[0.05] border border-white/10 focus:border-cyber-cyan rounded-xl py-2.5 pl-10 pr-4 text-center font-mono text-lg tracking-widest text-white placeholder-slate-600 focus:outline-none transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading || verifyCode.length !== 6}
            className="w-full py-3 rounded-xl bg-cyber-cyan hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-black text-xs shadow-lg transition flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Verify Account</span>}
          </button>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={handleResend}
              className="text-xs text-slate-400 hover:text-cyber-cyan underline transition cursor-pointer"
            >
              Didn't receive code? Resend OTP
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
};
