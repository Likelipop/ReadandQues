import { describe, it, expect } from 'vitest';
import { useSmartNotesStorage, useWorkspace } from '../index';
import { renderHook, act } from '@testing-library/react';

describe('Store and Hooks', () => {
  it('handles Smart Notes storage additions, deletion, and clear operations', () => {
    const { result } = renderHook(() => useSmartNotesStorage('art_test_123'));

    expect(result.current.notes).toEqual([]);

    act(() => {
      result.current.addNote({
        id: 'note_1',
        selected_text: 'Deep-sea geothermal extraction',
        explanation: 'Refers to tapping heat from underwater volcanic vents.',
        paraphrased_text: 'Subsea thermal energy harvesting',
        timestamp: Date.now(),
      });
    });

    expect(result.current.notes.length).toBe(1);
    expect(result.current.notes[0].selected_text).toBe('Deep-sea geothermal extraction');

    act(() => {
      result.current.removeNote('note_1');
    });

    expect(result.current.notes.length).toBe(0);
  });

  it('handles active tool and dictionary lookup state in workspace store', () => {
    const { result } = renderHook(() => useWorkspace());

    expect(result.current.activeTool).toBeNull();

    act(() => {
      result.current.setActiveTool('dictionary');
    });

    expect(result.current.activeTool).toBe('dictionary');

    act(() => {
      result.current.setActiveTool('dictionary');
    });

    expect(result.current.activeTool).toBeNull();
  });

  it('manages highlightColor and Zen Mode states in workspace store', () => {
    const { result } = renderHook(() => useWorkspace());

    expect(result.current.highlightColor).toBe('amber');
    expect(result.current.isZenMode).toBe(false);

    act(() => {
      result.current.setHighlightColor('emerald');
    });
    expect(result.current.highlightColor).toBe('emerald');

    act(() => {
      result.current.setHighlightColor('rose');
    });
    expect(result.current.highlightColor).toBe('rose');

    act(() => {
      result.current.toggleZenMode();
    });
    expect(result.current.isZenMode).toBe(true);

    act(() => {
      result.current.setZenMode(false);
    });
    expect(result.current.isZenMode).toBe(false);
  });
});
