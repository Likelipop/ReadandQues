import React, { useState, useEffect } from 'react';
import { Navbar } from './components/common/Navbar';
import { Footer } from './components/common/Footer';
import { TrendingTicker } from './components/common/TrendingTicker';
import { Toast } from './components/common/Toast';
import { HomePage } from './features/discovery/HomePage';
import { AllTestsPage } from './features/discovery/AllTestsPage';
import { ReadingSpacePage } from './features/workspace/ReadingSpacePage';
import { ProfilePage } from './features/auth/ProfilePage';
import { AuthModal } from './features/auth/AuthModal';
import { BottomChatDock } from './features/rag/BottomChatDock';
import { useAuth } from './store';
import { api } from './api/client';
import { NavTheme } from './types';

export default function App() {
  const [currentView, setCurrentView] = useState<'home' | 'all-tests' | 'readspace' | 'profile'>('home');
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [selectedTheme, setSelectedTheme] = useState<string>('All');
  const [navThemes, setNavThemes] = useState<NavTheme[]>([]);
  const [trendingTopics, setTrendingTopics] = useState<Array<{ id: string; title: string }>>([]);

  // Auth modal
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState<'login' | 'register'>('login');

  // Toast
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const { fetchCurrentUser } = useAuth();

  useEffect(() => {
    fetchCurrentUser();

    api.homepage
      .get()
      .then((data) => {
        if (data.nav_themes) setNavThemes(data.nav_themes);
        if (data.trending_topics) setTrendingTopics(data.trending_topics);
      })
      .catch(() => {});
  }, []);

  const handleNavigate = (view: string, articleId?: string) => {
    if (view === 'readspace' && articleId) {
      setSelectedArticleId(articleId);
      setCurrentView('readspace');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (view === 'all-tests') {
      setCurrentView('all-tests');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (view === 'profile') {
      setCurrentView('profile');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      setCurrentView('home');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleOpenAuth = (mode: 'login' | 'register' = 'login') => {
    setAuthModalTab(mode);
    setAuthModalOpen(true);
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast((prev) => (prev?.message === message ? null : prev));
    }, 4500);
  };

  return (
    <div className="min-h-screen bg-obsidian-900 text-slate-100 flex flex-col font-sans selection:bg-cyber-violet/30 selection:text-cyber-cyan">
      {/* 1. Global Navigation Bar */}
      <Navbar
        currentView={currentView}
        onNavigate={handleNavigate}
        onOpenAuth={handleOpenAuth}
        navThemes={navThemes}
        selectedTheme={selectedTheme}
        onSelectTheme={(themeId) => {
          setSelectedTheme(themeId);
          if (currentView !== 'all-tests' && currentView !== 'home') {
            setCurrentView('all-tests');
          }
        }}
        onShowToast={showToast}
      />

      {/* 2. Trending Topics Banner */}
      {currentView === 'home' && trendingTopics.length > 0 && (
        <TrendingTicker
          topics={trendingTopics}
          onSelectArticle={(aid) => handleNavigate('readspace', aid)}
        />
      )}

      {/* 3. Main Dynamic Content View */}
      <div className="flex-1">
        {currentView === 'home' && (
          <HomePage
            onSelectArticle={(aid) => handleNavigate('readspace', aid)}
            selectedTheme={selectedTheme}
            onSelectTheme={setSelectedTheme}
            onExploreTopic={(keyword) => {
              setSelectedTheme('All');
              setCurrentView('all-tests');
            }}
          />
        )}

        {currentView === 'all-tests' && (
          <AllTestsPage
            initialTheme={selectedTheme}
            onSelectArticle={(aid) => handleNavigate('readspace', aid)}
          />
        )}

        {currentView === 'readspace' && selectedArticleId && (
          <ReadingSpacePage
            articleId={selectedArticleId}
            onNavigateHome={() => handleNavigate('home')}
            onSelectArticle={(aid) => handleNavigate('readspace', aid)}
          />
        )}

        {currentView === 'profile' && (
          <ProfilePage
            onShowToast={showToast}
            onOpenAuth={() => handleOpenAuth('login')}
          />
        )}
      </div>

      {/* 4. Global Footer */}
      <Footer
        navThemes={navThemes}
        onSelectTheme={(t) => {
          setSelectedTheme(t);
          setCurrentView('all-tests');
        }}
        onNavigate={handleNavigate}
      />

      {/* 5. VS Code-Style Bottom RAG Chat Dock */}
      <BottomChatDock
        activeArticleId={currentView === 'readspace' ? selectedArticleId || undefined : undefined}
      />

      {/* 6. Global Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialTab={authModalTab}
        onShowToast={showToast}
      />

      {/* 7. Global Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
