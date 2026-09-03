import React, { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';

interface MarkdownViewProps {
  content: string;
  className?: string;
}

export const MarkdownView: React.FC<MarkdownViewProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Split content by code blocks first
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className={`markdown-view space-y-3 leading-relaxed text-slate-200 text-sm ${className}`}>
      {parts.map((part, index) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          return <CodeBlock key={index} codeChunk={part} />;
        }
        return <FormattedBlocks key={index} textChunk={part} />;
      })}
    </div>
  );
};

const CodeBlock: React.FC<{ codeChunk: string }> = ({ codeChunk }) => {
  const [copied, setCopied] = useState(false);
  const lines = codeChunk.slice(3, -3).trim().split('\n');
  const language = (lines[0].trim().toLowerCase() || 'text');
  const code = lines.slice(lines[0].match(/^[a-zA-Z0-9_-]+$/) ? 1 : 0).join('\n');

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-white/10 bg-obsidian-950/80 shadow-lg text-xs">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-white/[0.04] border-b border-white/10 text-slate-400 font-mono text-[11px]">
        <span className="uppercase tracking-wider text-cyber-cyan font-semibold">{language.toUpperCase()}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-white transition-colors cursor-pointer px-2 py-0.5 rounded hover:bg-white/10"
          aria-label="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-cyber-emerald" />
              <span className="text-cyber-emerald">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto text-slate-200 font-mono leading-normal">
        <code>{code}</code>
      </pre>
    </div>
  );
};

const FormattedBlocks: React.FC<{ textChunk: string }> = ({ textChunk }) => {
  const rawLines = textChunk.split('\n');
  const blocks: React.ReactNode[] = [];
  let currentParagraph: string[] = [];

  const flushParagraph = (idx: number) => {
    if (currentParagraph.length > 0) {
      const text = currentParagraph.join('\n');
      blocks.push(
        <p key={`p-${idx}`} className="text-slate-300 leading-relaxed">
          {currentParagraph.map((line, lIdx) => (
            <React.Fragment key={lIdx}>
              {renderInlineStyles(line)}
              {lIdx < currentParagraph.length - 1 && <br />}
            </React.Fragment>
          ))}
        </p>
      );
      currentParagraph = [];
    }
  };

  let i = 0;
  while (i < rawLines.length) {
    const line = rawLines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph(i);
      i++;
      continue;
    }

    // Heading 3: ### ...
    if (trimmed.startsWith('### ')) {
      flushParagraph(i);
      blocks.push(
        <h3 key={`h3-${i}`} className="text-base font-bold text-white mt-3 mb-1.5 flex items-center gap-1.5">
          <span className="w-1.5 h-4 rounded-full bg-cyber-cyan inline-block" />
          {renderInlineStyles(trimmed.slice(4))}
        </h3>
      );
      i++;
      continue;
    }

    // Heading 2: ## ...
    if (trimmed.startsWith('## ')) {
      flushParagraph(i);
      blocks.push(
        <h2 key={`h2-${i}`} className="text-lg font-bold text-white mt-4 mb-2 pb-1 border-b border-white/10 flex items-center gap-2">
          <span className="w-2 h-5 rounded-full bg-cyber-violet inline-block" />
          {renderInlineStyles(trimmed.slice(3))}
        </h2>
      );
      i++;
      continue;
    }

    // Heading 1: # ...
    if (trimmed.startsWith('# ')) {
      flushParagraph(i);
      blocks.push(
        <h1 key={`h1-${i}`} className="text-xl font-extrabold text-white mt-4 mb-2 flex items-center gap-2">
          {renderInlineStyles(trimmed.slice(2))}
        </h1>
      );
      i++;
      continue;
    }

    // Blockquote: > ...
    if (trimmed.startsWith('> ')) {
      flushParagraph(i);
      blocks.push(
        <blockquote key={`bq-${i}`} className="pl-3.5 py-1.5 border-l-2 border-cyber-cyan bg-cyber-cyan/5 rounded-r-lg my-2 text-slate-300 italic text-xs">
          {renderInlineStyles(trimmed.slice(2))}
        </blockquote>
      );
      i++;
      continue;
    }

    // Markdown Table: | col | col |
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushParagraph(i);
      const tableLines: string[] = [];
      while (i < rawLines.length && rawLines[i].trim().startsWith('|')) {
        tableLines.push(rawLines[i].trim());
        i++;
      }
      blocks.push(<MarkdownTable key={`tbl-${i}`} tableLines={tableLines} />);
      continue;
    }

    // Unordered List: - or *
    if (/^[-*•]\s+/.test(trimmed)) {
      flushParagraph(i);
      const listItems: string[] = [];
      while (i < rawLines.length && /^[-*•]\s+/.test(rawLines[i].trim())) {
        listItems.push(rawLines[i].trim().replace(/^[-*•]\s+/, ''));
        i++;
      }
      blocks.push(
        <ul key={`ul-${i}`} className="space-y-1.5 my-2 pl-4 list-disc marker:text-cyber-cyan text-slate-300">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx}>{renderInlineStyles(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered List: 1. 2.
    if (/^\d+\.\s+/.test(trimmed)) {
      flushParagraph(i);
      const listItems: string[] = [];
      while (i < rawLines.length && /^\d+\.\s+/.test(rawLines[i].trim())) {
        listItems.push(rawLines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      blocks.push(
        <ol key={`ol-${i}`} className="space-y-1.5 my-2 pl-4 list-decimal marker:text-cyber-cyan text-slate-300">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx}>{renderInlineStyles(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    // Standard paragraph line
    currentParagraph.push(line);
    i++;
  }

  flushParagraph(rawLines.length);
  return <>{blocks}</>;
};

const MarkdownTable: React.FC<{ tableLines: string[] }> = ({ tableLines }) => {
  const filtered = tableLines.filter(r => !r.includes('---'));
  const rows = filtered.map(r => r.split('|').map(c => c.trim()).filter(Boolean));

  if (rows.length === 0) return null;
  const [header, ...body] = rows;

  return (
    <div className="overflow-x-auto my-3 rounded-xl border border-white/10 shadow-md">
      <table className="w-full text-left border-collapse text-xs">
        {header && (
          <thead>
            <tr className="bg-white/[0.06] border-b border-white/10 text-white font-semibold">
              {header.map((col, idx) => (
                <th key={idx} className="p-2.5">{renderInlineStyles(col)}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="divide-y divide-white/5 bg-white/[0.02]">
          {body.map((row, rIdx) => (
            <tr key={rIdx} className="hover:bg-white/[0.04] transition-colors">
              {row.map((cell, cIdx) => (
                <td key={cIdx} className="p-2.5 text-slate-300">{renderInlineStyles(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/**
 * Parses inline formatting: Bold, Italic, Inline Code, KaTeX Math ($...$), Links [text](url).
 */
function renderInlineStyles(text: string): React.ReactNode {
  if (!text) return null;

  const tokens = text.split(/(`[^`]+`|\$[^$]+\$|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|\*[^*]+\*)/g);

  return tokens.map((tok, idx) => {
    if (tok.startsWith('`') && tok.endsWith('`')) {
      return (
        <code key={idx} className="px-1.5 py-0.5 mx-0.5 rounded-md bg-white/[0.08] text-cyber-cyan font-mono text-[11px] border border-white/10">
          {tok.slice(1, -1)}
        </code>
      );
    }
    if (tok.startsWith('$') && tok.endsWith('$')) {
      return (
        <span key={idx} className="px-1.5 py-0.5 mx-0.5 rounded bg-purple-900/30 text-amber-300 font-mono text-[11px] border border-purple-500/20 italic">
          {tok.slice(1, -1)}
        </span>
      );
    }
    if (tok.startsWith('[') && tok.includes('](') && tok.endsWith(')')) {
      const match = tok.match(/\[(.*?)\]\((.*?)\)/);
      if (match) {
        const [, label, url] = match;
        return (
          <a
            key={idx}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-cyber-cyan hover:text-cyan-300 underline underline-offset-2 transition-colors font-medium"
          >
            {label}
            <ExternalLink className="w-3 h-3 inline shrink-0" />
          </a>
        );
      }
    }
    if (tok.startsWith('**') && tok.endsWith('**')) {
      return (
        <strong key={idx} className="text-white font-bold">
          {tok.slice(2, -2)}
        </strong>
      );
    }
    if (tok.startsWith('*') && tok.endsWith('*')) {
      return (
        <em key={idx} className="text-slate-300 italic">
          {tok.slice(1, -1)}
        </em>
      );
    }
    return tok;
  });
}
