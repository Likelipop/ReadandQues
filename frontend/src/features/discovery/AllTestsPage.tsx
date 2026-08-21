import React, { useState, useEffect } from 'react';
import { Compass, Search, X, Loader2, Calendar } from 'lucide-react';
import { ArticleCard as ArticleCardType } from '../../types';
import { ArticleCard } from './ArticleCard';
import { DateFilterOption, DATE_FILTER_OPTIONS } from '../../utils/dateFilter';
import { api } from '../../api/client';

interface AllTestsPageProps {
  initialQuery?: string;
  initialTheme?: string;
  onSelectArticle: (id: string) => void;
}

export const AllTestsPage: React.FC<AllTestsPageProps> = ({
  initialQuery = '',
  initialTheme = 'All',
  onSelectArticle,
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [selectedTheme, setSelectedTheme] = useState(initialTheme);
  const [selectedGenre, setSelectedGenre] = useState('All');
  const [selectedDateFilter, setSelectedDateFilter] = useState<DateFilterOption>('all');
  const [page, setPage] = useState(1);

  const [articles, setArticles] = useState<ArticleCardType[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const [themes, setThemes] = useState<string[]>(['All']);
  const [genres, setGenres] = useState<string[]>(['All']);

  // Fetch themes & genres once
  useEffect(() => {
    api.homepage
      .get()
      .then((data) => {
        if (data.themes) setThemes(data.themes);
        if (data.genres) setGenres(data.genres);
      })
      .catch(() => {});
  }, []);

  // Fetch articles on filter/page change
  useEffect(() => {
    setLoading(true);
    api.articles
      .list({
        theme: selectedTheme,
        genre: selectedGenre,
        date_filter: selectedDateFilter,
        q: query,
        page,
        limit: 12,
      })
      .then((res) => {
        setArticles(res.articles || []);
        setTotalCount(res.total_count || 0);
      })
      .catch(() => {
        setArticles([]);
        setTotalCount(0);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [query, selectedTheme, selectedGenre, selectedDateFilter, page]);

  const totalPages = Math.max(1, Math.ceil(totalCount / 12));

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-2.5">
            <Compass className="w-7 h-7 text-cyber-violet" />
            <span>
              {query ? (
                <>
                  Search Results for <span className="text-cyber-cyan">"{query}"</span>
                </>
              ) : (
                'Explore All Reading Tests'
              )}
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Choose an authentic reading passage from international news, or search by keyword and topic.
          </p>
        </div>

        {query && (
          <button
            onClick={() => {
              setQuery('');
              setPage(1);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-slate-300 bg-white/5 hover:bg-white/10 rounded-xl transition self-start md:self-auto cursor-pointer"
          >
            <X className="w-4 h-4 text-red-400" /> Clear Search
          </button>
        )}
      </div>

      {/* Filter Tabs Container */}
      <div className="glass-card p-4 space-y-4">
        {/* Theme Pills */}
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-none pb-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1">
            Theme:
          </span>
          {themes.map((theme) => (
            <button
              key={theme}
              onClick={() => {
                setSelectedTheme(theme);
                setPage(1);
              }}
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

        {/* Date Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-none border-t border-white/5 pt-3">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
            <Calendar className="w-3 h-3 text-cyber-cyan" /> Published:
          </span>
          {DATE_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => {
                setSelectedDateFilter(opt.id);
                setPage(1);
              }}
              className={`px-3 py-1 text-xs font-bold rounded-full transition shrink-0 cursor-pointer ${
                selectedDateFilter === opt.id
                  ? 'bg-cyber-cyan/25 text-cyber-cyan border border-cyber-cyan/50 shadow-sm'
                  : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Genre Pills if available */}
        {genres.length > 1 && (
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-none border-t border-white/5 pt-3">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1">
              Genre:
            </span>
            {genres.map((g) => (
              <button
                key={g}
                onClick={() => {
                  setSelectedGenre(g);
                  setPage(1);
                }}
                className={`px-3 py-1 text-xs font-semibold rounded-full transition shrink-0 cursor-pointer ${
                  selectedGenre === g
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Articles Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 className="w-8 h-8 text-cyber-violet animate-spin" />
          <span className="text-xs text-slate-400">Loading tests...</span>
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
        <div className="glass-card p-16 text-center max-w-md mx-auto space-y-4 my-10">
          <Search className="w-12 h-12 text-slate-500 mx-auto" />
          <h3 className="font-bold text-base text-white">No Reading Tests Found</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            {query
              ? `We couldn't find any articles matching "${query}". Try another search term or paste a news URL.`
              : 'No articles found matching the selected filters.'}
          </p>
          <button
            onClick={() => {
              setQuery('');
              setSelectedTheme('All');
              setSelectedGenre('All');
              setSelectedDateFilter('all');
              setPage(1);
            }}
            className="px-5 py-2.5 rounded-xl bg-cyber-violet text-white text-xs font-bold hover:bg-purple-600 transition cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none text-xs font-bold text-slate-300 hover:text-white transition cursor-pointer"
          >
            Previous
          </button>

          <span className="text-xs text-slate-400 font-medium px-4">
            Page <strong className="text-white">{page}</strong> of {totalPages}
          </span>

          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:pointer-events-none text-xs font-bold text-slate-300 hover:text-white transition cursor-pointer"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
