'use client';
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Check, ChevronLeft, ChevronRight, Clock3, ExternalLink, Flag, ListChecks, Save, ShieldCheck, X } from 'lucide-react';
import { api, pct, Run, send } from '@/lib/api';
import { useData } from '@/lib/use-data';
import { ErrorBox, Loading } from './ui';
import { QuestionContent, RichText } from './question-content';
import { trapDialogFocus } from '@/lib/dialog-focus';

export default function ExamRunner({ id }: { id: string }) {
  const { data: run, setData: setRun, error: loadError, loading, reload } = useData<Run>(`/exam-runs/${id}`);
  const [index, setIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [filter, setFilter] = useState('all');
  const [showMap, setShowMap] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const finishTitleId = useId();
  const questionHeading = useRef<HTMLHeadingElement>(null);
  const navigate = useCallback((next: number) => {
    setIndex(next); setSaved(false); setShowMap(false);
    sessionStorage.setItem(`exam-position:${id}`, String(next));
    setTimeout(() => {
      questionHeading.current?.focus({ preventScroll: true });
      window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
    }, 0);
  }, [id]);
  useEffect(() => { const stored = Number(sessionStorage.getItem(`exam-position:${id}`) || 0); setIndex(Number.isFinite(stored) ? stored : 0); }, [id]);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const itemCount = run?.items.length ?? 0;
  useEffect(() => {
    if (loading || loadError || !itemCount) return;
    function onArrow(event: KeyboardEvent) {
      if (event.defaultPrevented || busy || event.repeat || event.isComposing || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
      if (document.querySelector('dialog[open], [aria-modal="true"], [aria-controls="site-navigation"][aria-expanded="true"]')) return;
      // Radios keep their native arrow-key selection; editable and scrollable
      // content must also retain the keys it needs.
      if (event.target instanceof Element && event.target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="radio"], [role="slider"], [role="spinbutton"], [role="tab"], [role="listbox"], [role="menu"], [role="tree"], [role="grid"], .native-table-wrap, .native-equation, .figure-equation, .figure-viewport, .math-inline')) return;
      const next = index + (event.key === 'ArrowRight' ? 1 : -1);
      if (next < 0 || next >= itemCount) return;
      event.preventDefault();
      navigate(next);
    }
    window.addEventListener('keydown', onArrow);
    return () => window.removeEventListener('keydown', onArrow);
  }, [busy, index, itemCount, loadError, loading, navigate]);
  if (loading) return <Loading/>;
  if (loadError || !run) return <ErrorBox message={loadError || 'Execução não encontrada.'} retry={reload}/>;
  const finished = !!run.finished_at;
  const current = run.items[Math.min(index, run.items.length - 1)];
  const answered = Object.values(run.answers).filter(Boolean).length;
  const elapsed = Math.max(0, Math.floor(((run.finished_at ? run.finished_at * 1000 : now) - run.started_at * 1000) / 1000));
  const time = `${Math.floor(elapsed / 3600).toString().padStart(2, '0')}:${Math.floor(elapsed % 3600 / 60).toString().padStart(2, '0')}:${(elapsed % 60).toString().padStart(2, '0')}`;
  async function choose(choice: string | null) {
    if (busy || finished) return;
    setBusy(true); setError(''); setSaved(false);
    const before = run?.answers || {};
    setRun(previous => previous ? { ...previous, answers: { ...previous.answers, [current.id]: choice } } : previous);
    try {
      const result = await send<{ answers: Run['answers'] }>(`/exam-runs/${id}/answers/${current.id}`, { choice }, 'PUT');
      setRun(previous => previous ? { ...previous, answers: result.answers } : previous); setSaved(true);
    } catch (e) { setRun(previous => previous ? { ...previous, answers: before } : previous); setError((e as Error).message + ' A alteração não foi salva. Selecione a alternativa novamente para tentar.'); }
    finally { setBusy(false); }
  }
  async function finish() {
    if (busy) return;
    setBusy(true); setError('');
    try { setRun(await api<Run>(`/exam-runs/${id}/finish`, { method: 'POST' })); dialog.current?.close(); navigate(0); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const status = (question: Run['items'][number]) => question.annulled ? 'annulled' : !run.answers[question.id] ? 'unanswered' : run.answers[question.id] === question.correct_answer ? 'correct' : 'incorrect';
  return <><div className="runner-top"><Link className="text-link muted" href={finished ? '/history' : '/exams'}><ArrowLeft size={16}/>{finished ? 'Voltar ao histórico' : 'Sair e continuar depois'}</Link><span className="badge">{run.exam.booklet}</span></div><div className="runner-heading"><div><p className="eyebrow">{finished ? 'PROVA CONCLUÍDA' : 'SEU MOMENTO DE PRATICAR'}</p><h1>{run.exam.title}</h1><p className="small-text muted">{run.exam.application} · {run.items.length} questões · {finished ? 'Resultado salvo no seu histórico' : 'Suas respostas são salvas a cada escolha'}</p></div><div className="runner-clock"><Clock3 size={18}/><span>{time}</span><small>tempo decorrido</small></div></div>{run.exam.content_quality?.review_status === 'pending' && <p className="notice-box">Este caderno foi extraído automaticamente e aguarda conferência. Consulte o original ao encontrar dúvidas no texto, nas fórmulas ou nas figuras.</p>}{finished && run.result && <section className="result-summary"><div className="result-score"><span className="eyebrow">APROVEITAMENTO</span><strong>{pct(run.result.percentage)}</strong><span>{run.result.correct} de {run.result.total} questões válidas</span></div><div className="result-metrics"><div><i className="legend-dot correct"/><strong>{run.result.correct}</strong><span>Acertos</span></div><div><i className="legend-dot incorrect"/><strong>{run.result.incorrect}</strong><span>Erros</span></div><div><i className="legend-dot unanswered"/><strong>{run.result.unanswered}</strong><span>Em branco</span></div><div><i className="legend-dot annulled"/><strong>{run.result.annulled}</strong><span>Anuladas</span></div></div><p>Correção objetiva pelo gabarito. Questões anuladas não entram no percentual. Este resultado não é uma nota TRI.</p></section>}{error && <ErrorBox message={error}/>}<div className="runner-progress"><div><span>{answered} de {run.items.length} respondidas</span><span>{Math.round(answered / run.items.length * 100)}%</span></div><div className="progress-track"><i style={{ width: `${answered / run.items.length * 100}%` }}/></div></div><div className="runner-layout"><section className="panel question-panel"><header className="question-header"><div><span className="badge">{current.area}</span><h2 tabIndex={-1} ref={questionHeading}>Questão {current.number.toString().padStart(2, '0')}</h2></div><span className="small-text muted">{index + 1} / {run.items.length}</span></header>{!!current.preparation_errors && <p className="notice-box">Esta questão tem pendências de apresentação registradas. Confira a página {current.page} do <a className="text-link" href={`${run.exam.source.url}#page=${current.page}`} target="_blank" rel="noreferrer">caderno oficial</a> antes de interpretar a correção.</p>}{current.annulled && <p className="notice-box">Questão anulada no gabarito oficial. Não entra no cálculo de desempenho.</p>}<div className="question-content"><QuestionContent question={current}/></div><fieldset className="alternatives" disabled={busy || finished}><legend>{finished ? 'Sua resposta e gabarito' : 'Marque sua resposta'}</legend>{current.alternatives.map(option => { const chosen = run.answers[current.id] === option.letter; const right = finished && !current.annulled && current.correct_answer === option.letter; const wrong = finished && !current.annulled && chosen && !right; return <label className={`alternative ${chosen ? 'chosen' : ''} ${right ? 'right' : ''} ${wrong ? 'wrong' : ''}`} key={option.letter}><input type="radio" name={`answer-${current.id}`} value={option.letter} checked={chosen} onChange={() => choose(option.letter)}/><span className="alternative-letter">{option.letter}</span><span className="alternative-text"><RichText text={option.text}/>{option.image && <img src={`/api${option.image.path}`} alt={option.image.alt}/>}</span>{right && <span className="answer-note"><Check size={15}/>Gabarito</span>}{wrong && <span className="answer-note"><X size={15}/>Sua resposta</span>}{chosen && !finished && <Check size={17}/>}</label>; })}</fieldset><div className="answer-status"><span role="status" className={saved ? 'saved' : 'muted'}>{busy ? <><Save size={14}/>Salvando…</> : saved ? <><ShieldCheck size={14}/>Resposta salva</> : finished ? <><ShieldCheck size={14}/>Resultado definitivo</> : <><Save size={14}/>Respostas salvas na sua conta</>}</span>{!finished && <button className="text-button muted" disabled={busy || !run.answers[current.id]} onClick={() => choose(null)}>Limpar resposta</button>}</div><div className="question-navigation"><button className="button secondary" disabled={busy || index === 0} onClick={() => navigate(index - 1)}><ChevronLeft size={17}/>Anterior</button>{index < run.items.length - 1 ? <button className="button" disabled={busy} onClick={() => navigate(index + 1)}>Próxima questão <ChevronRight size={17}/></button> : !finished ? <button className="button" disabled={busy} onClick={() => dialog.current?.showModal()}>Revisar e finalizar <Flag size={16}/></button> : <Link className="button" href="/progress">Ver meu desempenho <ArrowRight size={16}/></Link>}</div></section><aside className="question-aside"><button className="map-toggle button secondary" onClick={() => setShowMap(!showMap)}><ListChecks size={18}/>{showMap ? 'Ocultar mapa de questões' : 'Abrir mapa de questões'}</button><div className={`panel question-map ${showMap ? 'map-open' : ''}`}><div className="row between"><h3>Mapa de questões</h3><ListChecks size={18} className="muted"/></div><p className="small-text muted">Navegue livremente entre as questões.</p>{finished && <select aria-label="Filtrar revisão" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">Todas as questões</option><option value="correct">Acertos</option><option value="incorrect">Erros</option><option value="unanswered">Em branco</option><option value="annulled">Anuladas</option></select>}<div className="question-grid">{run.items.map((question, i) => { const state = finished ? status(question) : run.answers[question.id] ? 'answered' : ''; return filter !== 'all' && finished && state !== filter ? null : <button key={question.id} disabled={busy} className={`question-number ${state} ${index === i ? 'current' : ''}`} aria-label={`Questão ${question.number}${state ? `, ${{ correct: 'correta', incorrect: 'incorreta', unanswered: 'em branco', annulled: 'anulada', answered: 'respondida' }[state]}` : ''}`} aria-current={index === i ? 'step' : undefined} onClick={() => navigate(i)}>{question.number}</button>; })}</div><div className="map-legend"><span><i className="legend-dot answered"/>{finished ? 'Acertos' : 'Respondida'}</span><span><i className="legend-dot unanswered"/>{finished ? 'Em branco' : 'Não respondida'}</span>{finished && <><span><i className="legend-dot incorrect"/>Erros</span><span><i className="legend-dot annulled"/>Anuladas</span></>}</div>{!finished && <button className="button full" disabled={busy} onClick={() => dialog.current?.showModal()}><Flag size={16}/>Finalizar prova</button>}</div><div className="runner-tip"><ShieldCheck size={20}/><p>{finished ? 'Seu resultado está salvo. Você pode revisitar cada questão sempre que quiser.' : 'Você pode voltar e alterar qualquer resposta antes de finalizar. Estude no seu ritmo.'}</p></div><a className="source-link" href={run.exam.source.url} target="_blank" rel="noreferrer">Consultar caderno oficial <ExternalLink size={13}/></a></aside></div><dialog ref={dialog} className="confirm-dialog" onKeyDown={trapDialogFocus} aria-labelledby={finishTitleId} aria-describedby={`${finishTitleId}-description`}><div className="dialog-heading"><span className="stat-icon teal"><Flag size={23}/></span><button className="icon-button" aria-label="Fechar confirmação" disabled={busy} onClick={() => dialog.current?.close()}><X size={20}/></button></div><h2 id={finishTitleId}>Pronto para finalizar?</h2><p id={`${finishTitleId}-description`}>Você respondeu <strong>{answered} de {run.items.length} questões</strong>. {answered < run.items.length && `${run.items.length - answered} questões estão em branco. `}Após a confirmação, as respostas serão corrigidas e não poderão ser alteradas.</p>{error && <ErrorBox message={error}/>}<div className="dialog-actions"><button className="button secondary" disabled={busy} onClick={() => dialog.current?.close()}>Continuar revisando</button><button className="button" disabled={busy} onClick={finish}>{busy ? 'Finalizando…' : 'Confirmar finalização'}</button></div></dialog></>;
}
