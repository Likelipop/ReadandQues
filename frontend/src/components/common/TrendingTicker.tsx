import React from 'react';
import { Flame } from 'lucide-react';

interface TrendingTickerProps {
  topics?: Array<{ id: string; title: string }>;
  onSelectArticle?: (id: string) => void;
}

export const TrendingTicker: React.FC<TrendingTickerProps> = ({
  topics = [],
  onSelectArticle,
}) => {
  if (!topics || topics.length === 0) return null;

  return (
    <div className="bg-cyber-violet/10 border-b border-cyber-violet/20 text-xs py-2 px-4 overflow-hidden">
      <div className="max-w-7xl mx-auto flex items-center gap-3">
        <div className="flex items-center gap-1 text-cyber-violet font-extrabold uppercase tracking-wider shrink-0">
          <Flame className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
          <span>Trending:</span>
        </div>

        <div className="flex gap-6 overflow-x-auto whitespace-nowrap scrollbar-none flex-grow">
          {topics.map((item, idx) => (
            <div key={item.id || idx} className="flex items-center gap-2">
              <button
                onClick={() => onSelectArticle && onSelectArticle(item.id)}
                className="text-slate-300 hover:text-cyber-cyan transition text-xs truncate max-w-[320px] cursor-pointer"
              >
                {item.title}
              </button>
              {idx < topics.length - 1 && (
                <span className="text-slate-600 select-none">•</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
