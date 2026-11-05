export type PreparationAudit = {
  version: string;
  changes: unknown[];
  issues: { code: string; severity: string; message: string; location: string; excerpt?: string }[];
};

export function PreparationReview({ audit }: { audit?: PreparationAudit }) {
  if (!audit) return null;
  const blocked = audit.issues.some(issue => issue.severity === 'error');
  return (
    <aside className="notice-box" aria-label="Preparação automática">
      <strong>Preparação automática</strong>
      <p>
        {audit.changes.length} transformações registradas. Confira fórmulas, alternativas e vínculos com o original
        antes de aprovar.
      </p>
      {blocked && (
        <p>
          <strong>Corrija as pendências bloqueantes e salve uma nova versão para liberar a aprovação.</strong>
        </p>
      )}
      {audit.issues.length > 0 && (
        <details open={blocked}>
          <summary>{audit.issues.length} pontos para conferir</summary>
          <ul>
            {audit.issues.map((issue, i) => (
              <li key={i}>
                <strong>{issue.severity === 'error' ? 'Correção necessária: ' : 'Conferir: '}</strong>
                {issue.message}
                {issue.excerpt && <p>{issue.excerpt}</p>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </aside>
  );
}
