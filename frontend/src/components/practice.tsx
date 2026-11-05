'use client';
import { attempts, paths } from '@/lib/endpoints';
import { date } from '@/lib/format';
import type { RecommendationEvent } from '@/lib/types';
import { useData } from '@/lib/use-data';
import { SessionForm } from './session-form';
import { ErrorBox } from './ui';

const FUNCTION_NAMES: Record<string, string> = { reforco: 'Reforço', revisao: 'Revisão', exploracao: 'Exploração' };
const RECENT = 10;

export default function PracticePage() {
  const recommendations = useData<RecommendationEvent[]>(paths.recommendations);
  const recent = (recommendations.data || []).slice(-RECENT).reverse();
  return (
    <>
      <SessionForm
        eyebrow="PRÁTICA NO SEU RITMO"
        title="Iniciar prática"
        text="As questões são escolhidas pelo que você já respondeu: reforço onde houve erros repetidos, revisão do que ficou para trás e exploração de temas com poucas respostas."
        placeholder="Ex.: praticar Matemática por meia hora"
        submitLabel="Começar prática"
        unavailable="A prática ficará disponível quando houver questões com temas publicados e sem pendências bloqueantes."
        start={attempts.startPractice}
        pathFor={id => `/practice/${id}`}
      />
      <section className="panel breakdown-panel">
        <h2>Como suas questões foram escolhidas</h2>
        <p className="small-text muted">
          Cada escolha considera só respostas de sessões concluídas e pode mudar com novas evidências. Os motivos
          descrevem suas respostas; não são uma nota nem uma medida de domínio do conteúdo.
        </p>
        {recommendations.error ? (
          <ErrorBox message={recommendations.error} retry={recommendations.reload} />
        ) : !recent.length ? (
          <p className="small-text muted">Suas recomendações aparecerão aqui depois da primeira prática.</p>
        ) : (
          <div className="breakdown-list">
            {recent.map(event => (
              <article key={`${event.session_id}-${event.position}`}>
                <h3>{FUNCTION_NAMES[event.function] || event.function}</h3>
                <p className="small-text muted">
                  {date(event.created_at)} · {event.reason}
                </p>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
