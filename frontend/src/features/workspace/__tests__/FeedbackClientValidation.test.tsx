import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ReadingSpacePage } from '../ReadingSpacePage';
import { ArticleReader } from '../ArticleReader';
import { LeftSidebar } from '../LeftSidebar';
import { UnifiedReadingDock } from '../UnifiedReadingDock';
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
      explain: vi.fn(),
      getPassageProof: vi.fn(),
    },
    dictionary: {
      lookup: vi.fn(),
    },
    auth: {
      me: vi.fn(),
      logout: vi.fn(),
    },
  },
}));

describe('QA Validation Suite: Client 4 Feedback Items', () => {
  const mockArticle: Article = {
    id: 'art-feedback-val-1',
    article_id: 'art-feedback-val-1',
    title: 'Cognitive Architecture in Autonomous Robotics',
    source_name: 'IEEE Transactions',
    theme: 'Robotics & AI',
    genre: 'academic',
    summary: 'An exploration of modular perception and motor control in robotics.',
    original_text:
      'Autonomous robots utilize multi-modal sensor fusion to build spatial representations of dynamic environments.\n\nPath planning algorithms ensure deterministic trajectory execution while avoiding unexpected obstacles.\n\nFeedback control loops continually regulate motor actuators to maintain stability.',
    cleaned_text:
      'Autonomous robots utilize multi-modal sensor fusion to build spatial representations of dynamic environments.\n\nPath planning algorithms ensure deterministic trajectory execution while avoiding unexpected obstacles.\n\nFeedback control loops continually regulate motor actuators to maintain stability.',
    word_count: 850,
    status: 'completed',
    stage: 'gold',
    exams: [
      {
        exam_id: 'exam_fb_1',
        title: 'Robotics Cognitive Architecture Exam',
        quizzes: [
          {
            quiz_type: 'multiple_choice',
            question: 'What do autonomous robots utilize for spatial representation?',
            options: ['Multi-modal sensor fusion', 'Analog tape reels', 'Clockwork gears', 'Static maps only'],
            correct_answer: 'Multi-modal sensor fusion',
            explanation: 'Paragraph 1 explains sensor fusion.',
            supporting_text: 'Autonomous robots utilize multi-modal sensor fusion',
          },
        ],
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    workspaceStore.setState({
      article: mockArticle,
      activeTool: null,
      highlightColor: 'amber',
      isZenMode: false,
      highlights: [],
      quizAnswers: {},
      quizSubmitted: false,
      score: 0,
      totalQuestions: 0,
      isTimerRunning: false,
      elapsedSeconds: 0,
      relatedArticles: [],
      activeDictionaryWord: null,
      isDictionaryLoading: false,
    });

    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // FEEDBACK ITEM 1: Smart Ink In-Place Simplification & Eraser Revert
  // ══════════════════════════════════════════════════════════════════════════════

  describe('Feedback Item 1: Selection HUD and Clean ArticleReader', () => {
    it('renders article paragraphs cleanly without smart ink clutter', () => {
      render(<ArticleReader article={mockArticle} />);

      const firstSentence = screen.getByText(
        /Autonomous robots utilize multi-modal sensor fusion/i
      );
      expect(firstSentence).toBeInTheDocument();
      expect(screen.queryByText('💡 Explained')).not.toBeInTheDocument();
    });

    it('confirms LeftSidebar remains clean and empty when idle with zero streaming into left panel', () => {
      const { container } = render(<LeftSidebar article={mockArticle} />);
      expect(container.firstChild).toBeNull();

      // Ensure NO streaming containers or notes containers exist in LeftSidebar
      expect(screen.queryByText(/AI Stream/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Streaming explanation/i)).not.toBeInTheDocument();
    });
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // FEEDBACK ITEM 2: Dictionary Direct Click & Popover Suppression
  // ══════════════════════════════════════════════════════════════════════════════

  describe('Feedback Item 2: Dictionary Direct Click & Popover Suppression', () => {
    it('clicking a word in dictionary mode invokes lookup without showing selection popover HUD', async () => {
      const handleToast = vi.fn();
      workspaceStore.setState({ activeTool: 'dictionary' });

      vi.mocked(api.dictionary.lookup).mockResolvedValueOnce({
        word: 'fusion',
        found: true,
        part_of_speech: 'noun',
        definitions: [
          {
            part_of_speech: 'noun',
            definition: 'The process or result of joining two or more things together to form a single entity.',
            examples: ['A fusion of sensor data.'],
            synonyms: ['blend', 'combination', 'synthesis'],
            antonyms: ['separation'],
          },
        ],
      });

      render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      const textNode = screen.getByText(/Autonomous robots utilize multi-modal sensor fusion/i);
      fireEvent.click(textNode);

      // Verify dictionary lookup was invoked
      await waitFor(() => {
        expect(api.dictionary.lookup).toHaveBeenCalled();
      });

      // Crucial: Selection HUD Popover must NOT be rendered
      expect(screen.queryByRole('toolbar', { name: /Selection Actions HUD/i })).not.toBeInTheDocument();
      expect(screen.queryByText('Mark')).not.toBeInTheDocument();
      expect(screen.queryByText('Explain')).not.toBeInTheDocument();
    });

    it('suppresses selectionchange popover HUD completely when activeTool is dictionary', async () => {
      workspaceStore.setState({ activeTool: 'dictionary' });

      const { container } = render(<ArticleReader article={mockArticle} />);

      const contentContainer = container.querySelector('.select-text')!;
      const mockRange = {
        commonAncestorContainer: contentContainer,
        getBoundingClientRect: () => ({ left: 150, top: 250, width: 60, height: 18 }),
      };

      vi.spyOn(window, 'getSelection').mockReturnValue({
        isCollapsed: false,
        rangeCount: 1,
        getRangeAt: () => mockRange,
        toString: () => 'sensor fusion',
      } as any);

      // Trigger selectionchange
      fireEvent(document, new Event('selectionchange'));

      // Popover HUD must NOT appear when dictionary tool is active
      expect(screen.queryByRole('toolbar', { name: /Selection Actions HUD/i })).not.toBeInTheDocument();
    });

    it('shows HUD in Pointer mode for selection and allows clicking Define button to lookup word and dismiss HUD', async () => {
      workspaceStore.setState({ activeTool: null }); // Pointer mode

      vi.mocked(api.dictionary.lookup).mockResolvedValueOnce({
        word: 'actuators',
        found: true,
        part_of_speech: 'noun',
        definitions: [
          {
            part_of_speech: 'noun',
            definition: 'A device that causes a machine or other device to operate.',
            examples: [],
            synonyms: ['driver', 'motor'],
            antonyms: [],
          },
        ],
      });

      const handleToast = vi.fn();
      const { container } = render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      const contentContainer = container.querySelector('.select-text')!;
      const mockRange = {
        commonAncestorContainer: contentContainer,
        getBoundingClientRect: () => ({ left: 200, top: 300, width: 50, height: 20 }),
      };

      vi.spyOn(window, 'getSelection').mockReturnValue({
        isCollapsed: false,
        rangeCount: 1,
        getRangeAt: () => mockRange,
        toString: () => 'actuators',
      } as any);

      fireEvent(document, new Event('selectionchange'));

      await waitFor(() => {
        expect(screen.getByRole('toolbar', { name: /Selection Actions HUD/i })).toBeInTheDocument();
      });

      const defineBtn = screen.getByRole('button', { name: /Define word/i });
      fireEvent.mouseDown(defineBtn);

      expect(api.dictionary.lookup).toHaveBeenCalledWith('actuators');
      expect(handleToast).toHaveBeenCalledWith('Looking up "actuators" in Dictionary', 'info');

      // HUD is dismissed after clicking Define
      expect(screen.queryByRole('toolbar', { name: /Selection Actions HUD/i })).not.toBeInTheDocument();
    });
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // FEEDBACK ITEM 3: Left Panel Clean Design & WordNet Lexicon Card
  // ══════════════════════════════════════════════════════════════════════════════

  describe('Feedback Item 3: Left Panel Clean Design & WordNet Lexicon Card', () => {
    it('confirms LeftSidebar renders null when idle to maintain distraction-free workspace', () => {
      const { container } = render(<LeftSidebar article={mockArticle} />);
      expect(container.firstChild).toBeNull();
    });

    it('renders clean WordNet dictionary card with ZERO raw asterisks (***), pronunciation button, and synonym chips', () => {
      workspaceStore.setState({
        activeDictionaryWord: {
          word: 'deterministic',
          found: true,
          part_of_speech: 'adjective',
          definitions: [
            {
              part_of_speech: 'adjective',
              definition: 'Relating to the philosophical doctrine that all events are determined by causes external to the will.',
              examples: ['A deterministic computational model.'],
              synonyms: ['predictable', 'causal', 'settled'],
              antonyms: ['random', 'probabilistic'],
            },
          ],
        },
      });

      const { container } = render(<LeftSidebar article={mockArticle} />);

      // Verify Vocabulary header and content
      expect(screen.getByText('Vocabulary Lexicon')).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 4, name: /deterministic/i })).toBeInTheDocument();
      expect(screen.getAllByText(/adjective/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Relating to the philosophical doctrine/i)).toBeInTheDocument();
      expect(screen.getByText('"A deterministic computational model."')).toBeInTheDocument();

      // Synonyms
      expect(screen.getByText('predictable')).toBeInTheDocument();
      expect(screen.getByText('causal')).toBeInTheDocument();
      expect(screen.getByText('settled')).toBeInTheDocument();

      // Pronunciation speak button
      expect(screen.getByLabelText('Listen pronunciation')).toBeInTheDocument();

      // Ensure ZERO raw asterisks *** appear in rendered HTML
      expect(container.innerHTML).not.toContain('***');

      // Test closing dictionary card
      const closeBtn = screen.getByLabelText('Close dictionary card');
      fireEvent.click(closeBtn);
      expect(workspaceStore.getState().activeDictionaryWord).toBeNull();
    });

    it('allows clicking a synonym chip in WordNet card to lookup synonym word', () => {
      workspaceStore.setState({
        activeDictionaryWord: {
          word: 'fusion',
          found: true,
          part_of_speech: 'noun',
          definitions: [
            {
              part_of_speech: 'noun',
              definition: 'The merging of different elements.',
              examples: [],
              synonyms: ['synthesis', 'blend'],
              antonyms: [],
            },
          ],
        },
      });

      render(<LeftSidebar article={mockArticle} />);

      const synthesisChip = screen.getByText('synthesis');
      fireEvent.click(synthesisChip);

      expect(api.dictionary.lookup).toHaveBeenCalledWith('synthesis');
    });
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // FEEDBACK ITEM 4: Workspace Layout & Default Quiz State
  // ══════════════════════════════════════════════════════════════════════════════

  describe('Feedback Item 4: Workspace Layout & Default Quiz State', () => {
    it('defaults to isQuizOpen = false on article load with generous reader width', async () => {
      vi.mocked(api.articles.get).mockResolvedValueOnce({
        status: 'success',
        article: mockArticle,
        related_articles: [],
      });

      const { container } = render(
        <ReadingSpacePage
          articleId="art-feedback-val-1"
          onNavigateHome={vi.fn()}
          onSelectArticle={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(
          screen.getAllByText('Cognitive Architecture in Autonomous Robotics').length
        ).toBeGreaterThan(0);
      });

      // 1. Verify Quiz is handled cleanly via Left AI Study Dock and not cluttering top bar
      expect(screen.queryByText('Show AI Quiz')).not.toBeInTheDocument();
      expect(screen.queryByText('Hide Quiz')).not.toBeInTheDocument();

      // 2. Reader container gets generous width (max-w-4xl)
      const readerWrapper = container.querySelector('.max-w-4xl');
      expect(readerWrapper).toBeInTheDocument();
    });

    it('renders clean full-width reader container when lexicon is not active', async () => {
      vi.mocked(api.articles.get).mockResolvedValueOnce({
        status: 'success',
        article: mockArticle,
        related_articles: [],
      });

      const { container } = render(
        <ReadingSpacePage
          articleId="art-feedback-val-1"
          onNavigateHome={vi.fn()}
          onSelectArticle={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(
          screen.getAllByText('Cognitive Architecture in Autonomous Robotics').length
        ).toBeGreaterThan(0);
      });

      // Reader takes clean 12-col max-w-4xl space
      const reader12Col = container.querySelector('.lg\\:col-span-12');
      expect(reader12Col).toBeInTheDocument();

      // Returns to generous reader and no quiz column
      expect(container.querySelector('.lg\\:col-span-5')).not.toBeInTheDocument();
    });

    it('toggles Zen Mode into centered distraction-free max-w-[76ch] single column', async () => {
      vi.mocked(api.articles.get).mockResolvedValueOnce({
        status: 'success',
        article: mockArticle,
        related_articles: [],
      });

      render(
        <ReadingSpacePage
          articleId="art-feedback-val-1"
          onNavigateHome={vi.fn()}
          onSelectArticle={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(
          screen.getAllByText('Cognitive Architecture in Autonomous Robotics').length
        ).toBeGreaterThan(0);
      });

      // Press 'Z' shortcut to enter Zen mode
      fireEvent.keyDown(window, { key: 'z' });
      expect(workspaceStore.getState().isZenMode).toBe(true);

      expect(screen.getByText('Zen Mode Active')).toBeInTheDocument();
      const main = screen.getByRole('main');
      expect(main.className).toContain('max-w-[76ch]');

      // Exit Zen mode via button
      const exitBtn = screen.getByRole('button', { name: /Exit Zen Mode/i });
      fireEvent.click(exitBtn);
      expect(workspaceStore.getState().isZenMode).toBe(false);
      expect(screen.queryByText('Zen Mode Active')).not.toBeInTheDocument();
    });
  });
});
