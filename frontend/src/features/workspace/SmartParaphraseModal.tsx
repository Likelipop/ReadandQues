import React, { useState, useEffect } from 'react';
import { Sparkles, X, Copy, Check, Loader2, BookOpen } from 'lucide-react';
import { api } from '../../api/client';
import { SmartParaphraseResult } from '../../types';

interface SmartParaphraseModalProps {
  articleId: string;
  selectedText: string;
  onClose: () => void;
}

export const SmartParaphraseModal: React.FC<SmartParaphraseModalProps> = ({
  articleId,
  selectedText,
  onClose,
}) => {
  const [result, setResult] = useState<SmartParaphraseResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!selectedText.trim() || !articleId) return;

    setLoading(true);
    setError(null);

    api.articles
      .smartParaphrase(articleId, {
        paragraph_text: selectedText,
        highlighted_text: selectedText,
      })
      .then((res) => {
        setResult(res);
        setLoading(false);
      })
      .catch((err: any) => {
        setError(err.message || 'Failed to paraphrase text');
        setLoading(false);
      });
  }, [articleId, selectedText]);

  const handleCopy = () => {
    if (result?.paraphrased_text && typeof navigator !== 'undefined') {
      navigator.clipboard.writeText(result.paraphrased_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Smart Paraphrase Popover"
      className="fixed bottom-10 left-1/2 -translate-x-1/2 z-50 w-full max-w-lg p-5 glass-card glow-violet border border-white/20 shadow-2xl animate-in slide-in-from-bottom-5 duration-200"
    >
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-cyber-violet/20 border border-cyber-violet/40 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-cyber-cyan" />
          </div>
          <span className="font-bold text-xs text-white">AI Smart Paraphrase</span>
          <span className="text-[10px] font-bold uppercase px-1.5 py-0.2 rounded bg-cyber-violet/20 text-cyber-violet border border-cyber-violet/30">
            Band 8.5
          </span>
        </div>

        <button
          onClick={onClose}
          aria-label="Close paraphrase popover"
          className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="py-3 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-6 gap-2 text-xs text-slate-400">
            <Loader2 className="w-4 h-4 text-cyber-violet animate-spin" />
            <span>Analyzing lexical context & generating CEFR simplification...</span>
          </div>
        ) : error ? (
          <div className="text-xs text-red-400 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
            {error}
          </div>
        ) : result ? (
          <div className="space-y-3">
            {/* Original Selection */}
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Original Selection
              </span>
              <p className="text-xs text-slate-300 italic p-2.5 rounded-lg bg-black/30 border border-white/5 line-clamp-3">
                "{selectedText}"
              </p>
            </div>

            {/* Paraphrased Result */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-cyber-cyan uppercase tracking-wider flex items-center gap-1">
                  <BookOpen className="w-3 h-3" /> Academic Paraphrase
                </span>
                <button
                  onClick={handleCopy}
                  className="text-[10px] text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer"
                >
                  {copied ? <Check className="w-3 h-3 text-cyber-emerald" /> : <Copy className="w-3 h-3" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <p className="text-xs font-semibold text-white p-3 rounded-xl bg-cyber-violet/10 border border-cyber-violet/30 shadow-inner">
                {result.paraphrased_text}
              </p>
            </div>

            {/* Explanation */}
            {result.explanation && (
              <div className="p-2.5 rounded-lg bg-white/[0.02] border border-white/5 text-[11px] text-slate-400 leading-relaxed">
                <strong className="text-slate-300 block mb-0.5">Linguistic Context:</strong>
                {result.explanation}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};
