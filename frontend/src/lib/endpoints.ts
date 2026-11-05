import { api, send } from './api';
import type { Diagnostic, Exam, History, DiagnosticSummary, RecommendationEvent, Run, User } from './types';

// Paths read through useData, and the calls that change something, by feature.
export const paths = {
  me: '/me',
  exams: '/exams',
  history: '/me/history',
  progress: '/me/progress',
  diagnosticHistory: '/me/sessions',
  knowledgeState: '/me/knowledge-state',
  recommendations: '/me/recommendations',
  diagnosticOptions: '/diagnostic-options',
  adminExams: '/admin/exams',
  adminAudit: '/admin/audit',
  archive: '/admin/archive',
  archiveQuestion: (id: string) => `/admin/archive/questions/${encodeURIComponent(id)}`,
  archiveQuestions: (year: number, offset: number, application: string, number: string) =>
    `/admin/archive/questions?year=${year}&limit=25&offset=${offset}${application ? `&application=${encodeURIComponent(application)}` : ''}${number ? `&number=${number}` : ''}`,
};

export const account = {
  current: () => api<User>(paths.me),
  enter: (mode: string, body: unknown) => send<User>(`/auth/${mode}`, body),
  leave: () => api('/auth/logout', { method: 'POST' }),
  resetPassword: (token: string | undefined, password: FormDataEntryValue | null) =>
    send('/auth/reset-password', { token, password }),
  updatePreferences: (body: unknown) => send<User>('/me/preferences', body, 'PUT'),
  eraseHistory: () => api(paths.history, { method: 'DELETE' }),
  exportHistory: () =>
    Promise.all([
      api<History[]>(paths.history),
      api<DiagnosticSummary[]>(paths.diagnosticHistory),
      api<RecommendationEvent[]>(paths.recommendations),
    ]),
};

export const attempts = {
  startExam: (exam: Exam, key: string) => send<Run>('/exam-runs', { exam_id: exam.id, idempotency_key: key }),
  startDiagnostic: (body: object, key: string) => send<Diagnostic>('/sessions', { ...body, idempotency_key: key }),
  startPractice: (body: object, key: string) =>
    send<Diagnostic>('/practice-sessions', { ...body, idempotency_key: key }),
};

export const curation = {
  exam: <T>(id: string) => api<T>(`/admin/exams/${id}`),
  importExam: (payload: unknown) => send('/admin/imports', payload),
  review: (target: string, action: string, reason: string) => send(`/admin/reviews/${target}`, { action, reason }),
  editQuestion: (version: string, content: unknown, reason: string) =>
    send(`/admin/questions/${version}`, { content, reason }, 'PUT'),
};
