import React from 'react';
import { BookOpen, ChevronLeft, ChevronRight, Calendar, Filter } from 'lucide-react';
import { ArticleCard as ArticleCardType } from '../../types';
import { ArticleCard } from './ArticleCard';
import { DateFilterOption, DATE_FILTER_OPTIONS } from '../../utils/dateFilter';

interface ArticleGridProps {
  articles: ArticleCardType[];
  themes?: string[];
  selectedTheme?: string;
  onSelectTheme?: (theme: string) => void;
  dateFilter?: DateFilterOption;
  onSelectDateFilter?: (filter: DateFilterOption) => void;
  onSelectArticle: (id: string) => void;
  page?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
  isLoading?: boolean;
}

export const ArticleGrid: React.FC<ArticleGridProps> = ({
  articles,
  themes = [],
  selectedTheme = 'All',
  onSelectTheme,
  dateFilter = 'all',
  onSelectDateFilter,
  onSelectArticle,
  page = 1,
  totalPages = 1,
  onPageChange,
  isLoading = false,
}) => {
  return (
    <section className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-4">
        <div>
          <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-cyber-violet" />
            <span>Practice Reading Tests</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Select an article to start full passage reading and AI generated comprehension questions.
          </p>
        </div>

        {/* Date Filter Segmented Control Bar */}
        <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 shrink-0 self-start sm:self-auto">
          <div className="flex items-center gap-1 px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            <Calendar className="w-3 h-3 text-cyber-cyan" />
            <span className="hidden md:inline">Published:</span>
          </div>
          {DATE_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => onSelectDateFilter && onSelectDateFilter(opt.id)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition cursor-pointer ${
                dateFilter === opt.id
                  ? 'bg-cyber-violet text-white font-bold shadow-sm glow-violet'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {opt.shortLabel}
            </button>
          ))}
        </div>
      </div>

      {/* Theme Filter Bar */}
      {themes.length > 0 && (
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none pb-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
            <Filter className="w-3 h-3 text-slate-500" /> Theme:
          </span>
          {themes.map((theme) => (
            <button
              key={theme}
              onClick={() => onSelectTheme && onSelectTheme(theme)}
              className={`px-3 py-1 text-xs font-bold rounded-full transition shrink-0 cursor-pointer ${
                selectedTheme === theme
                  ? 'bg-cyber-violet text-white shadow-md glow-violet'
                  : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {theme}
            </button>
          ))}
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="glass-card h-72 animate-pulse bg-white/[0.02]" />
          ))}
        </div>
      ) : articles.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {articles.map((art) => (
            <ArticleCard
              key={art.id || art.article_id}
              article={art}
              onSelect={onSelectArticle}
            />
          ))}
        </div>
      ) : (
        <div className="glass-card p-12 text-center max-w-md mx-auto space-y-3">
          <BookOpen className="w-10 h-10 text-slate-500 mx-auto" />
          <h4 className="font-bold text-sm text-white">No Reading Tests Found</h4>
          <p className="text-xs text-slate-400">
            No articles match the selected category and date filter. Try selecting "All" or paste a news URL in the top search bar.
          </p>
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-6">
          <button
            onClick={() => onPageChange && onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none text-xs font-bold text-slate-300 hover:text-white transition flex items-center gap-1 cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" /> Previous
          </button>

          <span className="text-xs text-slate-400 font-medium">
            Page <strong className="text-white">{page}</strong> of {totalPages}
          </span>

          <button
            onClick={() => onPageChange && onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none text-xs font-bold text-slate-300 hover:text-white transition flex items-center gap-1 cursor-pointer"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </section>
  );
};
