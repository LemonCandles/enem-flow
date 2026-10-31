import katex from 'katex';
import 'katex/contrib/mhchem';

export function Formula({ tex, display = false }: { tex: string; display?: boolean }) {
  const html = katex.renderToString(tex, { displayMode: display, output: 'htmlAndMathml',
    throwOnError: false, trust: false, strict: 'ignore', maxExpand: 200, maxSize: 12 });
  return <span className={display ? 'math-display' : 'math-inline'} dangerouslySetInnerHTML={{ __html: html }}/>;
}

// Currency R$ stays ordinary text; math delimiters are explicit and never HTML.
const expressions = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|(?<![R\\])\$(?!\$)(?:\\.|[^$\\\n])+\$)/g;

export function RichText({ text }: { text: string }) {
  return <>{text.split(expressions).map((part, i) => {
    const display = part.startsWith('$$') || part.startsWith('\\[');
    const math = display || part.startsWith('\\(') || (part.startsWith('$') && part.endsWith('$'));
    return math ? <Formula key={i} tex={part.slice(display || part.startsWith('\\(') ? 2 : 1, display || part.startsWith('\\(') ? -2 : -1)} display={display}/> : part;
  })}</>;
}
