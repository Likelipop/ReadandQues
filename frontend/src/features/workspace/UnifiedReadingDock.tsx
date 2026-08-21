import React, { useState, useRef, useEffect } from 'react';
import {
  MousePointer,
  Highlighter,
  Eraser,
  Sparkles,
  BookOpen,
  Maximize2,
  Minimize2,
  HelpCircle,
  Keyboard,
  X,
  Palette,
} from 'lucide-react';
import { useWorkspace, ActiveTool, HighlightColor } from '../../store';
import { HIGHLIGHT_THEMES } from '../../hooks/useHighlighter';

export interface UnifiedReadingDockProps {
  isQuizOpen?: boolean;
  onToggleQuiz?: () => void;
  className?: string;
}

const COLOR_OPTIONS: Array<{
  key: HighlightColor;
  label: string;
  dotBg: string;
  ringColor: string;
  hotkey: string;
}> = [
  { key: 'amber', label: 'Amber Gold', dotBg: 'bg-amber-400', ringColor: 'ring-amber-400', hotkey: '1' },
  { key: 'emerald', label: 'Emerald Green', dotBg: 'bg-emerald-400', ringColor: 'ring-emerald-400', hotkey: '2' },
  { key: 'cyan', label: 'Cyan Blue', dotBg: 'bg-cyan-400', ringColor: 'ring-cyan-400', hotkey: '3' },
  { key: 'rose', label: 'Rose Pink', dotBg: 'bg-rose-400', ringColor: 'ring-rose-400', hotkey: '4' },
];

export const UnifiedReadingDock: React.FC<UnifiedReadingDockProps> = ({
  isQuizOpen = false,
  onToggleQuiz,
  className = '',
}) => {
  const {
    activeTool,
    setActiveTool,
    highlightColor,
    setHighlightColor,
    isZenMode,
    toggleZenMode,
  } = useWorkspace();

  const [isColorPickerOpen, setIsColorPickerOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const colorPickerRef = useRef<HTMLDivElement>(null);

  // Close color picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (colorPickerRef.current && !colorPickerRef.current.contains(e.target as Node)) {
        setIsColorPickerOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToolClick = (tool: ActiveTool) => {
    if (tool === 'pointer') {
      setActiveTool(null);
    } else {
      setActiveTool(tool);
    }
  };

  const isPointerActive = activeTool === 'pointer' || activeTool === null;

  return (
    <>
      {/* Floating Bottom-Center AuraDock */}
      <nav
        aria-label="Unified Reading Toolbox"
        className={`fixed bottom-5 sm:bottom-6 left-1/2 -translate-x-1/2 z-40 max-w-[95vw] px-2 sm:px-3 py-1.5 rounded-2xl glass-card glow-violet backdrop-blur-xl border border-white/20 shadow-2xl flex items-center gap-1 sm:gap-1.5 select-none transition-all duration-300 animate-in slide-in-from-bottom-4 ${className}`}
      >
        {/* 1. Pointer / Select Tool */}
        <button
          onClick={() => handleToolClick('pointer')}
          title="Pointer Mode (V / Esc) - Select & Read freely"
          aria-label="Pointer Tool"
          className={`relative p-2 sm:p-2.5 rounded-xl transition flex items-center justify-center cursor-pointer group ${
            isPointerActive
              ? 'bg-white/20 text-white font-bold shadow-md ring-1 ring-white/40'
              : 'text-slate-400 hover:text-white hover:bg-white/10'
          }`}
        >
          <MousePointer className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
            Pointer <kbd className="text-cyan-400 font-mono">V</kbd>
          </span>
        </button>

        {/* 2. Highlighter Tool + Color Picker popover */}
        <div className="relative" ref={colorPickerRef}>
          <div className="flex items-center">
            <button
              onClick={() => handleToolClick('marker')}
              title={`Highlighter (${highlightColor.toUpperCase()}) (H)`}
              aria-label="Highlighter Tool"
              className={`p-2 sm:p-2.5 rounded-l-xl transition flex items-center justify-center cursor-pointer group ${
                activeTool === 'marker'
                  ? `${HIGHLIGHT_THEMES[highlightColor].dotColor} text-slate-950 font-bold shadow-lg ring-2 ${HIGHLIGHT_THEMES[highlightColor].ringColor}`
                  : 'text-slate-400 hover:text-amber-300 hover:bg-white/10'
              }`}
            >
              <Highlighter className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
              <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
                Highlighter <kbd className="text-amber-400 font-mono">H</kbd>
              </span>
            </button>

            {/* Quick Color Swatch Popover Trigger */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsColorPickerOpen((prev) => !prev);
              }}
              title="Change Highlight Color"
              aria-label="Highlight Color Picker"
              className={`p-1.5 sm:p-2 rounded-r-xl border-l border-white/10 transition flex items-center justify-center cursor-pointer ${
                activeTool === 'marker'
                  ? 'bg-amber-500/30 text-amber-200 hover:bg-amber-500/40'
                  : 'text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              <span
                className={`w-2.5 h-2.5 rounded-full shadow-inner ${HIGHLIGHT_THEMES[highlightColor].dotColor}`}
              />
            </button>
          </div>

          {/* Color Palette Popover */}
          {isColorPickerOpen && (
            <div
              role="menu"
              aria-label="Highlight Colors"
              className="absolute bottom-full mb-3 left-1/2 -translate-x-1/2 p-2.5 rounded-2xl glass-card glow-violet backdrop-blur-2xl border border-white/20 shadow-2xl flex flex-col gap-2 min-w-[170px] animate-in zoom-95 duration-150 z-50"
            >
              <div className="flex items-center justify-between pb-1 border-b border-white/10">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <Palette className="w-3 h-3 text-cyan-400" /> Color
                </span>
                <span className="text-[9px] font-mono text-slate-500">Keys 1-4</span>
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                {COLOR_OPTIONS.map((opt) => {
                  const isSelected = highlightColor === opt.key;
                  return (
                    <button
                      key={opt.key}
                      onClick={() => {
                        setHighlightColor(opt.key);
                        if (activeTool !== 'marker') setActiveTool('marker');
                        setIsColorPickerOpen(false);
                      }}
                      className={`flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                        isSelected
                          ? `${HIGHLIGHT_THEMES[opt.key].badgeClass} font-bold shadow-sm ring-1 ring-white/30`
                          : 'bg-white/5 hover:bg-white/10 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className={`w-3 h-3 rounded-full ${opt.dotBg}`} />
                        <span className="text-[11px] capitalize">{opt.key}</span>
                      </div>
                      <span className="text-[9px] font-mono text-slate-400">{opt.hotkey}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* 3. Eraser Tool */}
        <button
          onClick={() => handleToolClick('eraser')}
          title="Eraser (E) - Click highlights to erase"
          aria-label="Eraser Tool"
          className={`relative p-2 sm:p-2.5 rounded-xl transition flex items-center justify-center cursor-pointer group ${
            activeTool === 'eraser'
              ? 'bg-rose-500 text-white font-bold shadow-lg ring-2 ring-rose-400'
              : 'text-slate-400 hover:text-rose-400 hover:bg-white/10'
          }`}
        >
          <Eraser className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
            Eraser <kbd className="text-rose-400 font-mono">E</kbd>
          </span>
        </button>

        {/* 4. Smart Ink Tool */}
        <button
          onClick={() => handleToolClick('smart_ink')}
          title="Smart Ink AI (I) - Click any sentence for live explanation"
          aria-label="Smart Ink Tool"
          className={`relative p-2 sm:p-2.5 rounded-xl transition flex items-center justify-center cursor-pointer group ${
            activeTool === 'smart_ink'
              ? 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white font-bold shadow-lg glow-violet ring-2 ring-purple-400'
              : 'text-slate-400 hover:text-purple-300 hover:bg-white/10'
          }`}
        >
          <Sparkles className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
            Smart Ink <kbd className="text-purple-400 font-mono">I</kbd>
          </span>
        </button>

        {/* 5. Dictionary Tool */}
        <button
          onClick={() => handleToolClick('dictionary')}
          title="Dictionary (D) - Click any word for offline definitions"
          aria-label="Dictionary Tool"
          className={`relative p-2 sm:p-2.5 rounded-xl transition flex items-center justify-center cursor-pointer group ${
            activeTool === 'dictionary'
              ? 'bg-cyan-400 text-slate-950 font-bold shadow-lg ring-2 ring-cyan-300'
              : 'text-slate-400 hover:text-cyan-300 hover:bg-white/10'
          }`}
        >
          <BookOpen className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
            Dictionary <kbd className="text-cyan-400 font-mono">D</kbd>
          </span>
        </button>

        <div className="h-5 sm:h-6 w-px bg-white/10 mx-0.5 sm:mx-1" />

        {/* 6. Zen Mode Toggle */}
        <button
          onClick={toggleZenMode}
          title={isZenMode ? 'Exit Zen Mode (Z)' : 'Zen Focus Mode (Z)'}
          aria-label="Toggle Zen Mode"
          className={`relative p-2 sm:p-2.5 rounded-xl transition flex items-center justify-center cursor-pointer group ${
            isZenMode
              ? 'bg-emerald-500 text-slate-950 font-bold shadow-lg ring-2 ring-emerald-400'
              : 'text-slate-400 hover:text-emerald-300 hover:bg-white/10'
          }`}
        >
          {isZenMode ? (
            <Minimize2 className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          ) : (
            <Maximize2 className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          )}
          <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
            {isZenMode ? 'Exit Zen' : 'Zen Mode'} <kbd className="text-emerald-400 font-mono">Z</kbd>
          </span>
        </button>

        {/* 7. AI Quiz Toggle */}
        {onToggleQuiz && (
          <button
            onClick={onToggleQuiz}
            title={isQuizOpen ? 'Hide AI Quiz (Q)' : 'Show AI Quiz (Q)'}
            aria-label="Toggle AI Reading Quiz"
            className={`relative p-2 sm:p-2.5 rounded-xl transition flex items-center justify-center cursor-pointer group ${
              isQuizOpen
                ? 'bg-cyber-violet text-white font-bold shadow-lg glow-violet ring-2 ring-purple-400'
                : 'text-slate-400 hover:text-cyber-violet hover:bg-white/10'
            }`}
          >
            <HelpCircle className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
            <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
              Quiz <kbd className="text-cyber-violet font-mono">Q</kbd>
            </span>
          </button>
        )}

        {/* 8. Keyboard Shortcuts Help Trigger */}
        <button
          onClick={() => setIsShortcutsOpen(true)}
          title="Keyboard Shortcuts (?)"
          aria-label="Keyboard Shortcuts"
          className="relative p-2 sm:p-2.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition flex items-center justify-center cursor-pointer group"
        >
          <Keyboard className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
          <span className="hidden group-hover:block absolute -top-8 px-2 py-0.5 text-[10px] font-medium bg-slate-900/90 text-slate-200 rounded border border-white/10 shadow-lg pointer-events-none whitespace-nowrap">
            Shortcuts <kbd className="text-cyan-400 font-mono">?</kbd>
          </span>
        </button>
      </nav>

      {/* Keyboard Shortcuts Cheat Sheet Modal */}
      {isShortcutsOpen && (
        <div
          role="dialog"
          aria-label="Keyboard Shortcuts Cheat Sheet"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200"
          onClick={() => setIsShortcutsOpen(false)}
        >
          <div
            className="w-full max-w-md p-6 rounded-3xl glass-card glow-violet backdrop-blur-2xl border border-white/20 shadow-2xl space-y-5 animate-in zoom-95 duration-150 text-slate-100"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300">
                  <Keyboard className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-sm text-white">Reading Space Shortcuts</h3>
                  <p className="text-[11px] text-slate-400">Power user keyboard controls</p>
                </div>
              </div>

              <button
                onClick={() => setIsShortcutsOpen(false)}
                aria-label="Close shortcuts dialog"
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Shortcuts List */}
            <div className="space-y-2 text-xs">
              <div className="grid grid-cols-1 gap-2">
                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Pointer / Select Mode</span>
                  <div className="flex items-center gap-1">
                    <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-cyan-300">
                      V
                    </kbd>
                    <span className="text-slate-500">or</span>
                    <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-cyan-300">
                      Esc
                    </kbd>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Highlighter Tool</span>
                  <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-amber-300">
                    H
                  </kbd>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Eraser Tool</span>
                  <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-rose-300">
                    E
                  </kbd>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Smart Ink AI Stream</span>
                  <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-purple-300">
                    I
                  </kbd>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">WordNet Dictionary</span>
                  <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-cyan-300">
                    D
                  </kbd>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Paraphrase Selected Text</span>
                  <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-indigo-300">
                    P
                  </kbd>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Toggle Zen Focus Mode</span>
                  <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-emerald-300">
                    Z
                  </kbd>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Toggle AI Reading Quiz</span>
                  <kbd className="px-2 py-0.5 rounded bg-white/10 border border-white/20 font-mono text-[11px] text-cyber-violet">
                    Q
                  </kbd>
                </div>

                <div className="flex items-center justify-between p-2 rounded-xl bg-white/[0.03] border border-white/5">
                  <span className="text-slate-300 font-medium">Highlight Colors</span>
                  <div className="flex items-center gap-1 font-mono text-[11px]">
                    <kbd className="px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-300 border border-amber-400/30">
                      1
                    </kbd>
                    <kbd className="px-1.5 py-0.5 rounded bg-emerald-400/20 text-emerald-300 border border-emerald-400/30">
                      2
                    </kbd>
                    <kbd className="px-1.5 py-0.5 rounded bg-cyan-400/20 text-cyan-300 border border-cyan-400/30">
                      3
                    </kbd>
                    <kbd className="px-1.5 py-0.5 rounded bg-rose-400/20 text-rose-300 border border-rose-400/30">
                      4
                    </kbd>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="pt-2 border-t border-white/10 flex justify-end">
              <button
                onClick={() => setIsShortcutsOpen(false)}
                className="px-4 py-1.5 text-xs font-bold text-slate-300 hover:text-white bg-white/10 hover:bg-white/15 rounded-xl cursor-pointer transition"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
