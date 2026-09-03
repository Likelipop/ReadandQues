import { useState, useCallback } from 'react';

export interface Citation {
  article_id: string;
  title: string;
  url?: string;
  theme?: string;
  keywords?: string[];
  rrf_score?: number;
}

export interface StreamState {
  isStreaming: boolean;
  streamedText: string;
  citations: Citation[];
  quizData: any[];
  actionType: 'chat' | 'quiz';
  intent: string;
  error: string | null;
}

export interface StreamOptions {
  query: string;
  articleId?: string;
  pageContext?: string;
  articleText?: string;
  endpoint?: string;
  onComplete?: (finalText: string, citations: Citation[], quizData?: any[], actionType?: string) => void;
}

export type StreamCompleteCallback = (
  finalText: string,
  citations: Citation[],
  quizData?: any[],
  actionType?: string
) => void;

export function useSSEStream() {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    streamedText: '',
    citations: [],
    quizData: [],
    actionType: 'chat',
    intent: 'rag',
    error: null,
  });

  const startStream = useCallback(
    async (
      queryOrOptions: string | StreamOptions,
      articleId?: string,
      onComplete?: StreamCompleteCallback
    ) => {
      let query = '';
      let activeArticleId = articleId || '';
      let pageContext = 'homepage';
      let articleText = '';
      let endpoint = '/readspace/api/study-dock/stream/';
      let completeCallback = onComplete;

      if (typeof queryOrOptions === 'object') {
        query = queryOrOptions.query;
        activeArticleId = queryOrOptions.articleId || articleId || '';
        pageContext = queryOrOptions.pageContext || 'homepage';
        articleText = queryOrOptions.articleText || '';
        endpoint = queryOrOptions.endpoint || '/readspace/api/study-dock/stream/';
        completeCallback = queryOrOptions.onComplete || onComplete;
      } else {
        query = queryOrOptions;
      }

      setState({
        isStreaming: true,
        streamedText: '',
        citations: [],
        quizData: [],
        actionType: 'chat',
        intent: 'rag',
        error: null,
      });

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query,
            question: query,
            article_id: activeArticleId,
            page_context: pageContext,
            article_text: articleText,
          }),
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}: Failed to connect to stream`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let accumulatedText = '';
        let accumulatedCitations: Citation[] = [];
        let accumulatedQuizData: any[] = [];
        let returnedActionType: 'chat' | 'quiz' = 'chat';
        let returnedIntent = 'rag';
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          // Keep trailing partial chunk in buffer
          buffer = events.pop() || '';

          for (const event of events) {
            const trimmed = event.trim();
            if (!trimmed) continue;
            const lines = trimmed.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataPayload = line.replace('data: ', '').trim();
                if (dataPayload === '[DONE]') {
                  setState((prev) => ({ ...prev, isStreaming: false }));
                  if (completeCallback) {
                    completeCallback(accumulatedText, accumulatedCitations, accumulatedQuizData, returnedActionType);
                  }
                  return;
                }

                try {
                  const parsed = JSON.parse(dataPayload);
                  if (parsed.type === 'metadata' || parsed.type === 'metadata_final') {
                    if (parsed.citations) accumulatedCitations = parsed.citations;
                    if (parsed.quiz_data) accumulatedQuizData = parsed.quiz_data;
                    if (parsed.action_type) returnedActionType = parsed.action_type === 'quiz' ? 'quiz' : 'chat';
                    if (parsed.intent) returnedIntent = parsed.intent;
                    setState((prev) => ({
                      ...prev,
                      citations: accumulatedCitations,
                      quizData: accumulatedQuizData,
                      actionType: returnedActionType,
                      intent: returnedIntent,
                      error: parsed.error || prev.error,
                    }));
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
        }

        setState((prev) => ({ ...prev, isStreaming: false }));
        if (completeCallback) {
          completeCallback(accumulatedText, accumulatedCitations, accumulatedQuizData, returnedActionType);
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Stream error occurred';
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: message,
        }));
        if (completeCallback) {
          completeCallback(`⚠️ **Error:** ${message}`, [], [], 'chat');
        }
      }
    },
    []
  );

  return { ...state, startStream };
}
