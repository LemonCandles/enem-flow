import type { ReactNode, Ref } from 'react';
import Link from 'next/link';
import { ArrowRight, Check, ChevronLeft, ChevronRight, Flag, Save, ShieldCheck, X } from 'lucide-react';
import type { AttemptSource } from '@/lib/attempt-source';
import type { Diagnostic, Question } from '@/lib/types';
import { QuestionContent, RichText } from '../question-content';

export function QuestionPanel({
  current,
  index,
  total,
  answer,
  finished,
  busy,
  saved,
  source,
  session,
  sourceUrl,
  heading,
  help,
  onChoose,
  onNavigate,
  onReview,
}: {
  current: Question;
  index: number;
  total: number;
  answer: string | null | undefined;
  finished: boolean;
  busy: boolean;
  saved: boolean;
  source: AttemptSource;
  session: Diagnostic | undefined;
  sourceUrl: string;
  heading: Ref<HTMLHeadingElement>;
  help?: ReactNode;
  onChoose: (choice: string | null) => void;
  onNavigate: (next: number) => void;
  onReview: () => void;
}) {
  return (
    <section className="panel question-panel">
      <header className="question-header">
        <div>
          <span className="badge">{current.area}</span>
          <h2 tabIndex={-1} ref={heading}>
            Questão {source.questionNumber(current, index).toString().padStart(2, '0')}
          </h2>
        </div>
        <span className="small-text muted">
          {index + 1} / {total}
        </span>
      </header>
      {current.recommendation && (
        <p className="notice-box">
          <strong>Por que esta questão?</strong> {current.recommendation.reason}
        </p>
      )}
      {!!current.preparation_errors && (
        <p className="notice-box">
          Esta questão tem pendências de apresentação registradas. Confira a página {current.page} do{' '}
          <a
            className="text-link"
            href={`${current.source_url || sourceUrl}#page=${current.page}`}
            target="_blank"
            rel="noreferrer"
          >
            caderno oficial
          </a>{' '}
          antes de interpretar a correção.
        </p>
      )}
      {current.annulled && (
        <p className="notice-box">Questão anulada no gabarito oficial. Não entra no cálculo de desempenho.</p>
      )}
      {source.showsOrigin && (
        <p className="small-text muted">
          Questão original {current.number} · Página {current.page}
          {session && session.selection.repeated_items.includes(current.id) ? ' · Item já apresentado' : ''}
        </p>
      )}
      <div className="question-content">
        <QuestionContent question={current} />
      </div>
      {help}
      <fieldset className="alternatives" disabled={busy || finished}>
        <legend>{finished ? 'Sua resposta e gabarito' : 'Marque sua resposta'}</legend>
        {current.alternatives.map(option => {
          const chosen = answer === option.letter;
          const right = finished && !current.annulled && current.correct_answer === option.letter;
          const wrong = finished && !current.annulled && chosen && !right;
          return (
            <label
              className={`alternative ${chosen ? 'chosen' : ''} ${right ? 'right' : ''} ${wrong ? 'wrong' : ''}`}
              key={option.letter}
            >
              <input
                type="radio"
                name={`answer-${current.id}`}
                value={option.letter}
                checked={chosen}
                onChange={() => onChoose(option.letter)}
              />
              <span className="alternative-letter">{option.letter}</span>
              <span className="alternative-text">
                <RichText text={option.text} />
                {option.image && <img src={`/api${option.image.path}`} alt={option.image.alt} />}
              </span>
              {right && (
                <span className="answer-note">
                  <Check size={15} />
                  Gabarito
                </span>
              )}
              {wrong && (
                <span className="answer-note">
                  <X size={15} />
                  Sua resposta
                </span>
              )}
              {chosen && !finished && <Check size={17} />}
            </label>
          );
        })}
      </fieldset>
      <div className="answer-status">
        <span role="status" className={saved ? 'saved' : 'muted'}>
          {busy ? (
            <>
              <Save size={14} />
              Salvando…
            </>
          ) : saved ? (
            <>
              <ShieldCheck size={14} />
              Resposta salva
            </>
          ) : finished ? (
            <>
              <ShieldCheck size={14} />
              Resultado definitivo
            </>
          ) : (
            <>
              <Save size={14} />
              Respostas salvas na sua conta
            </>
          )}
        </span>
        {!finished && (
          <button className="text-button muted" disabled={busy || !answer} onClick={() => onChoose(null)}>
            Limpar resposta
          </button>
        )}
      </div>
      <div className="question-navigation">
        <button className="button secondary" disabled={busy || index === 0} onClick={() => onNavigate(index - 1)}>
          <ChevronLeft size={17} />
          Anterior
        </button>
        {index < total - 1 ? (
          <button className="button" disabled={busy} onClick={() => onNavigate(index + 1)}>
            Próxima questão <ChevronRight size={17} />
          </button>
        ) : !finished ? (
          <button className="button" disabled={busy} onClick={onReview}>
            Revisar e finalizar <Flag size={16} />
          </button>
        ) : (
          <Link className="button" href="/progress">
            Ver meu desempenho <ArrowRight size={16} />
          </Link>
        )}
      </div>
    </section>
  );
}
