import { useState, useCallback } from 'react';

export interface Citation {
  article_id: string;
  title: string;
  url?: string;
  theme?: string;
}

export interface StreamState {
  isStreaming: boolean;
  streamedText: string;
  citations: Citation[];
  error: string | null;
}

export function useSSEStream() {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    streamedText: '',
    citations: [],
    error: null,
  });

  const startStream = useCallback(async (question: string, articleId?: string) => {
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

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunkStr = decoder.decode(value, { stream: true });
        const lines = chunkStr.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataPayload = line.replace('data: ', '').strip ? line.replace('data: ', '').trim() : line.replace('data: ', '');
            if (dataPayload === '[DONE]') {
              setState((prev) => ({ ...prev, isStreaming: false }));
              return;
            }

            try {
              const parsed = JSON.parse(dataPayload);
              if (parsed.type === 'metadata') {
                setState((prev) => ({ ...prev, citations: parsed.citations || [] }));
              } else if (parsed.type === 'delta') {
                accumulatedText += parsed.text;
                setState((prev) => ({
                  ...prev,
                  streamedText: accumulatedText,
                }));
              }
            } catch (e) {
              // Ignore non-JSON lines
            }
          }
        }
      }

      setState((prev) => ({ ...prev, isStreaming: false }));
    } catch (err: any) {
      setState((prev) => ({
        ...prev,
        isStreaming: false,
        error: err.message || 'Stream error',
      }));
    }
  }, []);

  return { ...state, startStream };
}
