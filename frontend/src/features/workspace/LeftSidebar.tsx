import React from 'react';
import {
  BookOpen,
  X,
  Clock,
  Bookmark,
  Volume2,
  Loader2,
  HelpCircle,
} from 'lucide-react';
import { Article } from '../../types';
import { useWorkspace } from '../../store';

interface LeftSidebarProps {
  article: Article;
  onScrollToParagraph?: (pIndex: number) => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  article,
  onScrollToParagraph,
}) => {
  const {
    activeDictionaryWord,
    isDictionaryLoading,
    closeDictionaryCard,
    lookupDictionaryWord,
  } = useWorkspace();

  // Compute paragraph count
  const paragraphs = (article.cleaned_text || article.original_text || '')
    .split(/\n\s*\n/)
    .filter((p) => p.trim().length > 0);

  const readingTimeMin = Math.max(2, Math.ceil((article.word_count || 400) / 200));

  const handleSpeak = (text: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    }
  };

  const topRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (activeDictionaryWord) {
      topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [activeDictionaryWord]);

  return (
    <aside className="space-y-6 relative">
      <div ref={topRef} className="absolute -top-6 left-0 h-1 w-1" />

      {/* 1. Article Overview & Outline */}
      <div className="glass-card p-5 space-y-4 border border-white/10">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
            {article.theme || 'Academic'}
          </span>
          <span className="text-[10px] text-slate-400 flex items-center gap-1 font-mono">
            <Clock className="w-3 h-3 text-cyan-400" /> {readingTimeMin} min
          </span>
        </div>

        <div>
          <h3 className="font-extrabold text-sm text-white line-clamp-2 leading-snug">
            {article.title}
          </h3>
          <p className="text-[11px] text-slate-400 mt-1">
            {article.source_name || 'Academic News'} • {article.word_count || 0} words
          </p>
        </div>

        {/* Passage Section Jump Index */}
        {paragraphs.length > 0 && (
          <div className="pt-2 border-t border-white/5 space-y-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
              <Bookmark className="w-3 h-3 text-indigo-400" /> Passage Sections ({paragraphs.length})
            </span>
            <div className="grid grid-cols-4 gap-1.5">
              {paragraphs.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => onScrollToParagraph && onScrollToParagraph(idx)}
                  className="py-1 px-2 text-[11px] font-mono font-bold rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition text-center cursor-pointer border border-white/5"
                  title={`Jump to paragraph ${idx + 1}`}
                >
                  § {idx + 1}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 2. WordNet Dictionary Card */}
      {activeDictionaryWord || isDictionaryLoading ? (
        <div className="glass-card glow-cyan p-5 space-y-3.5 border border-cyan-500/30 bg-cyan-950/20 animate-in fade-in zoom-95 duration-200">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-cyan-400/20 border border-cyan-400/30 flex items-center justify-center text-cyan-300">
                <BookOpen className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-black uppercase tracking-wider text-cyan-400 block">
                  WordNet Lexicon
                </span>
                <h4 className="font-black text-base text-white capitalize flex items-center gap-2">
                  {activeDictionaryWord?.word || 'Looking up...'}
                  {activeDictionaryWord && (
                    <button
                      onClick={() => handleSpeak(activeDictionaryWord.word)}
                      className="p-1 hover:text-cyan-300 text-slate-400 hover:bg-white/10 rounded-lg transition cursor-pointer"
                      title="Pronounce word"
                      aria-label="Listen pronunciation"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                </h4>
              </div>
            </div>

            <button
              onClick={closeDictionaryCard}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition cursor-pointer"
              title="Close dictionary card"
              aria-label="Close dictionary card"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {isDictionaryLoading ? (
            <div className="py-6 flex flex-col items-center justify-center gap-2 text-xs text-slate-400">
              <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
              <span>Looking up in offline WordNet...</span>
            </div>
          ) : activeDictionaryWord?.found ? (
            <div className="space-y-3 text-xs">
              {activeDictionaryWord.part_of_speech && (
                <span className="inline-block px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 text-[10px] font-bold uppercase tracking-wider border border-cyan-500/30">
                  {activeDictionaryWord.part_of_speech}
                </span>
              )}

              {/* Definitions */}
              <div className="space-y-2.5">
                {activeDictionaryWord.definitions.slice(0, 4).map((def, dIdx) => (
                  <div
                    key={dIdx}
                    className="space-y-1.5 bg-black/40 p-3 rounded-xl border border-white/5"
                  >
                    <p className="text-slate-200 leading-relaxed font-medium">
                      {def.definition}
                    </p>
                    {def.examples && def.examples.length > 0 && (
                      <p className="text-[11px] text-slate-400 italic bg-white/[0.02] p-1.5 rounded-lg border-l-2 border-cyan-500/40 pl-2.5">
                        "{def.examples[0]}"
                      </p>
                    )}
                    {def.synonyms && def.synonyms.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[9px] text-slate-500 font-bold uppercase">
                          Synonyms:
                        </span>
                        {def.synonyms.slice(0, 6).map((syn, sIdx) => (
                          <button
                            key={sIdx}
                            onClick={() => lookupDictionaryWord(syn)}
                            className="text-[10px] text-cyan-300 hover:text-cyan-100 bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/30 px-2 py-0.5 rounded-lg cursor-pointer transition font-medium"
                          >
                            {syn}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-3 bg-black/30 rounded-xl border border-white/5 text-xs text-slate-400 italic">
              No definitions found for "{activeDictionaryWord?.word}".
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card p-4 space-y-2 border border-white/5 bg-white/[0.01]">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-400">
            <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
            <span>Interactive WordNet Dictionary</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Select any word or switch to <strong className="text-cyan-300">Dictionary Mode (D)</strong> to click words directly and inspect instant definitions, pronunciation, and synonyms.
          </p>
        </div>
      )}
    </aside>
  );
};
