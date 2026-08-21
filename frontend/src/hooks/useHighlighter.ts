import React, { useEffect, useCallback, useRef } from 'react';
import { useWorkspace, HighlightColor } from '../store';
import { api } from '../api/client';

export const HIGHLIGHT_THEMES: Record<
  HighlightColor,
  {
    name: string;
    classSuffix: string;
    markClass: string;
    dotColor: string;
    ringColor: string;
    badgeClass: string;
  }
> = {
  amber: {
    name: 'Amber Gold',
    classSuffix: 'amber',
    markClass: 'user-highlight user-highlight-amber bg-amber-400/30 text-amber-200 border-amber-400/50',
    dotColor: 'bg-amber-400',
    ringColor: 'ring-amber-400',
    badgeClass: 'bg-amber-400/20 text-amber-300 border-amber-400/30',
  },
  emerald: {
    name: 'Emerald Green',
    classSuffix: 'emerald',
    markClass: 'user-highlight user-highlight-emerald bg-emerald-400/30 text-emerald-200 border-emerald-400/50',
    dotColor: 'bg-emerald-400',
    ringColor: 'ring-emerald-400',
    badgeClass: 'bg-emerald-400/20 text-emerald-300 border-emerald-400/30',
  },
  cyan: {
    name: 'Cyan Blue',
    classSuffix: 'cyan',
    markClass: 'user-highlight user-highlight-cyan bg-cyan-400/30 text-cyan-200 border-cyan-400/50',
    dotColor: 'bg-cyan-400',
    ringColor: 'ring-cyan-400',
    badgeClass: 'bg-cyan-400/20 text-cyan-300 border-cyan-400/30',
  },
  rose: {
    name: 'Rose Pink',
    classSuffix: 'rose',
    markClass: 'user-highlight user-highlight-rose bg-rose-400/30 text-rose-200 border-rose-400/50',
    dotColor: 'bg-rose-400',
    ringColor: 'ring-rose-400',
    badgeClass: 'bg-rose-400/20 text-rose-300 border-rose-400/30',
  },
};

export function getHighlightMarkClass(color: HighlightColor = 'amber'): string {
  const theme = HIGHLIGHT_THEMES[color] || HIGHLIGHT_THEMES.amber;
  return `${theme.markClass} rounded px-0.5 py-0.2 border-b cursor-pointer transition-colors duration-150`;
}

export interface HighlightItem {
  text: string;
  color: HighlightColor;
}

export function useHighlighter(
  articleId: string,
  containerRef: React.RefObject<HTMLElement | null>
) {
  const { activeTool, highlightColor } = useWorkspace();
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const storageKey = `article_highlights_${articleId}`;

  const triggerDbSave = useCallback(() => {
    if (!containerRef.current || !articleId) return;
    try {
      const marks = containerRef.current.querySelectorAll('mark.user-highlight');
      const items: HighlightItem[] = Array.from(marks)
        .map((m) => {
          const text = (m.getAttribute('data-original-text') || m.textContent || '').trim();
          const color = (m.getAttribute('data-color') as HighlightColor) || 'amber';
          return { text, color };
        })
        .filter((s) => s.text.length >= 2);

      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = setTimeout(() => {
        api.articles.saveMarkers(articleId, JSON.stringify(items)).catch(() => {});
      }, 2000);
    } catch {
      // ignore
    }
  }, [articleId, containerRef]);

  const saveHighlights = useCallback(() => {
    if (!containerRef.current || !articleId) return;
    try {
      const marks = containerRef.current.querySelectorAll('mark.user-highlight');
      const items: HighlightItem[] = Array.from(marks)
        .map((m) => {
          const text = (m.getAttribute('data-original-text') || m.textContent || '').trim();
          const color = (m.getAttribute('data-color') as HighlightColor) || 'amber';
          return { text, color };
        })
        .filter((s) => s.text.length >= 2);

      localStorage.setItem(storageKey, JSON.stringify(items));
      triggerDbSave();
    } catch (e) {
      console.error('Error saving highlights:', e);
    }
  }, [articleId, containerRef, storageKey, triggerDbSave]);

  const restoreHighlights = useCallback(() => {
    if (!containerRef.current || !articleId) return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return;
      const rawItems: any[] = JSON.parse(raw);
      if (!Array.isArray(rawItems) || rawItems.length === 0) return;

      const container = containerRef.current;
      rawItems.forEach((item) => {
        const textToFind = typeof item === 'string' ? item : item?.text;
        const color: HighlightColor =
          typeof item === 'object' && item?.color && HIGHLIGHT_THEMES[item.color as HighlightColor]
            ? item.color
            : 'amber';

        if (!textToFind || textToFind.length < 2) return;

        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
        let node: Node | null;
        const textNodes: Text[] = [];
        while ((node = walker.nextNode())) {
          if (
            node.parentNode &&
            (node.parentNode as HTMLElement).nodeName.toLowerCase() !== 'mark' &&
            (node.parentNode as HTMLElement).nodeName.toLowerCase() !== 'script' &&
            (node.parentNode as HTMLElement).nodeName.toLowerCase() !== 'style'
          ) {
            textNodes.push(node as Text);
          }
        }

        for (const tNode of textNodes) {
          const content = tNode.nodeValue || '';
          const idx = content.indexOf(textToFind);
          if (idx !== -1) {
            try {
              const range = document.createRange();
              range.setStart(tNode, idx);
              range.setEnd(tNode, idx + textToFind.length);
              const mark = document.createElement('mark');
              mark.className = getHighlightMarkClass(color);
              mark.setAttribute('data-original-text', textToFind);
              mark.setAttribute('data-color', color);
              range.surroundContents(mark);
            } catch {
              // ignore
            }
            break;
          }
        }
      });
    } catch {
      // ignore
    }
  }, [articleId, containerRef, storageKey]);

  // Programmatic highlight for active text selection (e.g. from Contextual HUD)
  const highlightSelection = useCallback(
    (color?: HighlightColor) => {
      const activeColor = color || highlightColor || 'amber';
      const container = containerRef.current;
      if (!container) return false;

      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.rangeCount) return false;

      const range = sel.getRangeAt(0);
      if (!container.contains(range.commonAncestorContainer)) return false;

      const selectedText = sel.toString().trim();
      if (selectedText.length < 2) return false;

      try {
        const mark = document.createElement('mark');
        mark.className = getHighlightMarkClass(activeColor);
        mark.setAttribute('data-original-text', selectedText);
        mark.setAttribute('data-color', activeColor);
        mark.textContent = selectedText;
        range.deleteContents();
        range.insertNode(mark);
        sel.removeAllRanges();
        saveHighlights();
        return true;
      } catch (err) {
        console.error('Error applying highlight:', err);
        return false;
      }
    },
    [containerRef, highlightColor, saveHighlights]
  );

  // Handle mouseup for applying highlights or erasing
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleMouseUp = () => {
      if (activeTool !== 'marker') return;
      highlightSelection(highlightColor);
    };

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (activeTool === 'eraser' && target && target.classList.contains('user-highlight')) {
        const parent = target.parentNode;
        if (parent) {
          const text = document.createTextNode(target.textContent || '');
          parent.replaceChild(text, target);
          parent.normalize();
          saveHighlights();
        }
      }
    };

    container.addEventListener('mouseup', handleMouseUp);
    container.addEventListener('click', handleClick);

    return () => {
      container.removeEventListener('mouseup', handleMouseUp);
      container.removeEventListener('click', handleClick);
    };
  }, [activeTool, containerRef, highlightColor, highlightSelection, saveHighlights]);

  // Restore on mount or article change
  useEffect(() => {
    const timer = setTimeout(() => {
      restoreHighlights();
    }, 100);
    return () => clearTimeout(timer);
  }, [restoreHighlights]);

  return { saveHighlights, restoreHighlights, highlightSelection };
}
