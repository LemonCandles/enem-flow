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
export type Recommendation = { function: string; reason: string; policy_version: string };
export type HelpLevel = 'orientation' | 'hint' | 'solution';
export type DeliveredHelp = { level: HelpLevel; message: string; mode: 'tutor' | 'material'; delivered_at: number };
// Practice only: whether approved help exists for the item and what was already received.
export type HelpState = { available: boolean; next_level: HelpLevel | null; delivered: DeliveredHelp[] };
export type HelpEvent = DeliveredHelp & {
  id: string;
  session_id: string;
  item_id: string;
  content_version: number;
  outcome: 'requested' | 'delivered';
  requested_at: number;
  provider: Record<string, unknown>;
};
export type TutorMaterial = {
  id: string;
  question_id: string;
  version: number;
  status: 'proposal' | 'approved' | 'rejected' | 'superseded';
  origin: 'human' | 'llm';
  levels: Record<HelpLevel, string>;
  provenance: Record<string, unknown>;
  created_at: number;
  reviewed_at: number | null;
  review_reason: string | null;
  current: boolean;
};
export type LayoutProposal = {
  id: string;
  question_version_id: string;
  adapter_version: string;
  status: 'proposal' | 'invalid' | 'approved' | 'rejected';
  errors: string[];
  comparison: {
    preserved_ratio: number;
    missing_words: number;
    extra_words: number;
    missing_sample: string[];
    blocks_before: number;
    blocks_after: number;
    figures_before: number;
    figures_after: number;
  };
  converted: Question | null;
  result_version_id: string | null;
};
export type TutorStatus = { enabled: boolean; missing: string[]; model: string | null; daily_limit: number };
export type Question = {
  source_url?: string;
  recommendation?: Recommendation;
  help?: HelpState;
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
  kind: 'diagnostic' | 'practice';
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
export type DiagnosticOptions = {
  areas: { area: string; eligible_items: number; exhausted?: boolean; themes: Record<string, number> }[];
};
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
export type RecommendationEvent = {
  session_id: string;
  position: number;
  item_id: string;
  policy_version: string;
  function: string;
  reason: string;
  created_at: number;
};
