import katex from 'katex';
import { ExternalLink } from 'lucide-react';
import type { ContentBlock, Question } from '@/lib/api';

function Formula({ tex, display = false }: { tex: string; display?: boolean }) {
  const html = katex.renderToString(tex, { displayMode: display, output: 'htmlAndMathml',
    throwOnError: false, trust: false, strict: 'ignore', maxExpand: 200, maxSize: 12 });
  // KaTeX escapes text, disables trusted HTML/URL commands, and produces the markup.
  return <span className={display ? 'math-display' : 'math-inline'} dangerouslySetInnerHTML={{ __html: html }}/>;
}

export function RichText({ text }: { text: string }) {
  return <>{text.split(/(?<!R)(\$[^$\n]+\$)/g).map((part, i) => part.startsWith('$') && part.endsWith('$')
    ? <Formula key={i} tex={part.slice(1, -1)}/> : part)}</>;
}

function Block({ block }: { block: ContentBlock }) {
  switch (block.type) {
    case 'paragraph': return <p className={`native-paragraph ${/Disponível em:|Acesso em:|\(adaptado\)/.test(block.text) ? 'question-credit' : ''}`}><RichText text={block.text}/></p>;
    case 'math': return <div className="native-equation"><Formula tex={block.tex} display/></div>;
    case 'image': return <figure className="question-figure"><img src={`/api${block.asset.path}`} alt={block.asset.alt}/><figcaption><a href={`/api${block.asset.path}`} target="_blank" rel="noreferrer">Ampliar figura <ExternalLink size={12}/></a></figcaption></figure>;
    case 'table': return <div className="native-table-wrap" tabIndex={0} role="region" aria-label={block.caption}><table className="native-table"><caption>{block.caption}</caption><thead><tr>{block.headers.map((header, i) => <th scope="col" key={i}><RichText text={header}/></th>)}</tr></thead><tbody>{block.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}><RichText text={cell}/></td>)}</tr>)}</tbody></table></div>;
  }
}

export function QuestionContent({ question }: { question: Question }) {
  if (question.blocks?.length) return <div className="native-question">{question.blocks.map((block, index) => <Block key={index} block={block}/>)}</div>;
  return <div className="native-question"><div className="semantic-statement"><RichText text={question.statement}/></div>{question.images.map(asset => <figure className="question-figure" key={asset.path}><img src={`/api${asset.path}`} alt={asset.alt}/></figure>)}</div>;
}
