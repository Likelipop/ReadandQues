import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BottomChatDock } from '../BottomChatDock';

// Mock useSSEStream hook
vi.mock('../../hooks/useSSEStream', () => ({
  useSSEStream: () => ({
    isStreaming: false,
    streamedText: '',
    citations: [],
    error: null,
    startStream: vi.fn(),
  }),
}));

describe('BottomChatDock', () => {
  it('renders collapsed dock bar at bottom with placeholder and shortcut prompt initially', () => {
    render(<BottomChatDock activeArticleId="test-1" />);
    expect(
      screen.getByText('Ask AI Study Dock anything about news & comprehension...')
    ).toBeInTheDocument();
    expect(screen.getByText('Ctrl')).toBeInTheDocument();
    expect(screen.getByText('K')).toBeInTheDocument();
  });

  it('expands panel when bottom bar is clicked', () => {
    render(<BottomChatDock activeArticleId="test-1" />);
    const bar = screen.getByText('Ask AI Study Dock anything about news & comprehension...');
    fireEvent.click(bar);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('AI Study Dock')).toBeInTheDocument();
    expect(screen.getByText('Hybrid RAG + Cross-Encoder')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('Ask a question about current news or reading comprehension...')
    ).toBeInTheDocument();
  });

  it('allows collapsing expanded dock', () => {
    render(<BottomChatDock activeArticleId="test-1" />);
    const bar = screen.getByText('Ask AI Study Dock anything about news & comprehension...');
    fireEvent.click(bar);

    expect(screen.getByRole('dialog')).toBeInTheDocument();

    const collapseBtn = screen.getByLabelText('Collapse Dock');
    fireEvent.click(collapseBtn);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(
      screen.getByText('Ask AI Study Dock anything about news & comprehension...')
    ).toBeInTheDocument();
  });

  it('toggles fullscreen height mode', () => {
    render(<BottomChatDock activeArticleId="test-1" />);
    const bar = screen.getByText('Ask AI Study Dock anything about news & comprehension...');
    fireEvent.click(bar);

    const fullHeightBtn = screen.getByLabelText('Expand full height');
    fireEvent.click(fullHeightBtn);

    expect(screen.getByLabelText('Exit full height')).toBeInTheDocument();
  });

  it('resets chat history when reset button is clicked', () => {
    render(<BottomChatDock activeArticleId="test-1" />);
    const bar = screen.getByText('Ask AI Study Dock anything about news & comprehension...');
    fireEvent.click(bar);

    const resetBtn = screen.getByLabelText('Clear chat history');
    fireEvent.click(resetBtn);

    expect(screen.getByText(/Chat history reset/i)).toBeInTheDocument();
  });
});
