'use client';
import { FormEvent, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Diagnostic, DiagnosticOptions, send } from '@/lib/api';
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
  return <><PageTitle eyebrow="CONHEÇA SEU PONTO DE PARTIDA" title="Iniciar diagnóstico" text="Responda a questões de temas variados e consulte seu resultado ao finalizar."/>
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
