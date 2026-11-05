'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BookOpen, Check, Clock3 } from 'lucide-react';
import { paths } from '@/lib/endpoints';
import { date, pct } from '@/lib/format';
import type { DiagnosticSummary, History } from '@/lib/types';
import { useData } from '@/lib/use-data';
import { Empty, ErrorBox, Loading, PageTitle } from './ui';

export function HistoryPage() {
  const { data, error, loading, reload } = useData<History[]>(paths.history);
  const diagnostics = useData<DiagnosticSummary[]>(paths.diagnosticHistory);
  const [filter, setFilter] = useState('all');
  if (loading || diagnostics.loading) return <Loading />;
  const rows =
    data?.filter(run => filter === 'all' || (filter === 'finished' ? run.finished_at : !run.finished_at)) || [];
  return (
    <>
      <PageTitle
        eyebrow="SEU CAMINHO ATÉ AQUI"
        title="Histórico de provas"
        text="Relembre seus resultados ou retome provas e diagnósticos."
      />
      {error && <ErrorBox message={error} retry={reload} />}
      <DiagnosticHistory
        data={diagnostics.data}
        error={diagnostics.error}
        reload={diagnostics.reload}
        filter={filter}
      />
      <div className="segmented" aria-label="Filtrar histórico">
        {[
          ['all', 'Todos os registros'],
          ['open', 'Em andamento'],
          ['finished', 'Concluídas'],
        ].map(([key, label]) => (
          <button
            className={filter === key ? 'active' : ''}
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
            key={key}
          >
            {label}
          </button>
        ))}
      </div>
      {rows.length ? (
        <section className="panel history-panel">
          <div className="history-table">
            <div className="history-table-head">
              <span>PROVA</span>
              <span>INÍCIO</span>
              <span>STATUS</span>
              <span>RESULTADO</span>
              <span />
            </div>
            {rows.map(run => (
              <div className="history-row" key={run.id}>
                <div className="history-exam">
                  <span className="stat-icon teal">
                    <BookOpen size={20} />
                  </span>
                  <div>
                    <strong>{run.exam.title}</strong>
                    <span>{run.exam.booklet}</span>
                  </div>
                </div>
                <span className="muted small-text">{date(run.started_at)}</span>
                <span className={`badge ${run.finished_at ? 'green' : 'amber'}`}>
                  {run.finished_at ? <Check size={12} /> : <Clock3 size={12} />}{' '}
                  {run.finished_at ? 'Concluída' : 'Em andamento'}
                </span>
                <div className="history-result">
                  <strong>
                    {run.finished_at ? pct(run.result?.percentage) : `${run.answered}/${run.exam.item_count}`}
                  </strong>
                  <span>{run.finished_at ? `${run.result?.correct} acertos` : 'respondidas'}</span>
                </div>
                <Link className="button secondary compact" href={`/runs/${run.id}`}>
                  {run.finished_at ? 'Ver resultado' : 'Continuar'}
                  <ArrowRight size={14} />
                </Link>
              </div>
            ))}
          </div>
        </section>
      ) : (
        <section className="panel">
          <Empty
            title="Seu caminho está só começando"
            text="As provas iniciadas e concluídas ficam guardadas aqui, só para você."
          />
        </section>
      )}
    </>
  );
}

function DiagnosticHistory({
  data,
  error,
  reload,
  filter,
}: {
  data?: DiagnosticSummary[];
  error: string;
  reload: () => void;
  filter: string;
}) {
  if (error) return <ErrorBox message={error} retry={reload} />;
  const rows = data?.filter(s => filter === 'all' || (filter === 'finished' ? s.finished_at : !s.finished_at)) || [];
  return (
    <section className="panel breakdown-panel">
      <h2>Diagnósticos</h2>
      {!rows.length ? (
        <p className="small-text muted">
          Nenhum diagnóstico neste filtro. <Link href="/diagnostic">Iniciar diagnóstico</Link>
        </p>
      ) : (
        <div className="breakdown-list">
          {rows.map(s => (
            <article key={s.id}>
              <h3>
                {s.area} · {s.objective}
              </h3>
              <p className="small-text muted">
                {date(s.started_at)} ·{' '}
                {s.finished_at
                  ? `Concluído · ${pct(s.result?.percentage)}`
                  : `${s.answered}/${s.selection.selected_items} respondidas`}
              </p>
              <Link className="button secondary compact" href={`/sessions/${s.id}`}>
                {s.finished_at ? 'Ver diagnóstico' : 'Continuar diagnóstico'}
              </Link>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
