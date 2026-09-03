import React from 'react';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

export interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info';
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, type = 'info', onClose }) => {
  return (
    <div
      role="alert"
      className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-2xl animate-in slide-in-from-top-4 duration-200 text-xs font-medium max-w-md ${
        type === 'error'
          ? 'bg-red-500/10 border-red-500/30 text-red-200'
          : type === 'success'
          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
          : 'bg-cyber-violet/10 border-cyber-violet/30 text-cyber-cyan'
      }`}
    >
      {type === 'error' ? (
        <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
      ) : (
        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
      )}
      <span className="flex-1">{message}</span>
      <button
        onClick={onClose}
        className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition cursor-pointer"
        aria-label="Close notification"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
