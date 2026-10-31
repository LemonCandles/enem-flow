import type { ContentBlock, Question } from '@/lib/api';
import { Formula, RichText } from './latex';
import QuestionFigure from './question-figure';
export { RichText } from './latex';

function Block({ block, number }: { block: ContentBlock; number: number }) {
  switch (block.type) {
    case 'paragraph': return <p className={`native-paragraph ${block.role === 'credit' || (block.role == null && /Disponível em:|Acesso em:|\(adaptado\)/.test(block.text)) ? 'question-credit' : ''}`}><RichText text={block.text}/></p>;
    case 'math': return <div className="native-equation" tabIndex={0} role="region" aria-label={`Equação da questão ${number}; role horizontalmente se necessário`}><Formula tex={block.tex} display/></div>;
    case 'image': return <QuestionFigure asset={block.asset} title={`Figura da questão ${number}`} caption={block.caption} credit={block.credit} equations={block.equations}/>;
    case 'table': return <div className="native-table-wrap" tabIndex={0} role="region" aria-label={block.caption}><table className="native-table"><caption>{block.caption}</caption><thead><tr>{block.headers.map((header, i) => <th scope="col" key={i}><RichText text={header}/></th>)}</tr></thead><tbody>{block.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}><RichText text={cell}/></td>)}</tr>)}</tbody></table></div>;
  }
}

export function QuestionContent({ question }: { question: Question }) {
  if (question.blocks?.length) return <div className="native-question">{question.blocks.map((block, index) => <Block key={index} block={block} number={question.number}/>)}</div>;
  return <div className="native-question"><div className="semantic-statement"><RichText text={question.statement}/></div>{question.images.map(asset => <QuestionFigure key={asset.path} asset={asset} title={`Figura da questão ${question.number}`}/>)}</div>;
}
