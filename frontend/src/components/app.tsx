'use client';

import { useEffect, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  BookOpen,
  Target,
  ChartNoAxesCombined,
  ChevronRight,
  History as HistoryIcon,
  House,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  UserRound,
  X,
} from 'lucide-react';
import { ApiError } from '@/lib/api';
import { diagnosticAttempt, examAttempt } from '@/lib/attempt-source';
import { useMobileMenu } from '@/lib/use-mobile-menu';
import { account } from '@/lib/endpoints';
import type { User } from '@/lib/types';
import Auth from './auth';
import { ErrorBox, Loading } from './ui';
import { Brand } from './design';
import ThemeToggle from './theme-toggle';
import Dashboard from './dashboard';
import Catalog from './catalog';
import { HistoryPage, ProgressPage, SettingsPage } from './student';
import ExamRunner from './exam-runner';
import Admin from './admin';
import DiagnosticPage from './diagnostic';

const links = [
  { href: '/', label: 'Início', icon: House },
  { href: '/exams', label: 'Provas', icon: BookOpen },
  { href: '/diagnostic', label: 'Diagnóstico', icon: Target },
  { href: '/progress', label: 'Desempenho', icon: ChartNoAxesCombined },
  { href: '/history', label: 'Histórico', icon: HistoryIcon },
];

const attemptId = (path: string) => path.split('/')[2];

// Each page of the site: how to recognize its path, its title and what to show.
type Page = {
  matches: (path: string) => boolean;
  title: string;
  render: (user: User, onUpdate: (user: User) => void, path: string) => ReactNode;
  adminOnly?: boolean;
};

const exact = (expected: string) => (path: string) => path === expected;
const under = (prefix: string) => (path: string) => path.startsWith(prefix);

const pages: Page[] = [
  { matches: exact('/'), title: 'Início', render: () => <Dashboard /> },
  { matches: exact('/exams'), title: 'Provas', render: () => <Catalog /> },
  { matches: exact('/diagnostic'), title: 'Diagnóstico', render: () => <DiagnosticPage /> },
  { matches: exact('/progress'), title: 'Desempenho', render: () => <ProgressPage /> },
  { matches: exact('/history'), title: 'Histórico', render: () => <HistoryPage /> },
  {
    matches: under('/sessions/'),
    title: 'Seu diagnóstico',
    render: (_, __, path) => <ExamRunner key={path} id={attemptId(path)} source={diagnosticAttempt} />,
  },
  {
    matches: under('/runs/'),
    title: 'Sua prova',
    render: (_, __, path) => <ExamRunner key={path} id={attemptId(path)} source={examAttempt} />,
  },
  {
    matches: exact('/settings'),
    title: 'Configurações',
    render: (user, onUpdate) => <SettingsPage user={user} onUpdate={onUpdate} />,
  },
  { matches: exact('/admin'), title: 'Curadoria', render: () => <Admin />, adminOnly: true },
];

function NotFound() {
  return (
    <div className="empty-state">
      <h1>Página não encontrada</h1>
      <Link href="/">Voltar ao início</Link>
    </div>
  );
}

export default function App() {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [recovery, setRecovery] = useState('');
  const { mobile, setMobile, sidebar, menuButton } = useMobileMenu(path);

  function load() {
    const token = new URLSearchParams(window.location.search).get('recovery');
    if (token) {
      setRecovery(token);
      window.history.replaceState({}, '', window.location.pathname);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    account
      .current()
      .then(setUser)
      .catch(e => {
        if (!(e instanceof ApiError && e.status === 401)) setError(e.message);
      })
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function logout() {
    try {
      await account.leave();
      setUser(null);
      setMobile(false);
      router.push('/');
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (loading) return <Loading />;
  if (error && !user)
    return (
      <main className="connection-error">
        <ErrorBox message={error} retry={load} />
      </main>
    );
  if (recovery || !user)
    return (
      <Auth
        onLogin={setUser}
        recoveryToken={recovery}
        onRecoveryComplete={() => {
          setRecovery('');
          setUser(null);
        }}
      />
    );
  const page = pages.find(candidate => candidate.matches(path));
  const title = page?.title ?? 'Página não encontrada';
  const allowed = page && (!page.adminOnly || user.role === 'admin');

  return (
    <div className={`app-shell ${path === '/' ? 'home-shell' : ''}`}>
      <a className="skip-link" href="#main">
        Pular para o conteúdo
      </a>
      {mobile && (
        <button className="sidebar-scrim" aria-label="Fechar menu" tabIndex={-1} onClick={() => setMobile(false)} />
      )}
      <aside ref={sidebar} id="site-navigation" className={`sidebar ${mobile ? 'open' : ''}`} aria-label="Menu do site">
        <Brand />
        <button className="mobile-close icon-button" aria-label="Fechar menu" onClick={() => setMobile(false)}>
          <X />
        </button>
        <nav aria-label="Navegação principal">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              className={`nav-item ${path === href ? 'active' : ''}`}
              aria-current={path === href ? 'page' : undefined}
              href={href}
            >
              <Icon size={21} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {user.role === 'admin' && (
            <Link
              href="/admin"
              className={`nav-item ${path === '/admin' ? 'active' : ''}`}
              aria-current={path === '/admin' ? 'page' : undefined}
            >
              <ShieldCheck size={21} />
              Curadoria
            </Link>
          )}
          <Link
            href="/settings"
            className={`nav-item ${path === '/settings' ? 'active' : ''}`}
            aria-current={path === '/settings' ? 'page' : undefined}
          >
            <Settings size={21} />
            Configurações
          </Link>
          <div className="sidebar-profile">
            <UserRound size={21} />
            <div>
              <strong>{user.name}</strong>
              <span>{user.role === 'admin' ? 'Conta de curadoria' : 'Minha conta'}</span>
            </div>
          </div>
          <button className="nav-item logout-button" onClick={logout}>
            <LogOut size={19} />
            Sair da conta
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="row">
            <button
              ref={menuButton}
              className="mobile-menu icon-button"
              aria-label="Abrir menu"
              aria-controls="site-navigation"
              aria-expanded={mobile}
              onClick={() => setMobile(true)}
            >
              <Menu />
            </button>
            {path === '/' ? (
              <span className="home-welcome">Seu espaço, {user.name.split(' ')[0]}.</span>
            ) : (
              <span className="breadcrumb">
                <Link href="/">Meu espaço</Link>
                <ChevronRight size={13} />
                <strong>{title}</strong>
              </span>
            )}
          </div>
          <ThemeToggle />
        </header>
        <main
          id="main"
          className={`main-content ${path === '/' ? 'home-main' : ''} ${path.startsWith('/runs/') || path.startsWith('/sessions/') ? 'runner-main' : ''}`}
          tabIndex={-1}
        >
          {error && <ErrorBox message={error} />}
          {allowed ? page.render(user, setUser, path) : <NotFound />}
        </main>
        <footer className="main-footer">
          <span>
            Enem Flow <span className="dot">·</span> Um passo de cada vez.
          </span>
          <span>Produto independente do Inep.</span>
        </footer>
      </div>
    </div>
  );
}
