import React, { useEffect, useState } from 'react';
import { HelpCircle, Clock, CheckCircle2, XCircle, AlertCircle, RefreshCw, Loader2, ChevronDown } from 'lucide-react';
import { Article, Quiz } from '../../types';
import { useWorkspace } from '../../store';
import { CitationTooltip } from '../../components/ui/CitationTooltip';
import { api } from '../../api/client';

interface QuizSidebarProps {
  article: Article;
  onRefreshArticle?: () => void;
}

export const QuizSidebar: React.FC<QuizSidebarProps> = ({
  article,
  onRefreshArticle,
}) => {
  const {
    quizAnswers,
    setAnswer,
    quizSubmitted,
    score,
    totalQuestions,
    submitQuiz,
    elapsedSeconds,
    tickTimer,
  } = useWorkspace();

  const [isPolling, setIsPolling] = useState(false);
  const [pollStatus, setPollStatus] = useState(article.status || 'pending');

  const articleId = article.id || article.article_id || '';
  const exams = article.exams && article.exams.length > 0 ? article.exams[0] : null;
  const quizzes: Quiz[] = exams?.quizzes || [];

  // Stopwatch timer tick
  useEffect(() => {
    const interval = setInterval(() => {
      tickTimer();
    }, 1000);
    return () => clearInterval(interval);
  }, [tickTimer]);

  // Format timer as mm:ss
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // Dynamic status polling if quizzes are generating
  useEffect(() => {
    if (quizzes.length > 0 || quizSubmitted) return;

    let timer: ReturnType<typeof setTimeout> | undefined;
    const checkStatus = async () => {
      try {
        const res = await api.articles.status(articleId);
        setPollStatus(res.ai_status || res.status);
        if (res.has_quiz || res.ai_status === 'completed') {
          if (onRefreshArticle) onRefreshArticle();
        } else if (res.ai_status !== 'failed' && res.ai_status !== 'error') {
          timer = setTimeout(checkStatus, 3000);
        }
      } catch {
        // retry in 5s
        timer = setTimeout(checkStatus, 5000);
      }
    };

    setIsPolling(true);
    checkStatus();

    return () => clearTimeout(timer);
  }, [articleId, quizzes.length, quizSubmitted, onRefreshArticle]);

  const handleTriggerQuiz = async () => {
    try {
      await api.articles.triggerQuiz(articleId);
      setIsPolling(true);
      setPollStatus('processing');
    } catch {
      // ignore
    }
  };

  // Helper to parse Summary Completion Fill-in-the-Blank [1]...[5] into inline inputs
  const renderFIBText = (questionText: string, quizIndex: number) => {
    const parts = (questionText || '').split(/(\[\d+\][\s_–—]*|\(\d+\)[\s_–—]*)/g);
    return (
      <div className="text-xs text-slate-200 leading-loose font-sans">
        {parts.map((part, pIdx) => {
          const match = part.match(/\[(\d+)\]/) || part.match(/\((\d+)\)/);
          if (match) {
            const blankNumber = match[1];
            const key = `q_${quizIndex}_blank_${blankNumber}`;
            const value = quizAnswers[key] || '';

            return (
              <span key={pIdx} className="inline-flex items-center mx-1 my-0.5 align-baseline">
                <span className="inline-flex items-center justify-center px-1.5 py-0.5 rounded-l-md bg-cyber-violet/20 border border-r-0 border-cyber-violet/40 text-cyber-violet font-mono text-[11px] font-bold select-none">
                  [{blankNumber}]
                </span>
                <input
                  type="text"
                  value={value}
                  disabled={quizSubmitted}
                  onChange={(e) => setAnswer(key, e.target.value)}
                  placeholder="type here..."
                  className="px-2 py-0.5 bg-slate-900 border border-cyber-violet/40 focus:border-cyber-violet rounded-r-md text-xs text-white focus:outline-none w-28 sm:w-32"
                />
              </span>
            );
          }
          return <span key={pIdx}>{part}</span>;
        })}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-obsidian-900/60 rounded-2xl glass-card border border-white/10 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-cyber-violet/20 border border-cyber-violet/40 flex items-center justify-center">
            <HelpCircle className="w-4 h-4 text-cyber-violet" />
          </div>
          <div>
            <h3 className="font-bold text-xs text-white">Academic AI Quiz</h3>
            <p className="text-[10px] text-slate-400">Authentic reading comprehension</p>
          </div>
        </div>

        {/* Stopwatch Timer */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-xs font-mono font-bold text-slate-200 shadow-inner">
          <Clock className="w-3.5 h-3.5 text-cyber-cyan" />
          <span>{formatTime(elapsedSeconds)}</span>
        </div>
      </div>

      {/* Quiz List or In-Progress State */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 text-xs custom-scrollbar">
        {quizzes.length > 0 ? (
          <>
            {/* Score Banner when submitted */}
            {quizSubmitted && (
              <div className="p-4 rounded-xl bg-gradient-to-r from-cyber-violet/20 to-indigo-950/40 border border-cyber-violet/40 space-y-2 animate-in zoom-95 duration-200">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-cyber-cyan uppercase tracking-wider">
                    Exam Result
                  </span>
                  <span className="text-sm font-black text-white font-mono bg-cyber-violet/40 px-2.5 py-0.5 rounded-lg border border-cyber-violet/50">
                    Score: {score} / {totalQuestions || quizzes.length}
                  </span>
                </div>
                <p className="text-[11px] text-slate-300">
                  {score / Math.max(1, totalQuestions || quizzes.length) >= 0.7
                    ? '🎉 Excellent reading accuracy! Review the explanations and passage proofs below.'
                    : '📖 Good effort! Review the grounding proofs below to see exactly where each answer appears in the text.'}
                </p>
              </div>
            )}

            {/* Questions list */}
            {quizzes.map((quiz, idx) => {
              const qKey = `q_${idx}`;
              const selectedValue = quizAnswers[qKey] || '';
              const isCorrect =
                quizSubmitted &&
                selectedValue.trim().toLowerCase() ===
                  (quiz.correct_answer || '').trim().toLowerCase();

              return (
                <div
                  key={idx}
                  className={`p-5 rounded-2xl glass-card space-y-3 transition border ${
                    quizSubmitted
                      ? isCorrect
                        ? 'border-cyber-emerald/40 bg-emerald-500/[0.04]'
                        : 'border-red-500/40 bg-red-500/[0.04]'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  {/* Question Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2">
                      <span className="text-xs font-black text-cyber-violet bg-cyber-violet/10 px-2 py-0.5 rounded uppercase shrink-0">
                        {idx + 1}
                      </span>
                      <div>
                        <p className="font-bold text-white text-xs leading-snug">
                          {quiz.quiz_type === 'fill_in_blank'
                            ? 'Summary Completion'
                            : quiz.question}
                        </p>
                        <span className="text-[10px] text-slate-400 italic">
                          {quiz.quiz_type === 'yes_no_notgiven'
                            ? 'YES / NO / NOT GIVEN'
                            : quiz.quiz_type === 'multiple_choice'
                            ? 'Multiple Choice'
                            : 'Fill in the blanks with words from the passage'}
                        </span>
                      </div>
                    </div>

                    {/* Result Badge */}
                    {quizSubmitted && (
                      <span className="shrink-0">
                        {isCorrect ? (
                          <CheckCircle2 className="w-5 h-5 text-cyber-emerald" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-400" />
                        )}
                      </span>
                    )}
                  </div>

                  {/* 1. Dropdown for YES / NO / NOT GIVEN */}
                  {quiz.quiz_type === 'yes_no_notgiven' && (
                    <div className="mt-2 space-y-1.5">
                      <label className="block text-[11px] font-medium text-slate-300">
                        Select your response from dropdown:
                      </label>
                      <div className="relative">
                        <select
                          value={selectedValue}
                          disabled={quizSubmitted}
                          onChange={(e) => setAnswer(qKey, e.target.value)}
                          className={`w-full px-3.5 py-2 text-xs rounded-xl bg-slate-900 border appearance-none cursor-pointer focus:outline-none transition-all pr-10 font-medium ${
                            quizSubmitted
                              ? isCorrect
                                ? 'border-cyber-emerald/80 bg-emerald-950/30 text-emerald-200'
                                : 'border-red-500/80 bg-rose-950/30 text-rose-200'
                              : selectedValue
                                ? 'border-cyber-violet/80 bg-cyber-violet/20 text-white'
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
                  )}

                  {/* 2. Options for Multiple Choice */}
                  {quiz.quiz_type === 'multiple_choice' && quiz.options && (
                    <div className="space-y-2 pt-1">
                      {quiz.options.map((opt, optIdx) => {
                        const isThisSelected = selectedValue === opt;
                        const isThisCorrect =
                          quizSubmitted &&
                          opt.trim().toLowerCase() ===
                            (quiz.correct_answer || '').trim().toLowerCase();

                        return (
                          <label
                            key={optIdx}
                            className={`flex items-center gap-3 p-2.5 rounded-xl border transition cursor-pointer text-xs ${
                              isThisSelected
                                ? 'bg-cyber-violet/20 border-cyber-violet text-white'
                                : 'bg-white/[0.02] border-white/5 text-slate-300 hover:bg-white/[0.05]'
                            } ${
                              quizSubmitted && isThisCorrect
                                ? 'border-cyber-emerald bg-emerald-500/20 text-emerald-200 font-bold'
                                : ''
                            }`}
                          >
                            <input
                              type="radio"
                              name={`quiz_${idx}`}
                              value={opt}
                              checked={isThisSelected}
                              disabled={quizSubmitted}
                              onChange={() => setAnswer(qKey, opt)}
                              className="w-4 h-4 text-cyber-violet border-white/20 focus:ring-cyber-violet"
                            />
                            <span>{opt}</span>
                          </label>
                        );
                      })}
                    </div>
                  )}

                  {/* 3. Fill in the Blank Render */}
                  {quiz.quiz_type === 'fill_in_blank' && (
                    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                      {renderFIBText(quiz.question, idx)}
                    </div>
                  )}

                  {/* Post-submission Review: Explanation & Passage Proof Tooltip */}
                  {quizSubmitted && (
                    <div className="mt-3 pt-3 border-t border-white/10 space-y-2 text-[11px]">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-slate-400">
                          Correct Answer:{' '}
                          <strong className="text-cyber-emerald">{quiz.correct_answer}</strong>
                        </span>

                        {/* Passage Proof Grounding Tooltip */}
                        <CitationTooltip articleId={articleId} questionIdx={idx}>
                          Show Verbatim Proof
                        </CitationTooltip>
                      </div>

                      {quiz.explanation && (
                        <div className="p-2.5 rounded-lg bg-black/40 border border-white/5 text-slate-300 leading-relaxed">
                          <strong className="text-cyber-cyan block mb-0.5">Explanation:</strong>
                          {quiz.explanation}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Submit Exam Button */}
            {!quizSubmitted && (
              <button
                onClick={() => submitQuiz(articleId, quizzes.length)}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-cyber-emerald to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-black text-sm shadow-xl transition transform hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
              >
                Submit Exam Attempt
              </button>
            )}
          </>
        ) : (
          /* Processing / In-Progress State */
          <div className="p-8 glass-card text-center space-y-4 my-8">
            {pollStatus !== 'failed' && pollStatus !== 'error' ? (
              <>
                <Loader2 className="w-10 h-10 text-cyber-violet animate-spin mx-auto" />
                <h4 className="font-bold text-sm text-white">Generating AI Reading Quiz...</h4>
                <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto">
                  Our LangGraph AI agent is analyzing the text chunks and crafting authentic questions. You can keep reading on the left!
                </p>
              </>
            ) : (
              <>
                <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
                <h4 className="font-bold text-sm text-white">Quiz Generation Incomplete</h4>
                <p className="text-xs text-slate-400 max-w-xs mx-auto">
                  We could not automatically generate questions for this article, but the full text is available to read.
                </p>
                <button
                  onClick={handleTriggerQuiz}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-cyber-violet hover:bg-purple-600 text-white font-bold text-xs rounded-xl shadow transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Re-trigger AI Generation
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
