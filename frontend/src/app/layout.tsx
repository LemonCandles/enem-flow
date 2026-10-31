import type { Metadata } from 'next';
import 'katex/dist/katex.min.css';
import './globals.css';

export const metadata: Metadata = { title: 'Enem Flow · Aprender, no seu tempo.', description: 'Resolva provas oficiais do ENEM, acompanhe seu desempenho e construa seu caminho de aprendizado.' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR" data-theme="light" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: `(function(){var t;try{t=localStorage.getItem('enem-flow:theme')}catch(e){}if(t!=='light'&&t!=='dark')t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.dataset.theme=t})()` }}/></head><body>{children}</body></html>;
}
