import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ReadingSpacePage } from '../ReadingSpacePage';
import { QuizSidebar } from '../QuizSidebar';
import { SmartParaphraseModal } from '../SmartParaphraseModal';
import { StudyBuddyWidget } from '../../rag/StudyBuddyWidget';
import { Article } from '../../../types';
import { api } from '../../../api/client';
import { workspaceStore } from '../../../store';

vi.mock('../../../api/client', () => ({
  api: {
    articles: {
      get: vi.fn(),
      status: vi.fn(),
      submitExam: vi.fn(),
      saveMarkers: vi.fn(),
      smartParaphrase: vi.fn(),
      getPassageProof: vi.fn(),
    },
  },
}));

describe('Reading Workspace UI/UX Test Suite (Senior QA)', () => {
  const mockArticle: Article = {
    id: 'art-workspace-qa-1',
    article_id: 'art-workspace-qa-1',
    title: 'The Evolution of Neural Computing',
    source_name: 'MIT Technology Review',
    theme: 'Technology',
    genre: 'academic',
    summary: 'Neural networks and cognitive computing paradigms.',
    original_text: 'Deep neural networks mimic biological synapses to process non-linear representations.\n\nHardware accelerators like TPUs enable massive parallel computations.',
    cleaned_text: 'Deep neural networks mimic biological synapses to process non-linear representations.\n\nHardware accelerators like TPUs enable massive parallel computations.',
    word_count: 550,
    status: 'completed',
    stage: 'gold',
    exams: [
      {
        exam_id: 'exam_qa_1',
        title: 'Neural Computing Reading Exam',
        quizzes: [
          {
            quiz_type: 'multiple_choice',
            question: 'What do deep neural networks mimic?',
            options: ['Biological synapses', 'Digital clocks', 'Magnetic disks', 'Optical prisms'],
            correct_answer: 'Biological synapses',
            explanation: 'The passage explicitly states they mimic biological synapses.',
            supporting_text: 'Deep neural networks mimic biological synapses',
          },
          {
            quiz_type: 'multiple_choice',
            question: 'What hardware accelerator enables massive parallel computations?',
            options: ['TPUs', 'Sound cards', 'Floppy drives', 'Ethernet cables'],
            correct_answer: 'TPUs',
            explanation: 'Paragraph 2 identifies hardware accelerators like TPUs.',
            supporting_text: 'Hardware accelerators like TPUs',
          },
        ],
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    workspaceStore.setState({
      article: null,
      quizAnswers: {},
      quizSubmitted: false,
      score: 0,
      totalQuestions: 0,
      activeTool: null,
      highlights: [],
      elapsedSeconds: 0,
    });
  });

  // ── 1. ReadingSpace Layout & Navigation UX ─────────────────────────────────

  it('renders ReadingSpacePage with loading state then loads article content', async () => {
    vi.mocked(api.articles.get).mockResolvedValueOnce({
      status: 'success',
      article: mockArticle,
      related_articles: [],
    });

    const handleNavigateHome = vi.fn();
    const handleSelectArticle = vi.fn();

    render(
      <ReadingSpacePage
        articleId="art-workspace-qa-1"
        onNavigateHome={handleNavigateHome}
        onSelectArticle={handleSelectArticle}
      />
    );

    expect(screen.getByText(/Retrieving reading workspace & AI intelligence/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText('The Evolution of Neural Computing').length).toBeGreaterThan(0);
    });

    expect(screen.getByText('MIT Technology Review • 550 words')).toBeInTheDocument();
    expect(screen.getByText(/Deep neural networks mimic biological synapses/i)).toBeInTheDocument();
  });

  it('navigates back home when clicking back button', async () => {
    vi.mocked(api.articles.get).mockResolvedValueOnce({
      status: 'success',
      article: mockArticle,
      related_articles: [],
    });

    const handleNavigateHome = vi.fn();
    render(
      <ReadingSpacePage
        articleId="art-workspace-qa-1"
        onNavigateHome={handleNavigateHome}
        onSelectArticle={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getAllByText('The Evolution of Neural Computing').length).toBeGreaterThan(0);
    });

    const backBtn = screen.getByRole('button', { name: /^Back$/i });
    fireEvent.click(backBtn);
    expect(handleNavigateHome).toHaveBeenCalled();
  });

  // ── 2. Interactive Quiz Sidebar UX ──────────────────────────────────────────

  it('allows answering questions and submitting quiz attempt with instant score feedback', async () => {
    vi.mocked(api.articles.submitExam).mockResolvedValueOnce({
      status: 'success',
      id: 'att-1234',
      related_articles: [],
    });

    workspaceStore.setState({ article: mockArticle });

    render(<QuizSidebar article={mockArticle} />);

    expect(screen.getByText('What do deep neural networks mimic?')).toBeInTheDocument();
    expect(screen.getByText('Biological synapses')).toBeInTheDocument();

    const option1 = screen.getByText('Biological synapses');
    fireEvent.click(option1);

    const option2 = screen.getByText('TPUs');
    fireEvent.click(option2);

    const submitBtn = screen.getByRole('button', { name: /Submit Exam Attempt/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Score: 2 \/ 2/i)).toBeInTheDocument();
    });
  });

  // ── 3. Smart Paraphrase Modal UX ────────────────────────────────────

  it('renders SmartParaphraseModal with simplified text and closes on click', async () => {
    const handleClose = vi.fn();
    vi.mocked(api.articles.smartParaphrase).mockResolvedValueOnce({
      status: 'success',
      original_text: 'Deep neural networks mimic biological synapses',
      paraphrased_text: 'Advanced AI systems copy the way human brain cells connect',
      explanation: "Simplified 'mimic biological synapses' to 'copy how brain cells connect'.",
      expanded_text: 'Deep neural networks mimic biological synapses',
    });

    render(
      <SmartParaphraseModal
        articleId="art-workspace-qa-1"
        selectedText="Deep neural networks mimic biological synapses"
        onClose={handleClose}
      />
    );

    expect(screen.getByRole('dialog', { name: /Smart Paraphrase Popover/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByText('Advanced AI systems copy the way human brain cells connect')
      ).toBeInTheDocument();
    });

    expect(screen.getByText(/Simplified 'mimic biological synapses'/i)).toBeInTheDocument();

    const closeBtn = screen.getByLabelText(/Close paraphrase popover/i);
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalled();
  });

  // ── 4. StudyBuddy AI RAG Chat Widget UX ─────────────────────────────────────

  it('opens and closes StudyBuddy RAG drawer and handles input typing', () => {
    render(<StudyBuddyWidget activeArticleId="art-workspace-qa-1" />);

    const openBtn = screen.getByLabelText('Open AI Study Buddy Chat');
    fireEvent.click(openBtn);

    expect(screen.getByText('Study Buddy RAG')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Explain TPUs in simple terms' } });
    expect(input).toHaveValue('Explain TPUs in simple terms');

    const closeBtn = screen.getByLabelText('Close Chat');
    fireEvent.click(closeBtn);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
