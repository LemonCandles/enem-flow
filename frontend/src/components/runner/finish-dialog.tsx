'use client';
import { useId, type RefObject } from 'react';
import { Flag, X } from 'lucide-react';
import { trapDialogFocus } from '@/lib/dialog-focus';
import { ErrorBox } from '../ui';

export function FinishDialog({
  dialog,
  answered,
  total,
  busy,
  error,
  onConfirm,
}: {
  dialog: RefObject<HTMLDialogElement | null>;
  answered: number;
  total: number;
  busy: boolean;
  error: string;
  onConfirm: () => void;
}) {
  const finishTitleId = useId();
  return (
    <dialog
      ref={dialog}
      className="confirm-dialog"
      onKeyDown={trapDialogFocus}
      aria-labelledby={finishTitleId}
      aria-describedby={`${finishTitleId}-description`}
    >
      <div className="dialog-heading">
        <span className="stat-icon teal">
          <Flag size={23} />
        </span>
        <button
          className="icon-button"
          aria-label="Fechar confirmação"
          disabled={busy}
          onClick={() => dialog.current?.close()}
        >
          <X size={20} />
        </button>
      </div>
      <h2 id={finishTitleId}>Pronto para finalizar?</h2>
      <p id={`${finishTitleId}-description`}>
        Você respondeu{' '}
        <strong>
          {answered} de {total} questões
        </strong>
        . {answered < total && `${total - answered} questões estão em branco. `}Após a confirmação, as respostas serão
        corrigidas e não poderão ser alteradas.
      </p>
      {error && <ErrorBox message={error} />}
      <div className="dialog-actions">
        <button className="button secondary" disabled={busy} onClick={() => dialog.current?.close()}>
          Continuar revisando
        </button>
        <button className="button" disabled={busy} onClick={onConfirm}>
          {busy ? 'Finalizando…' : 'Confirmar finalização'}
        </button>
      </div>
    </dialog>
  );
}
