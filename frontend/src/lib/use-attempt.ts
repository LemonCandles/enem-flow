'use client';
import { useEffect, useRef, useState } from 'react';
import { api, ApiError, send } from './api';
import type { AttemptSource } from './attempt-source';
import type { Diagnostic, Run } from './types';
import { useData } from './use-data';

type PendingAnswer = { itemId: string; choice: string | null };

// An answer still being saved is kept for the tab until the server confirms it. A reload
// can read the attempt before that save ends, or the request may never have left.
function pendingAnswers(id: string) {
  const key = `exam-answer-pending:${id}`;
  return {
    read: () => JSON.parse(sessionStorage.getItem(key) || 'null') as PendingAnswer | null,
    write: (pending: PendingAnswer) => sessionStorage.setItem(key, JSON.stringify(pending)),
    clear: () => sessionStorage.removeItem(key),
  };
}

// Load an attempt, save each answer with rollback on failure, and finish it.
export function useAttempt(id: string, source: AttemptSource) {
  const endpoint = source.endpoint(id);
  const { data: raw, setData: setRaw, error: loadError, loading, reload } = useData<Run | Diagnostic>(endpoint);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const pendingChecked = useRef(false);

  async function save(itemId: string, choice: string | null, before: Run['answers']) {
    const pending = pendingAnswers(id);
    setBusy(true);
    setError('');
    setSaved(false);
    pending.write({ itemId, choice });
    setRaw(previous => (previous ? { ...previous, answers: { ...previous.answers, [itemId]: choice } } : previous));
    try {
      // keepalive lets the request finish even if the student closes the page now.
      const result = await send<{ answers: Run['answers'] }>(`${endpoint}/answers/${itemId}`, { choice }, 'PUT', true);
      pending.clear();
      setRaw(previous => (previous ? { ...previous, answers: result.answers } : previous));
      setSaved(true);
    } catch (e) {
      // Only an answer from the server settles it: leaving the page also cancels the request.
      if (e instanceof ApiError && e.status !== 0) pending.clear();
      setRaw(previous => (previous ? { ...previous, answers: before } : previous));
      setError((e as Error).message + ' A alteração não foi salva. Selecione a alternativa novamente para tentar.');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!raw || pendingChecked.current) return;
    pendingChecked.current = true;
    const pending = pendingAnswers(id);
    const unsaved = pending.read();
    if (!unsaved) return;
    if (raw.finished_at || (raw.answers[unsaved.itemId] ?? null) === unsaved.choice) pending.clear();
    else save(unsaved.itemId, unsaved.choice, raw.answers);
    // Runs once, when the attempt first loads.
  }, [raw]);

  async function choose(run: Run, itemId: string, choice: string | null) {
    if (busy || run.finished_at) return;
    await save(itemId, choice, run.answers);
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
