'use client';
import { FormEvent, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { paths } from '@/lib/endpoints';
import type { DiagnosticOptions } from '@/lib/types';
import { useData } from '@/lib/use-data';
import { Empty, ErrorBox, Loading, PageTitle } from './ui';

// Objective, area and time: the same request starts a diagnostic or a practice session.
export function SessionForm({
  eyebrow,
  title,
  text,
  placeholder,
  submitLabel,
  unavailable,
  start,
  pathFor,
  practice = false,
}: {
  eyebrow: string;
  title: string;
  text: string;
  placeholder: string;
  submitLabel: string;
  unavailable: string;
  start: (body: object, key: string) => Promise<{ id: string }>;
  pathFor: (id: string) => string;
  practice?: boolean;
}) {
  const [area, setArea] = useState('');
  const [minutes, setMinutes] = useState(15);
  const { data, loading, error, reload } = useData<DiagnosticOptions>(
    practice
      ? `${paths.practiceOptions}?available_minutes=${Math.max(3, Math.min(180, Math.floor(minutes || 3)))}`
      : paths.diagnosticOptions,
  );
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const pending = useRef<{ body: string; key: string } | null>(null);
  const router = useRouter();
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error} retry={reload} />;
  const chosen = data.areas.find(a => a.area === area) || data.areas[0];
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !chosen || !chosen.eligible_items) return;
    const form = new FormData(event.currentTarget);
    const body = { objective: String(form.get('objective')), area: chosen.area, available_minutes: minutes };
    const serialized = JSON.stringify(body);
    if (pending.current?.body !== serialized) pending.current = { body: serialized, key: crypto.randomUUID() };
    setBusy(true);
    setFailure('');
    try {
      const session = await start(body, pending.current.key);
      router.push(pathFor(session.id));
    } catch (e) {
      setFailure((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle eyebrow={eyebrow} title={title} text={text} />
      {!chosen ? (
        <section className="panel">
          <Empty title="Ainda não há questões elegíveis" text={unavailable} />
        </section>
      ) : (
        <section className="panel settings-panel">
          <h2>Seu objetivo para esta sessão</h2>
          <p className="small-text muted">
            O conjunto de questões fica definido ao iniciar. Você pode sair e retomar depois.
          </p>
          <form onSubmit={submit}>
            <label>
              Objetivo
              <input name="objective" required maxLength={120} placeholder={placeholder} />
            </label>
            <label>
              Área
              <select aria-label="Área" value={chosen.area} onChange={e => setArea(e.target.value)}>
                {data.areas.map(a => (
                  <option key={a.area}>{a.area}</option>
                ))}
              </select>
            </label>
            <label>
              Tempo disponível em minutos
              <input
                type="number"
                min={3}
                max={180}
                required
                value={minutes}
                onChange={e => setMinutes(Number(e.target.value))}
              />
            </label>
            <p className="notice-box">
              Previsão: {Math.min(20, Math.floor(minutes / 3), chosen.eligible_items)} questões, com cerca de 3 minutos
              por questão. O tempo não encerra a sessão.
            </p>
            <p className="small-text muted">
              {chosen.eligible_items} itens elegíveis em {Object.keys(chosen.themes).length} temas:{' '}
              {Object.keys(chosen.themes).join(', ')}. A cobertura depende dos rótulos publicados; habilidades serão
              incorporadas conforme forem publicadas.
            </p>
            {!chosen.eligible_items && (
              <p className="notice-box">
                As questões desta área atingiram o limite de exposição. Retome uma sessão pelo histórico ou escolha
                outra área.
              </p>
            )}
            {practice && (
              <p className="small-text muted">
                Provas disponíveis podem incluir itens sem temas publicados. A previsão considera somente identidades
                elegíveis e o seu limite de exposição.
              </p>
            )}
            {failure && <ErrorBox message={failure} />}
            <button className="button" disabled={busy || loading || !chosen.eligible_items}>
              {busy ? 'Preparando…' : submitLabel}
            </button>
          </form>
          <Link className="text-link" href="/history">
            Retomar pelo histórico
          </Link>
        </section>
      )}
    </>
  );
}
