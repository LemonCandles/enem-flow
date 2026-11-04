export const date = (timestamp: number) =>
  new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(timestamp * 1000);
export const pct = (value: number | null | undefined) =>
  value == null ? '—' : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
export const kindName = (kind: string) =>
  ({ complete: 'Caderno completo', section: 'Seção completa', collection: 'Coleção parcial' })[kind] || kind;
