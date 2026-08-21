import React from 'react';
import { BookOpen, CheckCircle2, Clock, Calendar, ArrowRight } from 'lucide-react';
import { ArticleCard as ArticleCardType } from '../../types';
import { formatPublishDate } from '../../utils/dateFilter';

interface ArticleCardProps {
  article: ArticleCardType;
  onSelect: (id: string) => void;
}

export const ArticleCard: React.FC<ArticleCardProps> = ({ article, onSelect }) => {
  const articleId = article.id || article.article_id || '';
  const estimatedMin = Math.max(1, Math.ceil((article.word_count || 300) / 200));
  const formattedDate = formatPublishDate(article.published_at);

  return (
    <div
      onClick={() => onSelect(articleId)}
      className="glass-card-interactive flex flex-col justify-between overflow-hidden group cursor-pointer relative"
    >
      {/* Thumbnail or fallback gradient */}
      <div className="h-44 w-full relative overflow-hidden bg-slate-950/80">
        {article.image_url ? (
          <img
            src={article.image_url}
            alt={article.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-tr from-indigo-950/60 via-purple-950/40 to-slate-900 flex items-center justify-center">
            <BookOpen className="w-10 h-10 text-white/20" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/20 to-transparent" />

        {/* Source & Attempt badges */}
        <div className="absolute top-3.5 left-3.5 right-3.5 flex items-center justify-between gap-2">
          <span className="text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full bg-black/70 backdrop-blur-md text-cyber-cyan border border-white/10 shadow-sm">
            {article.source_name || 'News'}
          </span>
          {article.has_attempted && (
            <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 backdrop-blur-md shadow-sm">
              <CheckCircle2 className="w-3 h-3" /> Completed
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium flex-wrap">
            <span className="text-indigo-400 font-semibold">{article.theme || 'General'}</span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" /> {estimatedMin} min read
            </span>
            {formattedDate && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1 text-slate-400">
                  <Calendar className="w-3 h-3 text-slate-500" /> {formattedDate}
                </span>
              </>
            )}
          </div>

          <h3 className="font-bold text-sm sm:text-base text-white group-hover:text-cyber-cyan transition-colors line-clamp-2 leading-snug">
            {article.title}
          </h3>

          <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
            {article.summary || 'Practice reading comprehension and AI generated questions.'}
          </p>
        </div>

        {/* Card Footer */}
        <div className="pt-3 border-t border-white/5 flex items-center justify-between mt-auto">
          <span className="text-xs text-slate-500 font-mono">
            {article.word_count || 0} words
          </span>

          <div className="inline-flex items-center gap-1 text-xs font-bold text-indigo-400 group-hover:text-cyan-300 transition-colors">
            <span>Start Practice</span>
            <ArrowRight className="w-3.5 h-3.5 transform group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>
    </div>
  );
};
