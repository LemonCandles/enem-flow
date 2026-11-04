'use client';
import { useState } from 'react';
import { api, send } from './api';
import type { AttemptSource } from './attempt-source';
import type { Diagnostic, Run } from './types';
import { useData } from './use-data';

// Load an attempt, save each answer with rollback on failure, and finish it.
export function useAttempt(id: string, source: AttemptSource) {
  const endpoint = source.endpoint(id);
  const { data: raw, setData: setRaw, error: loadError, loading, reload } = useData<Run | Diagnostic>(endpoint);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  async function choose(run: Run, itemId: string, choice: string | null) {
    if (busy || run.finished_at) return;
    setBusy(true);
    setError('');
    setSaved(false);
    const before = run.answers;
    setRaw(previous => (previous ? { ...previous, answers: { ...previous.answers, [itemId]: choice } } : previous));
    try {
      const result = await send<{ answers: Run['answers'] }>(`${endpoint}/answers/${itemId}`, { choice }, 'PUT');
      setRaw(previous => (previous ? { ...previous, answers: result.answers } : previous));
      setSaved(true);
    } catch (e) {
      setRaw(previous => (previous ? { ...previous, answers: before } : previous));
      setError((e as Error).message + ' A alteração não foi salva. Selecione a alternativa novamente para tentar.');
    } finally {
      setBusy(false);
    }
  }

  async function finish(onDone: () => void) {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      setRaw(await api<Run | Diagnostic>(`${endpoint}/finish`, { method: 'POST' }));
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return { raw, loading, loadError, reload, busy, error, saved, setSaved, choose, finish };
}
