import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { UnifiedReadingDock } from '../UnifiedReadingDock';
import { WorkspaceToolbar } from '../WorkspaceToolbar';
import { ArticleReader } from '../ArticleReader';
import { ReadingSpacePage } from '../ReadingSpacePage';
import { Article } from '../../../types';
import { api } from '../../../api/client';
import { workspaceStore, HighlightColor } from '../../../store';

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

describe('AuraDock Unified Reading Suite - Senior QA & DevOps Verification', () => {
  const mockArticle: Article = {
    id: 'art-auradock-qa-1',
    article_id: 'art-auradock-qa-1',
    title: 'Quantum Computing and Quantum Supremacy',
    source_name: 'Science Frontiers',
    theme: 'Physics & Computing',
    genre: 'academic',
    summary: 'An exploration of superconducting qubits and quantum advantage.',
    original_text:
      'Superconducting qubits enable superposition and entanglement in computational systems.\n\nQuantum algorithms like Grover search provide polynomial speedups over classical algorithms.',
    cleaned_text:
      'Superconducting qubits enable superposition and entanglement in computational systems.\n\nQuantum algorithms like Grover search provide polynomial speedups over classical algorithms.',
    word_count: 720,
    status: 'completed',
    stage: 'gold',
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

  // ── 1. Floating Dock Rendering & 7 Tool Buttons ───────────────────────────

  describe('1. Floating AuraDock UI Elements & Tool Toggles', () => {
    it('renders all 7 tool buttons plus color swatch and keyboard shortcut helper', () => {
      const handleToggleQuiz = vi.fn();
      render(<UnifiedReadingDock isQuizOpen={true} onToggleQuiz={handleToggleQuiz} />);

      // Nav container
      expect(screen.getByRole('navigation', { name: /Unified Reading Toolbox/i })).toBeInTheDocument();

      // Tool Buttons
      expect(screen.getByLabelText('Pointer Tool')).toBeInTheDocument();
      expect(screen.getByLabelText('Highlighter Tool')).toBeInTheDocument();
      expect(screen.getByLabelText('Highlight Color Picker')).toBeInTheDocument();
      expect(screen.getByLabelText('Eraser Tool')).toBeInTheDocument();
      expect(screen.getByLabelText('Smart Ink Tool')).toBeInTheDocument();
      expect(screen.getByLabelText('Dictionary Tool')).toBeInTheDocument();
      expect(screen.getByLabelText('Toggle Zen Mode')).toBeInTheDocument();
      expect(screen.getByLabelText('Toggle AI Reading Quiz')).toBeInTheDocument();
      expect(screen.getByLabelText('Keyboard Shortcuts')).toBeInTheDocument();
    });

    it('toggles tool active states properly (pointer, marker, eraser, smart_ink, dictionary)', () => {
      render(<UnifiedReadingDock isQuizOpen={false} onToggleQuiz={vi.fn()} />);

      // Default tool is null (pointer active by default)
      expect(workspaceStore.getState().activeTool).toBeNull();

      // Activate Marker
      fireEvent.click(screen.getByLabelText('Highlighter Tool'));
      expect(workspaceStore.getState().activeTool).toBe('marker');

      // Activate Eraser
      fireEvent.click(screen.getByLabelText('Eraser Tool'));
      expect(workspaceStore.getState().activeTool).toBe('eraser');

      // Activate Smart Ink
      fireEvent.click(screen.getByLabelText('Smart Ink Tool'));
      expect(workspaceStore.getState().activeTool).toBe('smart_ink');

      // Activate Dictionary
      fireEvent.click(screen.getByLabelText('Dictionary Tool'));
      expect(workspaceStore.getState().activeTool).toBe('dictionary');

      // Reset to Pointer Mode
      fireEvent.click(screen.getByLabelText('Pointer Tool'));
      expect(workspaceStore.getState().activeTool).toBeNull();
    });

    it('toggles Zen Mode directly from dock button', () => {
      render(<UnifiedReadingDock />);

      const zenBtn = screen.getByLabelText('Toggle Zen Mode');
      expect(workspaceStore.getState().isZenMode).toBe(false);

      fireEvent.click(zenBtn);
      expect(workspaceStore.getState().isZenMode).toBe(true);

      fireEvent.click(zenBtn);
      expect(workspaceStore.getState().isZenMode).toBe(false);
    });

    it('triggers onToggleQuiz callback when Quiz button is clicked', () => {
      const handleToggleQuiz = vi.fn();
      render(<UnifiedReadingDock isQuizOpen={false} onToggleQuiz={handleToggleQuiz} />);

      const quizBtn = screen.getByLabelText('Toggle AI Reading Quiz');
      fireEvent.click(quizBtn);
      expect(handleToggleQuiz).toHaveBeenCalledTimes(1);
    });

    it('omits Quiz toggle button when onToggleQuiz is not provided', () => {
      render(<UnifiedReadingDock />);
      expect(screen.queryByLabelText('Toggle AI Reading Quiz')).not.toBeInTheDocument();
    });

    it('works identically when wrapped via WorkspaceToolbar legacy component', () => {
      const handleToggleQuiz = vi.fn();
      render(<WorkspaceToolbar isQuizOpen={true} onToggleQuiz={handleToggleQuiz} />);

      expect(screen.getByRole('navigation', { name: /Unified Reading Toolbox/i })).toBeInTheDocument();
      expect(screen.getByLabelText('Pointer Tool')).toBeInTheDocument();
      expect(screen.getByLabelText('Highlighter Tool')).toBeInTheDocument();
    });
  });

  // ── 2. Color Swatch Picker Popover ────────────────────────────────────────

  describe('2. Color Swatch Picker Popover', () => {
    it('opens popover, allows selecting Amber, Emerald, Cyan, Rose and closes', () => {
      render(<UnifiedReadingDock />);

      const colorPickerTrigger = screen.getByLabelText('Highlight Color Picker');
      fireEvent.click(colorPickerTrigger);

      // Verify popover menu appears
      const menu = screen.getByRole('menu', { name: /Highlight Colors/i });
      expect(menu).toBeInTheDocument();
      expect(screen.getByText('Keys 1-4')).toBeInTheDocument();

      // Test selecting Emerald
      const emeraldBtn = screen.getByText(/Emerald/i);
      fireEvent.click(emeraldBtn);
      expect(workspaceStore.getState().highlightColor).toBe('emerald');
      expect(workspaceStore.getState().activeTool).toBe('marker');
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();

      // Reopen and select Cyan
      fireEvent.click(colorPickerTrigger);
      fireEvent.click(screen.getByText(/Cyan/i));
      expect(workspaceStore.getState().highlightColor).toBe('cyan');

      // Reopen and select Rose
      fireEvent.click(colorPickerTrigger);
      fireEvent.click(screen.getByText(/Rose/i));
      expect(workspaceStore.getState().highlightColor).toBe('rose');

      // Reopen and select Amber
      fireEvent.click(colorPickerTrigger);
      fireEvent.click(screen.getByText(/Amber/i));
      expect(workspaceStore.getState().highlightColor).toBe('amber');
    });

    it('closes color picker popover when clicking outside', () => {
      render(
        <div>
          <div data-testid="outside-element">Outside</div>
          <UnifiedReadingDock />
        </div>
      );

      const colorPickerTrigger = screen.getByLabelText('Highlight Color Picker');
      fireEvent.click(colorPickerTrigger);
      expect(screen.getByRole('menu', { name: /Highlight Colors/i })).toBeInTheDocument();

      // Click outside
      fireEvent.mouseDown(screen.getByTestId('outside-element'));
      expect(screen.queryByRole('menu', { name: /Highlight Colors/i })).not.toBeInTheDocument();
    });
  });

  // ── 3. Keyboard Shortcuts Modal Dialog ────────────────────────────────────

  describe('3. Keyboard Shortcuts Modal Dialog', () => {
    it('opens cheat sheet modal and lists all shortcut key bindings', () => {
      render(<UnifiedReadingDock />);

      const shortcutsTrigger = screen.getByLabelText('Keyboard Shortcuts');
      fireEvent.click(shortcutsTrigger);

      const dialog = screen.getByRole('dialog', { name: /Keyboard Shortcuts Cheat Sheet/i });
      expect(dialog).toBeInTheDocument();
      expect(screen.getByText('Reading Space Shortcuts')).toBeInTheDocument();
      expect(screen.getByText('Power user keyboard controls')).toBeInTheDocument();

      // Check all shortcut descriptions
      expect(screen.getByText('Pointer / Select Mode')).toBeInTheDocument();
      expect(screen.getByText('Highlighter Tool')).toBeInTheDocument();
      expect(screen.getByText('Eraser Tool')).toBeInTheDocument();
      expect(screen.getByText('Smart Ink AI Stream')).toBeInTheDocument();
      expect(screen.getByText('WordNet Dictionary')).toBeInTheDocument();
      expect(screen.getByText('Paraphrase Selected Text')).toBeInTheDocument();
      expect(screen.getByText('Toggle Zen Focus Mode')).toBeInTheDocument();
      expect(screen.getByText('Toggle AI Reading Quiz')).toBeInTheDocument();
      expect(screen.getByText('Highlight Colors')).toBeInTheDocument();
    });

    it('closes modal when clicking X button, Got it button, or backdrop', () => {
      render(<UnifiedReadingDock />);

      const shortcutsTrigger = screen.getByLabelText('Keyboard Shortcuts');

      // 1. Close via X button
      fireEvent.click(shortcutsTrigger);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      fireEvent.click(screen.getByLabelText('Close shortcuts dialog'));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      // 2. Close via "Got it" button
      fireEvent.click(shortcutsTrigger);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: /Got it/i }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      // 3. Close via backdrop click
      fireEvent.click(shortcutsTrigger);
      const dialogBackdrop = screen.getByRole('dialog');
      fireEvent.click(dialogBackdrop);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  // ── 4. Keyboard Shortcuts Dispatching ─────────────────────────────────────

  describe('4. Keyboard Shortcuts Dispatching in ArticleReader', () => {
    it('dispatches tool selection shortcuts: H, E, I, D, V, Esc', () => {
      const handleToast = vi.fn();
      render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      // Press 'H' -> Highlighter
      fireEvent.keyDown(window, { key: 'h' });
      expect(workspaceStore.getState().activeTool).toBe('marker');

      // Press 'E' -> Eraser
      fireEvent.keyDown(window, { key: 'e' });
      expect(workspaceStore.getState().activeTool).toBe('eraser');

      // Press 'I' -> Smart Ink
      fireEvent.keyDown(window, { key: 'i' });
      expect(workspaceStore.getState().activeTool).toBe('smart_ink');

      // Press 'D' -> Dictionary
      fireEvent.keyDown(window, { key: 'd' });
      expect(workspaceStore.getState().activeTool).toBe('dictionary');

      // Press 'V' -> Reset to Pointer
      fireEvent.keyDown(window, { key: 'v' });
      expect(workspaceStore.getState().activeTool).toBeNull();

      // Press 'H' then 'Escape' -> Reset to Pointer
      fireEvent.keyDown(window, { key: 'h' });
      expect(workspaceStore.getState().activeTool).toBe('marker');
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(workspaceStore.getState().activeTool).toBeNull();
    });

    it('dispatches highlight color shortcuts 1, 2, 3, 4', () => {
      render(<ArticleReader article={mockArticle} />);

      // 1 -> Amber
      fireEvent.keyDown(window, { key: '1' });
      expect(workspaceStore.getState().highlightColor).toBe('amber');
      expect(workspaceStore.getState().activeTool).toBe('marker');

      // 2 -> Emerald
      fireEvent.keyDown(window, { key: '2' });
      expect(workspaceStore.getState().highlightColor).toBe('emerald');
      expect(workspaceStore.getState().activeTool).toBe('marker');

      // 3 -> Cyan
      fireEvent.keyDown(window, { key: '3' });
      expect(workspaceStore.getState().highlightColor).toBe('cyan');
      expect(workspaceStore.getState().activeTool).toBe('marker');

      // 4 -> Rose
      fireEvent.keyDown(window, { key: '4' });
      expect(workspaceStore.getState().highlightColor).toBe('rose');
      expect(workspaceStore.getState().activeTool).toBe('marker');
    });

    it('dispatches Zen mode (Z) and Quiz toggle (Q) shortcuts', () => {
      const handleToggleQuiz = vi.fn();
      render(<ArticleReader article={mockArticle} onToggleQuiz={handleToggleQuiz} />);

      // Press 'Z' -> Toggle Zen Mode
      expect(workspaceStore.getState().isZenMode).toBe(false);
      fireEvent.keyDown(window, { key: 'z' });
      expect(workspaceStore.getState().isZenMode).toBe(true);
      fireEvent.keyDown(window, { key: 'z' });
      expect(workspaceStore.getState().isZenMode).toBe(false);

      // Press 'Q' -> onToggleQuiz callback
      fireEvent.keyDown(window, { key: 'q' });
      expect(handleToggleQuiz).toHaveBeenCalledTimes(1);
    });

    it('ignores shortcut keys when user is typing in form inputs or textareas', () => {
      render(
        <div>
          <input data-testid="test-input" type="text" />
          <textarea data-testid="test-textarea" />
          <ArticleReader article={mockArticle} />
        </div>
      );

      const input = screen.getByTestId('test-input');
      const textarea = screen.getByTestId('test-textarea');

      // Typing 'h' inside input should NOT activate marker tool
      fireEvent.keyDown(input, { key: 'h' });
      expect(workspaceStore.getState().activeTool).toBeNull();

      // Typing 'e' inside textarea should NOT activate eraser tool
      fireEvent.keyDown(textarea, { key: 'e' });
      expect(workspaceStore.getState().activeTool).toBeNull();

      // Typing 'z' inside input should NOT toggle zen mode
      fireEvent.keyDown(input, { key: 'z' });
      expect(workspaceStore.getState().isZenMode).toBe(false);
    });
  });

  // ── 5. Contextual Selection Action HUD Popover ────────────────────────────

  describe('5. Contextual Selection Action HUD in ArticleReader', () => {
    it('displays Floating Selection HUD when text is highlighted in reader', async () => {
      const { container } = render(<ArticleReader article={mockArticle} />);

      const contentContainer = container.querySelector('.select-text')!;
      expect(contentContainer).toBeInTheDocument();

      // Mock window.getSelection
      const mockRange = {
        commonAncestorContainer: contentContainer,
        getBoundingClientRect: () => ({
          left: 200,
          top: 300,
          width: 80,
          height: 20,
        }),
      };

      vi.spyOn(window, 'getSelection').mockImplementation(() => ({
        isCollapsed: false,
        rangeCount: 1,
        getRangeAt: () => mockRange,
        toString: () => 'superconducting qubits',
      } as any));

      // Trigger selection change event
      fireEvent(document, new Event('selectionchange'));

      await waitFor(() => {
        expect(screen.getByRole('toolbar', { name: /Selection Actions HUD/i })).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /Mark selection/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Define word/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Explain with Smart Ink/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Paraphrase selection/i })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Copy selection/i })).toBeInTheDocument();
    });

    it('triggers Dictionary lookup from HUD Define button', async () => {
      const { container } = render(<ArticleReader article={mockArticle} />);

      const contentContainer = container.querySelector('.select-text')!;
      const mockRange = {
        commonAncestorContainer: contentContainer,
        getBoundingClientRect: () => ({ left: 200, top: 300, width: 80, height: 20 }),
      };

      vi.spyOn(window, 'getSelection').mockReturnValue({
        isCollapsed: false,
        rangeCount: 1,
        getRangeAt: () => mockRange,
        toString: () => 'qubits',
      } as any);

      fireEvent(document, new Event('selectionchange'));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Define word/i })).toBeInTheDocument();
      });

      const defineBtn = screen.getByRole('button', { name: /Define word/i });
      fireEvent.mouseDown(defineBtn);

      expect(api.dictionary.lookup).toHaveBeenCalledWith('qubits');
    });

    it('triggers Copy action and calls navigator.clipboard.writeText', async () => {
      const handleToast = vi.fn();
      const { container } = render(<ArticleReader article={mockArticle} onShowToast={handleToast} />);

      const contentContainer = container.querySelector('.select-text')!;
      const mockRange = {
        commonAncestorContainer: contentContainer,
        getBoundingClientRect: () => ({ left: 200, top: 300, width: 80, height: 20 }),
      };

      vi.spyOn(window, 'getSelection').mockReturnValue({
        isCollapsed: false,
        rangeCount: 1,
        getRangeAt: () => mockRange,
        toString: () => 'entanglement in computational systems',
      } as any);

      fireEvent(document, new Event('selectionchange'));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Copy selection/i })).toBeInTheDocument();
      });

      const copyBtn = screen.getByRole('button', { name: /Copy selection/i });
      fireEvent.mouseDown(copyBtn);

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        'entanglement in computational systems'
      );
      expect(handleToast).toHaveBeenCalledWith('Copied text to clipboard', 'success');
    });

    it('triggers Smart Ink explanation from HUD Smart Ink button', async () => {
      vi.mocked(api.articles.explain).mockResolvedValueOnce({
        status: 'success',
        phrase: 'Superconducting qubits enable superposition',
        summary: 'Quantum computing summary',
        detailed_explanation: 'Quantum bits allow multiple states at once',
        simplified_version: 'Qubits can be in two states at once',
        key_terms: [],
      });

      const { container } = render(<ArticleReader article={mockArticle} />);

      const contentContainer = container.querySelector('.select-text')!;
      const mockRange = {
        commonAncestorContainer: contentContainer,
        getBoundingClientRect: () => ({ left: 200, top: 300, width: 80, height: 20 }),
      };

      vi.spyOn(window, 'getSelection').mockReturnValue({
        isCollapsed: false,
        rangeCount: 1,
        getRangeAt: () => mockRange,
        toString: () => 'Superconducting qubits enable superposition',
      } as any);

      fireEvent(document, new Event('selectionchange'));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Explain with Smart Ink/i })).toBeInTheDocument();
      });

      const smartInkBtn = screen.getByRole('button', { name: /Explain with Smart Ink/i });
      fireEvent.mouseDown(smartInkBtn);

      await waitFor(() => {
        expect(screen.getByText('💡 Explained')).toBeInTheDocument();
      });
    });
  });

  // ── 6. Zen Mode Reading Space Layout Verification ─────────────────────────

  describe('6. Zen Mode Reading Space Layout & Distraction-Free UX', () => {
    it('renders ReadingSpacePage in Zen Mode with max-w-[76ch] centered column and hidden sidebars', async () => {
      vi.mocked(api.articles.get).mockResolvedValueOnce({
        status: 'success',
        article: mockArticle,
        related_articles: [],
      });

      // Set Zen Mode active
      workspaceStore.setState({ isZenMode: true });

      render(
        <ReadingSpacePage
          articleId="art-auradock-qa-1"
          onNavigateHome={vi.fn()}
          onSelectArticle={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Zen Mode Active')).toBeInTheDocument();
      });

      // Subheader shows Exit Zen Mode button
      expect(screen.getByRole('button', { name: /Exit Zen Mode/i })).toBeInTheDocument();

      // Main element has zen mode centered column class
      const mainElem = screen.getByRole('main');
      expect(mainElem.className).toContain('max-w-[76ch]');
      expect(mainElem.className).toContain('mx-auto');

      // Sidebars (LeftSidebar outline / notes and QuizSidebar) are omitted in zen mode
      expect(screen.queryByText(/Smart Ink Notes/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Reading Speed & Comprehension/i)).not.toBeInTheDocument();

      // Unified dock is rendered inside Zen mode
      expect(screen.getByRole('navigation', { name: /Unified Reading Toolbox/i })).toBeInTheDocument();

      // Clicking Exit Zen Mode returns to standard layout
      const exitZenBtn = screen.getByRole('button', { name: /Exit Zen Mode/i });
      fireEvent.click(exitZenBtn);
      expect(workspaceStore.getState().isZenMode).toBe(false);
    });

    it('renders standard 3-column layout when Zen Mode is inactive', async () => {
      vi.mocked(api.articles.get).mockResolvedValueOnce({
        status: 'success',
        article: mockArticle,
        related_articles: [],
      });

      workspaceStore.setState({ isZenMode: false });

      render(
        <ReadingSpacePage
          articleId="art-auradock-qa-1"
          onNavigateHome={vi.fn()}
          onSelectArticle={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText('Quantum Computing and Quantum Supremacy').length).toBeGreaterThan(0);
      });

      expect(screen.queryByText('Zen Mode Active')).not.toBeInTheDocument();
      const mainElem = screen.getByRole('main');
      expect(mainElem.className).toContain('max-w-7xl');
      expect(mainElem.className).toContain('grid');
    });
  });
});
