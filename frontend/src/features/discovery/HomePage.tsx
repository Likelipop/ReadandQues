import React, { useState, useEffect } from 'react';
import { HeroHotNews } from './HeroHotNews';
import { Recommendations } from './Recommendations';
import { ArticleGrid } from './ArticleGrid';
import { HomepageData } from '../../types';
import { DateFilterOption } from '../../utils/dateFilter';
import { api } from '../../api/client';
import { Loader2 } from 'lucide-react';

interface HomePageProps {
  onSelectArticle: (id: string) => void;
  selectedTheme?: string;
  onSelectTheme?: (theme: string) => void;
  onExploreTopic?: (keyword: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({
  onSelectArticle,
  selectedTheme = 'All',
  onSelectTheme,
  onExploreTopic,
}) => {
  const [data, setData] = useState<HomepageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtered articles state for grid
  const [gridTheme, setGridTheme] = useState(selectedTheme);
  const [gridDateFilter, setGridDateFilter] = useState<DateFilterOption>('all');
  const [gridPage, setGridPage] = useState(1);
  const [gridArticles, setGridArticles] = useState(data?.articles || []);
  const [totalCount, setTotalCount] = useState(data?.total_count || 0);
  const [gridLoading, setGridLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    api.homepage
      .get()
      .then((res) => {
        if (isMounted) {
          setData(res);
          setGridArticles(res.articles || []);
          setTotalCount(res.total_count || 0);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load homepage');
          setLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // When theme changes from navbar or local grid
  useEffect(() => {
    if (selectedTheme !== gridTheme) {
      setGridTheme(selectedTheme);
      setGridPage(1);
    }
  }, [selectedTheme]);

  useEffect(() => {
    if (!data) return;
    setGridLoading(true);
    api.articles
      .list({
        theme: gridTheme,
        date_filter: gridDateFilter,
        page: gridPage,
        limit: 12,
      })
      .then((res) => {
        setGridArticles(res.articles || []);
        setTotalCount(res.total_count || 0);
      })
      .catch(() => {})
      .finally(() => {
        setGridLoading(false);
      });
  }, [gridTheme, gridDateFilter, gridPage, data]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-8 h-8 text-cyber-violet animate-spin" />
        <span className="text-xs text-slate-400 font-medium">
          Loading latest reading materials...
        </span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-md mx-auto my-20 p-8 glass-card text-center space-y-4">
        <div className="text-red-400 text-sm font-bold">Error loading homepage</div>
        <p className="text-xs text-slate-400">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-cyber-violet text-white text-xs font-bold rounded-xl"
        >
          Retry
        </button>
      </div>
    );
  }

  const totalPages = Math.ceil(totalCount / 12);

  return (
    <div className="space-y-16 max-w-7xl mx-auto px-6 py-8">
      {/* 1. Hero Hot News */}
      <HeroHotNews
        articles={data.hero_articles}
        onSelectArticle={onSelectArticle}
      />

      {/* 2. Adaptive Recommendations */}
      {data.recommended_articles && data.recommended_articles.length > 0 && (
        <Recommendations
          articles={data.recommended_articles}
          onSelectArticle={onSelectArticle}
        />
      )}

      {/* 4. Reading Tests Catalog Grid */}
      <ArticleGrid
        articles={gridArticles}
        themes={data.themes}
        selectedTheme={gridTheme}
        onSelectTheme={(t) => {
          setGridTheme(t);
          if (onSelectTheme) onSelectTheme(t);
          setGridPage(1);
        }}
        dateFilter={gridDateFilter}
        onSelectDateFilter={(df) => {
          setGridDateFilter(df);
          setGridPage(1);
        }}
        onSelectArticle={onSelectArticle}
        page={gridPage}
        totalPages={totalPages}
        onPageChange={setGridPage}
        isLoading={gridLoading}
      />
    </div>
  );
};
