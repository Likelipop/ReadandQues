import React, { useState } from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';

export interface ProofData {
  proof_found: boolean;
  proof_excerpt?: string;
  confidence_score?: number;
  reason?: string;
}

interface CitationTooltipProps {
  articleId: string;
  questionIdx: number;
  children: React.ReactNode;
}

export const CitationTooltip: React.FC<CitationTooltipProps> = ({
  articleId,
  questionIdx,
  children,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [proofData, setProofData] = useState<ProofData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFetchProof = async () => {
    if (isOpen) {
      setIsOpen(false);
      return;
    }

    setIsOpen(true);
    setError(null);

    if (!proofData) {
      setLoading(true);
      try {
        const res = await fetch(`/readspace/${articleId}/proof/${questionIdx}/`);
        if (!res.ok) {
          throw new Error(`HTTP error ${res.status}`);
        }
        const json = await res.json();
        if (json.status === 'success') {
          setProofData(json.proof);
        } else {
          setError(json.message || 'Proof not found');
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Failed to fetch proof';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <span className="relative inline-block">
      <button
        onClick={handleFetchProof}
        aria-expanded={isOpen}
        aria-label="View passage grounding proof"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-cyber-cyan bg-cyber-cyan/10 border border-cyber-cyan/30 rounded-lg hover:bg-cyber-cyan/20 transition-all cursor-pointer"
      >
        {children}
      </button>

      {isOpen && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-80 p-4 glass-card glow-cyan z-50 animate-in fade-in zoom-95 duration-200"
        >
          {loading ? (
            <div className="flex items-center justify-center py-4 gap-2 text-slate-400 text-xs">
              <div className="w-3 h-3 border-2 border-cyber-cyan border-t-transparent rounded-full animate-spin" />
              Retrieving grounded paragraph proof...
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-xs text-red-400 py-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : proofData?.proof_found ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-cyber-emerald">
                <CheckCircle2 className="w-4 h-4" />
                Grounding Passage Proof
              </div>
              <p className="text-xs text-slate-300 italic bg-black/30 p-2.5 rounded-lg border border-white/5">
                "{proofData.proof_excerpt}"
              </p>
              <div className="text-[10px] text-slate-400 flex justify-between items-center pt-1">
                <span>
                  Confidence:{' '}
                  {proofData.confidence_score !== undefined
                    ? `${(proofData.confidence_score * 100).toFixed(0)}%`
                    : 'N/A'}
                </span>
                <span className="text-cyber-cyan font-medium">Paragraph Proof Match</span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-400 py-2">No paragraph proof excerpt available.</div>
          )}
        </div>
      )}
    </span>
  );
};
