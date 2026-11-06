'use client';
import { useState } from 'react';
import { Lightbulb, Sparkles } from 'lucide-react';
import { paths, tutor } from '@/lib/endpoints';
import type { Exam, HelpLevel, Question, TutorMaterial, TutorStatus } from '@/lib/types';
import { useData } from '@/lib/use-data';
import { QuestionContent } from './question-content';
import { ErrorBox } from './ui';

type TutorExam = { exam: { id: string; title: string }; items: { id: string; number: number; material: string }[] };
type TutorQuestion = { question: Question; materials: TutorMaterial[] };

const LEVELS: { key: HelpLevel; label: string; hint: string }[] = [
  {
    key: 'orientation',
    label: 'Orientação',
    hint: 'O que a questão pede e qual conceito usar, sem indicar alternativa.',
  },
  { key: 'hint', label: 'Pista', hint: 'O próximo passo do raciocínio, ainda sem revelar a resposta.' },
  { key: 'solution', label: 'Resolução', hint: 'Passo a passo, terminando com a alternativa correta.' },
];
const MATERIAL_LABEL: Record<string, string> = {
  approved: 'Aprovado',
  proposal: 'Proposta',
  outdated: 'Desatualizado',
  none: 'Sem material',
  rejected: 'Rejeitado',
  superseded: 'Substituído',
};
const EMPTY: Record<HelpLevel, string> = { orientation: '', hint: '', solution: '' };

// Material reaches students only after approval here, for the exact version of the question.
export function TutorCuration({ exams }: { exams: Exam[] }) {
  const published = exams.filter(exam => exam.status === 'published');
  const status = useData<TutorStatus>(published.length ? paths.tutorStatus : null);
  const [examId, setExamId] = useState('');
  const [versionId, setVersionId] = useState('');
  const chosenExam = examId || published[0]?.id || '';
  const list = useData<TutorExam>(chosenExam ? paths.tutorExam(chosenExam) : null);
  const items = list.data?.exam.id === chosenExam ? list.data.items : [];
  const chosenVersion = versionId || items[0]?.id || '';
  const detail = useData<TutorQuestion>(chosenVersion ? paths.tutorQuestion(chosenVersion) : null);
  const question = detail.data?.question.id === chosenVersion ? detail.data : undefined;
  const [levels, setLevels] = useState<Record<HelpLevel, string>>(EMPTY);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function act(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      detail.reload();
      list.reload();
      setNotice(success);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function review(material: TutorMaterial, action: 'approve' | 'reject') {
    if (reason.trim().length < 10) {
      setError('Registre o que foi conferido (mínimo 10 caracteres) antes de decidir.');
      return;
    }
    act(
      () => tutor.review(material.id, action, reason),
      action === 'approve' ? 'Material aprovado: a ajuda já aparece na prática.' : 'Proposta rejeitada.',
    );
  }
  if (!published.length) return null;
  return (
    <section className="panel tutor-curation" aria-labelledby="tutor-curation-heading">
      <div className="section-heading">
        <div>
          <h2 id="tutor-curation-heading">
            <Lightbulb size={18} aria-hidden="true" /> Material do tutor
          </h2>
          <p className="tiny muted">
            Três níveis de ajuda por questão. Propostas da IA ou da equipe só chegam à prática depois de aprovadas.
          </p>
        </div>
        {status.data && (
          <span className={`badge ${status.data.enabled ? 'green' : 'amber'}`}>
            {status.data.enabled
              ? `Provedor ativo · ${status.data.model}`
              : `Provedor desligado · falta ${status.data.missing.join(', ')}`}
          </span>
        )}
      </div>
      <div className="admin-question-toolbar">
        <select
          aria-label="Prova do material"
          value={chosenExam}
          onChange={e => {
            setExamId(e.target.value);
            setVersionId('');
          }}
        >
          {published.map(exam => (
            <option value={exam.id} key={exam.id}>
              {exam.title}
            </option>
          ))}
        </select>
        <select
          aria-label="Questão do material"
          value={chosenVersion}
          onChange={e => {
            setVersionId(e.target.value);
            setLevels(EMPTY);
            setNotice('');
            setError('');
          }}
        >
          {items.map(item => (
            <option value={item.id} key={item.id}>
              Questão {item.number} · {MATERIAL_LABEL[item.material]}
            </option>
          ))}
        </select>
      </div>
      {(error || list.error || detail.error) && <ErrorBox message={error || list.error || detail.error} />}
      {notice && (
        <p className="success-box" role="status">
          {notice}
        </p>
      )}
      {question && (
        <div className="tutor-curation-grid">
          <div className="question-content">
            <p className="eyebrow">
              QUESTÃO {question.question.number} · GABARITO{' '}
              {question.question.annulled ? 'ANULADA' : question.question.correct_answer}
            </p>
            <QuestionContent question={question.question} />
          </div>
          <div className="tutor-materials">
            {question.materials
              .slice()
              .reverse()
              .map(material => (
                <article className="tutor-material" key={material.id}>
                  <header>
                    <strong>Versão {material.version}</strong>
                    <span className={`badge ${material.status === 'approved' ? 'green' : 'amber'}`}>
                      {MATERIAL_LABEL[material.status]}
                    </span>
                    <span className="tiny muted">
                      {material.origin === 'llm' ? `IA · ${String(material.provenance.model)}` : 'Equipe'}
                      {!material.current && ' · escrito para outra versão da questão'}
                    </span>
                  </header>
                  {LEVELS.map(level => (
                    <p key={level.key}>
                      <b>{level.label}:</b> {material.levels[level.key]}
                    </p>
                  ))}
                  {material.status === 'proposal' && (
                    <div className="review-actions">
                      <button
                        className="button secondary compact"
                        disabled={busy}
                        onClick={() => setLevels(material.levels)}
                      >
                        Editar como nova proposta
                      </button>
                      <button
                        className="button secondary compact"
                        disabled={busy}
                        onClick={() => review(material, 'reject')}
                      >
                        Rejeitar
                      </button>
                      <button
                        className="button compact"
                        disabled={busy || !material.current}
                        onClick={() => review(material, 'approve')}
                      >
                        Aprovar
                      </button>
                    </div>
                  )}
                </article>
              ))}
            {!question.materials.length && <p className="muted">Ainda não há material para esta questão.</p>}
            <label className="review-reason">
              Justificativa da decisão
              <textarea
                value={reason}
                onChange={e => setReason(e.target.value)}
                maxLength={2000}
                placeholder="O que foi conferido: coerência com o gabarito, linguagem, ausência de resposta nos níveis iniciais."
              />
            </label>
            <div className="tutor-editor">
              {LEVELS.map(level => (
                <label key={level.key}>
                  {level.label}
                  <textarea
                    value={levels[level.key]}
                    maxLength={3000}
                    onChange={e => setLevels({ ...levels, [level.key]: e.target.value })}
                    placeholder={level.hint}
                  />
                </label>
              ))}
              <div className="review-actions">
                <button
                  className="button secondary"
                  disabled={busy || !status.data?.enabled}
                  title={status.data?.enabled ? undefined : 'Configure GROQ_API_KEY e os limites no .env'}
                  onClick={() =>
                    act(() => tutor.draft(chosenVersion), 'Proposta gerada pela IA. Revise antes de aprovar.')
                  }
                >
                  <Sparkles size={16} />
                  Gerar proposta com IA
                </button>
                <button
                  className="button"
                  disabled={busy || LEVELS.some(level => !levels[level.key].trim())}
                  onClick={() =>
                    act(async () => {
                      await tutor.writeMaterial(chosenVersion, levels);
                      setLevels(EMPTY);
                    }, 'Proposta salva. Revise e aprove para liberar na prática.')
                  }
                >
                  Salvar proposta
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
