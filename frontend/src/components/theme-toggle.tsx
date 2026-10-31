'use client';

import { Moon, Sun } from 'lucide-react';

export default function ThemeToggle() {
  function toggle() {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('enem-flow:theme', next); } catch { /* Theme still works when storage is unavailable. */ }
  }
  return <button type="button" className="theme-toggle icon-button" aria-label="Alternar tema" title="Alternar tema claro e escuro" onClick={toggle}>
    <Sun className="theme-sun" size={20} aria-hidden="true"/>
    <Moon className="theme-moon" size={20} aria-hidden="true"/>
  </button>;
}
