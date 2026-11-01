'use client';
import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { useData } from '@/lib/use-data';
import { ErrorBox, Loading } from './ui';

type Source = { id: string; year: number; application: string; day: number | null; booklet: string; variant: string; role: string; status: string; url: string; path: string; sha256: string };
type Inventory = { years: number[]; applications: string[]; references: number; downloaded: number; unavailable: { url: string; official_title: string; label: string }[]; coverage: { occurrences?: number; canonical_questions?: number; sources_with_issues?: number }; files: Source[] };
type Occurrence = { occurrence_id: string; canonical_id: string; year: number; application: string; booklet: string; number: number; page: number | null; language?: string | null; has_visual: boolean };
type Detail = Occurrence & { text: string; issues: string[]; source_issues: string[]; source: Source; occurrences: Occurrence[] };

function ExtractedQuestion({ id }: { id: string }) {
  const detail = useData<Detail>(`/admin/archive/questions/${encodeURIComponent(id)}`);
  if (detail.loading) return <Loading/>;
  if (detail.error) return <ErrorBox message={detail.error} retry={detail.reload}/>;
  if (!detail.data) return null;
  const item = detail.data;
  return <article className="archive-detail" aria-label={`Extração da questão ${item.number}`}><div className="section-heading"><h3>Questão {item.number} · {item.source.year}</h3><a className="text-link" href={`${item.source.url}${item.page ? `#page=${item.page}` : ''}`} target="_blank" rel="noreferrer">Conferir {item.page ? `página ${item.page}` : 'texto'} no original <ExternalLink size={14}/></a></div><p className="small-text muted">{item.source.application} · {item.source.booklet} · {item.source.variant}</p><p className="notice-box">Extração para curadoria. Texto, fórmulas, figuras, alternativas e gabarito precisam de conferência antes da publicação.</p><div className="archive-transcript">{item.text}</div><details><summary>{item.occurrences.length} ocorrência(s) com a mesma identidade canônica</summary><ul>{item.occurrences.map(row => <li key={row.occurrence_id}>{row.year} · {row.application} · {row.booklet} · questão {row.number}</li>)}</ul></details><details><summary>Pontos para revisão</summary><ul>{[...item.issues, ...item.source_issues].map((issue, i) => <li key={i}>{issue}</li>)}</ul></details><p className="tiny muted">Origem: {item.source.path}<br/>SHA-256: {item.source.sha256}</p></article>;
}

function Occurrences({ year, application, number }: { year: number; application: string; number: string }) {
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState('');
  const path = `/admin/archive/questions?year=${year}&limit=25&offset=${offset}${application ? `&application=${encodeURIComponent(application)}` : ''}${number ? `&number=${number}` : ''}`;
  const questions = useData<{ total: number; items: Occurrence[] }>(path);
  if (questions.loading) return <Loading/>;
  if (questions.error) return <ErrorBox message={questions.error} retry={questions.reload}/>;
  const data = questions.data;
  return <><p className="small-text muted" role="status">{data?.total.toLocaleString('pt-BR') || 0} ocorrências extraídas neste recorte. Cores e versões podem repetir questões.</p><div className="archive-questions">{data?.items.map(item => <button key={item.occurrence_id} className="archive-question" aria-pressed={selected === item.occurrence_id} onClick={() => setSelected(item.occurrence_id)}><strong>Questão {item.number}</strong><span>{item.application} · {item.booklet}</span><span className="tiny muted">{item.page ? `Página ${item.page}` : 'Sem paginação'}{item.language ? ` · ${item.language}` : ''}{item.has_visual ? ' · contém figura' : ''}</span></button>)}</div><div className="row between"><button className="button secondary compact" disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 25))}>Anteriores</button><span className="tiny muted">{data?.total ? `${offset + 1}–${Math.min(offset + 25, data.total)} de ${data.total}` : 'Nenhuma ocorrência'}</span><button className="button secondary compact" disabled={!data || offset + 25 >= data.total} onClick={() => setOffset(value => value + 25)}>Próximas</button></div>{selected && <ExtractedQuestion key={selected} id={selected}/>}</>;
}

export default function Archive() {
  const inventory = useData<Inventory>('/admin/archive');
  const [chosenYear, setYear] = useState<number>();
  const [application, setApplication] = useState('');
  const [number, setNumber] = useState('');
  if (inventory.loading) return <Loading/>;
  if (inventory.error) return <ErrorBox message={inventory.error} retry={inventory.reload}/>;
  const data = inventory.data;
  if (!data?.years.length) return <section className="panel"><h2>Acervo oficial</h2><p>O catálogo de fontes ainda não foi instalado neste ambiente.</p></section>;
  const year = chosenYear ?? data.years[0];
  const files = data.files.filter(file => file.year === year && (!application || file.application === application));
  const applications = [...new Set(data.files.filter(file => file.year === year).map(file => file.application))].sort();
  return <section className="panel archive-panel"><div className="section-heading"><div><h2>Acervo oficial para curadoria</h2><p className="small-text muted">{data.years.length} anos · {data.downloaded}/{data.references} arquivos de origem obtidos · {data.coverage.occurrences?.toLocaleString('pt-BR') || 0} ocorrências extraídas</p></div><span className="badge amber">Aguardando revisão</span></div><p>Consulte as extrações por ano e aplicação. A aprovação de uma versão continua no banco de conteúdo acima.</p><div className="archive-filters"><label>Ano<select value={year} onChange={event => { setYear(Number(event.target.value)); setApplication(''); }}>{data.years.map(value => <option key={value} value={value}>{value}</option>)}</select></label><label>Aplicação<select value={application} onChange={event => setApplication(event.target.value)}><option value="">Todas</option>{applications.map(value => <option key={value}>{value}</option>)}</select></label><label>Número da questão<input type="number" min="1" max="1000" value={number} onChange={event => { const value = event.target.value; if (value === '' || (+value >= 1 && +value <= 1000)) setNumber(value); }} placeholder="Todos"/></label></div><p className="tiny muted">{files.length} referências de origem neste recorte · {files.filter(file => file.status === 'error').length} indisponíveis no servidor oficial</p><Occurrences key={`${year}-${application}-${number}`} year={year} application={application} number={number}/>{data.unavailable.length > 0 && <details><summary>Arquivos indisponíveis no acervo oficial</summary><ul>{data.unavailable.map(item => <li key={item.url}>{item.official_title} · {item.label}: <a className="text-link" href={item.url} target="_blank" rel="noreferrer">URL registrada <ExternalLink size={12}/></a></li>)}</ul></details>}<details><summary>Fontes do ano e aplicação selecionados</summary><div className="archive-sources">{files.map(file => <p key={file.id}><a className="text-link" href={file.url} target="_blank" rel="noreferrer">{file.booklet} · {file.day ? `${file.day}º dia` : 'dia único'} · {file.variant} · {file.role} <ExternalLink size={12}/></a><span className="tiny muted">{file.status === 'downloaded' ? 'Obtido e verificado por hash' : 'Indisponível'}</span></p>)}</div></details></section>;
}
