import React from 'react';
import { NavTheme } from '../../types';

interface FooterProps {
  navThemes?: NavTheme[];
  onSelectTheme?: (themeId: string) => void;
  onNavigate?: (view: string) => void;
}

export const Footer: React.FC<FooterProps> = ({
  navThemes = [],
  onSelectTheme,
  onNavigate,
}) => {
  return (
    <footer className="bg-black/60 border-t border-white/10 text-slate-400 mt-20 pt-14 pb-8">
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-10 mb-10">
        {/* Brand */}
        <div className="space-y-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyber-violet to-cyber-cyan flex items-center justify-center font-black text-white text-sm">
              R
            </div>
            <span className="font-extrabold text-lg tracking-tight text-white">
              READ<span className="text-cyber-violet">QUES</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Next-generation academic reading platform and real-time RAG intelligence. Master authentic reading passages generated from daily world news.
          </p>
        </div>

        {/* Categories Col 1 */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">
            Themes
          </h4>
          <ul className="space-y-1.5 text-xs">
            {navThemes.slice(0, 4).map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => {
                    if (onSelectTheme) onSelectTheme(t.id);
                    if (onNavigate) onNavigate('all-tests');
                  }}
                  className="hover:text-cyber-cyan transition cursor-pointer"
                >
                  {t.name}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Categories Col 2 */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">
            More Topics
          </h4>
          <ul className="space-y-1.5 text-xs">
            {navThemes.slice(4, 8).map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => {
                    if (onSelectTheme) onSelectTheme(t.id);
                    if (onNavigate) onNavigate('all-tests');
                  }}
                  className="hover:text-cyber-cyan transition cursor-pointer"
                >
                  {t.name}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {/* Links */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">
            Platform
          </h4>
          <ul className="space-y-1.5 text-xs">
            <li>
              <button
                onClick={() => onNavigate && onNavigate('home')}
                className="hover:text-cyber-cyan transition cursor-pointer"
              >
                Homepage Feed
              </button>
            </li>
            <li>
              <button
                onClick={() => onNavigate && onNavigate('all-tests')}
                className="hover:text-cyber-cyan transition cursor-pointer"
              >
                Explore All Tests
              </button>
            </li>
            <li>
              <span className="text-slate-500">Academic Grading</span>
            </li>
            <li>
              <span className="text-slate-500">Passage Proof Grounding</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/5 pt-6 text-center text-[11px] text-slate-500 max-w-7xl mx-auto px-6">
        &copy; {new Date().getFullYear()} ReadAndQues AI Reading Platform. All rights reserved.
      </div>
    </footer>
  );
};
