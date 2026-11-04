'use client';
import { useCallback, useEffect, useRef, useState } from 'react';

// Current question, remembered per attempt, with the left and right arrow keys.
export function useQuestionNavigation(id: string, itemCount: number, disabled: boolean, onNavigate: () => void) {
  const [index, setIndex] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const navigate = useCallback(
    (next: number) => {
      setIndex(next);
      onNavigate();
      sessionStorage.setItem(`exam-position:${id}`, String(next));
      setTimeout(() => {
        heading.current?.focus({ preventScroll: true });
        window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
      }, 0);
    },
    [id, onNavigate],
  );
  useEffect(() => {
    const stored = Number(sessionStorage.getItem(`exam-position:${id}`) || 0);
    setIndex(Number.isFinite(stored) ? stored : 0);
  }, [id]);
  useEffect(() => {
    if (disabled || !itemCount) return;
    function onArrow(event: KeyboardEvent) {
      if (
        event.defaultPrevented ||
        event.repeat ||
        event.isComposing ||
        event.altKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey
      )
        return;
      if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
      if (
        document.querySelector(
          'dialog[open], [aria-modal="true"], [aria-controls="site-navigation"][aria-expanded="true"]',
        )
      )
        return;
      // Radios keep their native arrow-key selection; editable and scrollable
      // content must also retain the keys it needs.
      if (
        event.target instanceof Element &&
        event.target.closest(
          'input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="radio"], [role="slider"], [role="spinbutton"], [role="tab"], [role="listbox"], [role="menu"], [role="tree"], [role="grid"], .native-table-wrap, .native-equation, .figure-equation, .figure-viewport, .math-inline',
        )
      )
        return;
      const next = index + (event.key === 'ArrowRight' ? 1 : -1);
      if (next < 0 || next >= itemCount) return;
      event.preventDefault();
      navigate(next);
    }
    window.addEventListener('keydown', onArrow);
    return () => window.removeEventListener('keydown', onArrow);
  }, [disabled, index, itemCount, navigate]);
  return { index, navigate, heading };
}
