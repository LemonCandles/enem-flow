'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { Minus, Plus, RotateCcw, X, ZoomIn } from 'lucide-react';
import type { Asset } from '@/lib/api';
import { Formula, RichText } from './latex';
import { trapDialogFocus } from '@/lib/dialog-focus';

type Props = { asset: Asset; title?: string; caption?: string; credit?: string; equations?: string[] };

export default function QuestionFigure({ asset, title = 'Figura da questão', caption = '', credit = '', equations = [] }: Props) {
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (!open) return;
    const modal = dialog.current!;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    modal.showModal();
    return () => { if (modal.open) modal.close(); document.body.style.overflow = overflow; };
  }, [open]);
  useEffect(() => {
    if (open && viewport.current) viewport.current.scrollTo({ left: (viewport.current.scrollWidth - viewport.current.clientWidth) / 2, top: 0 });
  }, [open, zoom]);

  function details(prefix: string) {
    return <>
      {!!equations.length && <div className="figure-equations" aria-label="Reações representadas na figura">{equations.map((tex, i) => <div className="figure-equation" tabIndex={0} role="region" aria-label={`Reação ${i + 1}; role horizontalmente se necessário`} key={i}><Formula tex={tex} display/></div>)}</div>}
      <figcaption id={`${prefix}-caption`}>
        <p className="figure-caption"><RichText text={caption || asset.alt}/></p>
        {credit && <p className="figure-credit"><RichText text={credit}/></p>}
      </figcaption>
    </>;
  }
  function enlarge() { setZoom(1); setOpen(true); }

  return <>
    <figure className="question-figure">
      <button type="button" className="figure-image-button" aria-label={`Ampliar: ${asset.alt}`} aria-haspopup="dialog" onClick={enlarge}><img src={`/api${asset.path}`} alt={asset.alt} aria-describedby={`${id}-caption`}/></button>
      {details(id)}
      <button type="button" className="figure-zoom" aria-haspopup="dialog" onClick={enlarge}><ZoomIn size={15}/>Ampliar figura</button>
    </figure>
    <dialog ref={dialog} className="figure-dialog" aria-labelledby={`${id}-title`} onKeyDown={trapDialogFocus} onClose={() => setOpen(false)} onClick={event => { if (event.target === event.currentTarget) setOpen(false); }}>
      {open && <>
        <header className="figure-dialog-header"><h2 id={`${id}-title`}>{title}</h2><button type="button" className="icon-button" aria-label="Fechar ampliação" autoFocus onClick={() => setOpen(false)}><X/></button></header>
        <div className="figure-zoom-controls" aria-label="Controles de ampliação"><button type="button" className="icon-button" aria-label="Diminuir ampliação" disabled={zoom <= .5} onClick={() => setZoom(value => Math.max(.5, value - .25))}><Minus size={18}/></button><output aria-live="polite">{Math.round(zoom * 100)}%</output><button type="button" className="icon-button" aria-label="Aumentar ampliação" disabled={zoom >= 3} onClick={() => setZoom(value => Math.min(3, value + .25))}><Plus size={18}/></button><button type="button" className="text-button" onClick={() => setZoom(1)}><RotateCcw size={15}/>Restaurar tamanho</button></div>
        <figure className="expanded-figure"><div ref={viewport} className="figure-viewport" tabIndex={0} aria-label="Figura ampliada; role para percorrer a imagem"><div className="figure-canvas" style={{ width: `${zoom * 100}%` }}><img src={`/api${asset.path}`} alt={asset.alt} aria-describedby={`${id}-expanded-caption`} style={{ maxHeight: `${zoom * 55}dvh` }}/></div></div>{details(`${id}-expanded`)}</figure>
      </>}
    </dialog>
  </>;
}
