'use client';
import { FormEvent, useRef, useState } from 'react';
import { Check, Download, Trash2 } from 'lucide-react';
import { account } from '@/lib/endpoints';
import type { User } from '@/lib/types';
import { ErrorBox, PageTitle } from './ui';

export function SettingsPage({ user, onUpdate }: { user: User; onUpdate: (u: User) => void }) {
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setNotice('');
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      onUpdate(
        await account.updatePreferences({
          name: form.get('name'),
          target_course: form.get('target_course'),
          daily_goal: Number(form.get('daily_goal')),
        }),
      );
      setNotice('Preferências atualizadas.');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function erase() {
    setBusy(true);
    setError('');
    try {
      await account.eraseHistory();
      setNotice('Seu histórico, provas e diagnósticos foram excluídos.');
      dialog.current?.close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function exportHistory() {
    try {
      const [history, diagnostics, recommendations] = await account.exportHistory();
      const blob = new Blob([JSON.stringify({ exams: history, diagnostics, recommendations }, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'meu-historico-enem-flow.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="DO SEU JEITO"
        title="Configurações"
        text="Personalize seu espaço e mantenha o controle do seu histórico."
      />
      {error && <ErrorBox message={error} />}
      {notice && (
        <p role="status" className="success-box">
          {notice}
        </p>
      )}
      <section className="panel settings-panel">
        <h2>Seu perfil e seus objetivos</h2>
        <p className="small-text muted">{user.email}</p>
        <form onSubmit={save}>
          <label>
            Seu nome
            <input name="name" defaultValue={user.name} minLength={2} maxLength={80} required />
          </label>
          <label>
            Curso ou objetivo
            <input
              name="target_course"
              defaultValue={user.preferences.target_course || ''}
              placeholder="Ex.: Engenharia em uma universidade federal"
              maxLength={120}
            />
          </label>
          <label>
            Objetivo pessoal de questões por dia
            <input
              type="number"
              name="daily_goal"
              defaultValue={user.preferences.daily_goal || 10}
              min={1}
              max={100}
              required
            />
          </label>
          <button className="button" disabled={busy} type="submit">
            {busy ? 'Salvando…' : 'Salvar preferências'}
            <Check size={17} />
          </button>
        </form>
      </section>
      <section className="panel settings-panel">
        <h2>Seu histórico, suas escolhas</h2>
        <p className="muted small-text">
          Exporte seus resultados de provas e diagnósticos ou exclua as sessões e os eventos associados.
        </p>
        <div className="row settings-actions">
          <button className="button secondary" onClick={exportHistory}>
            <Download size={17} />
            Exportar resultados
          </button>
          <button className="button danger-outline" onClick={() => dialog.current?.showModal()}>
            <Trash2 size={17} />
            Excluir meu histórico
          </button>
        </div>
      </section>
      <dialog className="confirm-dialog" ref={dialog}>
        <span className="stat-icon orange">
          <Trash2 size={22} />
        </span>
        <h2>Excluir todo o histórico?</h2>
        <p>
          Esta ação exclui seus resultados, respostas, provas e diagnósticos em andamento. A exclusão é permanente. Sua
          conta e suas preferências serão mantidas.
        </p>
        {error && <ErrorBox message={error} />}
        <div className="dialog-actions">
          <button className="button secondary" disabled={busy} onClick={() => dialog.current?.close()}>
            Cancelar
          </button>
          <button className="button danger" disabled={busy} onClick={erase}>
            {busy ? 'Excluindo…' : 'Excluir definitivamente'}
          </button>
        </div>
      </dialog>
    </>
  );
}
