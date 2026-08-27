import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { LeftSidebar } from '../LeftSidebar';
import { WorkspaceToolbar } from '../WorkspaceToolbar';
import { UnifiedReadingDock } from '../UnifiedReadingDock';
import { ArticleReader } from '../ArticleReader';
import { Article } from '../../../types';
import { workspaceStore } from '../../../store';
import { HIGHLIGHT_THEMES, getHighlightMarkClass } from '../../../hooks/useHighlighter';

describe('Workspace Components & Unified Reading Suite', () => {
  const dummyArticle: Article = {
    id: 'art_ws_1',
    article_id: 'art_ws_1',
    title: 'The Future of AI in Education',
    source_name: 'Nature News',
    theme: 'Education',
    genre: 'academic',
    summary: 'How generative agents personalize tutoring.',
    original_text: 'Artificial intelligence is reshaping pedagogy across the globe.\n\nDeep learning transforms classrooms.',
    word_count: 650,
    stage: 'gold',
    status: 'completed',
  };

  beforeEach(() => {
    workspaceStore.setState({
      article: dummyArticle,
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
  });

  it('renders LeftSidebar with article statistics, section jumps, and WordNet lexicon', () => {
    render(<LeftSidebar article={dummyArticle} />);

    expect(screen.getByText('Education')).toBeInTheDocument();
    expect(screen.getByText('The Future of AI in Education')).toBeInTheDocument();
    expect(screen.getByText(/650 words/)).toBeInTheDocument();
    expect(screen.getByText('Nature News • 650 words')).toBeInTheDocument();
    expect(screen.getByText(/Passage Sections/)).toBeInTheDocument();
    expect(screen.getByText(/Interactive WordNet Dictionary/)).toBeInTheDocument();
  });

  it('renders WorkspaceToolbar and delegates seamlessly to UnifiedReadingDock', () => {
    const handleToggleQuiz = vi.fn();
    render(<WorkspaceToolbar isQuizOpen={true} onToggleQuiz={handleToggleQuiz} />);

    expect(screen.getByLabelText('Pointer Tool')).toBeInTheDocument();
    expect(screen.getByLabelText('Highlighter Tool')).toBeInTheDocument();
    expect(screen.getByLabelText('Eraser Tool')).toBeInTheDocument();
    expect(screen.getByLabelText('Smart Ink Tool')).toBeInTheDocument();
    expect(screen.getByLabelText('Dictionary Tool')).toBeInTheDocument();
    expect(screen.getByLabelText('Toggle Zen Mode')).toBeInTheDocument();
    expect(screen.getByLabelText('Keyboard Shortcuts')).toBeInTheDocument();

    const quizBtn = screen.getByLabelText('Toggle AI Reading Quiz');
    fireEvent.click(quizBtn);
    expect(handleToggleQuiz).toHaveBeenCalled();
  });

  it('operates UnifiedReadingDock tool toggles, color picker, and shortcuts cheat sheet', () => {
    const handleToggleQuiz = vi.fn();
    render(<UnifiedReadingDock isQuizOpen={false} onToggleQuiz={handleToggleQuiz} />);

    // 1. Tool toggles
    const markerBtn = screen.getByLabelText('Highlighter Tool');
    fireEvent.click(markerBtn);
    expect(workspaceStore.getState().activeTool).toBe('marker');

    const eraserBtn = screen.getByLabelText('Eraser Tool');
    fireEvent.click(eraserBtn);
    expect(workspaceStore.getState().activeTool).toBe('eraser');

    const smartInkBtn = screen.getByLabelText('Smart Ink Tool');
    fireEvent.click(smartInkBtn);
    expect(workspaceStore.getState().activeTool).toBe('smart_ink');

    const pointerBtn = screen.getByLabelText('Pointer Tool');
    fireEvent.click(pointerBtn);
    expect(workspaceStore.getState().activeTool).toBeNull();

    // 2. Color Picker Popover
    const colorPickerBtn = screen.getByLabelText('Highlight Color Picker');
    fireEvent.click(colorPickerBtn);

    expect(screen.getByRole('menu', { name: /Highlight Colors/i })).toBeInTheDocument();
    const emeraldBtn = screen.getByText(/Emerald/i);
    fireEvent.click(emeraldBtn);
    expect(workspaceStore.getState().highlightColor).toBe('emerald');

    // 3. Zen Mode toggle
    const zenBtn = screen.getByLabelText('Toggle Zen Mode');
    fireEvent.click(zenBtn);
    expect(workspaceStore.getState().isZenMode).toBe(true);

    // 4. Keyboard Shortcuts Modal
    const shortcutsBtn = screen.getByLabelText('Keyboard Shortcuts');
    fireEvent.click(shortcutsBtn);
    expect(screen.getByRole('dialog', { name: /Keyboard Shortcuts/i })).toBeInTheDocument();
    expect(screen.getByText('Reading Space Shortcuts')).toBeInTheDocument();

    const closeShortcutsBtn = screen.getByLabelText('Close shortcuts dialog');
    fireEvent.click(closeShortcutsBtn);
    expect(screen.queryByRole('dialog', { name: /Keyboard Shortcuts/i })).not.toBeInTheDocument();
  });

  it('validates multi-color highlight classes and themes in useHighlighter', () => {
    expect(HIGHLIGHT_THEMES.amber.classSuffix).toBe('amber');
    expect(HIGHLIGHT_THEMES.emerald.classSuffix).toBe('emerald');
    expect(HIGHLIGHT_THEMES.cyan.classSuffix).toBe('cyan');
    expect(HIGHLIGHT_THEMES.rose.classSuffix).toBe('rose');

    const amberClass = getHighlightMarkClass('amber');
    expect(amberClass).toContain('user-highlight-amber');
    expect(amberClass).toContain('bg-amber-400/30');

    const emeraldClass = getHighlightMarkClass('emerald');
    expect(emeraldClass).toContain('user-highlight-emerald');
    expect(emeraldClass).toContain('bg-emerald-400/30');

    const cyanClass = getHighlightMarkClass('cyan');
    expect(cyanClass).toContain('user-highlight-cyan');
    expect(cyanClass).toContain('bg-cyan-400/30');

    const roseClass = getHighlightMarkClass('rose');
    expect(roseClass).toContain('user-highlight-rose');
    expect(roseClass).toContain('bg-rose-400/30');
  });

  it('renders ArticleReader and ensures non-aggressive 1-click behavior', () => {
    const handleToast = vi.fn();
    render(<ArticleReader article={dummyArticle} onShowToast={handleToast} />);

    expect(screen.getByText('The Future of AI in Education')).toBeInTheDocument();
    expect(screen.getByText(/Artificial intelligence is reshaping pedagogy/)).toBeInTheDocument();

    // Clicking text in pointer mode does NOT trigger any toast or explanation
    const sentence = screen.getByText(/Artificial intelligence is reshaping pedagogy/);
    fireEvent.click(sentence);
    expect(handleToast).not.toHaveBeenCalled();
  });

  it('performs in-place Smart Ink sentence explanation and Eraser restore cycle', async () => {
    const handleToast = vi.fn();
    workspaceStore.setState({ activeTool: 'smart_ink' });

    render(<ArticleReader article={dummyArticle} onShowToast={handleToast} />);

    const sentence = screen.getByText(/Artificial intelligence is reshaping pedagogy/);
    fireEvent.click(sentence);

    // Should display in-place explained sentence with badge and restore button
    await waitFor(() => {
      expect(screen.getByText('💡 Explained')).toBeInTheDocument();
      expect(screen.getByText('Original')).toBeInTheDocument();
    });

    // Test restoring via Original button
    const restoreBtn = screen.getByLabelText('Restore original sentence');
    fireEvent.click(restoreBtn);

    await waitFor(() => {
      expect(screen.queryByText('💡 Explained')).not.toBeInTheDocument();
      expect(screen.getByText(/Artificial intelligence is reshaping pedagogy/)).toBeInTheDocument();
    });
  });

  it('handles Dictionary tool click without showing floating HUD popover', async () => {
    const handleToast = vi.fn();
    workspaceStore.setState({ activeTool: 'dictionary' });

    render(<ArticleReader article={dummyArticle} onShowToast={handleToast} />);

    const sentence = screen.getByText(/Artificial intelligence is reshaping pedagogy/);
    fireEvent.click(sentence);

    expect(handleToast).toHaveBeenCalledWith(expect.stringContaining('Looking up'), 'info');
    // Popover HUD must remain suppressed
    expect(screen.queryByRole('toolbar', { name: /Selection Actions HUD/i })).not.toBeInTheDocument();
  });

  it('renders LeftSidebar active dictionary card with pronunciations and synonyms', () => {
    workspaceStore.setState({
      activeDictionaryWord: {
        word: 'pedagogy',
        found: true,
        part_of_speech: 'noun',
        definitions: [
          {
            part_of_speech: 'noun',
            definition: 'The method and practice of teaching.',
            examples: ['Innovative pedagogical strategies in modern classrooms.'],
            synonyms: ['teaching', 'education', 'instruction'],
            antonyms: [],
          },
        ],
      },
    });

    render(<LeftSidebar article={dummyArticle} />);

    expect(screen.getByText('WordNet Lexicon')).toBeInTheDocument();
    expect(screen.getByText('pedagogy')).toBeInTheDocument();
    expect(screen.getByLabelText('Listen pronunciation')).toBeInTheDocument();
    expect(screen.getByText('The method and practice of teaching.')).toBeInTheDocument();
    expect(screen.getByText('"Innovative pedagogical strategies in modern classrooms."')).toBeInTheDocument();
    expect(screen.getByText('teaching')).toBeInTheDocument();
    expect(screen.getByText('education')).toBeInTheDocument();
  });
});
