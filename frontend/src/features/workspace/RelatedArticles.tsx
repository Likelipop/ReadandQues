import React from 'react';
import { Sparkles, BookOpen } from 'lucide-react';
import { ArticleCard } from '../../types';

interface RelatedArticlesProps {
  articles: ArticleCard[];
  onSelectArticle: (id: string) => void;
}

export const RelatedArticles: React.FC<RelatedArticlesProps> = ({
  articles,
  onSelectArticle,
}) => {
  if (!articles || articles.length === 0) return null;

  return (
    <section className="mt-12 pt-8 border-t border-white/10 space-y-4">
      <div className="flex items-center gap-2 text-xs font-bold text-cyber-cyan uppercase tracking-wider">
        <Sparkles className="w-4 h-4 text-cyber-violet" />
        <span>Related Reading Tests</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {articles.slice(0, 3).map((art) => {
          const aid = art.id || art.article_id || '';
          return (
            <div
              key={aid}
              onClick={() => onSelectArticle(aid)}
              className="glass-card p-4 hover:border-cyber-violet/40 transition cursor-pointer flex flex-col justify-between group space-y-2"
            >
              <div className="space-y-1">
                <span className="text-[9px] font-bold text-cyber-cyan uppercase">
                  {art.source_name || 'News'}
                </span>
                <h4 className="text-xs font-bold text-white group-hover:text-cyber-cyan transition line-clamp-2 leading-snug">
                  {art.title}
                </h4>
              </div>

              <div className="text-[10px] text-slate-400 flex items-center justify-between pt-2 border-t border-white/5">
                <span>{art.word_count || 0} words</span>
                <span className="text-cyber-violet font-semibold group-hover:translate-x-0.5 transition">
                  Practice →
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
