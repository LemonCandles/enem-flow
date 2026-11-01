'use client';
import { useState } from 'react';
import { BookOpen, Search, SlidersHorizontal } from 'lucide-react';
import { Exam, History } from '@/lib/api';
import { useData } from '@/lib/use-data';
import { useStart } from '@/lib/use-start';
import { Empty, ErrorBox, ExamCard, Loading, PageTitle } from './ui';

export default function Catalog() {
  const exams = useData<Exam[]>('/exams');
  const history = useData<History[]>('/me/history');
  const [filters, setFilters] = useState({ year: '', area: '', application: '', booklet: '', q: '' });
  const { start, busy, error } = useStart();
  if (exams.loading || history.loading) return <Loading/>;
  if (exams.error || history.error) return <ErrorBox message={exams.error || history.error} retry={() => { exams.reload(); history.reload(); }}/>;
  const all = exams.data || [];
  const list = all.filter(exam => (!filters.year || exam.year === Number(filters.year)) && (!filters.area || exam.areas.includes(filters.area)) && (!filters.application || filters.application === exam.application) && (!filters.booklet || filters.booklet === exam.booklet) && (!filters.q || `${exam.title} ${exam.booklet}`.toLocaleLowerCase().includes(filters.q.toLocaleLowerCase())));
  const field = (key: keyof typeof filters, value: string) => setFilters(current => ({ ...current, [key]: value }));
  return <><PageTitle eyebrow="PRÁTICA QUE TRANSFORMA" title="Banco de provas" text="Escolha seu desafio. As respostas ficam salvas para você continuar depois."/><div className="catalog-banner"><span className="stat-icon teal"><BookOpen size={22}/></span><div><strong>Conteúdo oficial, um novo jeito de praticar.</strong><p className="small-text muted">Provas oficiais do Inep com texto e figuras extraídos do caderno original. Dois cadernos já passaram por conferência de conteúdo e gabarito.</p></div><span className="badge green">{all.length} {all.length === 1 ? 'prova disponível' : 'provas disponíveis'}</span></div><section className="panel filter-panel" aria-label="Filtrar provas"><div className="search-field"><Search size={18}/><input aria-label="Buscar prova" placeholder="Buscar por prova ou caderno…" value={filters.q} onChange={e => field('q', e.target.value)}/></div><div className="filters"><span className="filter-label"><SlidersHorizontal size={16}/>Filtrar por</span>{(['year', 'area', 'application', 'booklet'] as const).map(key => { const options = [...new Set(all.flatMap(e => key === 'area' ? e.areas : [String(e[key])]))].sort(); const labels = { year: 'Todos os anos', area: 'Todas as áreas', application: 'Todas as aplicações', booklet: 'Todos os cadernos' }; return <select aria-label={labels[key]} key={key} value={filters[key]} onChange={e => field(key, e.target.value)}><option value="">{labels[key]}</option>{options.map(option => <option key={option}>{option}</option>)}</select>; })}</div></section><div className="section-heading"><span className="small-text muted">{list.length} {list.length === 1 ? 'prova encontrada' : 'provas encontradas'}</span>{Object.values(filters).some(Boolean) && <button className="text-button" onClick={() => setFilters({ year: '', area: '', application: '', booklet: '', q: '' })}>Limpar filtros</button>}</div>{error && <ErrorBox message={error}/>}<div className="catalog-grid">{list.map(exam => <ExamCard key={exam.id} exam={exam} onStart={start} busy={busy} resume={history.data?.find(r => r.exam.id === exam.id && !r.finished_at)?.id}/>)}</div>{!list.length && <Empty title={all.length ? 'Nenhuma prova com esses filtros' : 'Novas provas a caminho'} text={all.length ? 'Experimente outro ano, área ou termo de busca.' : 'O catálogo será liberado conforme a revisão dos cadernos.'}/>}<p className="catalog-footnote">Caderno completo: todas as questões de um dia de aplicação. Seções e coleções parciais são identificadas separadamente. O catálogo inclui o segundo dia de 2024 e a seção de Matemática de 2023.</p></>;
}
