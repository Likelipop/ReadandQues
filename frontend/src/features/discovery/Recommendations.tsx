import React from 'react';
import { Compass, Sparkles } from 'lucide-react';
import { ArticleCard as ArticleCardType } from '../../types';
import { ArticleCard } from './ArticleCard';

interface RecommendationsProps {
  articles?: ArticleCardType[];
  onSelectArticle: (id: string) => void;
}

export const Recommendations: React.FC<RecommendationsProps> = ({
  articles = [],
  onSelectArticle,
}) => {
  if (!articles || articles.length === 0) return null;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-bold text-cyber-cyan uppercase tracking-wider">
          <Compass className="w-4 h-4 text-cyber-violet" />
          <span>Adaptive Recommendations</span>
        </div>
        <span className="text-[11px] text-slate-400 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-amber-400" /> Based on your reading progress
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {articles.map((art) => (
          <ArticleCard
            key={art.id || art.article_id}
            article={art}
            onSelect={onSelectArticle}
          />
        ))}
      </div>
    </section>
  );
};
