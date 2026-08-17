import React, { useState } from 'react';
import { MessageSquare, X, Send, Bot, Sparkles, BookOpen } from 'lucide-react';
import { useSSEStream } from '../../hooks/useSSEStream';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: any[];
}

export const StudyBuddyWidget: React.FC<{ activeArticleId?: string }> = ({ activeArticleId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hi! I am your AI Study Buddy. Ask me anything about IELTS news or reading comprehension!',
    },
  ]);

  const { isStreaming, streamedText, citations, startStream } = useSSEStream();

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userQ = input.trim();
    setInput('');

    setMessages((prev) => [...prev, { role: 'user', content: userQ }]);

    // Trigger streaming hook
    await startStream(userQ, activeArticleId);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2.5 px-5 py-3.5 bg-gradient-to-r from-cyber-violet to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold rounded-full shadow-2xl glow-violet transition-all duration-300 transform hover:scale-105 active:scale-95 cursor-pointer"
        >
          <Bot className="w-5 h-5 text-cyber-cyan animate-pulse" />
          <span>Study Buddy AI</span>
          <Sparkles className="w-4 h-4 text-amber-300" />
        </button>
      ) : (
        <div className="w-[380px] h-[520px] glass-card glow-violet flex flex-col overflow-hidden animate-in slide-in-from-bottom-6 duration-300">
          {/* Header */}
          <div className="p-4 bg-white/[0.06] border-b border-white/10 flex justify-between items-center">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-cyber-violet/20 border border-cyber-violet/40 flex items-center justify-center">
                <Bot className="w-4 h-4 text-cyber-cyan" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                  Study Buddy RAG
                  <span className="w-2 h-2 rounded-full bg-cyber-emerald animate-ping" />
                </h4>
                <p className="text-[10px] text-slate-400">
                  {activeArticleId ? 'Workspace Article Context' : 'Global IELTS News RAG'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-full bg-cyber-cyan/20 border border-cyber-cyan/40 flex items-center justify-center shrink-0">
                    <Bot className="w-3.5 h-3.5 text-cyber-cyan" />
                  </div>
                )}
                <div
                  className={`p-3 rounded-2xl max-w-[82%] leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-cyber-violet text-white rounded-br-none'
                      : 'bg-white/[0.07] border border-white/10 text-slate-200 rounded-bl-none'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Live Streaming Message */}
            {isStreaming && (
              <div className="flex gap-2.5 justify-start">
                <div className="w-6 h-6 rounded-full bg-cyber-cyan/20 border border-cyber-cyan/40 flex items-center justify-center shrink-0 animate-pulse">
                  <Bot className="w-3.5 h-3.5 text-cyber-cyan" />
                </div>
                <div className="p-3 rounded-2xl max-w-[82%] bg-white/[0.07] border border-white/10 text-slate-200 rounded-bl-none">
                  {streamedText || <span className="animate-pulse">Thinking...</span>}
                  {citations.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-white/10 text-[10px] space-y-1">
                      <div className="text-cyber-cyan font-semibold flex items-center gap-1">
                        <BookOpen className="w-3 h-3" /> Grounded Sources:
                      </div>
                      {citations.map((c, idx) => (
                        <div key={idx} className="text-slate-400 truncate">
                          • {c.title}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-3 bg-white/[0.04] border-t border-white/10 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a question..."
              className="flex-1 bg-white/[0.06] border border-white/10 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyber-violet transition-all"
            />
            <button
              onClick={handleSend}
              disabled={isStreaming || !input.trim()}
              className="p-2 bg-cyber-violet hover:bg-purple-600 disabled:opacity-50 text-white rounded-xl transition-all cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
