import React from 'react';
import { StudyBuddyWidget } from './features/rag/StudyBuddyWidget';
import { CitationTooltip } from './components/ui/CitationTooltip';
import { Sparkles, BookOpen, Compass, Trophy } from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-obsidian-900 text-slate-100 flex flex-col font-sans">
      {/* Navbar */}
      <header className="border-b border-white/10 bg-white/[0.02] backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyber-violet to-cyber-cyan flex items-center justify-center font-black text-white text-lg shadow-lg glow-violet">
              R
            </div>
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              ReadAndQues
            </span>
          </div>

          <nav className="flex items-center gap-6 text-sm font-medium text-slate-300">
            <a href="#" className="flex items-center gap-2 hover:text-cyber-cyan transition-all">
              <Compass className="w-4 h-4" /> Explore
            </a>
            <a href="#" className="flex items-center gap-2 hover:text-cyber-cyan transition-all">
              <BookOpen className="w-4 h-4" /> Workspace
            </a>
            <a href="#" className="flex items-center gap-2 hover:text-cyber-cyan transition-all">
              <Trophy className="w-4 h-4" /> Leaderboard
            </a>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-12 space-y-12">
        <section className="text-center space-y-4 max-w-3xl mx-auto pt-6">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyber-violet/10 border border-cyber-violet/30 text-cyber-violet text-xs font-semibold glow-violet">
            <Sparkles className="w-3.5 h-3.5" /> Next-Gen IELTS AI Reading Platform
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight">
            Master IELTS Reading with <span className="bg-gradient-to-r from-cyber-violet via-indigo-400 to-cyber-cyan bg-clip-text text-transparent">Real-Time RAG AI</span>
          </h1>
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            Practice authentic IELTS questions generated dynamically from daily world news. Verified by passage proof grounding and interactive Study Buddy AI.
          </p>
        </section>

        {/* Demo Proof Card */}
        <section className="glass-card p-8 max-w-2xl mx-auto space-y-4 glow-violet">
          <h3 className="text-sm font-bold text-cyber-cyan uppercase tracking-wider">Passage Proof Demonstration</h3>
          <p className="text-sm text-slate-300">
            Question 1: What is the primary cause of global agricultural vulnerability according to recent reports?
          </p>
          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-400">Correct Answer: Extreme weather shifts</span>
            <CitationTooltip articleId="art_demo" questionIdx={0}>
              Show Verbatim Proof
            </CitationTooltip>
          </div>
        </section>
      </main>

      {/* Floating RAG Chat Widget */}
      <StudyBuddyWidget />
    </div>
  );
}
