"""Relatório de cobertura reproduzido dos manifestos, sem contagens teóricas."""
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def report():
    catalog=json.loads((ROOT/'data/sources/catalogo/acervo.json').read_text())
    bank=json.loads((ROOT/'data/bank/coverage.json').read_text())
    sources=json.loads((ROOT/'data/bank/sources.json').read_text())
    reference=json.loads((ROOT/'data/datasets/adaptive-math-reference-v1.json').read_text())
    files=catalog['files'];errors=[r for r in files if r['status']=='error']
    lines=['# Cobertura do acervo oficial','',
        'Coleta de **31/10/2026**, reproduzida a partir de `data/sources/catalogo/acervo.json` e `data/bank/coverage.json`. Escopo: todas as aplicações e formatos com arquivos vinculados no [acervo do Inep](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos).','',
        f'- **{len(catalog["pages"])} anos:** 1998–2025.',
        f'- **{len(files)} referências**, correspondentes a **{len({r["url"] for r in files})} URLs** de arquivos.',
        f'- **{sum(r["status"]=="downloaded" for r in files)} referências obtidas**; **{len(errors)} URLs indisponíveis**.',
        f'- **{sum(r.get("bytes",0) for r in files)/1_000_000_000:.2f} GB** de originais organizados, incluindo cópias de arquivos compartilhados por mais de um caderno/formato.',
        f'- **{bank["pdfs"]} PDFs e {bank.get("txts",0)} TXT de prova indexados**; **{bank["occurrences"]} ocorrências extraídas**.',
        f'- **{bank["canonical_questions"]} identidades conservadoras**; **{bank["duplicate_occurrences"]} ocorrências agrupadas**. Essa contagem inclui identidades provisórias e não é a quantidade comprovada de questões semanticamente únicas de todo o ENEM.',
        f'- **{bank["sources_with_issues"]} fontes com observações de integridade da extração**. Todas as extrações históricas aguardam conferência de conteúdo, inclusive quando a numeração foi reconhecida.',
        '- **135 questões nos dois lotes conferidos**: segundo dia azul de 2024 e Matemática azul de 2023. Anuladas 129/2024 e 164/2023; 133 itens válidos. As quatro cores desses lotes têm 540 ocorrências vinculadas.',
        '- **89 questões válidas de Matemática em oito temas** na referência exploratória. Habilidades candidatas aguardam segunda revisão e não foram publicadas como rótulos.','',
        'Arquivos originais, ocorrências, provas geradas e questões conferidas são contagens diferentes. Cores, aplicações, línguas e versões acessíveis podem repetir itens. Fora dos vínculos conferidos entre cores, somente texto exatamente normalizado é agrupado automaticamente; figuras são tratadas conservadoramente. Os índices se ligam às identidades do catálogo conferido por fonte e número. A geração e a publicação automática, com pendências explícitas, estão documentadas em [banco e classificação](banco-classificacao.md#publicação-automática-do-acervo).','',
        '## Cobertura por ano','',
        '| Ano | Referências | Obtidas | Aplicações do acervo | Fontes de questões indexadas | Ocorrências extraídas |',
        '| --- | ---: | ---: | --- | ---: | ---: |']
    for year in sorted({r['year'] for r in files}):
        selected=[r for r in files if r['year']==year];stats=next(r for r in bank['by_year'] if r['year']==year)
        applications=', '.join(sorted({r['application'] for r in selected}))
        lines.append(f'| {year} | {len(selected)} | {sum(r["status"]=="downloaded" for r in selected)} | {applications} | {stats["pdfs"]} | {stats["occurrences"]} |')
    lines+=['','A coluna de fontes indexadas inclui TXT quando presentes; os nomes de aplicação normalizados preservam a distinção dos títulos oficiais, disponíveis no manifesto. Ausência de arquivo no índice não autoriza concluir que uma aplicação nunca existiu.','',
        '## URLs oficiais indisponíveis','',
        '| Ano e aplicação | Arquivo | Resultado |','| --- | --- | --- |']
    for r in errors:lines.append(f'| {r["year"]} · {r["application"]} | [{r["label"]} — {r["official_title"]}]({r["url"]}) | {r.get("error", "Indisponível")} |')
    lines+=['','Não foi usado gabarito de outra aplicação como substituto. Uma URL de nome parecido pode pertencer, por exemplo, à aplicação de Belém; o número do caderno sozinho não determina a prova.','',
        '## Fontes com observações de extração','',
        '| Fonte | Questões extraídas | Observação |','| --- | ---: | --- |']
    occurrences=json.loads((ROOT/'data/bank/occurrences.json').read_text());counts=Counter(r['source_id'] for r in occurrences)
    for s in sources:
        if s['issues']:lines.append(f'| `{s["source_path"]}` | {counts[s["source_id"]]} | '+ ' '.join(s['issues']).replace('|','/')+' |')
    lines+=['','Uma observação de contagem não resolve OCR, leitura de fórmulas, tabelas ou textos compartilhados. O texto bruto permanece consultável na curadoria e não é usado como questão aprovada sem preparação.','',
        '## Temas da referência de Matemática','',
        '| Tema | Questões válidas |','| --- | ---: |']
    for theme,count in reference['theme_counts'].items():lines.append(f'| {theme} | {count} |')
    lines+=['','## Reproduzir','',
        '```bash','python scripts/archive_enem.py inventory','python scripts/archive_enem.py sync --workers 4','python scripts/archive_enem.py audit','.venv/bin/python scripts/build_bank.py --workers 4','.venv/bin/python scripts/report_bank.py','```','',
        'Enquanto os dois links oficiais permanecerem quebrados, `sync` e `audit` retornam 2 e mantêm as demais fontes verificadas. O [guia das fontes](../data/sources/README.md) explica o intermediário TLS opcional, arquivos locais versus versionados e organização dos derivados. O [processo de classificação](banco-classificacao.md) registra a revisão e seus limites.','']
    return '\n'.join(lines)


if __name__=='__main__':
    target=ROOT/'docs/cobertura-acervo.md';target.write_text(report());print(target.relative_to(ROOT))
