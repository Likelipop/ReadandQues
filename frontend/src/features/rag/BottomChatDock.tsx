import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  Sparkles,
  BookOpen,
  AlertCircle,
  ChevronUp,
  ChevronDown,
  Maximize2,
  Minimize2,
  Trash2,
  X,
  Layers,
  Terminal,
  ExternalLink,
  RotateCcw,
} from 'lucide-react';
import { useSSEStream, Citation } from '../../hooks/useSSEStream';
import { MarkdownView } from '../../components/common/MarkdownView';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp: string;
}

const SAMPLE_QUESTIONS = [
  'What are the primary factors driving climate change in recent news?',
  'Summarize key academic concepts and IELTS vocabulary from today\'s articles.',
  'How does AI automation impact economic productivity and jobs?',
];

export const BottomChatDock: React.FC<{ activeArticleId?: string }> = ({ activeArticleId }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [input, setInput] = useState('');
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        '👋 **Hello! I am your AI Study Dock & RAG Assistant.**\n\nAsk me anything about current news, article concepts, or reading comprehension. I use **Semantic Chunking + Hybrid BM25 & Dense Vector Search with Cross-Encoder Reranking** to deliver grounded, precise insights.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { isStreaming, streamedText, citations, error, startStream } = useSSEStream();

  // Scroll to bottom on new message or stream chunk
  useEffect(() => {
    if (isExpanded) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamedText, isExpanded]);

  // Global Keyboard Shortcut: Ctrl + K or Cmd + K to toggle dock
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsExpanded((prev) => !prev);
        setTimeout(() => inputRef.current?.focus(), 150);
      }
      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isExpanded]);

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

    await startStream(queryToSend, activeArticleId, (finalText, finalCitations) => {
      if (finalText.trim()) {
        const assistantMsg: Message = {
          id: `asst_${Date.now()}`,
          role: 'assistant',
          content: finalText,
          citations: finalCitations,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    });
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome_reset',
        role: 'assistant',
        content: '🧹 *Chat history reset. How can I assist your reading today?*',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // Collect all active citations from the latest response
  const activeCitations =
    isStreaming && citations.length > 0
      ? citations
      : messages[messages.length - 1]?.citations || [];

  return (
    <div
      role="region"
      aria-label="AI Study Dock Chat"
      className="fixed bottom-0 left-0 right-0 z-40 flex flex-col items-center pointer-events-none"
    >
      {/* ── COLLAPSED BAR (Docked at Bottom Center) ────────────────────────── */}
      {!isExpanded && (
        <div className="pointer-events-auto w-full max-w-3xl px-4 pb-3 animate-in slide-in-from-bottom-4 duration-300">
          <div
            onClick={() => {
              setIsExpanded(true);
              setTimeout(() => inputRef.current?.focus(), 150);
            }}
            className="group relative flex items-center justify-between gap-3 px-4 py-3 bg-obsidian-950/90 hover:bg-obsidian-900 border border-white/15 hover:border-cyber-violet/60 rounded-2xl shadow-2xl backdrop-blur-xl transition-all duration-300 cursor-pointer glow-violet"
          >
            {/* Glowing Accent Ring */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-cyber-violet/20 via-cyber-cyan/20 to-indigo-600/20 rounded-2xl blur-sm opacity-50 group-hover:opacity-100 transition-opacity" />

            <div className="relative flex items-center gap-3 flex-1 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyber-violet to-indigo-600 flex items-center justify-center shadow-md shrink-0">
                <Bot className="w-4 h-4 text-cyber-cyan animate-pulse" />
              </div>
              <span className="text-sm font-medium text-slate-300 group-hover:text-white truncate">
                Ask AI Study Dock anything about news & comprehension...
              </span>
            </div>

            <div className="relative flex items-center gap-2 shrink-0">
              <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-lg bg-white/[0.08] text-slate-400 border border-white/10">
                <kbd className="font-semibold">Ctrl</kbd>+<kbd className="font-semibold">K</kbd>
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsExpanded(true);
                }}
                aria-label="Expand Chat Dock"
                className="p-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white transition-colors cursor-pointer"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── EXPANDED PANEL (VS Code Bottom Dock Style) ──────────────────────── */}
      {isExpanded && (
        <div
          role="dialog"
          aria-label="AI Study Dock Expanded Panel"
          className={`pointer-events-auto w-full transition-all duration-300 flex flex-col bg-obsidian-950/95 backdrop-blur-2xl border-t border-white/15 shadow-[0_-15px_40px_rgba(0,0,0,0.6)] ${
            isFullscreen ? 'h-screen' : 'h-[62vh] max-h-[750px] min-h-[420px]'
          }`}
        >
          {/* Header Bar */}
          <div className="flex items-center justify-between px-5 py-2.5 bg-white/[0.03] border-b border-white/10 select-none">
            {/* Left: Branding & Status */}
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyber-violet to-indigo-600 flex items-center justify-center shadow">
                <Bot className="w-4 h-4 text-cyber-cyan" />
              </div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  AI Study Dock
                  <span className="text-[10px] font-normal px-2 py-0.5 rounded-full bg-cyber-emerald/15 text-cyber-emerald border border-cyber-emerald/30 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyber-emerald animate-pulse" />
                    Hybrid RAG + Cross-Encoder
                  </span>
                </h3>
                <span className="text-xs text-slate-500 hidden md:inline">•</span>
                <span className="text-xs text-slate-400 hidden md:inline">
                  {activeArticleId ? `Context: Article ${activeArticleId}` : 'Global News Knowledge Base'}
                </span>
              </div>
            </div>

            {/* Right: Window Controls */}
            <div className="flex items-center gap-1.5 text-slate-400">
              <button
                onClick={handleClearHistory}
                aria-label="Clear chat history"
                title="Clear Chat History"
                className="p-1.5 rounded-lg hover:bg-white/10 hover:text-slate-200 transition-colors cursor-pointer text-xs flex items-center gap-1 mr-2"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Reset</span>
              </button>

              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                aria-label={isFullscreen ? 'Exit full height' : 'Expand full height'}
                title={isFullscreen ? 'Exit Fullscreen' : 'Full Height'}
                className="p-1.5 rounded-lg hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
              >
                {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>

              <button
                onClick={() => setIsExpanded(false)}
                aria-label="Collapse Dock"
                title="Collapse Dock (Esc)"
                className="p-1.5 rounded-lg hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Main Body: 2 Columns Layout (Split Chat + Citations Panel) */}
          <div className="flex-1 flex overflow-hidden">
            {/* Left Column: Chat Conversation Stream */}
            <div className="flex-1 flex flex-col min-w-0 border-r border-white/10">
              <div className="flex-1 p-5 overflow-y-auto space-y-4">
                {/* Initial Suggested Chips */}
                {messages.length <= 1 && (
                  <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/10 space-y-2.5 mb-4">
                    <div className="text-xs font-semibold text-cyber-cyan flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-300" /> Suggested Questions
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      {SAMPLE_QUESTIONS.map((q, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSend(q)}
                          className="text-left text-xs p-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 hover:text-white border border-white/5 hover:border-cyber-violet/40 transition-all cursor-pointer leading-snug"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Messages List */}
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-7 h-7 rounded-lg bg-cyber-violet/20 border border-cyber-violet/40 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="w-4 h-4 text-cyber-cyan" />
                      </div>
                    )}

                    <div
                      className={`max-w-[85%] rounded-2xl p-4 leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-cyber-violet text-white rounded-br-none shadow-lg'
                          : 'bg-white/[0.04] border border-white/10 text-slate-200 rounded-bl-none shadow-md'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4 mb-1 text-[11px] text-slate-400">
                        <span className="font-semibold text-slate-300">
                          {msg.role === 'user' ? 'You' : 'Study Dock AI'}
                        </span>
                        <span>{msg.timestamp}</span>
                      </div>

                      {msg.role === 'assistant' ? (
                        <MarkdownView content={msg.content} />
                      ) : (
                        <p className="whitespace-pre-wrap text-sm text-white">{msg.content}</p>
                      )}

                      {/* Inline Citation Badges */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-white/10 flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] font-semibold text-cyber-cyan flex items-center gap-1 mr-1">
                            <BookOpen className="w-3 h-3" /> Sources:
                          </span>
                          {msg.citations.map((c, cIdx) => (
                            <button
                              key={cIdx}
                              onClick={() => setSelectedCitation(c)}
                              className="text-[11px] px-2 py-0.5 rounded-md bg-white/[0.08] hover:bg-white/15 text-slate-300 hover:text-white border border-white/10 transition-colors flex items-center gap-1 cursor-pointer"
                            >
                              <span>[{cIdx + 1}] {c.title}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Streaming Assistant Response */}
                {isStreaming && (
                  <div className="flex gap-3.5 justify-start" aria-live="polite">
                    <div className="w-7 h-7 rounded-lg bg-cyber-violet/20 border border-cyber-violet/40 flex items-center justify-center shrink-0 mt-0.5 animate-pulse">
                      <Bot className="w-4 h-4 text-cyber-cyan" />
                    </div>
                    <div className="max-w-[85%] rounded-2xl rounded-bl-none p-4 bg-white/[0.04] border border-white/10 text-slate-200">
                      <div className="flex items-center gap-2 mb-1.5 text-[11px] text-cyber-cyan font-medium">
                        <span className="w-2 h-2 rounded-full bg-cyber-cyan animate-ping" />
                        Generating grounded answer...
                      </div>
                      {streamedText ? (
                        <MarkdownView content={streamedText} />
                      ) : (
                        <div className="text-slate-400 italic text-sm animate-pulse flex items-center gap-2">
                          <span>Synthesizing information from Top Reranked Chunks...</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {error && (
                  <div className="flex items-center gap-2.5 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Bottom Input Area */}
              <div className="p-3.5 bg-white/[0.02] border-t border-white/10">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSend();
                  }}
                  className="flex items-center gap-2 max-w-4xl mx-auto"
                >
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask a question about current news or reading comprehension..."
                    aria-label="Ask a question"
                    className="flex-1 bg-white/[0.06] border border-white/15 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyber-violet focus:ring-1 focus:ring-cyber-violet transition-all"
                  />
                  <button
                    type="submit"
                    disabled={isStreaming || !input.trim()}
                    aria-label="Send message"
                    className="flex items-center gap-1.5 px-4 py-2.5 bg-gradient-to-r from-cyber-violet to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 text-white font-medium text-sm rounded-xl shadow-lg transition-all cursor-pointer"
                  >
                    <Send className="w-4 h-4" />
                    <span className="hidden sm:inline">Send</span>
                  </button>
                </form>
              </div>
            </div>

            {/* Right Column: Grounded Chunks & Citations Drawer */}
            <div className="w-80 hidden lg:flex flex-col bg-white/[0.01] p-4 overflow-y-auto space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-white/10">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyber-cyan" /> Grounding Chunks
                </h4>
                <span className="text-[10px] font-mono text-slate-400">
                  {activeCitations.length} Citations
                </span>
              </div>

              {activeCitations.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-xs space-y-2">
                  <BookOpen className="w-6 h-6 mx-auto opacity-40" />
                  <p>No active citations yet.</p>
                  <p className="text-[11px] text-slate-600">
                    Retrieved documents and source verification will appear here.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {activeCitations.map((c, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl bg-white/[0.04] border border-white/10 hover:border-cyber-cyan/40 transition-all text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-white truncate">
                          [{i + 1}] {c.title}
                        </span>
                        {c.rrf_score && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyber-violet/20 text-cyber-cyan border border-cyber-violet/40 shrink-0">
                            Score: {c.rrf_score}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span className="px-1.5 py-0.5 rounded bg-white/5 text-slate-300">
                          {c.theme || 'General'}
                        </span>
                        {c.url && (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyber-cyan hover:underline flex items-center gap-1"
                          >
                            Open <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
