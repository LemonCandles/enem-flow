'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Clock3 } from 'lucide-react';
import type { AttemptSource } from '@/lib/attempt-source';
import { useAttempt } from '@/lib/use-attempt';
import { useQuestionNavigation } from '@/lib/use-question-navigation';
import { FinishDialog } from './runner/finish-dialog';
import { QuestionAside } from './runner/question-aside';
import { QuestionPanel } from './runner/question-panel';
import { ResultSummary } from './runner/result-summary';
import { TutorHelp } from './runner/tutor-help';
import { ErrorBox, Loading } from './ui';

export default function ExamRunner({ id, source }: { id: string; source: AttemptSource }) {
  const attempt = useAttempt(id, source);
  const { raw, loading, loadError, reload, busy, error, saved, setSaved } = attempt;
  const run = raw && source.toRun(raw);
  const diagnosticSession = raw && source.session(raw);
  const [now, setNow] = useState(Date.now());
  const [showMap, setShowMap] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const reset = useCallback(() => {
    setSaved(false);
    setShowMap(false);
  }, [setSaved]);
  const { index, navigate, heading } = useQuestionNavigation(
    id,
    run?.items.length ?? 0,
    loading || !!loadError || busy,
    reset,
  );
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  if (loading) return <Loading />;
  if (loadError || !run) return <ErrorBox message={loadError || 'Execução não encontrada.'} retry={reload} />;
  const finished = !!run.finished_at;
  const current = run.items[Math.min(index, run.items.length - 1)];
  const answered = Object.values(run.answers).filter(Boolean).length;
  const elapsed = Math.max(
    0,
    Math.floor(((run.finished_at ? run.finished_at * 1000 : now) - run.started_at * 1000) / 1000),
  );
  const time = `${Math.floor(elapsed / 3600)
    .toString()
    .padStart(2, '0')}:${Math.floor((elapsed % 3600) / 60)
    .toString()
    .padStart(2, '0')}:${(elapsed % 60).toString().padStart(2, '0')}`;
  const review = () => dialog.current?.showModal();
  return (
    <>
      <div className="runner-top">
        <Link className="text-link muted" href={finished ? '/history' : source.leaveHref}>
          <ArrowLeft size={16} />
          {finished ? 'Voltar ao histórico' : 'Sair e continuar depois'}
        </Link>
        <span className="badge">{run.exam.booklet}</span>
      </div>
      <div className="runner-heading">
        <div>
          <p className="eyebrow">{finished ? source.concludedLabel : 'SEU MOMENTO DE PRATICAR'}</p>
          <h1>{run.exam.title}</h1>
          <p className="small-text muted">
            {run.exam.application} · {run.items.length} questões ·{' '}
            {finished ? 'Resultado salvo no seu histórico' : 'Suas respostas são salvas a cada escolha'}
          </p>
        </div>
        <div className="runner-clock">
          <Clock3 size={18} />
          <span>{time}</span>
          <small>tempo decorrido</small>
        </div>
      </div>
      {finished && run.result && <ResultSummary result={run.result} />}
      {diagnosticSession && (
        <p className="notice-box">
          Tempo planejado: {diagnosticSession.available_minutes} minutos, sem encerramento automático. Cobertura:{' '}
          {Object.values(diagnosticSession.selection.themes).filter(n => n > 0).length} de{' '}
          {Object.keys(diagnosticSession.selection.themes).length} temas disponíveis ·{' '}
          {diagnosticSession.selection.selected_items} de {diagnosticSession.selection.requested_items} itens
          planejados. {finished ? 'Consulte a quantidade de evidência no painel.' : 'A correção aparece ao finalizar.'}
        </p>
      )}
      {error && <ErrorBox message={error} />}
      <div className="runner-progress">
        <div>
          <span>
            {answered} de {run.items.length} respondidas
          </span>
          <span>{Math.round((answered / run.items.length) * 100)}%</span>
        </div>
        <div className="progress-track">
          <i style={{ width: `${(answered / run.items.length) * 100}%` }} />
        </div>
      </div>
      <div className="runner-layout">
        <QuestionPanel
          current={current}
          index={index}
          total={run.items.length}
          answer={run.answers[current.id]}
          finished={finished}
          busy={busy}
          saved={saved}
          source={source}
          session={diagnosticSession}
          sourceUrl={run.exam.source.url}
          heading={heading}
          help={
            source.offersHelp &&
            current.help && <TutorHelp sessionId={id} itemId={current.id} state={current.help} finished={finished} />
          }
          onChoose={choice => attempt.choose(run, current.id, choice)}
          onNavigate={navigate}
          onReview={review}
        />
        <QuestionAside
          items={run.items}
          answers={run.answers}
          index={index}
          finished={finished}
          busy={busy}
          showMap={showMap}
          source={source}
          sourceUrl={current.source_url || run.exam.source.url}
          onToggle={() => setShowMap(!showMap)}
          onNavigate={navigate}
          onReview={review}
        />
      </div>
      <FinishDialog
        dialog={dialog}
        answered={answered}
        total={run.items.length}
        busy={busy}
        error={error}
        onConfirm={() =>
          attempt.finish(() => {
            dialog.current?.close();
            navigate(0);
          })
        }
      />
    </>
  );
}
