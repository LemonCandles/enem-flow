'use client';
import { ChangeEvent, useState } from 'react';
import { ExternalLink, LayoutTemplate, Upload } from 'lucide-react';
import { layout, paths } from '@/lib/endpoints';
import type { LayoutProposal, Question } from '@/lib/types';
import { useData } from '@/lib/use-data';
import { QuestionContent } from './question-content';
import { ErrorBox } from './ui';

type LayoutQuestion = {
  published: Question;
  source_url: string | null;
  page: number;
  proposals: LayoutProposal[];
};

const STATUS: Record<LayoutProposal['status'], string> = {
  proposal: 'Aguardando revisão',
  invalid: 'Recusada pelo adaptador',
  approved: 'Aprovada',
  rejected: 'Rejeitada',
};

function asQuestion(content: Question, id: string): Question {
  return { ...content, id, question_id: id, version: 0 };
}

// A proposal never changes what students see: approval creates a draft that goes through review.
export function LayoutReview({ versionId, onChanged }: { versionId: string; onChanged: () => void }) {
  const data = useData<LayoutQuestion>(paths.layoutQuestion(versionId));
  const [reason, setReason] = useState('');
  const [compared, setCompared] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const pending = data.data?.proposals.find(p => p.status === 'proposal');
  const latest = data.data?.proposals[0];

  async function act(action: () => Promise<unknown>, success: string, changed = false) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      data.reload();
      if (changed) onChanged();
      setNotice(success);
      setReason('');
      setCompared(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    act(async () => {
      const payload = JSON.parse(await file.text());
      if (payload.question_version !== versionId)
        throw new Error('A proposta foi gerada para outra versão desta questão.');
      await layout.submit(payload);
    }, 'Proposta recebida. Confira a conversão e compare com o original.');
  }
  function review(action: 'approve' | 'reject') {
    if (!pending) return;
    if (reason.trim().length < 10) {
      setError('Registre a justificativa (mínimo 10 caracteres).');
      return;
    }
    act(
      () => layout.review(pending.id, action, reason, compared),
      action === 'approve'
        ? 'Nova versão criada como rascunho com os blocos propostos. Revise e publique a prova novamente.'
        : 'Proposta rejeitada; os blocos publicados continuam.',
      action === 'approve',
    );
  }
  return (
    <section className="layout-review" aria-labelledby={`layout-${versionId}`}>
      <div className="section-heading">
        <h3 id={`layout-${versionId}`}>
          <LayoutTemplate size={16} aria-hidden="true" /> Layout proposto
        </h3>
        <label className="button secondary compact upload-button">
          <Upload size={15} />
          Enviar proposta
          <input type="file" accept="application/json,.json" onChange={upload} disabled={busy} />
        </label>
      </div>
      <p className="tiny muted">
        Gere a proposta com <code>scripts/propose_layout.py</code>. O adaptador recusa fonte ou versão divergentes,
        figuras ausentes, vínculos inválidos e ordem incompleta; a apresentação publicada não muda até a aprovação.
      </p>
      {(error || data.error) && <ErrorBox message={error || data.error} />}
      {notice && (
        <p className="success-box" role="status">
          {notice}
        </p>
      )}
      {latest?.status === 'invalid' && (
        <div className="notice-box">
          <strong>{STATUS.invalid}:</strong>
          <ul>
            {latest.errors.map(message => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}
      {pending?.converted && data.data && (
        <>
          <p className="small-text">
            Texto preservado: {Math.round(pending.comparison.preserved_ratio * 100)}% ·{' '}
            {pending.comparison.missing_words} palavras ausentes · {pending.comparison.extra_words} novas · blocos{' '}
            {pending.comparison.blocks_before} → {pending.comparison.blocks_after} · figuras{' '}
            {pending.comparison.figures_before} → {pending.comparison.figures_after}
            {!!pending.comparison.missing_sample.length && (
              <> · ausentes: {pending.comparison.missing_sample.join(', ')}</>
            )}
          </p>
          <div className="layout-compare">
            <div>
              <p className="eyebrow">PUBLICADO</p>
              <div className="question-content">
                <QuestionContent question={asQuestion(data.data.published, `${versionId}-publicado`)} />
              </div>
            </div>
            <div>
              <p className="eyebrow">PROPOSTO · {pending.adapter_version}</p>
              <div className="question-content">
                <QuestionContent question={asQuestion(pending.converted, `${versionId}-proposto`)} />
              </div>
              <ol className="layout-alternatives">
                {pending.converted.alternatives.map(option => (
                  <li key={option.letter}>
                    <b>{option.letter}</b> {option.text}
                    {option.image && <img src={`/api${option.image.path}`} alt={option.image.alt} />}
                  </li>
                ))}
              </ol>
            </div>
          </div>
          {data.data.source_url && (
            <a
              className="text-link"
              href={`${data.data.source_url}#page=${data.data.page}`}
              target="_blank"
              rel="noreferrer"
            >
              Abrir a página {data.data.page} do caderno original <ExternalLink size={14} />
            </a>
          )}
          <label className="checkbox-line">
            <input type="checkbox" checked={compared} onChange={e => setCompared(e.target.checked)} />
            Comparei a proposta com o caderno original: texto, ordem, figuras, legendas e alternativas.
          </label>
          <label className="review-reason">
            Justificativa
            <textarea value={reason} onChange={e => setReason(e.target.value)} maxLength={2000} />
          </label>
          <div className="review-actions">
            <button className="button secondary" disabled={busy} onClick={() => review('reject')}>
              Rejeitar proposta
            </button>
            <button className="button" disabled={busy || !compared} onClick={() => review('approve')}>
              Aprovar e criar rascunho
            </button>
          </div>
        </>
      )}
    </section>
  );
}
