'use client';
import { ChangeEvent, useState } from 'react';
import { Check, ExternalLink, FileJson, Save, ShieldCheck, Upload, X } from 'lucide-react';
import { api, date, Exam, send } from '@/lib/api';
import { useData } from '@/lib/use-data';
import { Empty, ErrorBox, Loading, PageTitle } from './ui';

type PreparationAudit = { version: string; changes: unknown[]; issues: { code: string; severity: string; message: string; location: string; excerpt?: string }[] };
type AdminQuestion = { id: string; question_id: string; version: number; status: string; content: { number: number; statement: string; correct_answer: string | null; annulled: boolean; page: number; labels: { discipline: string | null; themes: string[]; skills: string[] }; images: { path: string; alt: string }[]; layout?: { preparation?: PreparationAudit }; [key: string]: unknown } };
type AdminExam = Exam & { items: AdminQuestion[] };
type Audit = { id: string; target_id: string; action: string; reason: string; created_at: number };
const statusLabel: Record<string, string> = { published: 'Publicada', approved: 'Aprovada', draft: 'Rascunho', in_review: 'Em revisão', withdrawn: 'Retirada' };

function PreparationReview({ audit }: { audit?: PreparationAudit }) {
  if (!audit) return null;
  const blocked = audit.issues.some(issue => issue.severity === 'error');
  return <aside className="notice-box" aria-label="Preparação automática"><strong>Preparação automática</strong><p>{audit.changes.length} transformações registradas. Confira fórmulas, alternativas e vínculos com o original antes de aprovar.</p>{blocked && <p><strong>Corrija as pendências bloqueantes e salve uma nova versão para liberar a aprovação.</strong></p>}{audit.issues.length > 0 && <details open={blocked}><summary>{audit.issues.length} pontos para conferir</summary><ul>{audit.issues.map((issue, i) => <li key={i}><strong>{issue.severity === 'error' ? 'Correção necessária: ' : 'Conferir: '}</strong>{issue.message}{issue.excerpt && <p>{issue.excerpt}</p>}</li>)}</ul></details>}</aside>;
}

export default function Admin() {
  const exams = useData<Exam[]>('/admin/exams');
  const audit = useData<Audit[]>('/admin/audit');
  const [selected, setSelected] = useState<AdminExam>();
  const [itemIndex, setItemIndex] = useState(0);
  const [editor, setEditor] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  async function open(id: string, index = 0) {
    const exam = await api<AdminExam>(`/admin/exams/${id}`); setSelected(exam); setItemIndex(index); setEditor(JSON.stringify(exam.items[index].content, null, 2));
  }
  function select(index: number) { if (!selected) return; setItemIndex(index); setEditor(JSON.stringify(selected.items[index].content, null, 2)); setReason(''); setNotice(''); setError(''); }
  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true); setError(''); setNotice('');
    try { await action(); exams.reload(); audit.reload(); setNotice(success); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 4_000_000) { setError('O arquivo deve ter no máximo 4 MB.'); return; }
    run(async () => { const payload = JSON.parse(await file.text()); await send('/admin/imports', payload); }, 'Prova preparada e importada como rascunho. Abra a revisão para conferir as transformações e os avisos.');
    event.target.value = '';
  }
  function review(action: string, examTarget = false) {
    if (!selected) return;
    if (reason.trim().length < 10) { setError('Registre uma justificativa com pelo menos 10 caracteres.'); return; }
    run(async () => { await send(`/admin/reviews/${examTarget ? selected.id : selected.items[itemIndex].id}`, { action, reason }); await open(selected.id, itemIndex); }, 'Decisão registrada na trilha de revisão.');
  }
  function save() {
    if (!selected) return;
    if (reason.trim().length < 10) { setError('Registre a justificativa da correção (mínimo 10 caracteres).'); return; }
    run(async () => { await send(`/admin/questions/${selected.items[itemIndex].id}`, { content: JSON.parse(editor), reason }, 'PUT'); await open(selected.id, itemIndex); }, 'Nova versão criada como rascunho. As tentativas anteriores foram preservadas. Revise e publique novamente.');
  }
  if (exams.loading) return <Loading/>;
  const current = selected?.items[itemIndex];
  return <><PageTitle eyebrow="QUALIDADE DESDE A ORIGEM" title="Curadoria de conteúdo" text="Importe, confira o original, revise e publique versões rastreáveis." action={<label className="button upload-button"><Upload size={17}/>Importar JSON<input type="file" accept="application/json,.json" onChange={upload} disabled={busy}/></label>}/>{(error || exams.error) && <ErrorBox message={error || exams.error} retry={exams.error ? exams.reload : undefined}/ >}{notice && <p className="success-box" role="status">{notice}</p>}<div className="curation-flow"><span><FileJson size={16}/>Importar</span><i/><span><ShieldCheck size={16}/>Revisar cada questão</span><i/><span><Check size={16}/>Publicar prova</span></div><section className="panel admin-exams"><div className="section-heading"><h2>Banco de conteúdo</h2><span className="tiny muted">{exams.data?.length || 0} provas importadas</span></div>{exams.data?.length ? exams.data.map(exam => <div className="admin-exam-row" key={exam.id}><div><strong>{exam.title}</strong><p className="tiny muted">{exam.booklet} · {exam.approved_items}/{exam.item_count} versões aprovadas · {exam.item_count}/{exam.expected_items} itens</p></div><span className={`badge ${exam.status === 'published' ? 'green' : 'amber'}`}>{statusLabel[exam.status]}</span><button className="button secondary compact" disabled={busy} onClick={() => run(() => open(exam.id), 'Prova carregada para revisão.')}>Revisar</button></div>) : <Empty title="Nenhuma prova importada" text="Envie um arquivo no contrato JSON 1.0 para iniciar a revisão."/>}</section>{selected && current && <section className="panel admin-review"><div className="section-heading"><div><h2>{selected.title}</h2><p className="tiny muted">Publicação exige todas as versões aprovadas e a quantidade declarada de itens.</p></div><button className="icon-button" aria-label="Fechar revisão" onClick={() => setSelected(undefined)}><X size={20}/></button></div><div className="admin-question-toolbar"><select aria-label="Questão para revisão" value={itemIndex} onChange={e => select(Number(e.target.value))}>{selected.items.map((question, i) => <option value={i} key={question.id}>Questão {question.content.number} · v{question.version} · {statusLabel[question.status]}</option>)}</select><span className={`badge ${current.status === 'approved' ? 'green' : 'amber'}`}>{statusLabel[current.status]}</span><a href={`${selected.source.url}#page=${current.content.page}`} target="_blank" rel="noreferrer" className="text-link">Abrir PDF original <ExternalLink size={14}/></a></div><PreparationReview audit={current.content.layout?.preparation}/><div className="admin-editor-grid"><div className="admin-original"><p className="eyebrow">ORIGINAL · PÁGINA {current.content.page}</p>{current.content.images.map(asset => <img src={`/api${asset.path}`} alt={asset.alt} key={asset.path}/>)}{!current.content.images.length && <p>Consulte o PDF original para conferir a extração.</p>}</div><div><label>Conteúdo da versão {current.version}<textarea className="code-editor" value={editor} onChange={e => setEditor(e.target.value)} spellCheck={false}/></label><p className="tiny muted">Corrija o enunciado, alternativas, rótulos e gabarito no contrato de conteúdo. Salvar cria uma nova versão e suspende a publicação até nova revisão.</p><button className="button secondary" onClick={save} disabled={busy}><Save size={16}/>Salvar nova versão</button></div></div><label className="review-reason">Justificativa da revisão ou alteração<textarea value={reason} onChange={e => setReason(e.target.value)} minLength={10} maxLength={2000} placeholder="Registre o que foi conferido ou corrigido e a evidência usada."/></label><div className="review-actions"><button className="button secondary" disabled={busy} onClick={() => review('reject')}>Devolver para revisão</button><button className="button secondary" disabled={busy || current.content.layout?.preparation?.issues.some(issue => issue.severity === 'error')} onClick={() => review('approve')}><ShieldCheck size={16}/>Aprovar questão</button><span/><button className="button danger-outline" disabled={busy} onClick={() => review('withdraw', true)}>Retirar prova</button><button className="button" disabled={busy} onClick={() => review('publish', true)}>Publicar prova <Check size={16}/></button></div><details className="source-details"><summary>Origem e rastreabilidade</summary><pre>{JSON.stringify(selected.source, null, 2)}</pre></details></section>}<section className="panel audit-panel"><h2>Últimas decisões</h2>{audit.error && <ErrorBox message={audit.error} retry={audit.reload}/ >}{audit.data?.slice(0, 15).map(row => <div className="audit-row" key={row.id}><span className="badge">{row.action}</span><div><strong>{row.target_id}</strong><p>{row.reason}</p><span className="tiny muted">{date(row.created_at)}</span></div></div>)}{!audit.data?.length && <p className="muted">As decisões de revisão aparecerão aqui.</p>}</section></>;
}
