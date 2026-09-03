import React, { useState, useEffect } from 'react';
import { ArrowLeft, Loader2, HelpCircle, Minimize2 } from 'lucide-react';
import { Article } from '../../types';
import { api } from '../../api/client';
import { useWorkspace } from '../../store';
import { LeftSidebar } from './LeftSidebar';
import { ArticleReader } from './ArticleReader';
import { WorkspaceToolbar } from './WorkspaceToolbar';
import { QuizSidebar } from './QuizSidebar';
import { RelatedArticles } from './RelatedArticles';

interface ReadingSpacePageProps {
  articleId: string;
  onNavigateHome: () => void;
  onSelectArticle: (id: string) => void;
  onShowToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const ReadingSpacePage: React.FC<ReadingSpacePageProps> = ({
  articleId,
  onNavigateHome,
  onSelectArticle,
  onShowToast,
}) => {
  const [article, setLocalArticle] = useState<Article | null>(null);
  const [related, setRelated] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isQuizOpen, setIsQuizOpen] = useState(false);
  const [isLeftPanelOpen, setIsLeftPanelOpen] = useState(false);

  const {
    setArticle: setStoreArticle,
    activeDictionaryWord,
    isDictionaryLoading,
    isZenMode,
    toggleZenMode,
  } = useWorkspace();

  // Automatically open Left Panel on mobile/tablet when a word is looked up (when not in Zen mode)
  useEffect(() => {
    if (!isZenMode && activeDictionaryWord) {
      setIsLeftPanelOpen(true);
    }
  }, [activeDictionaryWord, isZenMode]);

  const fetchArticle = () => {
    setLoading(true);
    setError(null);
    api.articles
      .get(articleId)
      .then((res) => {
        setLocalArticle(res.article);
        setRelated(res.related_articles || []);
        setStoreArticle(res.article);
        setLoading(false);
      })
      .catch((err: any) => {
        setError(err.message || 'Failed to load article');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchArticle();
  }, [articleId]);

  const handleScrollToParagraph = (pIndex: number) => {
    const el = document.getElementById(`paragraph-${pIndex}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('ring-2', 'ring-indigo-400', 'ring-offset-2', 'ring-offset-slate-950');
      setTimeout(() => {
        el.classList.remove('ring-2', 'ring-indigo-400', 'ring-offset-2', 'ring-offset-slate-950');
      }, 1500);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        <span className="text-xs text-slate-400 font-medium">
          Retrieving reading workspace & AI intelligence...
        </span>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-md mx-auto my-20 p-8 glass-card text-center space-y-4">
        <div className="text-red-400 text-sm font-bold">Article not found</div>
        <p className="text-xs text-slate-400">{error || 'Requested article could not be loaded.'}</p>
        <button
          onClick={onNavigateHome}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl cursor-pointer"
        >
          Return to Homepage
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-100px)] flex flex-col transition-all duration-300">
      {/* Workspace Sub-header */}
      <div className="border-b border-white/5 bg-slate-950/60 px-4 sm:px-6 py-2.5 sticky top-16 z-30 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={onNavigateHome}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-400 hover:text-white transition shrink-0 cursor-pointer bg-white/5 hover:bg-white/10 px-2.5 py-1 rounded-lg"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
            <div className="h-4 w-px bg-white/10" />
            <h2 className="text-xs sm:text-sm font-bold text-white truncate max-w-lg">
              {article.title}
            </h2>
            {isZenMode && (
              <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Zen Mode Active
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isZenMode ? (
              <button
                onClick={toggleZenMode}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30 transition cursor-pointer"
                title="Exit Zen Mode (Z)"
              >
                <Minimize2 className="w-3.5 h-3.5" />
                <span>Exit Zen Mode</span>
              </button>
            ) : (
              <>
                {/* Toggle Left Sidebar on mobile/tablet (only when dictionary word is active) */}
                {Boolean(activeDictionaryWord || isDictionaryLoading) && (
                  <button
                    onClick={() => setIsLeftPanelOpen(!isLeftPanelOpen)}
                    className="lg:hidden flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 border border-cyan-500/30 transition cursor-pointer"
                  >
                    <span>{isLeftPanelOpen ? 'Hide Lexicon' : '📖 Dictionary Lexicon'}</span>
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Workspace Area */}
      {isZenMode ? (
        /* Zen Mode: Centered distraction-free 76ch column */
        <main className="flex-1 w-full max-w-[76ch] mx-auto px-4 sm:px-6 py-8 relative transition-all duration-300 animate-in fade-in duration-300">
          <WorkspaceToolbar
            isQuizOpen={false}
            onToggleQuiz={() => setIsQuizOpen(!isQuizOpen)}
          />
          <div className="flex flex-col space-y-8">
            <ArticleReader
              article={article}
              onShowToast={onShowToast}
              onToggleQuiz={() => setIsQuizOpen(!isQuizOpen)}
            />
          </div>
        </main>
      ) : (
        /* Standard Workspace Layout */
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 relative transition-all duration-300">
          {/* Floating Unified AuraDock Toolbar */}
          <WorkspaceToolbar
            isQuizOpen={isQuizOpen}
            onToggleQuiz={() => setIsQuizOpen(!isQuizOpen)}
          />

          {/* Left Column: WordNet Dictionary Card (Visible only when dictionary lookup is active) */}
          {(activeDictionaryWord || isDictionaryLoading) && (
            <div
              className={`${
                isLeftPanelOpen ? 'block' : 'hidden'
              } ${isQuizOpen ? 'lg:hidden' : 'lg:block lg:col-span-3'}`}
            >
              <div className="sticky top-32 max-h-[calc(100vh-160px)] overflow-y-auto custom-scrollbar pr-2">
                <LeftSidebar
                  article={article}
                  onScrollToParagraph={handleScrollToParagraph}
                />
              </div>
            </div>
          )}

          {/* Center / Reading Column: Reading Passage & Recommendations */}
          <div
            className={`${
              isQuizOpen
                ? 'lg:col-span-7'
                : activeDictionaryWord || isDictionaryLoading
                ? 'lg:col-span-9'
                : 'lg:col-span-12 max-w-4xl mx-auto w-full'
            } flex flex-col space-y-8 min-w-0 transition-all duration-300`}
          >
            <ArticleReader
              article={article}
              onShowToast={onShowToast}
              onToggleQuiz={() => setIsQuizOpen(!isQuizOpen)}
            />
            <RelatedArticles
              articles={related}
              onSelectArticle={onSelectArticle}
            />
          </div>

          {/* Right Column: Timed AI Quiz Runner (Generous 42% 5-column width) */}
          {isQuizOpen && (
            <div className="lg:col-span-5 flex flex-col animate-in fade-in duration-200">
              <div className="sticky top-32 h-[calc(100vh-160px)]">
                <QuizSidebar
                  article={article}
                  onRefreshArticle={fetchArticle}
                />
              </div>
            </div>
          )}
        </main>
      )}
    </div>
  );
};
