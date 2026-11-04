// Shapes of the API responses.
export type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  preferences: { target_course?: string; daily_goal?: number };
};
export type Exam = {
  content_quality?: { origin: 'automatic' | 'reviewed'; review_status: string; blocking_issues: number };
  id: string;
  title: string;
  year: number;
  application: string;
  booklet: string;
  day: number;
  kind: string;
  expected_items: number;
  item_count: number;
  approved_items: number;
  duration_minutes: number;
  areas: string[];
  status: string;
  source: { url: string; publisher: string; notes: string; answer_key_url?: string };
};
export type Asset = { path: string; alt: string };
export type ContentBlock =
  | { type: 'paragraph'; text: string; role?: 'body' | 'credit' | null }
  | { type: 'image'; asset: Asset; caption?: string; credit?: string; equations?: string[] }
  | { type: 'math'; tex: string }
  | { type: 'table'; headers: string[]; rows: string[][]; caption: string };
export type Question = {
  source_url?: string;
  preparation_errors?: number;
  id: string;
  question_id: string;
  version: number;
  number: number;
  area: string;
  statement: string;
  blocks?: ContentBlock[];
  images: Asset[];
  alternatives: { letter: string; text: string; image?: Asset | null }[];
  labels: { discipline: string | null; themes: string[]; skills: string[] };
  page: number;
  original_layout: boolean;
  correct_answer?: string | null;
  annulled?: boolean;
};
export type Score = {
  correct: number;
  total: number;
  answered: number;
  unanswered: number;
  incorrect: number;
  annulled: number;
  percentage: number | null;
};
export type Run = {
  id: string;
  exam: Exam;
  items: Question[];
  answers: Record<string, string | null>;
  started_at: number;
  finished_at: number | null;
  result: Score | null;
};
export type History = {
  id: string;
  exam: Exam;
  started_at: number;
  finished_at: number | null;
  answered: number;
  result: Score | null;
};
export type Progress = {
  completed_runs: number;
  summary: Score;
  coverage: Record<string, { classified: number; total: number; percentage: number }>;
  breakdown: Record<string, { name: string; attempts: number; correct: number; percentage: number }[]>;
  evolution: { id: string; date: number; percentage: number | null; title: string }[];
};
export type Diagnostic = Omit<Run, 'exam'> & {
  objective: string;
  area: string;
  available_minutes: number;
  answered: number;
  selection: {
    version: string;
    requested_items: number;
    selected_items: number;
    eligible_items: number;
    themes: Record<string, number>;
    repeated_items: string[];
  };
};
export type DiagnosticSummary = Omit<Diagnostic, 'items'>;
export type DiagnosticOptions = { areas: { area: string; eligible_items: number; themes: Record<string, number> }[] };
export type KnowledgeGroup = {
  name: string;
  area: string;
  discipline: string | null;
  taxonomy_version: string;
  attempts: number;
  correct: number;
  independent_attempts: number;
  independent_correct: number;
  assisted_attempts: number;
  assisted_correct: number;
  unknown_help_attempts: number;
  repeated_attempts: number;
  unanswered: number;
  seen_items: number;
  distinct_answered_items: number;
  last_practice: number | null;
  estimate: number | null;
  evidence_status: 'none' | 'low' | 'available';
  recent: { correct: boolean; help_used: boolean | null }[];
};
export type KnowledgeState = {
  estimator: { version: string; minimum_evidence: number };
  themes: KnowledgeGroup[];
  skills: KnowledgeGroup[];
};
