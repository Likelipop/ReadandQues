import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Bot,
  Sparkles,
  BookOpen,
  AlertCircle,
  X,
  RotateCcw,
  HelpCircle,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  ChevronRight,
  ExternalLink,
  FileQuestion,
  Layers,
  ChevronDown,
  PenLine,
} from 'lucide-react';
import { useSSEStream, Citation } from '../../hooks/useSSEStream';
import { MarkdownView } from '../../components/common/MarkdownView';
import { useWorkspace } from '../../store';

export interface LeftAiDockProps {
  activeArticleId?: string;
  activeArticleText?: string;
  pageContext?: 'readspace' | 'homepage' | 'all-tests' | 'profile' | 'home';
  isOpen?: boolean;
  onToggle?: (open: boolean) => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  quizData?: any[];
  actionType?: 'chat' | 'quiz';
  timestamp: string;
}

const SAMPLE_QUESTIONS = [
  'Generate a reading comprehension quiz for this article',
  'Explain complex vocabulary and sentence structures in this passage',
  'What are the key takeaways and main arguments of this text?',
];

/**
 * Extract numbered blank tokens from question text, e.g. [1], [2] or (1), (2).
 */
const getQuestionBlanks = (questionText: string): string[] => {
  if (!questionText) return [];
  const bracketMatches = Array.from(
    new Set((questionText.match(/\[(\d+)\]/g) || []).map((m) => m.replace(/[\[\]]/g, '')))
  );
  if (bracketMatches.length > 0) return bracketMatches;

  const parenMatches = Array.from(
    new Set((questionText.match(/\((\d+)\)/g) || []).map((m) => m.replace(/[\(\)]/g, '')))
  );
  if (parenMatches.length > 0) return parenMatches;

  return [];
};

/**
 * Detect if a question is YES/NO/NOT GIVEN or TRUE/FALSE/NOT GIVEN.
 */
const isYesNoType = (quiz: any): boolean => {
  const typeStr = (quiz.quiz_type || '').toLowerCase().trim();
  if (
    typeStr.includes('yes_no') ||
    typeStr.includes('true_false') ||
    typeStr.includes('notgiven') ||
    typeStr.includes('not_given')
  ) {
    return true;
  }
  const ansStr = (quiz.correct_answer || '').toUpperCase().trim();
  if (['YES', 'NO', 'NOT GIVEN', 'TRUE', 'FALSE'].includes(ansStr)) {
    return true;
  }
  if (
    quiz.options &&
    quiz.options.length > 0 &&
    quiz.options.length <= 3 &&
    quiz.options.some((o: string) =>
      ['YES', 'TRUE', 'NOT GIVEN', 'NOT_GIVEN', 'NO', 'FALSE'].includes(
        o.toUpperCase().replace(/\s+/g, '_')
      )
    )
  ) {
    return true;
  }
  return false;
};

/**
 * Detect if a question is Fill in the Blanks / Summary Completion.
 */
const isFillInBlankType = (quiz: any): boolean => {
  if (isYesNoType(quiz)) return false;
  const typeStr = (quiz.quiz_type || '').toLowerCase().trim();
  if (typeStr.includes('blank') || typeStr.includes('fib') || typeStr.includes('summary')) {
    return true;
  }
  const blanks = getQuestionBlanks(quiz.question || '');
  if (blanks.length > 0) {
    return true;
  }
  return false;
};

export const LeftAiDock: React.FC<LeftAiDockProps> = ({
  activeArticleId,
  activeArticleText,
  pageContext = 'homepage',
  isOpen: controlledIsOpen,
  onToggle: controlledOnToggle,
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isExpanded = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;

  const setIsExpanded = useCallback(
    (open: boolean | ((prev: boolean) => boolean)) => {
      const nextVal = typeof open === 'function' ? open(isExpanded) : open;
      if (controlledOnToggle) {
        controlledOnToggle(nextVal);
      } else {
        setInternalIsOpen(nextVal);
      }
    },
    [isExpanded, controlledOnToggle]
  );

  const [mode, setMode] = useState<'chat' | 'quiz'>('chat');
  const [input, setInput] = useState('');
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  // Active quiz state in the dock
  const [activeQuizList, setActiveQuizList] = useState<any[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [showExitConfirm, setShowExitConfirm] = useState(false);

  const { article } = useWorkspace();
  const currentArticleText = activeArticleText || article?.original_text || article?.cleaned_text || '';
  const currentArticleId = activeArticleId || article?.id || article?.article_id || '';

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        '👋 **Hello! I am your AI Study Dock.**\n\nI can help you with:\n- 📖 **Vocabulary & Sentence Explanations**\n- 🔍 **News RAG Search across articles**\n- 📝 **Reading Comprehension Quizzes**\n\nAsk me anything or request a quiz!',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { isStreaming, streamedText, citations, quizData, actionType, error, startStream } = useSSEStream();

  // Scroll to bottom when messages update
  useEffect(() => {
    if (isExpanded && mode === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamedText, isExpanded, mode]);

  // Global Keyboard Shortcut: Ctrl + K or Cmd + K to toggle dock
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsExpanded((prev) => {
          const next = !prev;
          if (next) setTimeout(() => inputRef.current?.focus(), 150);
          return next;
        });
      }
      if (e.key === 'Escape' && isExpanded) {
        handleAttemptClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isExpanded, quizAnswers, quizSubmitted, activeQuizList]);

  // Listen to custom window event to trigger quiz from other components
  useEffect(() => {
    const handleTriggerQuizEvent = (event: Event) => {
      const customEvent = event as CustomEvent<{ query?: string }>;
      setIsExpanded(true);
      const query = customEvent.detail?.query || 'Generate a reading comprehension quiz for this article';
      handleSend(query);
    };

    window.addEventListener('trigger-ai-quiz', handleTriggerQuizEvent);
    return () => window.removeEventListener('trigger-ai-quiz', handleTriggerQuizEvent);
  }, [currentArticleId, currentArticleText]);

  // Attempt to close dock with confirmation if unsaved quiz exists
  const handleAttemptClose = () => {
    const hasUnsavedQuiz =
      mode === 'quiz' &&
      activeQuizList.length > 0 &&
      !quizSubmitted &&
      Object.keys(quizAnswers).length > 0;

    if (hasUnsavedQuiz) {
      setShowExitConfirm(true);
    } else {
      setIsExpanded(false);
      setShowExitConfirm(false);
    }
  };

  const handleConfirmClose = () => {
    setShowExitConfirm(false);
    setIsExpanded(false);
  };

  const handleSend = async (customQuery?: string) => {
    const queryToSend = (customQuery || input).trim();
    if (!queryToSend || isStreaming) return;

    setInput('');
    if (!isExpanded) setIsExpanded(true);

    const userMsg: Message = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: queryToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);

    await startStream({
      query: queryToSend,
      articleId: currentArticleId,
      pageContext: pageContext,
      articleText: currentArticleText,
      onComplete: (finalText, finalCitations, finalQuizData, returnedActionType) => {
        if (finalText && finalText.trim()) {
          const assistantMsg: Message = {
            id: `asst_${Date.now()}`,
            role: 'assistant',
            content: finalText,
            citations: finalCitations,
            quizData: finalQuizData,
            actionType: (returnedActionType as 'chat' | 'quiz') || 'chat',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }

        // If returned action is quiz and contains quiz data, switch to quiz mode
        if (returnedActionType === 'quiz' && finalQuizData && finalQuizData.length > 0) {
          setActiveQuizList(finalQuizData);
          setQuizAnswers({});
          setQuizSubmitted(false);
          setMode('quiz');
        }
      },
    });
  };

  const handleResetChat = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          '👋 **AI Study Dock reset.**\n\nAsk me anything about current news, vocabulary explanations, or generate reading comprehension quizzes.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
    setActiveQuizList([]);
    setQuizAnswers({});
    setQuizSubmitted(false);
    setMode('chat');
  };

  const handleSelectQuizAnswer = (questionIdx: number, answerVal: string) => {
    if (quizSubmitted) return;
    setQuizAnswers((prev) => ({
      ...prev,
      [`${questionIdx}`]: answerVal,
    }));
  };

  const calculateQuizScore = () => {
    let score = 0;
    activeQuizList.forEach((q, idx) => {
      const blanks = getQuestionBlanks(q.question || '');
      if (blanks.length > 0) {
        const correctRaw = (q.correct_answer || '').toLowerCase();
        let allBlanksMatched = true;
        let anyBlankFilled = false;
        blanks.forEach((bNum) => {
          const userVal = (quizAnswers[`${idx}_blank_${bNum}`] || '').trim().toLowerCase();
          if (userVal) anyBlankFilled = true;
          if (!userVal || !correctRaw.includes(userVal)) {
            allBlanksMatched = false;
          }
        });
        if (anyBlankFilled && allBlanksMatched) {
          score++;
        }
      } else {
        const userAns = (quizAnswers[`${idx}`] || '').trim().toLowerCase();
        const correctAns = (q.correct_answer || '').trim().toLowerCase();
        if (userAns && (userAns === correctAns || correctAns.includes(userAns))) {
          score++;
        }
      }
    });
    return score;
  };

  const answeredCount = activeQuizList.filter((q, idx) => {
    const blanks = getQuestionBlanks(q.question || '');
    if (blanks.length > 0) {
      return blanks.some((b) => !!(quizAnswers[`${idx}_blank_${b}`] || '').trim());
    }
    return !!(quizAnswers[`${idx}`] || '').trim();
  }).length;
  const totalQuizCount = activeQuizList.length;

  return (
    <>
      {/* ── 1. Collapsed Left Dock Trigger Tab ── */}
      {!isExpanded && (
        <aside
          role="complementary"
          aria-label="AI Study Dock Tab"
          onClick={() => {
            setIsExpanded(true);
            setTimeout(() => inputRef.current?.focus(), 150);
          }}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-40 flex items-center bg-obsidian-950/90 hover:bg-slate-900 border-y border-r border-cyber-cyan/30 hover:border-cyber-cyan text-slate-300 hover:text-white px-2 py-4 rounded-r-2xl shadow-xl hover:shadow-cyan-500/20 backdrop-blur-md cursor-pointer transition-all duration-200 group"
          title="Open AI Study Dock (Ctrl + K)"
        >
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan group-hover:scale-110 transition-transform">
              <Bot className="w-4 h-4" />
            </div>
            <span
              className="text-xs font-bold tracking-wider uppercase text-slate-300 group-hover:text-cyber-cyan select-none"
              style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
            >
              AI Study Dock
            </span>
            <span className="text-[10px] font-mono text-slate-500 bg-white/5 px-1 py-0.5 rounded border border-white/10">
              Ctrl+K
            </span>
          </div>
        </aside>
      )}

      {/* ── 2. Expanded Left Dock Panel ── */}
      {isExpanded && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="AI Study Dock"
          className="fixed inset-y-0 left-0 z-50 w-full sm:w-[440px] md:w-[480px] bg-slate-950/95 backdrop-blur-2xl border-r border-white/10 shadow-2xl flex flex-col transition-all duration-300 animate-in slide-in-from-left duration-200"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3.5 border-b border-white/10 bg-white/[0.03]">
            <div className="flex items-center gap-2.5">
              {mode === 'quiz' ? (
                <button
                  onClick={() => setMode('chat')}
                  className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition flex items-center gap-1.5 text-xs font-semibold"
                  title="Back to Chat"
                >
                  <ArrowLeft className="w-4 h-4 text-cyber-cyan" />
                  <span>Back to Chat</span>
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-cyber-cyan/15 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                      AI Study Dock
                    </h3>
                    <p className="text-[10px] text-slate-400">Explainer • Hybrid RAG • Quiz</p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-1">
              {activeQuizList.length > 0 && mode === 'chat' && (
                <button
                  onClick={() => setMode('quiz')}
                  className="px-2 py-1 text-xs rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/30 font-medium transition flex items-center gap-1"
                  title="Resume Quiz"
                >
                  <FileQuestion className="w-3.5 h-3.5" />
                  <span>Resume Quiz ({answeredCount}/{totalQuizCount})</span>
                </button>
              )}

              <button
                onClick={handleResetChat}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition"
                title="Clear chat history"
                aria-label="Clear chat history"
              >
                <RotateCcw className="w-4 h-4" />
              </button>

              <button
                onClick={handleAttemptClose}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition"
                title="Close AI Dock (Esc)"
                aria-label="Collapse Dock"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Exit Confirmation Banner / Dialog */}
          {showExitConfirm && (
            <div className="bg-amber-500/10 border-b border-amber-500/30 p-3.5 animate-in fade-in duration-150">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="flex-1 text-xs text-amber-200">
                  <p className="font-semibold">Unfinished Quiz in Progress</p>
                  <p className="mt-0.5 text-slate-300 text-[11px]">
                    You have answered {answeredCount}/{totalQuizCount} questions. Your answers will be saved if you close.
                  </p>
                  <div className="flex items-center gap-2 mt-2.5">
                    <button
                      onClick={() => setShowExitConfirm(false)}
                      className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-white/10 hover:bg-white/20 text-white transition"
                    >
                      Keep Working
                    </button>
                    <button
                      onClick={handleConfirmClose}
                      className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 transition"
                    >
                      Close Dock
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Mode 1: CHAT VIEW ── */}
          {mode === 'chat' && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm font-sans">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.role === 'user' ? 'items-end' : 'items-start'
                  } space-y-1.5 animate-in fade-in duration-150`}
                >
                  <div
                    className={`max-w-[90%] rounded-2xl p-3.5 shadow-md text-xs sm:text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-br from-indigo-600 to-cyber-violet text-white rounded-br-none'
                        : 'bg-white/[0.04] border border-white/10 text-slate-200 rounded-bl-none'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <MarkdownView content={msg.content} />
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}

                    {/* Citations badges if present */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-white/10">
                        <p className="text-[11px] font-semibold text-cyber-cyan flex items-center gap-1 mb-1.5">
                          <BookOpen className="w-3 h-3" />
                          <span>Sources & Grounded Context ({msg.citations.length})</span>
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c, i) => (
                            <button
                              key={i}
                              onClick={() => setSelectedCitation(c)}
                              className="text-[11px] px-2 py-0.5 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white transition flex items-center gap-1 truncate max-w-[200px]"
                              title={c.title}
                            >
                              <span className="truncate">{c.title}</span>
                              {c.url && <ExternalLink className="w-2.5 h-2.5 shrink-0 opacity-60" />}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Quiz shortcut button if message generated quiz */}
                    {msg.quizData && msg.quizData.length > 0 && (
                      <div className="mt-3 pt-2 border-t border-white/10">
                        <button
                          onClick={() => {
                            setActiveQuizList(msg.quizData!);
                            setMode('quiz');
                          }}
                          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-cyber-cyan/15 hover:bg-cyber-cyan/25 border border-cyber-cyan/40 text-cyber-cyan font-bold text-xs transition"
                        >
                          <FileQuestion className="w-4 h-4" />
                          <span>Start Interactive Quiz ({msg.quizData.length} questions)</span>
                        </button>
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 px-1 font-mono">{msg.timestamp}</span>
                </div>
              ))}

              {/* Streaming Response Indicator */}
              {isStreaming && (
                <div className="flex flex-col items-start space-y-1.5 animate-in fade-in">
                  <div className="max-w-[90%] rounded-2xl rounded-bl-none p-3.5 bg-white/[0.04] border border-white/10 text-slate-200 text-xs sm:text-sm">
                    {streamedText ? (
                      <MarkdownView content={streamedText} />
                    ) : (
                      <div className="flex items-center gap-2 text-slate-400 text-xs py-1">
                        <div className="w-2 h-2 rounded-full bg-cyber-cyan animate-pulse" />
                        <span>AI thinking & retrieving context...</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Error banner */}
              {error && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{error}</span>
                </div>
              )}

              {/* Suggested Questions */}
              {messages.length <= 2 && !isStreaming && (
                <div className="pt-2">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-amber-400" />
                    <span>Suggested Actions</span>
                  </p>
                  <div className="space-y-1.5">
                    {SAMPLE_QUESTIONS.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => handleSend(q)}
                        className="w-full text-left text-xs p-2.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 hover:border-cyber-cyan/30 text-slate-300 hover:text-white transition flex items-center justify-between group"
                      >
                        <span className="line-clamp-2">{q}</span>
                        <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 text-cyber-cyan shrink-0 ml-1 transition" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {/* ── Mode 2: QUIZ VIEW ── */}
          {mode === 'quiz' && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm font-sans">
              {/* Quiz status banner */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs">
                <div>
                  <h4 className="font-bold text-white flex items-center gap-1.5">
                    <FileQuestion className="w-4 h-4 text-indigo-400" />
                    <span>Reading Comprehension Quiz</span>
                  </h4>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    Answered {answeredCount} of {totalQuizCount} questions
                  </p>
                </div>
                {quizSubmitted ? (
                  <div className="px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30 text-xs">
                    Score: {calculateQuizScore()} / {totalQuizCount}
                  </div>
                ) : (
                  <button
                    onClick={() => setQuizSubmitted(true)}
                    disabled={answeredCount === 0}
                    className={`px-3 py-1.5 rounded-lg font-bold text-xs transition ${
                      answeredCount > 0
                        ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md'
                        : 'bg-white/5 text-slate-500 cursor-not-allowed'
                    }`}
                  >
                    Submit Quiz
                  </button>
                )}
              </div>

              {/* Quiz Items List */}
              {activeQuizList.map((quiz, qIdx) => {
                const isYesNo = isYesNoType(quiz);
                const isFIB = isFillInBlankType(quiz);
                const blanks = getQuestionBlanks(quiz.question || '');
                const userSelected = quizAnswers[`${qIdx}`] || '';

                // Calculate question correctness for submitted view
                let isCorrect = false;
                if (isFIB && blanks.length > 0) {
                  const correctRaw = (quiz.correct_answer || '').toLowerCase();
                  isCorrect = blanks.every((b) => {
                    const uVal = (quizAnswers[`${qIdx}_blank_${b}`] || '').trim().toLowerCase();
                    return uVal && correctRaw.includes(uVal);
                  });
                } else {
                  isCorrect =
                    userSelected.trim().toLowerCase() === (quiz.correct_answer || '').trim().toLowerCase();
                }

                return (
                  <div
                    key={qIdx}
                    className={`p-4 rounded-2xl border transition-all ${
                      quizSubmitted
                        ? isCorrect
                          ? 'bg-emerald-950/20 border-emerald-500/40'
                          : 'bg-rose-950/20 border-rose-500/40'
                        : 'bg-white/[0.03] border-white/10 hover:border-white/20'
                    }`}
                  >
                    {/* Header: Question Number + Type Badge */}
                    <div className="flex items-center justify-between mb-2.5">
                      <span className="text-xs font-bold text-cyber-cyan uppercase tracking-wider">
                        Question {qIdx + 1}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 px-2 py-0.5 rounded bg-white/5">
                        {isYesNo
                          ? 'Yes / No / Not Given'
                          : isFIB
                            ? 'Summary Completion'
                            : quiz.quiz_type || 'Multiple Choice'}
                      </span>
                    </div>

                    {/* 1. YES / NO / NOT GIVEN (Dropdown Menu) */}
                    {isYesNo ? (
                      <div>
                        <p className="text-sm font-semibold text-slate-100 mb-3 leading-relaxed">
                          {quiz.question}
                        </p>
                        <div className="mt-2 space-y-1.5">
                          <label className="block text-[11px] font-medium text-slate-300">
                            Select your answer from dropdown:
                          </label>
                          <div className="relative">
                            <select
                              value={userSelected}
                              onChange={(e) => handleSelectQuizAnswer(qIdx, e.target.value)}
                              disabled={quizSubmitted}
                              className={`w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl bg-slate-900 border appearance-none cursor-pointer focus:outline-none transition-all pr-10 font-medium ${
                                quizSubmitted
                                  ? isCorrect
                                    ? 'border-emerald-500/80 bg-emerald-950/30 text-emerald-200'
                                    : 'border-rose-500/80 bg-rose-950/30 text-rose-200'
                                  : userSelected
                                    ? 'border-indigo-500/80 bg-indigo-950/20 text-white'
                                    : 'border-white/10 text-slate-300 hover:border-white/20'
                              }`}
                            >
                              <option value="" disabled className="bg-slate-900 text-slate-500">
                                -- Select an option (YES / NO / NOT GIVEN) --
                              </option>
                              {(quiz.options && quiz.options.length > 0
                                ? quiz.options
                                : ['YES', 'NO', 'NOT GIVEN']
                              ).map((opt: string, optIdx: number) => (
                                <option key={optIdx} value={opt} className="bg-slate-900 text-slate-100">
                                  {opt}
                                </option>
                              ))}
                            </select>
                            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400">
                              <ChevronDown className="w-4 h-4" />
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : isFIB ? (
                      /* 2. FILL IN THE BLANKS (IELTS Format) */
                      blanks.length > 0 ? (
                        <div className="space-y-2">
                          <p className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                            <PenLine className="w-3.5 h-3.5 text-cyber-cyan" />
                            <span>Type the missing words directly into the numbered blanks below:</span>
                          </p>

                          {/* IELTS Style Inline Passage with Embedded Textboxes */}
                          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 text-xs sm:text-sm text-slate-200 leading-loose font-sans">
                            {(quiz.question || '').split(/(\[\d+\][\s_–—]*|\(\d+\)[\s_–—]*)/g).map((part: string, pIdx: number) => {
                              const match = part.match(/\[(\d+)\]/) || part.match(/\((\d+)\)/);
                              if (match) {
                                const bNum = match[1];
                                const blankKey = `${qIdx}_blank_${bNum}`;
                                const bVal = quizAnswers[blankKey] || '';
                                const isBlankRight =
                                  quizSubmitted &&
                                  (quiz.correct_answer || '').toLowerCase().includes(bVal.trim().toLowerCase()) &&
                                  bVal.trim().length > 0;

                                return (
                                  <span key={pIdx} className="inline-flex items-center mx-1 my-0.5 align-baseline">
                                    <span className="inline-flex items-center justify-center px-2 py-1 rounded-l-lg bg-cyber-cyan/15 border border-r-0 border-cyber-cyan/40 text-cyber-cyan font-mono text-xs font-bold select-none">
                                      [{bNum}]
                                    </span>
                                    <input
                                      type="text"
                                      value={bVal}
                                      onChange={(e) => {
                                        const val = e.target.value;
                                        setQuizAnswers((prev) => ({
                                          ...prev,
                                          [blankKey]: val,
                                          [`${qIdx}`]: val,
                                        }));
                                      }}
                                      disabled={quizSubmitted}
                                      placeholder="type here..."
                                      className={`px-2.5 py-1 text-xs sm:text-sm rounded-r-lg border font-sans transition-all w-28 sm:w-36 focus:outline-none ${
                                        quizSubmitted
                                          ? isBlankRight
                                            ? 'bg-emerald-950/60 border-emerald-500 text-emerald-200 font-semibold'
                                            : 'bg-rose-950/60 border-rose-500 text-rose-200'
                                          : 'bg-slate-900 border-cyber-cyan/40 focus:border-cyber-cyan text-white shadow-inner'
                                      }`}
                                    />
                                  </span>
                                );
                              }
                              return <span key={pIdx}>{part}</span>;
                            })}
                          </div>
                        </div>
                      ) : (
                        /* Single missing word / phrase */
                        <div>
                          <p className="text-sm font-semibold text-slate-100 mb-3 leading-relaxed">
                            {quiz.question}
                          </p>
                          <div className="mt-2 space-y-1.5">
                            <label className="block text-[11px] font-medium text-slate-300">
                              Enter the missing word or phrase from the passage:
                            </label>
                            <input
                              type="text"
                              value={quizAnswers[`${qIdx}`] || ''}
                              onChange={(e) => handleSelectQuizAnswer(qIdx, e.target.value)}
                              disabled={quizSubmitted}
                              placeholder="Type your answer here..."
                              className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl bg-slate-900 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:border-cyber-cyan transition-colors"
                            />
                          </div>
                        </div>
                      )
                    ) : (
                      /* 3. MULTIPLE CHOICE BUTTONS */
                      <div>
                        <p className="text-sm font-semibold text-slate-100 mb-3 leading-relaxed">
                          {quiz.question}
                        </p>
                        <div className="space-y-2 mt-3">
                          {(quiz.options || []).map((opt: string, optIdx: number) => {
                            const isOptionSelected = userSelected === opt;
                            const isThisCorrect =
                              (quiz.correct_answer || '').trim().toLowerCase() === opt.trim().toLowerCase();

                            let optionClass = 'bg-white/[0.02] border-white/10 text-slate-300 hover:bg-white/[0.06]';
                            if (isOptionSelected) {
                              optionClass = 'bg-indigo-600/30 border-indigo-500 text-white font-medium';
                            }
                            if (quizSubmitted) {
                              if (isThisCorrect) {
                                optionClass = 'bg-emerald-500/20 border-emerald-500 text-emerald-200 font-bold';
                              } else if (isOptionSelected && !isThisCorrect) {
                                optionClass = 'bg-rose-500/20 border-rose-500 text-rose-200';
                              }
                            }

                            return (
                              <button
                                key={optIdx}
                                onClick={() => handleSelectQuizAnswer(qIdx, opt)}
                                disabled={quizSubmitted}
                                className={`w-full text-left p-2.5 rounded-xl border text-xs leading-relaxed flex items-center justify-between transition cursor-pointer ${optionClass}`}
                              >
                                <div className="flex items-center gap-2.5">
                                  <span className="w-5 h-5 rounded-full border border-white/20 flex items-center justify-center text-[11px] font-mono text-slate-400 shrink-0">
                                    {String.fromCharCode(65 + optIdx)}
                                  </span>
                                  <span>{opt}</span>
                                </div>
                                {quizSubmitted && isThisCorrect && (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 ml-2" />
                                )}
                                {quizSubmitted && isOptionSelected && !isThisCorrect && (
                                  <XCircle className="w-4 h-4 text-rose-400 shrink-0 ml-2" />
                                )}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Explanations & Supporting Quotes after submission */}
                    {quizSubmitted && (
                      <div className="mt-3 pt-3 border-t border-white/10 text-xs space-y-2">
                        {isFIB && blanks.length > 0 && (
                          <div className="p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-500/20 text-indigo-200 text-[11px]">
                            <span className="font-semibold text-indigo-400 block mb-0.5">
                              ✓ Correct Answers:
                            </span>
                            <span className="font-mono">{quiz.correct_answer}</span>
                          </div>
                        )}
                        {quiz.supporting_text && (
                          <div className="p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-500/20 text-cyan-200 text-[11px]">
                            <p className="font-semibold text-cyan-400 mb-0.5">📖 Supporting Passage Text:</p>
                            <p className="italic">"{quiz.supporting_text}"</p>
                          </div>
                        )}
                        {quiz.explanation && (
                          <div className="text-slate-300 text-[11px]">
                            <span className="font-semibold text-indigo-300">Explanation: </span>
                            {quiz.explanation}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Footer Chat Input (Chat Mode) ── */}
          {mode === 'chat' && (
            <div className="p-3 border-t border-white/10 bg-slate-950/80">
              {/* ── Quick Action Dock (above input) ── */}
              <div className="flex items-center gap-1.5 mb-2 overflow-x-auto pb-0.5 no-scrollbar">
                <button
                  type="button"
                  onClick={() =>
                    handleSend(
                      pageContext === 'readspace'
                        ? 'Generate a reading comprehension quiz for this article'
                        : 'Generate a reading comprehension quiz on recent news'
                    )
                  }
                  disabled={isStreaming}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 hover:border-indigo-400 text-indigo-200 text-xs font-semibold transition shrink-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-sm group"
                  title="Generate interactive reading quiz"
                >
                  <FileQuestion className="w-3.5 h-3.5 text-indigo-400 group-hover:scale-110 transition-transform" />
                  <span>Quiz</span>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    handleSend(
                      pageContext === 'readspace'
                        ? 'Summarize the key points and core takeaways of this article'
                        : 'Summarize the top current news headlines'
                    )
                  }
                  disabled={isStreaming}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 hover:border-cyan-400 text-cyan-200 text-xs font-semibold transition shrink-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-sm group"
                  title="Summarize reading passage"
                >
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
                  <span>Summarize</span>
                </button>
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
                className="flex items-center gap-2"
              >
                <div className="relative flex-1">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={
                      pageContext === 'readspace'
                        ? 'Ask about this article, words, or create a quiz...'
                        : 'Ask anything across news or reading topics...'
                    }
                    disabled={isStreaming}
                    className="w-full pl-3.5 pr-9 py-2.5 text-xs sm:text-sm bg-white/[0.04] hover:bg-white/[0.07] focus:bg-white/[0.07] border border-white/10 focus:border-cyber-cyan rounded-xl text-white placeholder-slate-500 focus:outline-none transition shadow-inner"
                  />
                  {input && (
                    <button
                      type="button"
                      onClick={() => setInput('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={!input.trim() || isStreaming}
                  className="p-2.5 rounded-xl bg-cyber-cyan hover:bg-cyan-400 disabled:opacity-30 disabled:hover:bg-cyber-cyan text-slate-950 font-bold transition shadow-lg hover:shadow-cyan-500/30 shrink-0 cursor-pointer disabled:cursor-not-allowed"
                  title="Send message (Enter)"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Citation Detail Modal */}
      {selectedCitation && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
        >
          <div className="w-full max-w-md bg-slate-900 border border-white/10 rounded-2xl p-5 shadow-2xl space-y-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-cyber-cyan" />
                <h4 className="text-sm font-bold text-white">Source Citation</h4>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-1 text-xs">
              <p className="font-semibold text-white">{selectedCitation.title}</p>
              {selectedCitation.article_id && (
                <p className="text-[11px] font-mono text-slate-400">ID: {selectedCitation.article_id}</p>
              )}
              {selectedCitation.keywords && selectedCitation.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {selectedCitation.keywords.map((kw, i) => (
                    <span key={i} className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 text-[10px]">
                      {kw}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {selectedCitation.url && (
              <a
                href={selectedCitation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-2 px-3 rounded-xl bg-cyber-cyan/15 hover:bg-cyber-cyan/25 border border-cyber-cyan/30 text-cyber-cyan text-xs font-semibold flex items-center justify-center gap-1.5 transition"
              >
                <span>Open Original Article</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      )}
    </>
  );
};
