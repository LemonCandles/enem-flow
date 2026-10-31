import Link from 'next/link';
import { BRAND_CONTOUR, LEARNING_PIECES } from '@/lib/puzzle-geometry';

export function Brand() {
  return <Link className="brand" href="/" aria-label="Enem Flow — Início">
    enem{' '}<span>flow</span>
    <svg viewBox="0 0 24 36" width="24" height="36" fill="none" aria-hidden="true"><path d={BRAND_CONTOUR}/></svg>
  </Link>;
}

/** Closed, complementary puzzle pieces; the small offsets leave their fit visible. */
export function LearningPieces({ className = '' }: { className?: string }) {
  return <svg className={`learning-pieces ${className}`} viewBox="-20 -10 400 420" fill="none" aria-hidden="true" focusable="false">
    {LEARNING_PIECES.map(piece => <g key={piece.id} data-puzzle-piece={piece.id} transform={`translate(${piece.offset.join(' ')})`}>
      <path className="piece-outlines" data-piece-outline="" d={piece.outline} strokeWidth="1.7" strokeLinejoin="round"/>
      {piece.accent && <path className="piece-join" d={piece.accent} strokeWidth="2"/>}
      <g className="piece-symbols" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {piece.id === 'reading' ? <path d="M260 88c-12-10-24-10-36-6v46c12-4 24-2 36 8 12-10 24-12 36-8V82c-12-4-24-4-36 6v48"/> : piece.id === 'reasoning' ? <path d="m100 226 31 60H69Z"/> : <><circle cx="260" cy="228" r="10"/><circle className="piece-selected" cx="260" cy="260" r="10"/><circle cx="260" cy="292" r="10"/></>}
      </g>
    </g>)}
  </svg>;
}

export function CardSeam() {
  return <svg className="card-seam" viewBox="0 0 40 240" preserveAspectRatio="none" fill="none" aria-hidden="true"><path d="M20 0v66q0 12-12 12c-24 0-24 40 0 40q12 0 12 12v110"/></svg>;
}
