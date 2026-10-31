import Link from 'next/link';

export function Brand() {
  return <Link className="brand" href="/" aria-label="Enem Flow — Início">
    enem<span>flow</span>
    <svg viewBox="0 0 24 36" width="24" height="36" fill="none" aria-hidden="true"><path d="M2 2h10q4 0 4 4v5q0 3 3 3c6 0 6 9 0 9q-3 0-3 3v4q0 4-4 4H2"/></svg>
  </Link>;
}

/** The same outline vocabulary connects the hero to the live action cards. */
export function LearningPieces({ className = '' }: { className?: string }) {
  return <svg className={`learning-pieces ${className}`} viewBox="0 0 360 460" fill="none" aria-hidden="true" focusable="false">
    <g className="piece-outlines" strokeWidth="1.7" strokeLinejoin="round">
      <path d="M122 18h188q24 0 24 24v142q0 24-24 24h-42q-22 0-22 22c0 28-40 28-40 0v-14q0-22-22-22h-22q-11 0-17 9c-13 18-43 10-43-14V42q0-24 20-24Z"/>
      <path d="M36 208h114q22 0 22 22v30q0 18 18 18c28 0 28 40 0 40q-18 0-18 18v28q0 22-22 22H36q-22 0-22-22V230q0-22 22-22Z"/>
      <path d="M254 230h82q22 0 22 22v136q0 22-22 22H232q-22 0-22-22v-26q0-18 18-24 18-6 18-24v-62q0-22 8-22Z"/>
      <path d="M210 387v43q0 30-30 30"/>
    </g>
    <path className="piece-join" strokeWidth="2" d="M105 188q2 23 23 23 12 0 17-8 6-9 17-9h22q22 0 22 22v14c0 28 40 28 40 0m0 24v60q0 18-18 24-18 6-18 24v20"/>
    <g className="piece-symbols" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M207 93c-16-13-34-15-50-11v64c18-4 34 0 50 11 16-11 34-15 52-11V82c-18-4-36-2-52 11v64"/>
      <path d="m84 260 38 66H46Z"/>
      <circle cx="291" cy="278" r="12"/>
      <circle className="piece-selected" cx="291" cy="318" r="12"/>
      <circle cx="291" cy="358" r="12"/>
    </g>
  </svg>;
}

export function CardSeam() {
  return <svg className="card-seam" viewBox="0 0 40 240" preserveAspectRatio="none" fill="none" aria-hidden="true"><path d="M20 0v66q0 12-12 12c-24 0-24 40 0 40q12 0 12 12v110"/></svg>;
}
