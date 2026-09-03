import React from 'react';
import {
  BookOpen,
  X,
  Volume2,
  Loader2,
} from 'lucide-react';
import { Article } from '../../types';
import { useWorkspace } from '../../store';

interface LeftSidebarProps {
  article?: Article;
  onScrollToParagraph?: (pIndex: number) => void;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = () => {
  const {
    activeDictionaryWord,
    isDictionaryLoading,
    closeDictionaryCard,
    lookupDictionaryWord,
  } = useWorkspace();

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

  if (!activeDictionaryWord && !isDictionaryLoading) {
    return null;
  }

  return (
    <aside className="space-y-6 relative">
      <div ref={topRef} className="absolute -top-6 left-0 h-1 w-1" />

      {/* Instant Dictionary Card (Rendered only when active) */}
      <div className="glass-card glow-cyan p-5 space-y-3.5 border border-cyan-500/30 bg-cyan-950/20 animate-in fade-in zoom-95 duration-200">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-cyan-400/20 border border-cyan-400/30 flex items-center justify-center text-cyan-300">
                <BookOpen className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] font-black uppercase tracking-wider text-cyan-400 block">
                  Vocabulary Lexicon
                </span>
                <div className="flex items-center gap-2 flex-wrap">
                  <h4 className="font-black text-base text-white capitalize">
                    {activeDictionaryWord?.word || 'Looking up...'}
                  </h4>
                  {activeDictionaryWord?.phonetic && (
                    <span className="text-xs font-mono text-cyan-300 font-medium bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
                      {activeDictionaryWord.phonetic}
                    </span>
                  )}
                  {activeDictionaryWord && (
                    <button
                      onClick={() => handleSpeak(activeDictionaryWord.lemma || activeDictionaryWord.word)}
                      className="p-1 hover:text-cyan-300 text-slate-400 hover:bg-white/10 rounded-lg transition cursor-pointer"
                      title="Pronounce word"
                      aria-label="Listen pronunciation"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
                {activeDictionaryWord?.lemma && activeDictionaryWord.lemma !== activeDictionaryWord.word && (
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Base form: <strong className="text-cyan-300 font-semibold">{activeDictionaryWord.lemma}</strong>
                  </p>
                )}
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
              <span>Looking up in WordNet lexicon...</span>
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
                {activeDictionaryWord.definitions.slice(0, 5).map((def, dIdx) => (
                  <div
                    key={dIdx}
                    className="space-y-1.5 bg-black/40 p-3 rounded-xl border border-white/5"
                  >
                    <div className="flex items-center gap-1.5">
                      {def.part_of_speech && (
                        <span className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.2 rounded bg-white/10 text-cyan-300">
                          {def.part_of_speech}
                        </span>
                      )}
                      <p className="text-slate-200 leading-relaxed font-medium">
                        {def.definition}
                      </p>
                    </div>

                    {def.examples && def.examples.length > 0 && (
                      <div className="space-y-1 pt-0.5">
                        {def.examples.map((ex, eIdx) => (
                          <p
                            key={eIdx}
                            className="text-[11px] text-slate-400 italic bg-white/[0.02] p-1.5 rounded-lg border-l-2 border-cyan-500/40 pl-2.5"
                          >
                            "{ex}"
                          </p>
                        ))}
                      </div>
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
    </aside>
  );
};
