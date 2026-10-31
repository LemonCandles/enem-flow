'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { BookOpen, ChartNoAxesCombined, ChevronRight, History as HistoryIcon, House, LogOut, Menu, Settings, ShieldCheck, UserRound, X } from 'lucide-react';
import { api, ApiError, User } from '@/lib/api';
import Auth from './auth';
import { ErrorBox, Loading } from './ui';
import { Brand } from './design';
import ThemeToggle from './theme-toggle';
import Dashboard from './dashboard';
import Catalog from './catalog';
import { HistoryPage, ProgressPage, SettingsPage } from './student';
import ExamRunner from './exam-runner';
import Admin from './admin';

const links = [
  { href: '/', label: 'Início', icon: House },
  { href: '/exams', label: 'Provas', icon: BookOpen },
  { href: '/progress', label: 'Desempenho', icon: ChartNoAxesCombined },
  { href: '/history', label: 'Histórico', icon: HistoryIcon },
];

export default function App() {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mobile, setMobile] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);

  function load() {
    setLoading(true); setError('');
    api<User>('/me').then(setUser).catch(e => {
      if (!(e instanceof ApiError && e.status === 401)) setError(e.message);
    }).finally(() => setLoading(false));
  }
  useEffect(load, []);
  useEffect(() => { setMobile(false); }, [path]);
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 761px)');
    const closeOnDesktop = () => { if (desktop.matches) setMobile(false); };
    desktop.addEventListener('change', closeOnDesktop);
    return () => desktop.removeEventListener('change', closeOnDesktop);
  }, []);
  useEffect(() => {
    if (!mobile) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const nodes = sidebar.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
    const first = nodes?.[0];
    const last = nodes?.[nodes.length - 1];
    first?.focus();
    function keydown(event: KeyboardEvent) {
      if (event.key === 'Escape') setMobile(false);
      if (event.key !== 'Tab') return;
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    document.addEventListener('keydown', keydown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', keydown);
      menuButton.current?.focus();
    };
  }, [mobile]);

  async function logout() {
    try { await api('/auth/logout', { method: 'POST' }); setUser(null); setMobile(false); router.push('/'); }
    catch (e) { setError((e as Error).message); }
  }
  if (loading) return <Loading/>;
  if (error && !user) return <main className="connection-error"><ErrorBox message={error} retry={load}/></main>;
  if (!user) return <Auth onLogin={setUser}/>;
  const title = links.find(l => l.href === path)?.label || (path.startsWith('/runs/') ? 'Sua prova' : path === '/settings' ? 'Configurações' : path === '/admin' ? 'Curadoria' : 'Página não encontrada');

  return <div className={`app-shell ${path === '/' ? 'home-shell' : ''}`}>
    <a className="skip-link" href="#main">Pular para o conteúdo</a>
    {mobile && <button className="sidebar-scrim" aria-label="Fechar menu" tabIndex={-1} onClick={() => setMobile(false)}/>}
    <aside ref={sidebar} id="site-navigation" className={`sidebar ${mobile ? 'open' : ''}`} aria-label="Menu do site">
      <Brand/>
      <button className="mobile-close icon-button" aria-label="Fechar menu" onClick={() => setMobile(false)}><X/></button>
      <nav aria-label="Navegação principal">
        {links.map(({ href, label, icon: Icon }) => <Link key={href} className={`nav-item ${path === href ? 'active' : ''}`} aria-current={path === href ? 'page' : undefined} href={href}><Icon size={21}/>{label}</Link>)}
      </nav>
      <div className="sidebar-bottom">
        {user.role === 'admin' && <Link href="/admin" className={`nav-item ${path === '/admin' ? 'active' : ''}`} aria-current={path === '/admin' ? 'page' : undefined}><ShieldCheck size={21}/>Curadoria</Link>}
        <Link href="/settings" className={`nav-item ${path === '/settings' ? 'active' : ''}`} aria-current={path === '/settings' ? 'page' : undefined}><Settings size={21}/>Configurações</Link>
        <div className="sidebar-profile"><UserRound size={21}/><div><strong>{user.name}</strong><span>{user.role === 'admin' ? 'Conta de curadoria' : 'Minha conta'}</span></div></div>
        <button className="nav-item logout-button" onClick={logout}><LogOut size={19}/>Sair da conta</button>
      </div>
    </aside>
    <div className="main-shell">
      <header className="topbar">
        <div className="row">
          <button ref={menuButton} className="mobile-menu icon-button" aria-label="Abrir menu" aria-controls="site-navigation" aria-expanded={mobile} onClick={() => setMobile(true)}><Menu/></button>
          {path === '/' ? <span className="home-welcome">Seu espaço, {user.name.split(' ')[0]}.</span> : <span className="breadcrumb"><Link href="/">Meu espaço</Link><ChevronRight size={13}/><strong>{title}</strong></span>}
        </div>
        <ThemeToggle/>
      </header>
      <main id="main" className={`main-content ${path === '/' ? 'home-main' : ''} ${path.startsWith('/runs/') ? 'runner-main' : ''}`} tabIndex={-1}>
        {error && <ErrorBox message={error}/>}
        {path === '/' ? <Dashboard/> : path === '/exams' ? <Catalog/> : path === '/history' ? <HistoryPage/> : path === '/progress' ? <ProgressPage/> : path === '/settings' ? <SettingsPage user={user} onUpdate={setUser}/> : path === '/admin' && user.role === 'admin' ? <Admin/> : path.startsWith('/runs/') ? <ExamRunner id={path.split('/')[2]}/> : <div className="empty-state"><h1>Página não encontrada</h1><Link href="/">Voltar ao início</Link></div>}
      </main>
      <footer className="main-footer"><span>Enem Flow <span className="dot">·</span> Um passo de cada vez.</span><span>Produto independente do Inep.</span></footer>
    </div>
  </div>;
}
