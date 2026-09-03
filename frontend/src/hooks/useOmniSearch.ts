import { useState, useEffect, useRef, useCallback } from 'react';
import { SearchResultItem } from '../types';
import { api } from '../api/client';
import { useAuth } from '../store';

export type SearchMode = 'bm25' | 'ai';

export function isUrl(text: string): boolean {
  return /^(https?:\/\/)/i.test(text) || /^www\./i.test(text);
}

export function useOmniSearch(onNavigateToArticle?: (id: string) => void) {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('bm25');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const { deductStar } = useAuth();
  const typingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const performSearch = useCallback(
    async (text: string) => {
      if (!text.trim() || isUrl(text)) {
        setResults([]);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const res =
          searchMode === 'bm25'
            ? await api.search.keyword(text)
            : await api.search.semantic(text);

        if (res.status === 'success') {
          setResults(res.results || []);
          setIsDropdownOpen(true);
        } else {
          setResults([]);
        }
      } catch (err: any) {
        setError(err.message || 'Error searching articles');
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    },
    [searchMode]
  );

  useEffect(() => {
    if (typingTimer.current) clearTimeout(typingTimer.current);

    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setIsDropdownOpen(false);
      setIsLoading(false);
      return;
    }

    if (isUrl(trimmed)) {
      setResults([]);
      setIsDropdownOpen(false);
      setIsLoading(false);
      return;
    }

    typingTimer.current = setTimeout(() => {
      performSearch(trimmed);
    }, 350);

    return () => {
      if (typingTimer.current) clearTimeout(typingTimer.current);
    };
  }, [query, performSearch]);

  const handleImport = async (urlToImport: string) => {
    setIsImporting(true);
    setError(null);
    try {
      const res = await api.articles.import(urlToImport);
      deductStar();
      if (res.article_id && onNavigateToArticle) {
        onNavigateToArticle(res.article_id);
      }
      setQuery('');
      setIsDropdownOpen(false);
      return res;
    } catch (err: any) {
      setError(err.message || 'Failed to import article');
      throw err;
    } finally {
      setIsImporting(false);
    }
  };

  return {
    query,
    setQuery,
    searchMode,
    setSearchMode,
    results,
    isLoading,
    isImporting,
    error,
    isDropdownOpen,
    setIsDropdownOpen,
    handleImport,
    performSearch,
  };
}
