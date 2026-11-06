import { api, send } from './api';
import type {
  Diagnostic,
  DiagnosticSummary,
  Exam,
  HelpEvent,
  HelpLevel,
  History,
  RecommendationEvent,
  Run,
  TutorMaterial,
  User,
} from './types';

// Paths read through useData, and the calls that change something, by feature.
export const paths = {
  me: '/me',
  exams: '/exams',
  history: '/me/history',
  progress: '/me/progress',
  diagnosticHistory: '/me/sessions',
  knowledgeState: '/me/knowledge-state',
  recommendations: '/me/recommendations',
  helpEvents: '/me/help-events',
  diagnosticOptions: '/diagnostic-options',
  practiceOptions: '/practice-options',
  adminExams: '/admin/exams',
  adminAudit: '/admin/audit',
  tutorStatus: '/admin/tutor/status',
  tutorExam: (id: string) => `/admin/tutor/exams/${encodeURIComponent(id)}`,
  tutorQuestion: (id: string) => `/admin/tutor/questions/${encodeURIComponent(id)}`,
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
      api<HelpEvent[]>(paths.helpEvents),
    ]),
};

export const attempts = {
  startExam: (exam: Exam, key: string) => send<Run>('/exam-runs', { exam_id: exam.id, idempotency_key: key }),
  startDiagnostic: (body: object, key: string) => send<Diagnostic>('/sessions', { ...body, idempotency_key: key }),
  startPractice: (body: object, key: string) =>
    send<Diagnostic>('/practice-sessions', { ...body, idempotency_key: key }),
  requestHelp: (sessionId: string, itemId: string, level: HelpLevel, key: string) =>
    send<HelpEvent>(`/practice-sessions/${sessionId}/items/${encodeURIComponent(itemId)}/help`, {
      level,
      idempotency_key: key,
    }),
};

export const curation = {
  exam: <T>(id: string) => api<T>(`/admin/exams/${id}`),
  importExam: (payload: unknown) => send('/admin/imports', payload),
  review: (target: string, action: string, reason: string) => send(`/admin/reviews/${target}`, { action, reason }),
  editQuestion: (version: string, content: unknown, reason: string) =>
    send(`/admin/questions/${version}`, { content, reason }, 'PUT'),
};

export const tutor = {
  writeMaterial: (versionId: string, levels: Record<HelpLevel, string>) =>
    send<TutorMaterial>(`${paths.tutorQuestion(versionId)}/materials`, levels),
  draft: (versionId: string) => send<TutorMaterial>(`${paths.tutorQuestion(versionId)}/draft`),
  review: (materialId: string, action: 'approve' | 'reject', reason: string) =>
    send<TutorMaterial>(`/admin/tutor/materials/${materialId}/review`, { action, reason }),
};
