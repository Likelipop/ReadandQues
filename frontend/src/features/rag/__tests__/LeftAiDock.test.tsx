import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LeftAiDock } from '../LeftAiDock';
import { authStore } from '../../../store';

// Mock useSSEStream hook
vi.mock('../../../hooks/useSSEStream', () => ({
  useSSEStream: () => ({
    isStreaming: false,
    streamedText: '',
    citations: [],
    quizData: [],
    actionType: 'chat',
    intent: 'rag',
    error: null,
    startStream: vi.fn(),
  }),
}));

describe('LeftAiDock', () => {
  beforeEach(() => {
    // Reset auth store to unauthenticated guest by default
    authStore.setState({
      user: null,
      isLoading: false,
      error: null,
    });
  });

  describe('Unauthenticated Guest State', () => {
    it('renders collapsed trigger tab with lock indicator', () => {
      render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
      expect(screen.getByRole('complementary', { name: 'AI Study Dock Tab' })).toBeInTheDocument();
      expect(screen.getByText('AI Study Dock')).toBeInTheDocument();
      expect(screen.getByTestId('ai-dock-lock-badge')).toBeInTheDocument();
    });

    it('displays Auth Gate card and sign-in placeholder when opened as guest', () => {
      render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
      const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
      fireEvent.click(tab);

      expect(screen.getByRole('dialog', { name: 'AI Study Dock' })).toBeInTheDocument();
      expect(screen.getByTestId('ai-dock-auth-gate')).toBeInTheDocument();
      expect(screen.getByText('Sign In to Unlock AI Study Assistant')).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText('Sign in to chat with AI Study Assistant...')
      ).toBeInTheDocument();
    });

    it('triggers onOpenAuth when clicking Sign In button in Auth Gate', () => {
      const handleOpenAuth = vi.fn();
      render(
        <LeftAiDock
          activeArticleId="test-1"
          pageContext="readspace"
          onOpenAuth={handleOpenAuth}
        />
      );
      const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
      fireEvent.click(tab);

      const signInBtn = screen.getByRole('button', { name: /Sign In Now/i });
      fireEvent.click(signInBtn);
      expect(handleOpenAuth).toHaveBeenCalledWith('login');
    });

    it('triggers onOpenAuth when clicking Quick Action buttons (Quiz / Summarize)', () => {
      const handleOpenAuth = vi.fn();
      const handleShowToast = vi.fn();
      render(
        <LeftAiDock
          activeArticleId="test-1"
          pageContext="readspace"
          onOpenAuth={handleOpenAuth}
          onShowToast={handleShowToast}
        />
      );
      const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
      fireEvent.click(tab);

      const quizBtn = screen.getByRole('button', { name: /^Quiz$/i });
      fireEvent.click(quizBtn);
      expect(handleOpenAuth).toHaveBeenCalledWith('login');
    });
  });

  describe('Authenticated Member State', () => {
    beforeEach(() => {
      authStore.setState({
        user: {
          id: 1,
          username: 'member_user',
          email: 'member@example.com',
          is_authenticated: true,
          stars: 10,
        },
        isLoading: false,
        error: null,
      });
    });

    it('renders collapsed tab without lock badge', () => {
      render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
      expect(screen.queryByTestId('ai-dock-lock-badge')).not.toBeInTheDocument();
    });

    it('expands panel with full active chat input and no auth gate', () => {
      render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
      const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
      fireEvent.click(tab);

      expect(screen.getByRole('dialog', { name: 'AI Study Dock' })).toBeInTheDocument();
      expect(screen.queryByTestId('ai-dock-auth-gate')).not.toBeInTheDocument();
      expect(
        screen.getByPlaceholderText('Ask about this article, words, or create a quiz...')
      ).toBeInTheDocument();
    });

    it('allows closing expanded dock via close button', () => {
      render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
      const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
      fireEvent.click(tab);

      expect(screen.getByRole('dialog', { name: 'AI Study Dock' })).toBeInTheDocument();

      const closeBtn = screen.getByLabelText('Collapse Dock');
      fireEvent.click(closeBtn);

      expect(screen.queryByRole('dialog', { name: 'AI Study Dock' })).not.toBeInTheDocument();
      expect(screen.getByRole('complementary', { name: 'AI Study Dock Tab' })).toBeInTheDocument();
    });

    it('resets chat history when reset button is clicked', () => {
      render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
      const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
      fireEvent.click(tab);

      const resetBtn = screen.getByLabelText('Clear chat history');
      fireEvent.click(resetBtn);

      expect(screen.getByText(/AI Study Dock reset/i)).toBeInTheDocument();
    });
  });
});
