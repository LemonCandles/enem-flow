'use client';
import { useState } from 'react';
import { ExternalLink, Flag, ListChecks, ShieldCheck } from 'lucide-react';
import type { AttemptSource } from '@/lib/attempt-source';
import type { Question, Run } from '@/lib/types';

const status = (question: Question, answers: Run['answers']) =>
  question.annulled
    ? 'annulled'
    : !answers[question.id]
      ? 'unanswered'
      : answers[question.id] === question.correct_answer
        ? 'correct'
        : 'incorrect';

export function QuestionAside({
  items,
  answers,
  index,
  finished,
  busy,
  showMap,
  source,
  sourceUrl,
  onToggle,
  onNavigate,
  onReview,
}: {
  items: Question[];
  answers: Run['answers'];
  index: number;
  finished: boolean;
  busy: boolean;
  showMap: boolean;
  source: AttemptSource;
  sourceUrl: string;
  onToggle: () => void;
  onNavigate: (next: number) => void;
  onReview: () => void;
}) {
  const [filter, setFilter] = useState('all');
  return (
    <aside className="question-aside">
      <button className="map-toggle button secondary" onClick={onToggle}>
        <ListChecks size={18} />
        {showMap ? 'Ocultar mapa de questões' : 'Abrir mapa de questões'}
      </button>
      <div className={`panel question-map ${showMap ? 'map-open' : ''}`}>
        <div className="row between">
          <h3>Mapa de questões</h3>
          <ListChecks size={18} className="muted" />
        </div>
        <p className="small-text muted">Navegue livremente entre as questões.</p>
        {finished && (
          <select aria-label="Filtrar revisão" value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="all">Todas as questões</option>
            <option value="correct">Acertos</option>
            <option value="incorrect">Erros</option>
            <option value="unanswered">Em branco</option>
            <option value="annulled">Anuladas</option>
          </select>
        )}
        <div className="question-grid">
          {items.map((question, i) => {
            const state = finished ? status(question, answers) : answers[question.id] ? 'answered' : '';
            return filter !== 'all' && finished && state !== filter ? null : (
              <button
                key={question.id}
                disabled={busy}
                className={`question-number ${state} ${index === i ? 'current' : ''}`}
                aria-label={`Questão ${source.questionNumber(question, i)}${state ? `, ${{ correct: 'correta', incorrect: 'incorreta', unanswered: 'em branco', annulled: 'anulada', answered: 'respondida' }[state]}` : ''}`}
                aria-current={index === i ? 'step' : undefined}
                onClick={() => onNavigate(i)}
              >
                {source.questionNumber(question, i)}
              </button>
            );
          })}
        </div>
        <div className="map-legend">
          <span>
            <i className="legend-dot answered" />
            {finished ? 'Acertos' : 'Respondida'}
          </span>
          <span>
            <i className="legend-dot unanswered" />
            {finished ? 'Em branco' : 'Não respondida'}
          </span>
          {finished && (
            <>
              <span>
                <i className="legend-dot incorrect" />
                Erros
              </span>
              <span>
                <i className="legend-dot annulled" />
                Anuladas
              </span>
            </>
          )}
        </div>
        {!finished && (
          <button className="button full" disabled={busy} onClick={onReview}>
            <Flag size={16} />
            {source.finishLabel}
          </button>
        )}
      </div>
      <div className="runner-tip">
        <ShieldCheck size={20} />
        <p>
          {finished
            ? 'Seu resultado está salvo. Você pode revisitar cada questão sempre que quiser.'
            : 'Você pode voltar e alterar qualquer resposta antes de finalizar. Estude no seu ritmo.'}
        </p>
      </div>
      <a className="source-link" href={sourceUrl} target="_blank" rel="noreferrer">
        Consultar caderno oficial <ExternalLink size={13} />
      </a>
    </aside>
  );
}
