import { pct } from '@/lib/format';
import type { Score } from '@/lib/types';

export function ResultSummary({ result }: { result: Score }) {
  return (
    <section className="result-summary">
      <div className="result-score">
        <span className="eyebrow">APROVEITAMENTO</span>
        <strong>{pct(result.percentage)}</strong>
        <span>
          {result.correct} de {result.total} questões válidas
        </span>
      </div>
      <div className="result-metrics">
        <div>
          <i className="legend-dot correct" />
          <strong>{result.correct}</strong>
          <span>Acertos</span>
        </div>
        <div>
          <i className="legend-dot incorrect" />
          <strong>{result.incorrect}</strong>
          <span>Erros</span>
        </div>
        <div>
          <i className="legend-dot unanswered" />
          <strong>{result.unanswered}</strong>
          <span>Em branco</span>
        </div>
        <div>
          <i className="legend-dot annulled" />
          <strong>{result.annulled}</strong>
          <span>Anuladas</span>
        </div>
      </div>
      <p>
        Correção objetiva pelo gabarito. Questões anuladas não entram no percentual. Este resultado não é uma nota TRI.
      </p>
    </section>
  );
}
