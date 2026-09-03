import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LeftAiDock } from '../LeftAiDock';

// Mock useSSEStream hook
vi.mock('../../hooks/useSSEStream', () => ({
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
  it('renders collapsed trigger tab on the left initially', () => {
    render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
    expect(screen.getByRole('complementary', { name: 'AI Study Dock Tab' })).toBeInTheDocument();
    expect(screen.getByText('AI Study Dock')).toBeInTheDocument();
    expect(screen.getByText('Ctrl+K')).toBeInTheDocument();
  });

  it('expands panel when left tab is clicked', () => {
    render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
    const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
    fireEvent.click(tab);

    expect(screen.getByRole('dialog', { name: 'AI Study Dock' })).toBeInTheDocument();
    expect(screen.getByText('Explainer • Hybrid RAG • Quiz')).toBeInTheDocument();
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

  it('renders Quick Action Dock buttons (Quiz, Summarize) in chat mode', () => {
    render(<LeftAiDock activeArticleId="test-1" pageContext="readspace" />);
    const tab = screen.getByRole('complementary', { name: 'AI Study Dock Tab' });
    fireEvent.click(tab);

    expect(screen.getByRole('button', { name: /^Quiz$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Summarize$/i })).toBeInTheDocument();
  });
});
