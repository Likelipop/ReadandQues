import React, { useRef, useState, useEffect } from 'react';
import {
  Sparkles,
  BookOpen,
  Clock,
  Loader2,
  Highlighter,
  Copy,
  Check,
  RotateCcw,
} from 'lucide-react';
import { Article } from '../../types';
import { useHighlighter, HIGHLIGHT_THEMES } from '../../hooks/useHighlighter';
import { useWorkspace, HighlightColor } from '../../store';
import { api } from '../../api/client';
import { SmartParaphraseModal } from './SmartParaphraseModal';

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
  const [paraphraseTargetText, setParaphraseTargetText] = useState<string | null>(null);

  // In-place simplified sentences mapped by `p{pIdx}_s{sIdx}`
  const [simplifiedSentences, setSimplifiedSentences] = useState<Record<string, string>>({});
  // Loading status for inline sentence simplification
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
  const { highlightSelection } = useHighlighter(articleId, contentRef);

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
        setPopoverPos({
          x: Math.max(20, Math.min(window.innerWidth - 20, rect.left + rect.width / 2)),
          y: Math.max(10, rect.top - 10),
        });
        setSelectedText(text);
      } else {
        setPopoverPos(null);
        setSelectedText(null);
      }
    };

    document.addEventListener('selectionchange', handleSelection);
    return () => document.removeEventListener('selectionchange', handleSelection);
  }, [activeTool]);

  // Simplify a sentence in-place in the paragraph DOM
  const simplifySentenceInPlace = async (
    sentenceKey: string,
    sentenceText: string,
    paragraphText: string
  ) => {
    const cleanSentence = sentenceText.trim();
    if (!cleanSentence || loadingSentences[sentenceKey]) return;

    setLoadingSentences((prev) => ({ ...prev, [sentenceKey]: true }));
    if (onShowToast) {
      onShowToast('✨ Simplifying sentence with Smart Ink...', 'info');
    }

    try {
      const res = await api.articles.smartParaphrase(articleId, {
        paragraph_text: paragraphText,
        highlighted_text: cleanSentence,
      });

      const simplified =
        res.paraphrased_text ||
        res.simplified_version ||
        res.explanation ||
        cleanSentence;

      setSimplifiedSentences((prev) => ({
        ...prev,
        [sentenceKey]: simplified,
      }));

      if (onShowToast) {
        onShowToast('Sentence simplified in-place!', 'success');
      }
    } catch {
      // Fallback simplification if offline or mock
      setSimplifiedSentences((prev) => ({
        ...prev,
        [sentenceKey]: `In simple terms: ${cleanSentence}`,
      }));
      if (onShowToast) {
        onShowToast('Sentence simplified (offline)', 'info');
      }
    } finally {
      setLoadingSentences((prev) => ({ ...prev, [sentenceKey]: false }));
      setPopoverPos(null);
      setSelectedText(null);
    }
  };

  // Revert a simplified sentence back to original
  const restoreSentence = (sentenceKey: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSimplifiedSentences((prev) => {
      const next = { ...prev };
      delete next[sentenceKey];
      return next;
    });
    if (onShowToast) {
      onShowToast('Restored original sentence', 'info');
    }
  };

  // Split text into paragraphs
  const rawText = article.original_text || article.cleaned_text || article.summary || '';
  const paragraphs = rawText
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);

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

    // 2. Eraser Mode: If clicked sentence is simplified, revert it!
    if (activeTool === 'eraser') {
      restoreSentence(sentenceKey, e);
      return;
    }

    // 3. Marker Mode: Handled by useHighlighter
    if (activeTool === 'marker') {
      return;
    }

    // 4. Smart Ink Mode: In-Place Simplification!
    if (activeTool === 'smart_ink') {
      if (simplifiedSentences[sentenceKey]) {
        return;
      }
      simplifySentenceInPlace(sentenceKey, sentenceText, paragraphText);
    }
  };

  // Trigger Smart Ink simplification from HUD
  const handleHudSmartInk = () => {
    if (!selectedText) return;

    let targetKey: string | null = null;
    let targetSentence = selectedText;
    let targetParagraph = selectedText;

    for (let pIdx = 0; pIdx < paragraphs.length; pIdx++) {
      const p = paragraphs[pIdx];
      const sents = p.match(/[^.!?]+[.!?]+(\s+|$)|[^.!?]+$/g) || [p];
      for (let sIdx = 0; sIdx < sents.length; sIdx++) {
        const s = sents[sIdx];
        if (s.includes(selectedText) || selectedText.includes(s.trim())) {
          targetKey = `p${pIdx}_s${sIdx}`;
          targetSentence = s;
          targetParagraph = p;
          break;
        }
      }
      if (targetKey) break;
    }

    const key = targetKey || `p0_s0`;
    simplifySentenceInPlace(key, targetSentence, targetParagraph);
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

  // Trigger Paraphrase Modal from selection HUD or shortcut
  const handleTriggerParaphrase = () => {
    if (!selectedText) return;
    setParaphraseTargetText(selectedText);
    setPopoverPos(null);
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

      // I: Smart Ink tool
      if (key === 'i' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setActiveTool(activeTool === 'smart_ink' ? null : 'smart_ink');
        return;
      }

      // D: Dictionary tool
      if (key === 'd' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setActiveTool(activeTool === 'dictionary' ? null : 'dictionary');
        return;
      }

      // P: Paraphrase selection
      if (key === 'p' && !e.metaKey && !e.ctrlKey) {
        const sel = window.getSelection();
        const text = sel ? sel.toString().trim() : '';
        if (text.length >= 2) {
          e.preventDefault();
          setParaphraseTargetText(text);
        }
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
  const isAnySentenceLoading = Object.values(loadingSentences).some(Boolean);

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
            : activeTool === 'smart_ink'
            ? 'cursor-pointer'
            : 'cursor-auto'
        }`}
      >
        {paragraphs.map((p, idx) => {
          // Split paragraph into sentences for interaction
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
                  const isSimplified = !!simplifiedSentences[sentenceKey];
                  const isLoading = !!loadingSentences[sentenceKey];
                  const displayedText = isSimplified ? simplifiedSentences[sentenceKey] : sent;

                  if (isLoading) {
                    return (
                      <span
                        key={sIdx}
                        className="inline-flex items-center gap-1.5 bg-indigo-500/20 text-cyan-200 border border-indigo-500/40 rounded px-2 py-0.5 my-0.5 animate-pulse text-xs font-mono select-none"
                      >
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-300" />
                        <span>[⏳ Simplifying sentence...]</span>
                      </span>
                    );
                  }

                  if (isSimplified) {
                    return (
                      <span
                        key={sIdx}
                        data-sentence-key={sentenceKey}
                        onClick={(e) => handleSentenceClick(sentenceKey, sent, p, e)}
                        className={`inline-smart-ink group/ink relative inline-block transition-all duration-200 my-0.5 rounded px-1.5 py-0.5 bg-emerald-500/15 text-emerald-100 border-b border-emerald-400/50 ${
                          activeTool === 'eraser'
                            ? 'hover:bg-rose-500/20 hover:text-rose-200 hover:line-through cursor-crosshair ring-1 ring-rose-400/50'
                            : activeTool === 'dictionary'
                            ? 'cursor-help'
                            : 'cursor-default'
                        }`}
                      >
                        <span className="font-medium">{displayedText}</span>

                        {/* Inline ✨ Simplified Badge */}
                        <span className="inline-flex items-center gap-0.5 ml-1.5 text-[10px] font-black uppercase tracking-wider text-emerald-300 bg-emerald-500/20 border border-emerald-500/30 rounded px-1.5 py-0.5 select-none align-middle">
                          ✨ Simplified
                        </span>

                        {/* Quick Restore ↺ Original Button */}
                        <button
                          type="button"
                          onClick={(e) => restoreSentence(sentenceKey, e)}
                          title="Restore original sentence"
                          aria-label="Restore original sentence"
                          className="inline-flex items-center gap-0.5 ml-1 text-[10px] font-bold text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 rounded px-1.5 py-0.5 cursor-pointer transition select-none align-middle"
                        >
                          <RotateCcw className="w-2.5 h-2.5" />
                          <span>Original</span>
                        </button>
                      </span>
                    );
                  }

                  return (
                    <span
                      key={sIdx}
                      data-sentence-key={sentenceKey}
                      onClick={(e) => handleSentenceClick(sentenceKey, sent, p, e)}
                      title={
                        activeTool === 'smart_ink'
                          ? 'Click to simplify sentence in-place'
                          : activeTool === 'dictionary'
                          ? 'Click word to look up in WordNet Dictionary'
                          : undefined
                      }
                      className={`rounded px-0.5 transition-all duration-150 inline ${
                        activeTool === 'smart_ink'
                          ? 'hover:bg-purple-500/20 hover:text-white cursor-pointer'
                          : activeTool === 'dictionary'
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

      {/* Contextual Selection Action HUD Popover */}
      {popoverPos && selectedText && (
        <div
          role="toolbar"
          aria-label="Selection Actions HUD"
          style={{
            position: 'fixed',
            left: `${popoverPos.x}px`,
            top: `${popoverPos.y}px`,
            transform: 'translate(-50%, -100%)',
          }}
          className="z-50 flex items-center gap-1 sm:gap-1.5 p-1 rounded-2xl glass-card glow-violet backdrop-blur-2xl border border-white/20 shadow-2xl animate-in fade-in zoom-95 duration-150 select-none max-w-[95vw] overflow-x-auto"
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

          {/* 2. Define (Dictionary) Button */}
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

          {/* 3. Explain (Smart Ink) Button */}
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              handleHudSmartInk();
            }}
            disabled={isAnySentenceLoading}
            title="Explain with AI Smart Ink (I)"
            aria-label="Explain with Smart Ink"
            className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg cursor-pointer transition disabled:opacity-50"
          >
            {isAnySentenceLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-300" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            )}
            <span>{isAnySentenceLoading ? 'Simplifying...' : 'Smart Ink'}</span>
          </button>

          {/* 4. Paraphrase Button */}
          <button
            onMouseDown={(e) => {
              e.preventDefault();
              handleTriggerParaphrase();
            }}
            title="Smart Paraphrase (P)"
            aria-label="Paraphrase selection"
            className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 text-purple-200 border border-purple-500/30 font-bold text-xs cursor-pointer transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-300" />
            <span>Paraphrase</span>
          </button>

          {/* 5. Copy Button */}
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
        </div>
      )}

      {/* Smart Paraphrase Modal */}
      {paraphraseTargetText && (
        <SmartParaphraseModal
          articleId={articleId}
          selectedText={paraphraseTargetText}
          onClose={() => setParaphraseTargetText(null)}
        />
      )}
    </article>
  );
};
