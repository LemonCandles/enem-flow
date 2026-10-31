export type User = { id: string; name: string; email: string; role: string; preferences: { target_course?: string; daily_goal?: number } };
export type Exam = { id: string; title: string; year: number; application: string; booklet: string; day: number; kind: string; expected_items: number; item_count: number; approved_items: number; duration_minutes: number; areas: string[]; status: string; source: { url: string; publisher: string; notes: string; answer_key_url?: string } };
export type Asset = { path: string; alt: string };
export type ContentBlock = { type: 'paragraph'; text: string } | { type: 'image'; asset: Asset } | { type: 'math'; tex: string } | { type: 'table'; headers: string[]; rows: string[][]; caption: string };
export type Question = { id: string; question_id: string; version: number; number: number; area: string; statement: string; blocks?: ContentBlock[]; images: Asset[]; alternatives: { letter: string; text: string; image?: Asset | null }[]; labels: { discipline: string | null; themes: string[]; skills: string[] }; page: number; original_layout: boolean; correct_answer?: string | null; annulled?: boolean };
export type Score = { correct: number; total: number; answered: number; unanswered: number; incorrect: number; annulled: number; percentage: number | null };
export type Run = { id: string; exam: Exam; items: Question[]; answers: Record<string, string | null>; started_at: number; finished_at: number | null; result: Score | null };
export type History = { id: string; exam: Exam; started_at: number; finished_at: number | null; answered: number; result: Score | null };
export type Progress = { completed_runs: number; summary: Score; coverage: Record<string, { classified: number; total: number; percentage: number }>; breakdown: Record<string, { name: string; attempts: number; correct: number; percentage: number }[]>; evolution: { id: string; date: number; percentage: number | null; title: string }[] };

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json', ...init?.headers } });
  } catch { throw new ApiError(0, 'Não foi possível conectar. Confira sua conexão e tente novamente.'); }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    let message = typeof data.detail === 'string' ? data.detail : 'Não foi possível concluir a operação.';
    if (data.errors?.length) message += ` ${data.errors.map((e: { field: string; message: string }) => `${e.field}: ${e.message}`).join(' · ')}`;
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? undefined as T : response.json();
}

export function send<T>(path: string, body?: unknown, method = 'POST') {
  return api<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
}

export const date = (timestamp: number) => new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(timestamp * 1000);
export const pct = (value: number | null | undefined) => value == null ? '—' : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
export const kindName = (kind: string) => ({ complete: 'Caderno completo', section: 'Seção completa', collection: 'Coleção parcial' }[kind] || kind);
