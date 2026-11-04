import type { Diagnostic, Question, Run } from './types';

// What differs between an exam run and a diagnostic session. The runner only sees a
// Run: `toRun` adapts each response, and the rest answers the runner's questions.
export type AttemptSource = {
  endpoint: (id: string) => string;
  toRun: (raw: Run | Diagnostic) => Run;
  session: (raw: Run | Diagnostic) => Diagnostic | undefined;
  leaveHref: string;
  concludedLabel: string;
  finishLabel: string;
  questionNumber: (question: Question, position: number) => number;
  showsOrigin: boolean;
};

export const examAttempt: AttemptSource = {
  endpoint: id => `/exam-runs/${id}`,
  toRun: raw => raw as Run,
  session: () => undefined,
  leaveHref: '/exams',
  concludedLabel: 'PROVA CONCLUÍDA',
  finishLabel: 'Finalizar prova',
  questionNumber: question => question.number,
  showsOrigin: false,
};

function diagnosticAsRun(raw: Diagnostic): Run {
  return {
    ...raw,
    exam: {
      id: raw.id,
      title: `Diagnóstico · ${raw.area}`,
      booklet: 'Diagnóstico',
      application: raw.objective,
      year: 0,
      day: 0,
      kind: 'collection',
      expected_items: raw.items.length,
      item_count: raw.items.length,
      approved_items: raw.items.length,
      duration_minutes: raw.available_minutes,
      areas: [raw.area],
      status: 'published',
      source: { url: raw.items[0]?.source_url || '', publisher: 'Inep', notes: '' },
    },
  };
}

export const diagnosticAttempt: AttemptSource = {
  endpoint: id => `/sessions/${id}`,
  toRun: raw => diagnosticAsRun(raw as Diagnostic),
  session: raw => raw as Diagnostic,
  leaveHref: '/diagnostic',
  concludedLabel: 'DIAGNÓSTICO CONCLUÍDO',
  finishLabel: 'Finalizar diagnóstico',
  questionNumber: (_, position) => position + 1,
  showsOrigin: true,
};
