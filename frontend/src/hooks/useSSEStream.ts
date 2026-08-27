import { useState, useCallback } from 'react';

export interface Citation {
  article_id: string;
  title: string;
  url?: string;
  theme?: string;
  rrf_score?: number;
}

export interface StreamState {
  isStreaming: boolean;
  streamedText: string;
  citations: Citation[];
  error: string | null;
}

export type StreamCompleteCallback = (finalText: string, citations: Citation[]) => void;

export function useSSEStream() {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    streamedText: '',
    citations: [],
    error: null,
  });

  const startStream = useCallback(
    async (
      question: string,
      articleId?: string,
      onComplete?: StreamCompleteCallback
    ) => {
      setState({
        isStreaming: true,
        streamedText: '',
        citations: [],
        error: null,
      });

      try {
        const response = await fetch('/readspace/api/rag/stream/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ question, article_id: articleId }),
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}: Failed to connect to stream`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let accumulatedText = '';
        let accumulatedCitations: Citation[] = [];

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          const chunkStr = decoder.decode(value, { stream: true });
          const lines = chunkStr.split('\n\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataPayload = line.replace('data: ', '').trim();
              if (dataPayload === '[DONE]') {
                setState((prev) => ({ ...prev, isStreaming: false }));
                if (onComplete) {
                  onComplete(accumulatedText, accumulatedCitations);
                }
                return;
              }

              try {
                const parsed = JSON.parse(dataPayload);
                if (parsed.type === 'metadata') {
                  accumulatedCitations = parsed.citations || [];
                  setState((prev) => ({ ...prev, citations: accumulatedCitations }));
                } else if (parsed.type === 'delta') {
                  accumulatedText += parsed.text || '';
                  setState((prev) => ({
                    ...prev,
                    streamedText: accumulatedText,
                  }));
                }
              } catch {
                // Ignore non-JSON or partial lines
              }
            }
          }
        }

        setState((prev) => ({ ...prev, isStreaming: false }));
        if (onComplete && accumulatedText) {
          onComplete(accumulatedText, accumulatedCitations);
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Stream error occurred';
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: message,
        }));
      }
    },
    []
  );

  return { ...state, startStream };
}
