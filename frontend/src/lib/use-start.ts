'use client';
import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Exam, Run, send } from './api';

export function useStart() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const keys = useRef<Record<string, string>>({});
  async function start(exam: Exam) {
    if (busy) return;
    setBusy(true); setError('');
    keys.current[exam.id] ||= crypto.randomUUID();
    try { const run = await send<Run>('/exam-runs', { exam_id: exam.id, idempotency_key: keys.current[exam.id] }); router.push(`/runs/${run.id}`); }
    catch (e) { setError((e as Error).message); setBusy(false); }
  }
  return { start, busy, error };
}
