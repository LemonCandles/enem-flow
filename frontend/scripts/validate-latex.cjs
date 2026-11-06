// Compile every explicit expression in the shipped JSON, including figure footers.
const fs = require('node:fs');
const path = require('node:path');
const katex = require('katex');
require('katex/contrib/mhchem');

const input = process.argv.includes('--stdin') ? 0 : (process.argv[2] || path.resolve(__dirname, '../../data/enem-2024-dia2-azul.json'));
const data = JSON.parse(fs.readFileSync(input, 'utf8'));
const expressions = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\)|(?<![A-Z\\])\$(?!\$)(?:\\.|[^$\\\n])+\$)/g;
let count = 0;
const errors = [];
function compile(tex, number) {
  try { katex.renderToString(tex, { throwOnError: true, trust: false, strict: 'ignore', maxExpand: 200, maxSize: 12 }); count++; }
  catch (error) { errors.push(`Questão ${number}: ${error.message}`); }
}
function text(value, number) {
  for (const [token] of value.matchAll(expressions)) {
    const long = token.startsWith('$$') || token.startsWith('\\[') || token.startsWith('\\(');
    compile(token.slice(long ? 2 : 1, long ? -2 : -1), number);
  }
}
function visit(value, number, key = '') {
  if (typeof value === 'string') {
    if (key === 'tex' || key === 'equation') compile(value, number);
    else if (['text', 'statement', 'caption', 'credit', 'alt', 'cell'].includes(key)) text(value, number);
  } else if (Array.isArray(value)) {
    value.forEach(v => visit(v, number, key === 'equations' ? 'equation' : ['rows', 'headers', 'cell'].includes(key) ? 'cell' : key));
  } else if (value && typeof value === 'object') {
    Object.entries(value).forEach(([k,v]) => { if (k !== 'layout') visit(v, number, k); });
  }
}
for (const { content: c } of data.questions) visit(c, c.number);
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
else console.log(`${count} expressões LaTeX matemáticas/químicas válidas em ${data.questions.length} questões.`);
