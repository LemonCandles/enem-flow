#!/usr/bin/env python3
"""Ensaia a preparação generalizada em cadernos de layouts diferentes.

Executa `prepare_exam.py` com manifestos gerados a partir do acervo local e
resume as pendências de cada caderno. Nada é importado ou publicado: rascunhos,
relatórios e figuras ficam em `tmp/ensaio-preparacao/`. Exige os PDFs no
espelho local (`archive_enem.py sync`).
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pymupdf
from scripts.archive_enem import CATALOG, SOURCE_ROOT

OUTPUT = ROOT / 'tmp/ensaio-preparacao'
# Divisão das áreas por dia: até 2016, Humanas e Natureza no 1º dia; desde 2017, Linguagens e Humanas.
AREAS = {
    ('atual', 1): [dict(first=1, last=45, area='Linguagens'), dict(first=46, last=90, area='Ciências Humanas')],
    ('atual', 2): [dict(first=91, last=135, area='Ciências da Natureza'), dict(first=136, last=180, area='Matemática', discipline='Matemática')],
    ('anterior', 1): [dict(first=1, last=45, area='Ciências Humanas'), dict(first=46, last=90, area='Ciências da Natureza')],
    ('anterior', 2): [dict(first=91, last=135, area='Linguagens'), dict(first=136, last=180, area='Matemática', discipline='Matemática')],
}
# (ano, aplicação, dia, caderno, língua estrangeira, margem superior em pontos)
TARGETS = [
    (2024, 'regular', 1, 'caderno-1-azul', 'ingles', 64),
    (2024, 'regular', 1, 'caderno-1-azul', 'espanhol', 64),
    (2024, 'reaplicacao-ppl', 2, 'caderno-7-azul', None, 64),
    (2022, 'regular', 2, 'caderno-7-azul', None, 64),
    (2021, 'regular', 2, 'caderno-7-azul', None, 64),
    (2019, 'regular', 2, 'caderno-7-azul', None, 64),
    (2017, 'regular', 2, 'caderno-7-azul', None, 64),
    (2015, 'regular', 2, 'caderno-7-azul', 'ingles', 64),
    (2012, 'regular', 1, 'caderno-1-azul', None, 45),
]


def source(files, year, application, day, booklet, role):
    rows = [r for r in files if r['year'] == year and r['application'] == application and r.get('day') == day and r['booklet'] == booklet
            and r['role'] == role and r['variant'] == 'padrao' and r.get('modality') == 'impresso' and r['status'] == 'downloaded']
    if len(rows) != 1:
        raise SystemExit(f'{year} {application} dia {day} {booklet}: {len(rows)} arquivos de {role} no catálogo.')
    path = SOURCE_ROOT / rows[0]['path']
    if not path.is_file():
        raise SystemExit(f'{rows[0]["path"]} ausente. Execute archive_enem.py sync.')
    return rows[0], path


def run(files, target):
    year, application, day, booklet, language, top = target
    name = f'{year}-{application}-d{day}-{booklet}' + (f'-{language}' if language else '')
    prova, pdf = source(files, year, application, day, booklet, 'prova')
    gabarito, key = source(files, year, application, day, booklet, 'gabarito')
    with pymupdf.open(pdf) as doc:
        height = doc[1].rect.height
        # Last page with a question heading; later pages hold the essay sheet or blanks.
        last = max(n + 1 for n, page in enumerate(doc) if re.search(r'QUEST[ÃA]O\s+\d+', page.get_text(), re.I))
    manifest = dict(id=f'ensaio-{name}', title=f'Ensaio {name}', year=year, application=application, booklet=booklet, day=day,
                    kind='complete', expected_items=90, duration_minutes=300,
                    source=dict(url=prova['url'], answer_key_url=gabarito['url'], publisher='Inep'),
                    layout=dict(pages=[2, last], top=top, bottom=round(height) - 35, columns='auto'),
                    areas=AREAS[('atual' if year >= 2017 else 'anterior', day)], **({'language': language} if language else {}))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path, output, report = OUTPUT / f'{name}.manifest.json', OUTPUT / f'{name}.json', OUTPUT / f'{name}.report.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    report.unlink(missing_ok=True)
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare_exam.py'), '--manifest', str(path), '--pdf', str(pdf),
                             '--answer-key', str(key), '--output', str(output), '--assets-root', str(OUTPUT / 'assets' / name), '--force'],
                            cwd=ROOT, capture_output=True, text=True)
    if not report.exists():
        return dict(caderno=name, falha=(result.stderr or result.stdout).strip()[-300:])
    data = json.loads(report.read_text())
    errors = Counter(i['code'] for q in data['questions'] for i in q['issues'] if i['severity'] == 'error')
    return dict(caderno=name, questoes=len(data['questions']), bloqueantes=data['errors'], avisos=data['warnings'],
                graficas=sum(i['code'] == 'graphical_options' for q in data['questions'] for i in q['issues']), por_codigo=dict(errors.most_common()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', type=int, nargs='*', help='Limita o ensaio a estes anos.')
    args = parser.parse_args()
    files = json.loads(CATALOG.read_text())['files']
    targets = [t for t in TARGETS if not args.years or t[0] in args.years]
    with ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(lambda target: run(files, target), targets))
    (OUTPUT / 'resumo.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n')
    print('| Caderno | Questões | Bloqueantes | Avisos | Alternativas gráficas | Bloqueantes por tipo |')
    print('| --- | ---: | ---: | ---: | ---: | --- |')
    for row in rows:
        if 'falha' in row:
            print(f'| {row["caderno"]} | — | — | — | — | falha: {row["falha"]} |')
        else:
            kinds = ', '.join(f'{code} {count}' for code, count in row['por_codigo'].items()) or '—'
            print(f'| {row["caderno"]} | {row["questoes"]} | {row["bloqueantes"]} | {row["avisos"]} | {row["graficas"]} | {kinds} |')


if __name__ == '__main__':
    main()
