import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StudyBuddyWidget } from '../StudyBuddyWidget';

describe('StudyBuddyWidget', () => {
  it('renders closed toggle button initially', () => {
    render(<StudyBuddyWidget activeArticleId="test-1" />);
    const openButton = screen.getByLabelText('Open AI Study Buddy Chat');
    expect(openButton).toBeInTheDocument();
    expect(screen.getByText('Study Buddy AI')).toBeInTheDocument();
  });

  it('opens dialog when button is clicked', () => {
    render(<StudyBuddyWidget activeArticleId="test-1" />);
    const openButton = screen.getByLabelText('Open AI Study Buddy Chat');
    fireEvent.click(openButton);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Study Buddy RAG')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument();
  });

  it('allows closing dialog', () => {
    render(<StudyBuddyWidget activeArticleId="test-1" />);
    const openButton = screen.getByLabelText('Open AI Study Buddy Chat');
    fireEvent.click(openButton);

    const closeButton = screen.getByLabelText('Close Chat');
    fireEvent.click(closeButton);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
