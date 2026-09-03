import React, { useState } from 'react';
import { RefreshCw, Sparkles, Check, Copy } from 'lucide-react';
import { ParaphraseDemo } from '../../types';

interface ParaphraseCardProps {
  demo?: ParaphraseDemo;
}

export const ParaphraseCard: React.FC<ParaphraseCardProps> = ({ demo }) => {
  const [copied, setCopied] = useState(false);

  const defaultOriginal = demo?.original || 'Climate change poses severe threats to global food security.';
  const defaultParaphrased = demo?.paraphrased || 'Global food production is gravely endangered by shifts in world climate.';

  const handleCopy = () => {
    if (typeof navigator !== 'undefined') {
      navigator.clipboard.writeText(defaultParaphrased);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="glass-card glow-cyan p-6 space-y-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold text-cyber-cyan uppercase tracking-wider">
            <RefreshCw className="w-4 h-4 text-cyber-violet" />
            <span>AI Smart Paraphrase Engine</span>
          </div>
          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/40">
            Band 8.0+ Lexical
          </span>
        </div>

        <div className="mt-4 space-y-3">
          {/* Original */}
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Original Standard Text
            </span>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5 text-xs text-slate-300">
              {defaultOriginal}
            </div>
          </div>

          {/* Academic Paraphrase */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-cyber-cyan flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-300" /> Academic Paraphrase
              </span>
              <button
                onClick={handleCopy}
                className="text-[10px] text-slate-400 hover:text-white flex items-center gap-1 transition cursor-pointer"
              >
                {copied ? <Check className="w-3 h-3 text-cyber-emerald" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="p-3 rounded-xl bg-cyber-violet/10 border border-cyber-violet/30 text-xs font-medium text-white shadow-inner">
              {defaultParaphrased}
            </div>
          </div>
        </div>
      </div>

      <div className="pt-2 text-[11px] text-slate-400 flex items-center justify-between">
        <span>✨ Select any text inside the reader for instant paraphrase</span>
      </div>
    </div>
  );
};
