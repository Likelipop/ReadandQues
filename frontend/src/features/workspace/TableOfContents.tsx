import React from 'react';
import { BookOpen, ListFilter, Sparkles, Clock, Globe } from 'lucide-react';
import { Article } from '../../types';

interface TableOfContentsProps {
  article: Article;
  onJumpToSection?: (sectionId: string) => void;
}

export const TableOfContents: React.FC<TableOfContentsProps> = ({
  article,
}) => {
  const estimatedMin = Math.max(1, Math.ceil((article.word_count || 400) / 200));

  return (
    <aside className="space-y-6 text-xs">
      {/* Article Stats Panel */}
      <div className="glass-card p-4 space-y-3">
        <h4 className="font-bold text-white text-xs uppercase tracking-wider flex items-center gap-1.5 border-b border-white/10 pb-2">
          <BookOpen className="w-3.5 h-3.5 text-cyber-violet" />
          <span>Passage Intel</span>
        </h4>

        <div className="space-y-2 text-slate-300">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Theme</span>
            <span className="font-semibold text-cyber-cyan">{article.theme || 'General'}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Word Count</span>
            <span className="font-mono font-bold text-white">{article.word_count || 0}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Estimated Time</span>
            <span className="font-medium flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-400" /> {estimatedMin} mins
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Source</span>
            <span className="font-medium text-slate-200 truncate max-w-[120px]">
              {article.source_name || 'News'}
            </span>
          </div>
        </div>

        {article.url && (
          <div className="pt-2 border-t border-white/5">
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-cyber-cyan hover:underline"
            >
              <Globe className="w-3 h-3" /> View Original Source
            </a>
          </div>
        )}
      </div>

      {/* Reading Tips / AI Guidance */}
      <div className="glass-card p-4 space-y-2.5 border border-cyber-cyan/20">
        <div className="flex items-center gap-1.5 text-cyber-cyan font-bold text-xs uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Academic Reading Tips</span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          • Use the <strong>Marker</strong> tool to highlight keywords and supporting sentences.
        </p>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          • Select difficult sentences to trigger <strong>Smart Paraphrase</strong>.
        </p>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          • Submit the <strong>AI Quiz</strong> and click <em>Show Verbatim Proof</em> to see grounded excerpts.
        </p>
      </div>
    </aside>
  );
};
