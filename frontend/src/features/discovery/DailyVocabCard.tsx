import React, { useState } from 'react';
import {
  BookMarked,
  Volume2,
  Sparkles,
  Copy,
  Check,
  Calendar,
  Award,
  ArrowRight,
  Quote,
} from 'lucide-react';
import { DailyVocab } from '../../types';
import { getDeterministicDailyVocab, formatVocabDateBanner } from '../../utils/dailyVocab';

interface DailyVocabCardProps {
  vocab?: DailyVocab;
  onExploreTopic?: (keyword: string) => void;
}

export const DailyVocabCard: React.FC<DailyVocabCardProps> = ({
  vocab: propVocab,
  onExploreTopic,
}) => {
  const vocab = propVocab || getDeterministicDailyVocab();
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const formattedDate = formatVocabDateBanner(new Date());

  const handleSpeak = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(vocab.word);
      utter.lang = 'en-US';
      utter.rate = 0.9;
      utter.onstart = () => setIsSpeaking(true);
      utter.onend = () => setIsSpeaking(false);
      utter.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utter);
    }
  };

  const handleCopy = async () => {
    const textToCopy = `${vocab.word} (${vocab.phonetic}) [${vocab.part_of_speech || 'academic'}]\n` +
      `Definition: ${vocab.definition}\n` +
      `Example: "${vocab.example}"`;

    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(textToCopy);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = textToCopy;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="glass-card glow-violet relative overflow-hidden p-6 sm:p-8 rounded-2xl border border-white/10 shadow-2xl transition-all">
      {/* Subtle Background Glow Accent */}
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-gradient-to-br from-cyber-violet/20 via-purple-600/10 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-gradient-to-tr from-cyber-cyan/15 via-blue-600/10 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4 relative z-10">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-cyber-violet bg-cyber-violet/10 border border-cyber-violet/30 px-3 py-1 rounded-full">
            <BookMarked className="w-3.5 h-3.5 text-cyber-cyan" />
            <span>Word of the Day</span>
          </span>
          <span className="flex items-center gap-1 text-xs font-semibold text-slate-400">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span>{formattedDate}</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          {vocab.band_score && (
            <span className="flex items-center gap-1 text-[11px] font-bold uppercase px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              <Award className="w-3 h-3 text-emerald-400" />
              <span>{vocab.band_score}</span>
            </span>
          )}
          <span className="text-[11px] font-bold uppercase px-2.5 py-0.5 rounded-full bg-cyber-cyan/15 text-cyber-cyan border border-cyber-cyan/30">
            {vocab.part_of_speech || 'academic'}
          </span>
        </div>
      </div>

      {/* Main Spotlight Body */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start relative z-10">
        {/* Left Column: Word, Phonetic, Audio, Copy */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight drop-shadow-sm">
                {vocab.word}
              </h2>
              <p className="text-sm text-cyber-cyan font-mono mt-1 font-semibold">
                {vocab.phonetic}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleSpeak}
                aria-label="Listen to pronunciation"
                title="Listen to pronunciation"
                className={`p-2.5 rounded-xl border transition cursor-pointer ${
                  isSpeaking
                    ? 'bg-cyber-violet text-white border-cyber-violet scale-105 shadow-lg glow-violet'
                    : 'bg-white/5 hover:bg-cyber-violet/20 border-white/10 text-slate-300 hover:text-white'
                }`}
              >
                <Volume2 className={`w-4 h-4 ${isSpeaking ? 'animate-pulse' : ''}`} />
              </button>

              <button
                onClick={handleCopy}
                aria-label="Copy vocabulary card"
                title={copied ? 'Copied to clipboard!' : 'Copy vocabulary card'}
                className={`p-2.5 rounded-xl border transition cursor-pointer flex items-center gap-1 text-xs font-semibold ${
                  copied
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-white/5 hover:bg-white/10 border-white/10 text-slate-300 hover:text-white'
                }`}
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-medium">
            {vocab.definition}
          </p>
        </div>

        {/* Right Column: Context Example & Practice Action */}
        <div className="lg:col-span-7 flex flex-col justify-between h-full space-y-4">
          {/* Authentic Academic Context Box */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 text-xs sm:text-sm text-slate-300 relative">
            <div className="flex items-start gap-2.5">
              <Quote className="w-4 h-4 text-cyber-violet shrink-0 mt-0.5 opacity-80" />
              <p className="italic leading-relaxed">
                "{vocab.example}"
              </p>
            </div>
            <div className="mt-2 text-[10px] uppercase font-bold tracking-wider text-slate-500 text-right">
              Authentic Context Usage
            </div>
          </div>

          {/* Action CTA */}
          <div>
            <button
              onClick={() => onExploreTopic && onExploreTopic(vocab.word)}
              className="w-full py-3 px-5 rounded-xl bg-gradient-to-r from-cyber-violet to-purple-700 hover:from-purple-600 hover:to-cyber-violet text-white font-bold text-xs sm:text-sm shadow-lg glow-violet transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer group"
            >
              <Sparkles className="w-4 h-4 text-cyber-cyan group-hover:rotate-12 transition-transform" />
              <span>Practice Reading Tests with "{vocab.word}"</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
