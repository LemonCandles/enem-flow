'use client';
import { FormEvent, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Diagnostic, DiagnosticOptions, KnowledgeState, date, pct, send } from '@/lib/api';
import { useData } from '@/lib/use-data';
import { Empty, ErrorBox, Loading, PageTitle } from './ui';

export default function DiagnosticPage() {
  const { data, loading, error, reload } = useData<DiagnosticOptions>('/diagnostic-options');
  const [area, setArea] = useState('');
  const [minutes, setMinutes] = useState(15);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const pending = useRef<{ body: string; key: string } | null>(null);
  const router = useRouter();
  if (loading) return <Loading/>;
  if (error || !data) return <ErrorBox message={error} retry={reload}/>;
  const chosen = data.areas.find(a => a.area === area) || data.areas[0];
  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !chosen) return;
    const form = new FormData(event.currentTarget);
    const body = { objective: String(form.get('objective')), area: chosen.area, available_minutes: minutes };
    const serialized = JSON.stringify(body);
    if (pending.current?.body !== serialized) pending.current = { body: serialized, key: crypto.randomUUID() };
    setBusy(true); setFailure('');
    try {
      const session = await send<Diagnostic>('/sessions', { ...body, idempotency_key: pending.current.key });
      router.push(`/sessions/${session.id}`);
    } catch (e) { setFailure((e as Error).message); setBusy(false); }
  }
  return <><PageTitle eyebrow="CONHEÇA SEU PONTO DE PARTIDA" title="Iniciar diagnóstico" text="Responda a questões de temas variados e acompanhe suas evidências de prática."/>
    {!chosen ? <section className="panel"><Empty title="Ainda não há questões elegíveis" text="O diagnóstico ficará disponível quando houver questões com temas publicados e sem pendências bloqueantes."/></section> : <section className="panel settings-panel"><h2>Seu objetivo para esta sessão</h2>
      <p className="small-text muted">O conjunto de questões fica definido ao iniciar. Você pode sair e retomar depois.</p>
      <form onSubmit={start}><label>Objetivo<input name="objective" required maxLength={120} placeholder="Ex.: conhecer meu desempenho em Matemática"/></label>
        <label>Área<select aria-label="Área" value={chosen.area} onChange={e => setArea(e.target.value)}>{data.areas.map(a => <option key={a.area}>{a.area}</option>)}</select></label>
        <label>Tempo disponível em minutos<input type="number" min={3} max={180} required value={minutes} onChange={e => setMinutes(Number(e.target.value))}/></label>
        <p className="notice-box">Previsão: {Math.min(20, Math.floor(minutes / 3), chosen.eligible_items)} questões, com cerca de 3 minutos por questão. O tempo não encerra a sessão.</p>
        <p className="small-text muted">{chosen.eligible_items} itens elegíveis em {Object.keys(chosen.themes).length} temas: {Object.keys(chosen.themes).join(', ')}. A cobertura depende dos rótulos publicados; habilidades serão incorporadas conforme forem publicadas.</p>
        {failure && <ErrorBox message={failure}/>}<button className="button" disabled={busy}>{busy ? 'Preparando…' : 'Começar diagnóstico'}</button>
      </form><Link className="text-link" href="/history">Retomar pelo histórico</Link>
    </section>}</>;
}

export function KnowledgePanel() {
  const { data, loading, error, reload } = useData<KnowledgeState>('/me/knowledge-state');
  const [kind, setKind] = useState<'themes' | 'skills'>('themes');
  const [area, setArea] = useState('');
  if (loading) return <Loading/>;
  if (error || !data) return <ErrorBox message={error} retry={reload}/>;
  const areas = Array.from(new Set([...data.themes, ...data.skills].map(g => g.area))).sort();
  const latest = [...data.themes, ...data.skills].filter(g => g.last_practice !== null).sort((a, b) => b.last_practice! - a.last_practice!)[0];
  const selectedArea = area || latest?.area || areas[0] || 'all';
  const groups = data[kind].filter(g => selectedArea === 'all' || g.area === selectedArea);
  return <section className="panel breakdown-panel knowledge-panel" aria-labelledby="knowledge-heading"><h2 id="knowledge-heading">Estado por tema e habilidade</h2>
    <p className="small-text muted">Provas e diagnósticos finalizados contribuem para este painel. A estimativa usa a primeira resposta marcada sem ajuda de cada item, mesmo quando ele aparece em outra cor.</p>
    <div className="segmented"><button aria-pressed={kind === 'themes'} className={kind === 'themes' ? 'active' : ''} onClick={() => setKind('themes')}>Temas do diagnóstico</button><button aria-pressed={kind === 'skills'} className={kind === 'skills' ? 'active' : ''} onClick={() => setKind('skills')}>Habilidades publicadas</button></div>
    <label>Filtrar estado por área<select aria-label="Filtrar estado por área" value={selectedArea} onChange={e => setArea(e.target.value)}><option value="all">Todas as áreas</option>{areas.map(a => <option key={a}>{a}</option>)}</select></label>
    {!groups.length ? <p className="notice-box">Ainda não há rótulos publicados neste recorte. A ausência de classificação não informa o desempenho.</p> : <div className="breakdown-list">{groups.map(g => <article key={JSON.stringify([g.area, g.discipline, g.taxonomy_version, g.name])}>
      <div className="row between"><div><h3>{g.name}</h3><span className="tiny muted">{g.area}{g.discipline ? ` · ${g.discipline}` : ''} · {g.taxonomy_version}</span></div><strong>{pct(g.estimate === null ? null : g.estimate * 100)}</strong></div>
      <p className="small-text">{g.independent_correct} acertos em {g.independent_attempts} itens independentes · {g.evidence_status === 'none' ? 'Sem evidência' : g.evidence_status === 'low' ? 'Pouca evidência' : 'Evidência disponível'}</p>
      <p className="tiny muted">{g.attempts} respostas · {g.repeated_attempts} repetições · {g.seen_items} itens apresentados · {g.unanswered} em branco. Assistidas: {g.assisted_correct}/{g.assisted_attempts}.{g.unknown_help_attempts > 0 ? ` Ajuda não informada: ${g.unknown_help_attempts}.` : ''}</p>
      <p className="tiny muted">Prática recente: {g.recent.filter(r => r.correct).length}/{g.recent.length} acertos nas últimas {g.recent.length} respostas válidas · Última prática: {g.last_practice ? date(g.last_practice) : 'Ainda não registrada'}.</p>
    </article>)}</div>}
    <p className="notice-box">Estimativa suavizada: (1 + acertos independentes) / (2 + itens independentes). Menos de {data.estimator.minimum_evidence} itens recebe o aviso de pouca evidência. Repetições, respostas assistidas e em branco não alteram a estimativa. Os rótulos podem se sobrepor; um erro não identifica uma causa única. Este indicador descreve respostas observadas e não representa domínio comprovado nem nota TRI.</p>
  </section>;
}
