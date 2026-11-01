'use client';
import { FormEvent, useState } from 'react';
import { ArrowRight, BookOpen, ChartNoAxesCombined, Check, Eye, EyeOff } from 'lucide-react';
import { send, User } from '@/lib/api';
import { ErrorBox } from './ui';
import { Brand, LearningPieces } from './design';
import ThemeToggle from './theme-toggle';

export default function Auth({ onLogin, recoveryToken = '', onRecoveryComplete }: { onLogin: (user: User) => void; recoveryToken?: string; onRecoveryComplete?: () => void }) {
  const [mode, setMode] = useState<'login' | 'register' | 'reset'>(recoveryToken ? 'reset' : 'login');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState(false);
  const [notice, setNotice] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true);
    const fields = new FormData(event.currentTarget);
    try {
      if (mode === 'reset') {
        await send('/auth/reset-password', { token: recoveryToken, password: fields.get('password') });
        setMode('login'); setNotice('Senha atualizada. Entre com sua nova senha.');
        onRecoveryComplete?.();
      } else {
        const body = { email: fields.get('email'), password: fields.get('password'), ...(mode === 'register' ? { name: fields.get('name') } : {}) };
        onLogin(await send<User>(`/auth/${mode}`, body));
      }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <main className="auth-layout"><div className="auth-theme"><ThemeToggle/></div><section className="auth-story"><Brand/><div className="auth-story-content"><p className="eyebrow">UM PASSO DE CADA VEZ</p><h1>Aprender,<br/>no seu tempo.</h1><p>Transforme cada questão em um novo passo.<br/>Estude com clareza. Avance no seu ritmo.</p><div className="auth-features"><div><BookOpen/><span>Provas oficiais, conteúdo preservado</span></div><div><ChartNoAxesCombined/><span>Seu desempenho em um só lugar</span></div><div><Check/><span>Respostas salvas para continuar depois</span></div></div></div><p className="auth-foot">Um caminho de aprendizado que é só seu.</p><LearningPieces className="auth-pieces"/></section><section className="auth-form-side"><div className="auth-form-wrap"><span className="badge green">SEU ESPAÇO DE APRENDIZADO</span><h2>{mode === 'register' ? 'Comece sua jornada.' : mode === 'reset' ? 'Uma nova senha.' : 'Que bom ter você aqui.'}</h2><p className="muted">{mode === 'register' ? 'Crie sua conta e dê o primeiro passo rumo ao ENEM.' : mode === 'reset' ? 'Escolha uma senha com pelo menos 10 caracteres.' : 'Entre para continuar construindo seu próximo passo.'}</p>{mode !== 'reset' && <div className="auth-tabs"><button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError(''); }}>Entrar</button><button className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); setError(''); }}>Criar conta</button></div>}{notice && <p className="success-box" role="status">{notice}</p>}{error && <ErrorBox message={error}/>}<form onSubmit={submit} key={mode}>{mode === 'register' && <label>Seu nome<input name="name" autoComplete="name" placeholder="Como podemos chamar você?" minLength={2} maxLength={80} required/></label>}{mode !== 'reset' && <label>E-mail<input name="email" type="email" autoComplete="email" placeholder="voce@exemplo.com" maxLength={254} required/></label>}<label>{mode === 'reset' ? 'Nova senha' : 'Senha'}<span className="password-input"><input name="password" type={visible ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder="Pelo menos 10 caracteres" minLength={10} maxLength={128} required/><button type="button" aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18}/> : <Eye size={18}/>}</button></span></label><button className="button full" disabled={busy} type="submit">{busy ? 'Só um instante…' : mode === 'register' ? 'Criar minha conta' : mode === 'reset' ? 'Atualizar senha' : 'Entrar na minha conta'}<ArrowRight size={18}/></button></form>{mode === 'login' && <details className="recovery-help"><summary>Esqueceu sua senha?</summary><p>Na primeira versão, a recuperação é assistida pela administração da plataforma. Solicite um link de uso único ao responsável pela instalação.</p></details>}<p className="auth-disclaimer">Seus resultados ficam vinculados à sua conta.<br/>Você pode excluir seu histórico nas configurações.</p></div><p className="auth-copyright">© {new Date().getFullYear()} Enem Flow · Aprender é seguir em frente.</p></section></main>;
}
