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

  describe('Feedback Item 1: Smart Ink In-Place Explanation & Eraser Revert', () => {
    it('explains sentence directly in paragraph with 💡 Explained badge and ↺ Original chip when Smart Ink is active', async () => {
      vi.mocked(api.articles.explain).mockResolvedValueOnce({
        status: 'success',
        phrase: 'Autonomous robots utilize multi-modal sensor fusion to build spatial representations of dynamic environments.',
        summary: 'Sensor fusion robotics explanation.',
        detailed_explanation: 'Self-driving robots combine data from cameras and sensors to map changing surroundings.',
        simplified_version: 'Robots use sensors to see.',
        key_terms: [],
      });

      const handleToast = vi.fn();
      workspaceStore.setState({ activeTool: 'smart_ink' });

      render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      const firstSentence = screen.getByText(
        /Autonomous robots utilize multi-modal sensor fusion/i
      );
      expect(firstSentence).toBeInTheDocument();

      // Click the sentence with Smart Ink active
      fireEvent.click(firstSentence);

      expect(handleToast).toHaveBeenCalledWith(
        '✨ Explaining with Smart Ink...',
        'info'
      );

      // Verify API was called with the phrase and paragraph context
      expect(api.articles.explain).toHaveBeenCalledWith(
        'art-feedback-val-1',
        expect.objectContaining({
          phrase: expect.stringContaining('Autonomous robots utilize multi-modal sensor fusion'),
        })
      );

      // Verify in-place explained text, badge, and restore button appear
      await waitFor(() => {
        expect(
          screen.getByText(
            'Self-driving robots combine data from cameras and sensors to map changing surroundings.'
          )
        ).toBeInTheDocument();
        expect(screen.getByText('💡 Explained')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Restore original sentence/i })).toBeInTheDocument();
      });

      expect(handleToast).toHaveBeenCalledWith('Contextual explanation generated!', 'success');
    });

    it('reverts explained sentence to original text when clicking ↺ Original chip', async () => {
      vi.mocked(api.articles.explain).mockResolvedValueOnce({
        status: 'success',
        phrase: 'Autonomous robots utilize multi-modal sensor fusion to build spatial representations of dynamic environments.',
        summary: 'Summary',
        detailed_explanation: 'Robots combine sensors to map rooms.',
        simplified_version: 'Robots use sensors.',
        key_terms: [],
      });

      const handleToast = vi.fn();
      workspaceStore.setState({ activeTool: 'smart_ink' });

      render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      // Explain sentence
      const firstSentence = screen.getByText(/Autonomous robots utilize multi-modal sensor fusion/i);
      fireEvent.click(firstSentence);

      await waitFor(() => {
        expect(screen.getByText('💡 Explained')).toBeInTheDocument();
      });

      // Click "Original" restore button
      const restoreBtn = screen.getByRole('button', { name: /Restore original sentence/i });
      fireEvent.click(restoreBtn);

      // Verify restored to original text and badge removed
      await waitFor(() => {
        expect(screen.queryByText('💡 Explained')).not.toBeInTheDocument();
        expect(screen.queryByText('Robots combine sensors to map rooms.')).not.toBeInTheDocument();
        expect(
          screen.getByText(/Autonomous robots utilize multi-modal sensor fusion/i)
        ).toBeInTheDocument();
      });

      expect(handleToast).toHaveBeenCalledWith('Restored original sentence', 'info');
    });

    it('reverts explained sentence when clicked with Eraser tool active', async () => {
      vi.mocked(api.articles.explain).mockResolvedValueOnce({
        status: 'success',
        phrase: 'Autonomous robots utilize multi-modal sensor fusion to build spatial representations of dynamic environments.',
        summary: 'Summary',
        detailed_explanation: 'Robots combine sensors to map rooms.',
        simplified_version: 'Robots use sensors.',
        key_terms: [],
      });

      const handleToast = vi.fn();
      workspaceStore.setState({ activeTool: 'smart_ink' });

      const { rerender } = render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      // 1. Explain sentence with Smart Ink
      fireEvent.click(screen.getByText(/Autonomous robots utilize multi-modal sensor fusion/i));

      await waitFor(() => {
        expect(screen.getByText('💡 Explained')).toBeInTheDocument();
      });

      // 2. Switch to Eraser tool
      workspaceStore.setState({ activeTool: 'eraser' });
      rerender(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      // 3. Click the explained sentence with Eraser
      const explainedContainer = screen.getByText('Robots combine sensors to map rooms.').closest('span');
      expect(explainedContainer).toBeInTheDocument();
      fireEvent.click(explainedContainer!);

      // Verify restored
      await waitFor(() => {
        expect(screen.queryByText('💡 Explained')).not.toBeInTheDocument();
        expect(screen.queryByText('Robots combine sensors to map rooms.')).not.toBeInTheDocument();
        expect(
          screen.getByText(/Autonomous robots utilize multi-modal sensor fusion/i)
        ).toBeInTheDocument();
      });
      expect(handleToast).toHaveBeenCalledWith('Restored original sentence', 'info');
    });

    it('confirms LeftSidebar remains clean with zero streaming into left panel', () => {
      render(<LeftSidebar article={mockArticle} />);

      // LeftSidebar should show Overview, Section Jumps, and WordNet dictionary promo
      expect(screen.getByText('Robotics & AI')).toBeInTheDocument();
      expect(screen.getByText(/Passage Sections \(3\)/)).toBeInTheDocument();
      expect(screen.getByText(/Interactive WordNet Dictionary/)).toBeInTheDocument();

      // Ensure NO streaming containers or notes containers exist in LeftSidebar
      expect(screen.queryByText(/AI Stream/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Streaming explanation/i)).not.toBeInTheDocument();
    });

    it('gracefully handles offline/network failure with fallback in-place explanation', async () => {
      vi.mocked(api.articles.explain).mockRejectedValueOnce(new Error('Network error'));

      const handleToast = vi.fn();
      workspaceStore.setState({ activeTool: 'smart_ink' });

      render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      const secondSentence = screen.getByText(/Path planning algorithms ensure deterministic trajectory/i);
      fireEvent.click(secondSentence);

      await waitFor(() => {
        expect(screen.getByText(/💡 Explanation: Path planning algorithms/i)).toBeInTheDocument();
        expect(screen.getByText('💡 Explained')).toBeInTheDocument();
      });

      expect(handleToast).toHaveBeenCalledWith('Contextual explanation (offline)', 'info');
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
    it('displays article overview statistics and passage section jump buttons (§ 1, § 2, § 3)', () => {
      const handleScroll = vi.fn();
      render(<LeftSidebar article={mockArticle} onScrollToParagraph={handleScroll} />);

      // Overview Stats
      expect(screen.getByText('Robotics & AI')).toBeInTheDocument();
      expect(screen.getByText('Cognitive Architecture in Autonomous Robotics')).toBeInTheDocument();
      expect(screen.getByText('IEEE Transactions • 850 words')).toBeInTheDocument();
      expect(screen.getByText(/5 min/i)).toBeInTheDocument(); // 850 / 200 = ceil(4.25) -> 5 min

      // Section Jumps
      expect(screen.getByText('Passage Sections (3)')).toBeInTheDocument();
      expect(screen.getByTitle('Jump to paragraph 1')).toHaveTextContent('§ 1');
      expect(screen.getByTitle('Jump to paragraph 2')).toHaveTextContent('§ 2');
      expect(screen.getByTitle('Jump to paragraph 3')).toHaveTextContent('§ 3');

      // Click jump button
      fireEvent.click(screen.getByTitle('Jump to paragraph 2'));
      expect(handleScroll).toHaveBeenCalledWith(1);
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

      // Verify WordNet header and content
      expect(screen.getByText('WordNet Lexicon')).toBeInTheDocument();
      expect(screen.getByText('deterministic')).toBeInTheDocument();
      expect(screen.getByText('adjective')).toBeInTheDocument();
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
    it('defaults to isQuizOpen = false on article load with generous 9-column reader width and 3-col left panel', async () => {
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

      // 1. Verify Quiz is closed by default
      expect(screen.getByText('Show AI Quiz')).toBeInTheDocument();
      expect(screen.queryByText('Hide Quiz')).not.toBeInTheDocument();
      expect(screen.queryByText('Robotics Cognitive Architecture Exam')).not.toBeInTheDocument();

      // 2. Left panel container is visible (lg:col-span-3)
      const leftPanelWrapper = container.querySelector('.lg\\:col-span-3');
      expect(leftPanelWrapper).toBeInTheDocument();

      // 3. Reader container gets generous 9-column width (lg:col-span-9 max-w-4xl)
      const readerWrapper = container.querySelector('.lg\\:col-span-9');
      expect(readerWrapper).toBeInTheDocument();
      expect(readerWrapper?.className).toContain('max-w-4xl');
    });

    it('transitions to clean 7-col reader / 5-col quiz split (no 3-column squeeze) when Quiz is opened', async () => {
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

      // Open AI Quiz
      const showQuizBtn = screen.getByRole('button', { name: /Show AI Quiz/i });
      fireEvent.click(showQuizBtn);

      // Quiz button now says "Hide Quiz"
      expect(screen.getByText('Hide Quiz')).toBeInTheDocument();

      // Left panel is hidden on desktop (lg:hidden) to avoid 3-column squeeze
      const leftPanelHidden = container.querySelector('.lg\\:hidden');
      expect(leftPanelHidden).toBeInTheDocument();

      // Reader is now 7 columns (lg:col-span-7)
      const reader7Col = container.querySelector('.lg\\:col-span-7');
      expect(reader7Col).toBeInTheDocument();

      // Quiz column is 5 columns (lg:col-span-5)
      const quiz5Col = container.querySelector('.lg\\:col-span-5');
      expect(quiz5Col).toBeInTheDocument();
      expect(screen.getByText('Academic AI Quiz')).toBeInTheDocument();
      expect(screen.getByText('What do autonomous robots utilize for spatial representation?')).toBeInTheDocument();

      // Close AI Quiz again
      const hideQuizBtn = screen.getByRole('button', { name: /Hide Quiz/i });
      fireEvent.click(hideQuizBtn);

      // Returns to 9-col reader and 3-col left panel
      expect(container.querySelector('.lg\\:col-span-9')).toBeInTheDocument();
      expect(container.querySelector('.lg\\:col-span-3')).toBeInTheDocument();
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
