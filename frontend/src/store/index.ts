import { useState, useEffect } from 'react';
import {
  Article,
  ArticleCard,
  DictionaryLookupResult,
  SmartExplanationCard,
  UserProfile,
} from '../types';
import { api } from '../api/client';

// ── Auth Store ────────────────────────────────────────────────────────────────

type Listener<T> = (state: T) => void;

function createStore<T>(initialState: T) {
  let state = initialState;
  const listeners = new Set<Listener<T>>();

  const getState = () => state;

  const setState = (partial: Partial<T> | ((prev: T) => Partial<T>)) => {
    const nextState = typeof partial === 'function' ? partial(state) : partial;
    state = { ...state, ...nextState };
    listeners.forEach((listener) => listener(state));
  };

  const useStore = () => {
    const [current, setCurrent] = useState(state);
    useEffect(() => {
      listeners.add(setCurrent);
      return () => {
        listeners.delete(setCurrent);
      };
    }, []);
    return current;
  };

  return { getState, setState, useStore };
}

interface AuthState {
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;
}

export const authStore = createStore<AuthState>({
  user: null,
  isLoading: true,
  error: null,
});

export const useAuth = () => {
  const state = authStore.useStore();

  const fetchCurrentUser = async () => {
    authStore.setState({ isLoading: true, error: null });
    try {
      const user = await api.auth.me();
      authStore.setState({ user: user.is_authenticated ? user : null, isLoading: false });
    } catch {
      authStore.setState({ user: null, isLoading: false });
    }
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } finally {
      authStore.setState({ user: null });
    }
  };

  const setUser = (user: UserProfile | null) => {
    authStore.setState({ user });
  };

  const deductStar = () => {
    authStore.setState((prev) => {
      if (!prev.user) return prev;
      return { user: { ...prev.user, stars: Math.max(0, prev.user.stars - 1) } };
    });
  };

  return {
    ...state,
    fetchCurrentUser,
    logout,
    setUser,
    deductStar,
  };
};

// ── Workspace Store ───────────────────────────────────────────────────────────

export type ActiveTool = 'pointer' | 'marker' | 'eraser' | 'dictionary' | null;
export type HighlightColor = 'amber' | 'emerald' | 'cyan' | 'rose';

interface WorkspaceState {
  article: Article | null;
  activeTool: ActiveTool;
  highlightColor: HighlightColor;
  isZenMode: boolean;
  highlights: string[];
  quizAnswers: Record<string, string>;
  quizSubmitted: boolean;
  score: number;
  totalQuestions: number;
  isTimerRunning: boolean;
  elapsedSeconds: number;
  relatedArticles: ArticleCard[];
  activeDictionaryWord: DictionaryLookupResult | null;
  isDictionaryLoading: boolean;
}

export const workspaceStore = createStore<WorkspaceState>({
  article: null,
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

export const useWorkspace = () => {
  const state = workspaceStore.useStore();

  const setArticle = (article: Article | null) => {
    workspaceStore.setState({
      article,
      quizAnswers: {},
      quizSubmitted: false,
      score: 0,
      totalQuestions: 0,
      isTimerRunning: true,
      elapsedSeconds: 0,
      activeDictionaryWord: null,
    });
  };

  const setActiveTool = (tool: ActiveTool) => {
    workspaceStore.setState((prev) => ({
      activeTool: prev.activeTool === tool ? null : tool,
    }));
  };

  const setHighlightColor = (highlightColor: HighlightColor) => {
    workspaceStore.setState({ highlightColor });
  };

  const toggleZenMode = () => {
    workspaceStore.setState((prev) => ({ isZenMode: !prev.isZenMode }));
  };

  const setZenMode = (isZenMode: boolean) => {
    workspaceStore.setState({ isZenMode });
  };

  const setAnswer = (questionKey: string, answer: string) => {
    workspaceStore.setState((prev) => ({
      quizAnswers: { ...prev.quizAnswers, [questionKey]: answer },
    }));
  };

  const submitQuiz = async (articleId: string, total: number) => {
    const answers = workspaceStore.getState().quizAnswers;
    const article = workspaceStore.getState().article;
    const elapsed = workspaceStore.getState().elapsedSeconds;

    let calculatedScore = 0;
    if (article?.exams && article.exams[0]?.quizzes) {
      article.exams[0].quizzes.forEach((quiz, i) => {
        const key = `q_${i}`;
        const userAns = (answers[key] || '').trim().toLowerCase();
        const correctAns = (quiz.correct_answer || '').trim().toLowerCase();
        if (userAns && userAns === correctAns) {
          calculatedScore++;
        }
      });
    }

    try {
      const res = await api.articles.submitExam(articleId, {
        score: calculatedScore,
        total_questions: total,
        answers,
        elapsed_time: elapsed,
      });

      workspaceStore.setState({
        quizSubmitted: true,
        score: calculatedScore,
        totalQuestions: total,
        isTimerRunning: false,
        relatedArticles: res.related_articles || [],
      });
    } catch {
      workspaceStore.setState({
        quizSubmitted: true,
        score: calculatedScore,
        totalQuestions: total,
        isTimerRunning: false,
      });
    }
  };

  const tickTimer = () => {
    workspaceStore.setState((prev) => {
      if (!prev.isTimerRunning) return prev;
      return { elapsedSeconds: prev.elapsedSeconds + 1 };
    });
  };

  const lookupDictionaryWord = async (word: string) => {
    if (!word || !word.trim()) return;
    workspaceStore.setState({ isDictionaryLoading: true });
    try {
      const res = await api.dictionary.lookup(word.trim());
      workspaceStore.setState({
        activeDictionaryWord: res,
        isDictionaryLoading: false,
      });
    } catch {
      workspaceStore.setState({ isDictionaryLoading: false });
    }
  };

  const closeDictionaryCard = () => {
    workspaceStore.setState({ activeDictionaryWord: null });
  };

  return {
    ...state,
    setArticle,
    setActiveTool,
    setHighlightColor,
    toggleZenMode,
    setZenMode,
    setAnswer,
    submitQuiz,
    tickTimer,
    lookupDictionaryWord,
    closeDictionaryCard,
  };
};

// ── Smart Notes / Explanations Store ──────────────────────────────────────────

export interface StreamingNote {
  id: string;
  phrase: string;
  isTerm: boolean;
  streamedText: string;
  isStreaming: boolean;
}

interface SmartNotesState {
  notesByArticle: Record<string, SmartExplanationCard[]>;
  activeStreamingNote: StreamingNote | null;
}

export const smartNotesStore = createStore<SmartNotesState>({
  notesByArticle: {},
  activeStreamingNote: null,
});

export const useSmartNotesStorage = (articleId: string) => {
  const state = smartNotesStore.useStore();
  const storageKey = `article_smart_notes_${articleId}`;

  // Initialize from localStorage if not present in memory yet
  useEffect(() => {
    if (!articleId) return;
    if (state.notesByArticle[articleId] === undefined) {
      try {
        const raw = localStorage.getItem(storageKey);
        const initial = raw ? JSON.parse(raw) : [];
        smartNotesStore.setState((prev) => ({
          notesByArticle: { ...prev.notesByArticle, [articleId]: initial },
        }));
      } catch {
        smartNotesStore.setState((prev) => ({
          notesByArticle: { ...prev.notesByArticle, [articleId]: [] },
        }));
      }
    }
  }, [articleId, state.notesByArticle, storageKey]);

  const notes = state.notesByArticle[articleId] || [];
  const activeStreamingNote = state.activeStreamingNote;

  const addNote = (note: SmartExplanationCard) => {
    if (!articleId) return;
    smartNotesStore.setState((prev) => {
      const current = prev.notesByArticle[articleId] || [];
      const updated = [note, ...current];
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch {}
      return {
        notesByArticle: { ...prev.notesByArticle, [articleId]: updated },
      };
    });
  };

  const removeNote = (id: string) => {
    if (!articleId) return;
    smartNotesStore.setState((prev) => {
      const current = prev.notesByArticle[articleId] || [];
      const updated = current.filter((n) => n.id !== id);
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch {}
      return {
        notesByArticle: { ...prev.notesByArticle, [articleId]: updated },
      };
    });
  };

  const clearNotes = () => {
    if (!articleId) return;
    try {
      localStorage.removeItem(storageKey);
    } catch {}
    smartNotesStore.setState((prev) => ({
      notesByArticle: { ...prev.notesByArticle, [articleId]: [] },
    }));
  };

  const startStreamingExplanation = async (phrase: string, paragraphContext: string = '') => {
    const cleanPhrase = phrase.trim();
    if (!cleanPhrase) return;

    const isTerm = cleanPhrase.split(/\s+/).length <= 2;
    const noteId = `note_${Date.now()}`;

    smartNotesStore.setState({
      activeStreamingNote: {
        id: noteId,
        phrase: cleanPhrase,
        isTerm,
        streamedText: '',
        isStreaming: true,
      },
    });

    let accumulatedText = '';

    try {
      const response = await fetch('/readspace/api/explain/stream/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phrase: cleanPhrase,
          paragraph_context: paragraphContext.trim() || cleanPhrase,
          article_id: articleId,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Streaming connection failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunkStr = decoder.decode(value, { stream: true });
        const lines = chunkStr.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataPayload = line.replace('data: ', '').trim();
            if (dataPayload === '[DONE]') {
              break;
            }

            try {
              const parsed = JSON.parse(dataPayload);
              if (parsed.type === 'delta') {
                accumulatedText += parsed.text || '';
                smartNotesStore.setState((prev) => ({
                  activeStreamingNote: prev.activeStreamingNote
                    ? { ...prev.activeStreamingNote, streamedText: accumulatedText }
                    : null,
                }));
              }
            } catch {}
          }
        }
      }
    } catch {
      // Fallback generator if offline
      const fallback = isTerm
        ? `**💡 In Simple Words:**\n"${cleanPhrase}" refers to a fundamental concept used to describe a specific property or mechanism in this subject.\n\n**📖 How it's used here:**\nThe author introduces this term to clarify how this idea functions within the broader argument.\n\n**✨ Simpler Alternative:**\nA common, simpler way to think of it is a key defining factor.`
        : `**💡 In Simple Words:**\nThis sentence states that when we examine ${cleanPhrase.slice(0, 40)}..., we see a direct connection to the main outcome.\n\n**🎯 Main Point:**\nThe essential takeaway is understanding how this principle supports the overarching thesis.\n\n**🔍 Key Concept Breakdown:**\n• Focuses on the direct cause-and-effect relationship in this section of the passage.\n• Emphasizes that this concept is critical for overall comprehension.`;

      accumulatedText = fallback;
    } finally {
      const finalCard: SmartExplanationCard = {
        id: noteId,
        selected_text: cleanPhrase,
        summary: isTerm ? `Definition of "${cleanPhrase}"` : `Explanation of sentence`,
        explanation: accumulatedText,
        simplified_version: isTerm ? undefined : cleanPhrase,
        timestamp: Date.now(),
      };

      addNote(finalCard);
      smartNotesStore.setState({ activeStreamingNote: null });
    }
  };

  return { notes, activeStreamingNote, addNote, removeNote, clearNotes, startStreamingExplanation };
};
