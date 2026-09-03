import React, { useRef, useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  BookOpen,
  Clock,
  Highlighter,
  Eraser,
  Copy,
  Check,
} from 'lucide-react';
import { Article } from '../../types';
import { useHighlighter, HIGHLIGHT_THEMES } from '../../hooks/useHighlighter';
import { useWorkspace, HighlightColor } from '../../store';

export interface ArticleReaderProps {
  article: Article;
  onShowToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
  onToggleQuiz?: () => void;
}

export const ArticleReader: React.FC<ArticleReaderProps> = ({
  article,
  onShowToast,
  onToggleQuiz,
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [selectedText, setSelectedText] = useState<string | null>(null);
  const [popoverPos, setPopoverPos] = useState<{ x: number; y: number } | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // In-place explained sentences mapped by `p{pIdx}_s{sIdx}`
  const [simplifiedSentences, setSimplifiedSentences] = useState<Record<string, string>>({});
  // Loading status for inline sentence explanation
  const [loadingSentences, setLoadingSentences] = useState<Record<string, boolean>>({});

  const {
    activeTool,
    setActiveTool,
    highlightColor,
    setHighlightColor,
    toggleZenMode,
    lookupDictionaryWord,
  } = useWorkspace();

  const articleId = article.id || article.article_id || '';
  const { highlightSelection, eraseSelection } = useHighlighter(articleId, contentRef);

  const formattedDate = article.published_at
    ? new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(new Date(article.published_at))
    : 'Recent News';

  const estimatedMin = Math.max(1, Math.ceil((article.word_count || 400) / 200));

  // Selection change listener for showing the floating Action HUD when text is selected
  useEffect(() => {
    const handleSelection = () => {
      // STRICTLY suppress HUD popover if dictionary mode is active
      if (activeTool === 'dictionary') {
        setPopoverPos(null);
        setSelectedText(null);
        return;
      }

      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.rangeCount) {
        setPopoverPos(null);
        setSelectedText(null);
        return;
      }

      const range = sel.getRangeAt(0);
      if (!contentRef.current?.contains(range.commonAncestorContainer)) {
        setPopoverPos(null);
        setSelectedText(null);
        return;
      }

      const text = sel.toString().trim();
      if (text.length >= 2) {
        const rect = range.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;
        // Viewport-based calculation with boundary safety
        const x = Math.max(100, Math.min(window.innerWidth - 100, rect.left + rect.width / 2));
        const y = Math.max(50, rect.top - 10);
        setPopoverPos({ x, y });
        setSelectedText(text);
      } else {
        setPopoverPos(null);
        setSelectedText(null);
      }
    };

    document.addEventListener('selectionchange', handleSelection);
    return () => document.removeEventListener('selectionchange', handleSelection);
  }, [activeTool]);

  // Split text into paragraphs and blocks (supporting both double and single newlines)
  const rawText = article.original_text || article.cleaned_text || article.summary || '';
  const initialBlocks = rawText
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);

  // Fallback to single newline split if text wasn't double-newline formatted
  const rawBlocks =
    initialBlocks.length <= 1 && rawText.includes('\n')
      ? rawText
          .split(/\n+/)
          .map((p) => p.trim())
          .filter((p) => p.length > 0)
      : initialBlocks;

  // Filter out leading title heading if redundant with header h1
  const paragraphs = rawBlocks.filter((block, idx) => {
    if (idx === 0) {
      const cleanBlock = block.replace(/^[#\s]+/, '').trim().toLowerCase();
      const cleanTitle = (article.title || '').trim().toLowerCase();
      if (cleanBlock && cleanTitle && (cleanBlock === cleanTitle || cleanBlock.startsWith(cleanTitle))) {
        return false;
      }
    }
    return true;
  });

  // 1-Click Sentence / Word interaction on Markdown
  const handleSentenceClick = (
    sentenceKey: string,
    sentenceText: string,
    paragraphText: string,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();

    // 1. Dictionary Mode: Look up clicked word and STRICTLY suppress HUD popover
    if (activeTool === 'dictionary') {
      setPopoverPos(null);
      setSelectedText(null);

      let clickedWord = '';
      if (typeof document !== 'undefined' && (document as any).caretRangeFromPoint) {
        const range = (document as any).caretRangeFromPoint(e.clientX, e.clientY);
        if (range && range.startContainer?.nodeType === Node.TEXT_NODE) {
          const text = range.startContainer.textContent || '';
          const offset = range.startOffset;
          const left = text.slice(0, offset).search(/[a-zA-Z0-9_-]+$/);
          const right = text.slice(offset).search(/[^a-zA-Z0-9_-]/);
          const start = left >= 0 ? left : offset;
          const end = right >= 0 ? offset + right : text.length;
          clickedWord = text.slice(start, end).replace(/[^a-zA-Z-]/g, '').trim();
        }
      }
      if (!clickedWord) {
        const sel = window.getSelection();
        if (sel && sel.toString().trim()) {
          clickedWord = sel.toString().trim().replace(/[^a-zA-Z-]/g, '');
        } else {
          const words = sentenceText.split(/\s+/).map((w) => w.replace(/[^a-zA-Z-]/g, '')).filter(Boolean);
          clickedWord = words[0] || '';
        }
      }
      if (clickedWord) {
        lookupDictionaryWord(clickedWord);
        if (onShowToast) onShowToast(`Looking up "${clickedWord}" in Dictionary`, 'info');
      }
      return;
    }

    // 2. Marker Mode: Handled by useHighlighter
    if (activeTool === 'marker') {
      return;
    }
  };

  // Trigger Dictionary lookup from selection HUD
  const handleTriggerDictionary = () => {
    if (!selectedText) return;
    const cleanWord = selectedText.replace(/[^a-zA-Z-]/g, '').trim();
    if (cleanWord) {
      lookupDictionaryWord(cleanWord);
      if (onShowToast) onShowToast(`Looking up "${cleanWord}" in Dictionary`, 'info');
    }
    setPopoverPos(null);
    setSelectedText(null);
  };

  // Trigger Highlight from selection HUD
  const handleMarkSelection = (color?: HighlightColor) => {
    highlightSelection(color || highlightColor);
    setPopoverPos(null);
    setSelectedText(null);
  };

  // Trigger Erase / Remove highlight from selection HUD
  const handleEraseSelection = () => {
    const success = eraseSelection();
    if (success) {
      if (onShowToast) onShowToast('Highlight removed', 'info');
    } else {
      if (onShowToast) onShowToast('No highlight in selected text to remove', 'info');
    }
    setPopoverPos(null);
    setSelectedText(null);
  };

  // Copy selection to clipboard
  const handleCopySelection = () => {
    if (!selectedText) return;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(selectedText);
      setIsCopied(true);
      if (onShowToast) onShowToast('Copied text to clipboard', 'success');
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore shortcuts if user is typing in an input, textarea, or contenteditable
      const target = e.target as HTMLElement | null;
      if (
        target &&
        typeof target.getAttribute === 'function' &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable ||
          target.getAttribute('role') === 'textbox')
      ) {
        return;
      }

      const key = e.key.toLowerCase();

      // V or Escape: Pointer mode / dismiss
      if (key === 'v' || e.key === 'Escape') {
        setActiveTool(null);
        setPopoverPos(null);
        setSelectedText(null);
        return;
      }

      // H: Highlighter tool
      if (key === 'h' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setActiveTool(activeTool === 'marker' ? null : 'marker');
        return;
      }

      // E: Eraser tool
      if (key === 'e' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setActiveTool(activeTool === 'eraser' ? null : 'eraser');
        return;
      }

      // D: Dictionary tool
      if (key === 'd' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setActiveTool(activeTool === 'dictionary' ? null : 'dictionary');
        return;
      }

      // Z: Zen Mode
      if (key === 'z' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        toggleZenMode();
        return;
      }

      // Q: Quiz Toggle
      if (key === 'q' && !e.metaKey && !e.ctrlKey && onToggleQuiz) {
        e.preventDefault();
        onToggleQuiz();
        return;
      }

      // 1-4: Highlight Color selection
      if (['1', '2', '3', '4'].includes(e.key) && !e.metaKey && !e.ctrlKey) {
        const colorMap: Record<string, HighlightColor> = {
          '1': 'amber',
          '2': 'emerald',
          '3': 'cyan',
          '4': 'rose',
        };
        const selectedColor = colorMap[e.key];
        if (selectedColor) {
          setHighlightColor(selectedColor);
          if (activeTool !== 'marker') setActiveTool('marker');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTool, highlightColor, onToggleQuiz, setActiveTool, setHighlightColor, toggleZenMode]);

  const isSingleWord = selectedText ? selectedText.trim().split(/\s+/).length <= 2 : false;

  return (
    <article className="glass-card p-6 sm:p-10 space-y-8 relative">
      {/* Header */}
      <header className="border-b border-white/10 pb-6 space-y-4">
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <span className="px-3 py-1 rounded-full font-bold uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] tracking-wider">
            {article.source_name || 'Academic Source'}
          </span>
          <span className="text-slate-600">•</span>
          <span className="text-slate-400 font-medium">{formattedDate}</span>
          <span className="text-slate-600">•</span>
          <span className="text-slate-400 flex items-center gap-1 font-medium">
            <Clock className="w-3.5 h-3.5 text-cyan-400" /> {estimatedMin} min read
          </span>
          <span className="text-slate-600">•</span>
          <span className="font-mono text-slate-400 font-medium">{article.word_count || 0} words</span>
        </div>

        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white tracking-tight leading-tight">
          {article.title}
        </h1>

        {article.summary && (
          <p className="text-xs sm:text-sm text-slate-300 italic border-l-2 border-cyan-400 pl-4 py-1.5 bg-white/[0.02] rounded-r-xl">
            {article.summary}
          </p>
        )}
      </header>

      {/* Main Reading Content */}
      <div
        ref={contentRef}
        className={`space-y-6 text-slate-200 text-sm sm:text-base leading-[1.85] tracking-normal select-text ${
          activeTool === 'dictionary'
            ? 'cursor-help'
            : activeTool === 'marker'
            ? 'cursor-text'
            : activeTool === 'eraser'
            ? 'cursor-crosshair'
            : 'cursor-auto'
        }`}
      >
        {paragraphs.map((p, idx) => {
          const isH1 = p.startsWith('# ') && !p.startsWith('## ');
          const isH2 = p.startsWith('## ') && !p.startsWith('### ');
          const isH3 = p.startsWith('### ');
          const isHeading = isH1 || isH2 || isH3;

          if (isHeading) {
            const headingText = p.replace(/^[#\s]+/, '').trim();
            const headingKey = `h${idx}_s0`;
            return (
              <div
                key={idx}
                id={`heading-${idx}`}
                className="relative pt-4 pb-1 border-b border-white/10 scroll-mt-24"
              >
                <h2
                  className={`${
                    isH1 || isH2
                      ? 'text-lg sm:text-xl font-bold text-cyan-300'
                      : 'text-base sm:text-lg font-semibold text-cyan-200'
                  } tracking-tight leading-snug`}
                >
                  <span
                    data-sentence-key={headingKey}
                    onClick={(e) => handleSentenceClick(headingKey, headingText, p, e)}
                    title={
                      activeTool === 'dictionary'
                        ? 'Click word to look up in Dictionary'
                        : undefined
                    }
                    className={`rounded px-0.5 transition-all duration-150 inline ${
                      activeTool === 'dictionary'
                        ? 'hover:bg-cyan-500/20 hover:text-white cursor-help'
                        : ''
                    }`}
                  >
                    {headingText}
                  </span>
                </h2>
              </div>
            );
          }

          const sentences = p.match(/[^.!?]+[.!?]+(\s+|$)|[^.!?]+$/g) || [p];

          return (
            <div
              key={idx}
              id={`paragraph-${idx}`}
              className="relative group/p flex gap-3.5 items-start scroll-mt-24"
            >
              <span className="text-[10px] font-mono text-slate-500 select-none pt-1 shrink-0 w-4 text-right">
                {idx + 1}
              </span>
              <p className="flex-1 text-slate-200 leading-[1.85]">
                {sentences.map((sent, sIdx) => {
                  const sentenceKey = `p${idx}_s${sIdx}`;

                  return (
                    <span
                      key={sIdx}
                      data-sentence-key={sentenceKey}
                      onClick={(e) => handleSentenceClick(sentenceKey, sent, p, e)}
                      title={
                        activeTool === 'dictionary'
                          ? 'Click word to look up in Dictionary'
                          : undefined
                      }
                      className={`rounded px-0.5 transition-all duration-150 inline ${
                        activeTool === 'dictionary'
                          ? 'hover:bg-cyan-500/20 hover:text-white cursor-help'
                          : ''
                      }`}
                    >
                      {sent}
                    </span>
                  );
                })}
              </p>
            </div>
          );
        })}
      </div>

      {/* Contextual Selection Action HUD Popover Portal (Guarantees exact viewport positioning) */}
      {typeof document !== 'undefined' &&
        popoverPos &&
        selectedText &&
        createPortal(
          <div
            role="toolbar"
            aria-label="Selection Actions HUD"
            style={{
              position: 'fixed',
              left: `${popoverPos.x}px`,
              top: `${popoverPos.y}px`,
              transform: 'translate(-50%, -100%)',
              zIndex: 9999,
            }}
            className="flex items-center gap-1 sm:gap-1.5 p-1 rounded-2xl glass-card glow-violet backdrop-blur-2xl border border-white/20 shadow-2xl animate-in fade-in zoom-95 duration-150 select-none max-w-[95vw] overflow-x-auto pointer-events-auto"
          >
            {/* 1. Mark (Highlight) Button */}
            <button
              onMouseDown={(e) => {
                e.preventDefault();
                handleMarkSelection();
              }}
              title={`Mark selection (${highlightColor.toUpperCase()})`}
              aria-label="Mark selection"
              className={`flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-bold transition cursor-pointer ${HIGHLIGHT_THEMES[highlightColor].badgeClass} hover:opacity-90`}
            >
              <Highlighter className="w-3.5 h-3.5" />
              <span>Mark</span>
            </button>

            {/* 2. Erase / Remove Highlight Button */}
            <button
              onMouseDown={(e) => {
                e.preventDefault();
                handleEraseSelection();
              }}
              title="Erase highlight from selection"
              aria-label="Erase highlight"
              className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/30 font-bold text-xs cursor-pointer transition"
            >
              <Eraser className="w-3.5 h-3.5 text-rose-300" />
              <span>Erase</span>
            </button>

            {/* 3. Define (Dictionary) Button */}
            {isSingleWord && (
              <button
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleTriggerDictionary();
                }}
                title="Look up word in Dictionary (D)"
                aria-label="Define word"
                className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 border border-cyan-500/30 font-bold text-xs cursor-pointer transition"
              >
                <BookOpen className="w-3.5 h-3.5 text-cyan-300" />
                <span>Define</span>
              </button>
            )}

            {/* 4. Copy Button */}
            <button
              onMouseDown={(e) => {
                e.preventDefault();
                handleCopySelection();
              }}
              title="Copy selection"
              aria-label="Copy selection"
              className="p-1 px-2 rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 hover:text-white text-xs font-semibold cursor-pointer transition flex items-center gap-1"
            >
              {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{isCopied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>,
          document.body
        )}
    </article>
  );
};
