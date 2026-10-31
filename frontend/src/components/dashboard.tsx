'use client';

import Link from 'next/link';
import { ArrowRight, BookOpen, Check, FileText, History as HistoryIcon } from 'lucide-react';
import { Exam, History, pct, Progress } from '@/lib/api';
import { useData } from '@/lib/use-data';
import { useStart } from '@/lib/use-start';
import { ErrorBox, Loading } from './ui';
import { CardSeam, LearningPieces } from './design';

export default function Dashboard() {
  const exams = useData<Exam[]>('/exams');
  const progress = useData<Progress>('/me/progress');
  const history = useData<History[]>('/me/history');
  const { start, busy, error } = useStart();
  if (exams.loading || progress.loading || history.loading) return <Loading/>;
  if (exams.error || progress.error || history.error) return <ErrorBox message={exams.error || progress.error || history.error} retry={() => { exams.reload(); progress.reload(); history.reload(); }}/>;
  const p = progress.data!;
  const h = history.data!;
  const unfinished = h.find(run => !run.finished_at);
  const featured = unfinished?.exam || exams.data?.[0];
  const stats = [
    { label: 'Provas concluídas', value: p.completed_runs, helper: 'Um passo de cada vez' },
    { label: 'Questões respondidas', value: p.summary.answered, helper: 'Em provas finalizadas' },
    { label: 'Aproveitamento geral', value: pct(p.summary.total ? p.summary.percentage : null), helper: p.summary.total ? `${p.summary.correct} acertos em ${p.summary.total} questões válidas` : 'Seu caminho começa aqui' },
    { label: 'Provas em andamento', value: h.filter(run => !run.finished_at).length, helper: 'Para continuar no seu tempo' },
  ];

  return <>
    <section className="home-stage" aria-labelledby="home-title">
      <div className="home-intro">
        <div className="home-copy"><h1 id="home-title">Aprender,<br/>no seu tempo.</h1><p>Um espaço para aprender com calma.</p></div>
        <LearningPieces/>
      </div>
      <div className="home-actions">
        <article className="study-card resume-card">
          <FileText className="study-card-icon" size={32} strokeWidth={1.4}/>
          <div>
            <p className="study-card-label">{unfinished ? 'Continue de onde parou' : 'Seu próximo passo'}</p>
            <h2>{featured ? featured.title : 'Seu espaço está pronto'}</h2>
            <p className="study-card-detail">{unfinished ? <><Check size={14}/>Respostas salvas</> : featured ? `${featured.item_count} questões, no seu ritmo.` : 'Escolha uma prova assim que o catálogo estiver disponível.'}</p>
            {unfinished ? <Link className="button" href={`/runs/${unfinished.id}`}>Continuar prova<ArrowRight size={19}/></Link> : featured ? <button className="button" disabled={busy} onClick={() => start(featured)}>{busy ? 'Abrindo…' : 'Iniciar prova'}<ArrowRight size={19}/></button> : <Link className="button secondary" href="/exams">Explorar provas<ArrowRight size={19}/></Link>}
          </div>
        </article>
        <CardSeam/>
        <Link className="study-card catalog-card" href="/exams">
          <BookOpen className="study-card-icon" size={34} strokeWidth={1.4}/>
          <div><h2>Banco de provas</h2><p className="study-card-detail">Escolha seu próximo desafio.</p></div>
          <span className="circle-arrow"><ArrowRight size={24}/></span>
        </Link>
      </div>
    </section>
    {error && <ErrorBox message={error}/>}
    <section className="home-overview" aria-label="Resumo do aprendizado">
      <div className="section-heading"><div><p className="eyebrow">UM CAMINHO EM CONSTRUÇÃO</p><h2>O que você já construiu.</h2></div><Link className="text-link" href="/progress">Ver desempenho<ArrowRight size={16}/></Link></div>
      <div className="stats-grid">{stats.map(({ label, value, helper }) => <article className="stat-card" key={label}><span className="stat-label">{label}</span><strong className="stat-value">{value}</strong><span className="stat-helper">{helper}</span></article>)}</div>
      <Link className="home-history-link" href="/history"><HistoryIcon size={18}/>Seu histórico fica guardado aqui.<ArrowRight size={16}/></Link>
    </section>
  </>;
}
