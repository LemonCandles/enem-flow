'use client';
import { useState } from 'react';
import { Lightbulb } from 'lucide-react';
import { attempts } from '@/lib/endpoints';
import type { DeliveredHelp, HelpLevel, HelpState } from '@/lib/types';
import { RichText } from '../question-content';

const NAMES: Record<HelpLevel, string> = { orientation: 'Orientação', hint: 'Pista', solution: 'Resolução' };
const ACTIONS: Record<HelpLevel, string> = {
  orientation: 'Pedir orientação',
  hint: 'Pedir uma pista',
  solution: 'Ver a resolução',
};
const ORDER: HelpLevel[] = ['orientation', 'hint', 'solution'];

// Help by levels in practice. A failure shows a message and the practice goes on.
export function TutorHelp({
  sessionId,
  itemId,
  state,
  finished,
}: {
  sessionId: string;
  itemId: string;
  state: HelpState;
  finished: boolean;
}) {
  // Help received after loading the page, per item, so it stays when the student moves between questions.
  const [received, setReceived] = useState<Record<string, DeliveredHelp[]>>({});
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const error = errors[itemId];
  const delivered = [...state.delivered];
  for (const help of received[itemId] || []) if (!delivered.some(d => d.level === help.level)) delivered.push(help);
  const next = state.available ? ORDER.find(level => !delivered.some(d => d.level === level)) : undefined;
  if (!delivered.length && (!state.available || finished)) return null;

  async function ask(level: HelpLevel) {
    setBusy(itemId);
    setErrors(current => ({ ...current, [itemId]: '' }));
    // The same key is reused if the student retries after a failure: no duplicated help.
    const slot = `${itemId}:${level}`;
    const key = keys[slot] || crypto.randomUUID();
    setKeys(current => ({ ...current, [slot]: key }));
    try {
      const event = await attempts.requestHelp(sessionId, itemId, level, key);
      setReceived(current => ({ ...current, [itemId]: [...(current[itemId] || []), event] }));
    } catch (e) {
      const message = `${(e as Error).message} Você pode continuar a prática normalmente.`;
      setErrors(current => ({ ...current, [itemId]: message }));
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="tutor-help" aria-labelledby={`tutor-${itemId}`}>
      <h3 id={`tutor-${itemId}`}>
        <Lightbulb size={16} aria-hidden="true" />
        Ajuda do tutor
      </h3>
      {!finished && (
        <p className="small-text muted">
          Peça um nível por vez. Questões respondidas com ajuda continuam no seu histórico, mas não contam como
          evidência independente no painel.
        </p>
      )}
      {delivered.map(help => (
        <div className="tutor-message" key={help.level}>
          <strong>{NAMES[help.level]}</strong>
          <div aria-live="polite">
            <RichText text={help.message} />
          </div>
          {help.mode === 'material' && <small className="muted">Texto aprovado pela curadoria.</small>}
        </div>
      ))}
      {error && (
        <p className="notice-box" role="alert">
          {error}
        </p>
      )}
      {next && !finished && (
        <button className="button secondary compact" disabled={!!busy} onClick={() => ask(next)}>
          {busy === itemId ? 'Preparando a ajuda…' : ACTIONS[next]}
        </button>
      )}
    </section>
  );
}
