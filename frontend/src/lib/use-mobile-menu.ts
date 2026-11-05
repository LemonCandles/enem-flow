'use client';
import { useEffect, useRef, useState } from 'react';
import { keepTabInside } from './dialog-focus';

// Collapsed sidebar: closes on navigation and on desktop width, and holds the focus while open.
export function useMobileMenu(path: string) {
  const [mobile, setMobile] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    setMobile(false);
  }, [path]);
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 761px)');
    const closeOnDesktop = () => {
      if (desktop.matches) setMobile(false);
    };
    desktop.addEventListener('change', closeOnDesktop);
    return () => desktop.removeEventListener('change', closeOnDesktop);
  }, []);
  useEffect(() => {
    if (!mobile) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const nodes = sidebar.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
    const first = nodes?.[0];
    const last = nodes?.[nodes.length - 1];
    first?.focus();
    function keydown(event: KeyboardEvent) {
      if (event.key === 'Escape') setMobile(false);
      if (event.key !== 'Tab') return;
      keepTabInside(event, first, last);
    }
    document.addEventListener('keydown', keydown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', keydown);
      menuButton.current?.focus();
    };
  }, [mobile]);
  return { mobile, setMobile, sidebar, menuButton };
}
