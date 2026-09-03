import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSSEStream } from '../useSSEStream';

describe('useSSEStream', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes with default idle state', () => {
    const { result } = renderHook(() => useSSEStream());
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.streamedText).toBe('');
    expect(result.current.citations).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('handles stream network failure gracefully', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.startStream('What is artificial intelligence?');
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBe('Network error');
  });

  it('parses SSE delta and metadata events correctly and triggers onComplete', async () => {
    const sseData = [
      'data: {"type": "metadata", "citations": [{"article_id": "1", "title": "Test Source"}]}\n\n',
      'data: {"type": "delta", "text": "Hello "}\n\n',
      'data: {"type": "delta", "text": "world!"}\n\n',
      'data: [DONE]\n\n',
    ].join('');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData));
        controller.close();
      },
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: stream,
    } as unknown as Response);

    const onCompleteMock = vi.fn();
    const { result } = renderHook(() => useSSEStream());

    await act(async () => {
      await result.current.startStream('Hi', 'article-123', onCompleteMock);
    });

    expect(result.current.isStreaming).toBe(false);
    expect(onCompleteMock).toHaveBeenCalledWith('Hello world!', [{ article_id: '1', title: 'Test Source' }], [], 'chat');
  });
});
