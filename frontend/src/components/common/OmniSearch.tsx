import React, { useRef, useEffect } from 'react';
import { Search, Link as LinkIcon, Sparkles, Loader2 } from 'lucide-react';
import { useOmniSearch, isUrl } from '../../hooks/useOmniSearch';
import { SearchResultItem } from '../../types';

interface OmniSearchProps {
  onSelectArticle: (id: string) => void;
  onShowToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const OmniSearch: React.FC<OmniSearchProps> = ({
  onSelectArticle,
  onShowToast,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
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
  } = useOmniSearch(onSelectArticle);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [setIsDropdownOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = query.trim();
    if (!text) return;

    if (isUrl(text)) {
      try {
        if (onShowToast) onShowToast('Importing news article...', 'info');
        const res = await handleImport(text);
        if (onShowToast) {
          onShowToast(
            res.is_new ? 'Article successfully imported!' : 'Article loaded from library.',
            'success'
          );
        }
      } catch (err: any) {
        if (onShowToast) onShowToast(err.message || 'Import failed', 'error');
      }
    } else if (results.length > 0) {
      const topHit = results[0];
      onSelectArticle(topHit.id || topHit.article_id || '');
      setIsDropdownOpen(false);
      setQuery('');
    }
  };

  const isCurrentUrl = isUrl(query.trim());

  return (
    <div ref={containerRef} className="relative w-full max-w-lg">
      <form onSubmit={handleSubmit} className="relative flex items-center w-full">
        {/* Leading icon */}
        <div className="absolute left-3.5 text-slate-400 select-none pointer-events-none">
          {isCurrentUrl ? (
            <LinkIcon className="w-4 h-4 text-cyber-cyan animate-bounce" />
          ) : (
            <Search className="w-4 h-4 text-slate-400" />
          )}
        </div>

        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={
            isCurrentUrl
              ? 'Press Enter to import news URL...'
              : 'Paste URL to import, or search articles...'
          }
          disabled={isImporting}
          className="w-full bg-white/[0.05] hover:bg-white/[0.08] focus:bg-white/[0.09] text-xs md:text-sm text-white font-medium rounded-full py-2 pl-10 pr-24 border border-white/10 focus:border-cyber-violet focus:ring-2 focus:ring-cyber-violet/20 transition-all outline-none"
        />

        {/* Search Mode Toggle (KW vs AI) */}
        {!isCurrentUrl && query.trim() && (
          <div className="absolute right-9 flex items-center gap-0.5 bg-black/40 p-0.5 rounded-full border border-white/10">
            <button
              type="button"
              onClick={() => setSearchMode('bm25')}
              className={`px-1.5 py-0.5 text-[10px] font-bold rounded-full transition ${
                searchMode === 'bm25'
                  ? 'bg-cyber-violet text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              KW
            </button>
            <button
              type="button"
              onClick={() => setSearchMode('ai')}
              className={`px-1.5 py-0.5 text-[10px] font-bold rounded-full transition flex items-center gap-0.5 ${
                searchMode === 'ai'
                  ? 'bg-cyber-cyan text-slate-900 font-black shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-2.5 h-2.5" /> AI
            </button>
          </div>
        )}

        {/* Spinner */}
        {(isLoading || isImporting) && (
          <div className="absolute right-3.5 flex items-center justify-center">
            <Loader2 className="w-4 h-4 text-cyber-cyan animate-spin" />
          </div>
        )}
      </form>

      {/* Results Dropdown */}
      {isDropdownOpen && !isCurrentUrl && (
        <div className="absolute top-full mt-2 left-0 right-0 z-50 glass-card glow-violet rounded-xl overflow-hidden max-h-[380px] overflow-y-auto border border-white/10 shadow-2xl animate-in fade-in zoom-95 duration-150">
          {error && (
            <div className="p-3 text-xs text-red-300 bg-red-500/10 border-b border-red-500/20">
              {error}
            </div>
          )}

          {results.length === 0 && !isLoading && (
            <div className="p-4 text-center text-xs text-slate-400">
              No matching articles found for "{query}".
            </div>
          )}

          {results.map((res: SearchResultItem) => {
            const articleId = res.id || res.article_id || '';
            return (
              <button
                key={articleId}
                type="button"
                onClick={() => {
                  onSelectArticle(articleId);
                  setIsDropdownOpen(false);
                  setQuery('');
                }}
                className="w-full text-left p-3 border-b border-white/5 hover:bg-white/[0.07] transition flex flex-col gap-1 cursor-pointer"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-xs text-slate-100 line-clamp-1 hover:text-cyber-cyan transition">
                    {res.title}
                  </span>
                  {res.similarity !== undefined && (
                    <span className="text-[10px] font-bold text-cyber-emerald bg-cyber-emerald/10 px-1.5 py-0.2 rounded shrink-0">
                      {res.similarity}% match
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                  <span className="bg-white/10 text-slate-300 px-1.5 py-0.5 rounded uppercase font-semibold">
                    {res.source || res.source_name || 'News'}
                  </span>
                  {res.theme && <span>• {res.theme}</span>}
                  {res.date && <span>• {res.date}</span>}
                </div>

                {res.snippet && (
                  <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">
                    {res.snippet}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
