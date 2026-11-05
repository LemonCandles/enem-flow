'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, History as HistoryIcon, Target } from 'lucide-react';
import { paths } from '@/lib/endpoints';
import { date, pct } from '@/lib/format';
import type { Progress } from '@/lib/types';
import { useData } from '@/lib/use-data';
import { KnowledgePanel } from './diagnostic';
import { Empty, ErrorBox, Loading, PageTitle } from './ui';

export function ProgressPage() {
  const { data, error, loading, reload } = useData<Progress>(paths.progress);
  const [kind, setKind] = useState('area');
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBox message={error || 'Não foi possível carregar o painel.'} retry={reload} />;
  const labels: Record<string, string> = { area: 'Área', discipline: 'Matéria', theme: 'Tema', skill: 'Habilidade' };
  const coverage = data.coverage[kind];
  return (
    <>
      <PageTitle
        eyebrow="CLAREZA PARA SEGUIR EM FRENTE"
        title="Meu desempenho"
        text="Acompanhe resultados de provas e evidências dos seus diagnósticos."
      />
      <KnowledgePanel />
      {!data.completed_runs ? (
        <section className="panel">
          <Empty
            title="Uma prova abre novas descobertas"
            text="Finalize sua primeira prova para ver acertos, evolução e desempenho por área."
          />
        </section>
      ) : (
        <>
          <section className="stats-grid">
            <article className="stat-card">
              <span className="stat-label">Provas concluídas</span>
              <strong className="stat-value">{data.completed_runs}</strong>
              <span className="stat-helper">Tentativas registradas</span>
            </article>
            <article className="stat-card">
              <span className="stat-label">Aproveitamento geral</span>
              <strong className="stat-value">{pct(data.summary.percentage)}</strong>
              <span className="stat-helper">
                {data.summary.correct} de {data.summary.total} questões válidas
              </span>
            </article>
            <article className="stat-card">
              <span className="stat-label">Questões respondidas</span>
              <strong className="stat-value">{data.summary.answered}</strong>
              <span className="stat-helper">{data.summary.unanswered} em branco</span>
            </article>
            <article className="stat-card">
              <span className="stat-label">Cobertura de habilidades</span>
              <strong className="stat-value">{pct(data.coverage.skill.percentage)}</strong>
              <span className="stat-helper">
                {data.coverage.skill.classified} de {data.coverage.skill.total} tentativas com rótulos
              </span>
            </article>
          </section>
          <section className="panel breakdown-panel">
            <div className="section-heading">
              <div>
                <h2>Um olhar para cada conhecimento</h2>
                <p className="small-text muted">Taxa de acerto e quantidade de evidências disponíveis.</p>
              </div>
              <span className="stat-icon teal">
                <Target size={20} />
              </span>
            </div>
            <div className="segmented">
              {Object.entries(labels).map(([key, label]) => (
                <button
                  key={key}
                  className={kind === key ? 'active' : ''}
                  aria-pressed={kind === key}
                  onClick={() => setKind(key)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="coverage-note">
              <span>Cobertura de classificação por {labels[kind].toLowerCase()}</span>
              <strong>
                {coverage.classified}/{coverage.total} tentativas · {pct(coverage.percentage)}
              </strong>
            </div>
            <div className="breakdown-list">
              {data.breakdown[kind].map(group => (
                <article key={group.name}>
                  <div className="row between">
                    <div>
                      <h3>{group.name}</h3>
                      <span className="tiny muted">
                        {group.correct} acertos · {group.attempts} tentativas{' '}
                        {kind === 'theme' || kind === 'skill' ? '(rótulos podem se sobrepor)' : ''}
                      </span>
                    </div>
                    <strong>{pct(group.percentage)}</strong>
                  </div>
                  <div className="progress-track">
                    <i style={{ width: `${group.percentage}%` }} />
                  </div>
                </article>
              ))}
            </div>
            <p className="notice-box">
              Ausência de classificação não significa ausência de dificuldade. Os resultados descrevem acertos nas
              questões realizadas; não representam diagnóstico de aprendizagem nem nota TRI.
            </p>
          </section>
          <section className="panel evolution-panel">
            <h2>Evolução por prova</h2>
            <div className="progress-history">
              {data.evolution.map(point => (
                <Link key={point.id} href={`/runs/${point.id}`}>
                  <span className="stat-icon teal">
                    <HistoryIcon size={18} />
                  </span>
                  <div>
                    <strong>{point.title}</strong>
                    <span className="tiny muted">{date(point.date)}</span>
                  </div>
                  <strong>{pct(point.percentage)}</strong>
                  <ArrowRight size={16} />
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </>
  );
}
