import React from 'react';
import { Sparkles, ArrowRight, BookOpen, Clock, Flame } from 'lucide-react';
import { ArticleCard } from '../../types';

interface HeroHotNewsProps {
  articles?: ArticleCard[];
  onSelectArticle: (id: string) => void;
}

export const HeroHotNews: React.FC<HeroHotNewsProps> = ({
  articles = [],
  onSelectArticle,
}) => {
  if (!articles || articles.length === 0) return null;

  const featured = articles[0];
  const sideArticles = articles.slice(1, 4);

  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2 text-xs font-bold text-cyber-violet uppercase tracking-wider">
        <Sparkles className="w-4 h-4 text-cyber-cyan" />
        <span>Today's Top Reading Material</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Featured Hero Card */}
        {featured && (
          <div className="lg:col-span-2 glass-card glow-violet overflow-hidden group flex flex-col justify-between relative border border-white/10 hover:border-cyber-violet/40 transition-all duration-300">
            <div className="h-64 sm:h-72 w-full relative overflow-hidden bg-white/5">
              {featured.image_url ? (
                <img
                  src={featured.image_url}
                  alt={featured.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
              ) : (
                <div className="w-full h-full bg-gradient-to-tr from-cyber-violet/30 via-indigo-900/40 to-obsidian-900 flex items-center justify-center">
                  <BookOpen className="w-12 h-12 text-white/20" />
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-obsidian-900 via-obsidian-900/40 to-transparent" />

              <div className="absolute top-4 left-4 flex items-center gap-2">
                <span className="px-3 py-1 rounded-full text-xs font-black bg-cyber-violet text-white shadow-lg flex items-center gap-1">
                  <Flame className="w-3.5 h-3.5 text-amber-300" /> Hot Pick
                </span>
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-black/60 backdrop-blur-md text-cyber-cyan border border-white/10 uppercase">
                  {featured.source_name || 'News'}
                </span>
              </div>
            </div>

            <div className="p-6 sm:p-8 space-y-4 -mt-12 relative z-10">
              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span className="text-cyber-cyan font-semibold">{featured.theme || 'General'}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> {Math.max(2, Math.ceil((featured.word_count || 400) / 200))} min read
                </span>
                <span>•</span>
                <span>{featured.word_count || 0} words</span>
              </div>

              <h2 className="text-xl sm:text-2xl font-black text-white group-hover:text-cyber-cyan transition-colors leading-tight">
                {featured.title}
              </h2>

              <p className="text-xs sm:text-sm text-slate-300 line-clamp-2 leading-relaxed">
                {featured.summary || 'Read authentic world news passages with real-time passage grounding proof and interactive Study Buddy AI.'}
              </p>

              <div className="pt-2">
                <button
                  onClick={() => onSelectArticle(featured.id || featured.article_id || '')}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyber-violet to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs sm:text-sm shadow-xl glow-violet transition-all transform hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
                >
                  <span>Start Reading & AI Quiz</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Side Trending Cards */}
        <div className="flex flex-col gap-4">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Trending Today
          </div>

          {sideArticles.map((art) => {
            const aid = art.id || art.article_id || '';
            return (
              <div
                key={aid}
                onClick={() => onSelectArticle(aid)}
                className="glass-card p-4 hover:border-cyber-cyan/40 transition-all duration-200 cursor-pointer flex gap-4 items-center group"
              >
                <div className="w-20 h-20 rounded-xl overflow-hidden bg-white/5 shrink-0 relative">
                  {art.image_url ? (
                    <img
                      src={art.image_url}
                      alt={art.title}
                      className="w-full h-full object-cover group-hover:scale-110 transition duration-300"
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-tr from-cyber-violet/20 to-cyber-cyan/20 flex items-center justify-center">
                      <BookOpen className="w-5 h-5 text-white/30" />
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0 space-y-1">
                  <span className="text-[9px] font-extrabold text-cyber-cyan uppercase">
                    {art.source_name || 'News'}
                  </span>
                  <h4 className="text-xs font-bold text-white group-hover:text-cyber-cyan transition line-clamp-2 leading-snug">
                    {art.title}
                  </h4>
                  <div className="text-[10px] text-slate-400 flex items-center gap-2">
                    <span>{art.theme || 'General'}</span>
                    <span>•</span>
                    <span>{art.word_count || 0} words</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
