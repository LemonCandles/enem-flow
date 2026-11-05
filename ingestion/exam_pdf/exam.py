"""Build an exam from a manifest and its PDF, joining text, regions, key and figures."""

import hashlib
from contextlib import nullcontext
import re
from collections import Counter
from pathlib import Path

import pymupdf as fitz

from ingestion.pdf_headings import HEADING
from .answer_key import answer_key_rows
from .figures import alternative_graphics, graphics
from .regions import discover_regions, margin_headings
from .text import align_option_lines, diagnostic, garbled, lines, literal, mark_bare_options, textual_table


def from_manifest(manifest, pdf, answer_key=None):
    """Metadata/area ranges are explicit; answer keys never come from heuristics."""
    config = dict(manifest)
    answers = {int(k): v for k, v in config.get('answers', {}).items()}
    if answer_key:
        with fitz.open(answer_key) as doc:
            text = '\n'.join(p.get_text() for p in doc)
        covered = {n for area in config.get('areas', []) for n in range(area['first'], area['last'] + 1)} or None
        for n, answer in answer_key_rows(text, config.get('language'), covered, config.get('booklet')).items():
            if n in answers and answers[n] != answer:
                raise ValueError(f'Gabaritos conflitantes na questão {n}.')
            answers[n] = answer
    if not answers:
        raise ValueError('Informe answers no manifesto ou --answer-key com gabarito textual.')
    if any(v not in [None, *'ABCDE'] for v in answers.values()):
        raise ValueError('Gabarito deve conter A–E ou null para anuladas.')
    with fitz.open(pdf) as doc:
        languages = {}
        regions = discover_regions(doc, config, languages)
        if config.get('range'):
            # A section of the booklet: only these numbers are prepared.
            first, last = config['range']
            regions = {n: r for n, r in regions.items() if first <= n <= last}
            answers = {n: a for n, a in answers.items() if first <= n <= last}
        if not regions:
            raise ValueError(
                'Nenhum cabeçalho textual encontrado: confira páginas e margens. Sem camada de texto, o PDF exige OCR; com codificação quebrada, use outra cor legível da mesma aplicação.'
            )
        if set(regions) != set(answers):
            missing = sorted(set(answers) - set(regions))
            hint = ''
            outside = margin_headings(doc, config, missing)
            if outside:
                hint = f' Cabeçalhos fora das margens do layout (ajuste layout.top/bottom): {", ".join(outside)}.'
            raise ValueError(
                f'Questões e gabarito não coincidem: sem gabarito {sorted(set(regions) - set(answers))}; sem questão {missing}.{hint}'
            )
        questions = []
        for number, pieces in sorted(regions.items()):
            matches = [r for r in config['areas'] if r['first'] <= number <= r['last']]
            if len(matches) != 1:
                raise ValueError(f'Área ausente ou sobreposta para a questão {number}.')
            area = matches[0]
            questions.append(
                {
                    'question_id': f"{config['id']}-q{number}",
                    'content': {
                        'number': number,
                        'area': area['area'],
                        'statement': '\n\n'.join(
                            doc[r['page'] - 1].get_text(clip=fitz.Rect(r['bbox'])) for r in pieces
                        ),
                        'blocks': [],
                        'images': [],
                        'alternatives': [{'letter': a, 'text': 'Transcrição pendente de preparação.'} for a in 'ABCDE'],
                        'correct_answer': answers[number],
                        'annulled': answers[number] is None,
                        'labels': {
                            'discipline': area.get('discipline'),
                            'provenance': 'Área declarada no manifesto; classificação aguarda revisão.',
                        },
                        'page': pieces[0]['page'],
                        'original_layout': False,
                        'layout': {
                            'blocks': pieces,
                            **({'language': languages[number]} if number in languages else {}),
                        },
                    },
                }
            )
    fields = ['id', 'title', 'year', 'application', 'booklet', 'day', 'kind', 'expected_items', 'duration_minutes']
    result = {key: config[key] for key in fields}
    result['source'] = {**config['source'], 'sha256': hashlib.sha256(Path(pdf).read_bytes()).hexdigest()}
    if answer_key:
        result['source']['answer_key_sha256'] = hashlib.sha256(Path(answer_key).read_bytes()).hexdigest()
    if not result['source'].get('answer_key_sha256'):
        raise ValueError('Informe o hash SHA-256 do gabarito ou o arquivo --answer-key.')
    result['questions'] = questions
    if len(questions) != result['expected_items']:
        raise ValueError('Quantidade extraída diferente de expected_items.')
    return result


def extract_exam(data, pdf, assets_root, document=None):
    """Rebuild native blocks from positioned regions in an arbitrary exam JSON."""
    if document is not None and Path(document.name).resolve() != Path(pdf).resolve():
        raise ValueError('Documento aberto difere da fonte declarada.')
    with nullcontext(document) if document is not None else fitz.open(pdf) as doc:
        source_hash = hashlib.sha256(Path(pdf).read_bytes()).hexdigest()
        if source_hash != data['source']['sha256']:
            raise ValueError('Hash do PDF diferente da origem declarada no JSON.')
        for question in data['questions']:
            c = question['content']
            regions = (c.get('layout') or {}).get('blocks', [])
            if not regions:
                raise ValueError(f"Questão {c['number']}: faltam regiões page/bbox. Use --manifest para descobri-las.")
            entries, issues, positions = [], [], []
            for region in regions:
                pn = region['page']
                if not 1 <= pn <= len(doc):
                    raise ValueError('Página fora do PDF.')
                page, clip = doc[pn - 1], fitz.Rect(region['bbox'])
                if clip.is_empty or not page.rect.contains(clip):
                    raise ValueError('Região fora da página.')
                source_lines = lines(page, clip)
                mark_bare_options(source_lines)
                source_lines = align_option_lines(source_lines)
                figs = []
                for candidate in graphics(page, clip):
                    if candidate.get_area() >= clip.get_area() * 0.9:
                        issues.append(
                            diagnostic(
                                'whole_region_image',
                                'Imagem ocupa o recorte integral: separe os diagramas ou faça OCR e confira o texto antes de aprovar.',
                                f'page:{pn}',
                                'error',
                            )
                        )
                    else:
                        figs.append(candidate)
                tables = []
                # Tables with a rectangular cell grid become HTML data. Never
                # infer missing cells from prose or replace a table with OCR guesses.
                for table in page.find_tables(clip=clip, use_layout=False).tables:
                    if any(
                        l.get('option') and fitz.Rect(table.bbox).contains(fitz.Point(l['bbox'][:2]))
                        for l in source_lines
                    ):
                        continue
                    rows = table.extract()
                    if (
                        len(rows) > 1
                        and 1 < len(rows[0]) <= 12
                        and all(len(r) == len(rows[0]) for r in rows)
                        and textual_table(rows)
                    ):
                        if any(cell is None for row in rows for cell in row):
                            issues.append(
                                diagnostic(
                                    'merged_table_cells',
                                    'Tabela com células mescladas ou ausentes: confira a estrutura antes de aprovar.',
                                    f'page:{pn}',
                                    'error',
                                )
                            )
                        tables.append(
                            (
                                fitz.Rect(table.bbox),
                                {
                                    'type': 'table',
                                    'caption': 'Tabela extraída da prova; conferir cabeçalhos.',
                                    'headers': [literal(str(v or '')) for v in rows[0]],
                                    'rows': [[literal(str(v or '')) for v in row] for row in rows[1:]],
                                },
                            )
                        )
                figs = [
                    r
                    for r in figs
                    if not any(t[0].intersects(r) and (t[0] & r).get_area() > r.get_area() * 0.8 for t in tables)
                ]
                for r, block in tables:
                    entries.append(dict(type='block', block=block, page=pn, bbox=list(r), text=''))
                labelled_figs = alternative_graphics(figs, source_lines, clip)
                expanded = []
                for r, alternative in labelled_figs:
                    # Include labels touching the drawing, without absorbing nearby prose.
                    anchor = fitz.Rect(r)
                    for line in source_lines:
                        if line.get('option'):
                            continue
                        lr = fitz.Rect(line['bbox'])
                        if line['size'] <= 8.5 and lr.y0 >= anchor.y1:
                            continue
                        if not anchor.intersects(lr) and len(line['text']) > 50:
                            continue
                        if (anchor + (-3, -3, 3, 3)).intersects(lr) and len(line['text']) < 100:
                            r |= lr
                    r = (r + (-2, -2, 2, 2)) & clip
                    expanded.append(r)
                    digest = hashlib.sha256(f'{source_hash}:{pn}:{list(r)}'.encode()).hexdigest()[:16]
                    relative = Path(data['id']) / 'prepared' / f'{digest}.png'
                    target = Path(assets_root) / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=r).save(target)
                    block = {
                        'type': 'image',
                        'asset': {
                            'path': '/assets/' + relative.as_posix(),
                            'alt': f"Figura extraída da questão {c['number']}, página {pn}; descrição detalhada pendente.",
                        },
                    }
                    entries.append(
                        dict(type='block', block=block, page=pn, bbox=list(r), text='', alternative=alternative)
                    )
                    positions.append({'asset': block['asset']['path'], 'page': pn, 'bbox': list(r)})
                excluded = expanded + [r for r, _ in tables]
                uncontained = [
                    l for l in source_lines if not any(r.contains(fitz.Rect(l['bbox']).tl) for r in excluded)
                ]
                aligned = Counter(round(l['bbox'][1] / 3) for l in uncontained)
                if sum(count >= 3 for count in aligned.values()) >= 2:
                    issues.append(
                        diagnostic(
                            'spatial_layout',
                            'Linhas com múltiplas colunas fora de uma tabela reconhecida: confira tabela, fórmula ou diagrama e estruture os blocos.',
                            f'page:{pn}',
                            'error',
                        )
                    )
                broken = [l['text'] for l in source_lines if garbled(l['text'])]
                if broken:
                    issues.append(
                        diagnostic(
                            'garbled_text',
                            f'{len(broken)} linha(s) com codificação de texto quebrada: a fonte do PDF não informa as letras. Prepare por outra cor legível da mesma aplicação ou corrija a codificação; não aprove.',
                            f'page:{pn}',
                            'error',
                            broken[0],
                        )
                    )
                for line in source_lines:
                    center = (
                        fitz.Rect(line['bbox']).tl + (fitz.Rect(line['bbox']).br - fitz.Rect(line['bbox']).tl) * 0.5
                    )
                    if not line.get('option') and any(r.contains(center) for r in excluded):
                        continue
                    if HEADING.match(line['text']):
                        continue
                    if not line['text']:
                        continue
                    if line['uncertain']:
                        issues.append(
                            diagnostic(
                                'spatial_math',
                                'Índice/expoente não numérico precisa de transcrição LaTeX.',
                                f'page:{pn}',
                                excerpt=line['text'],
                            )
                        )
                    if re.search(r'[√∫∑]|\b\d+\s+\d+\s*/', line['text']):
                        issues.append(
                            diagnostic(
                                'complex_math',
                                'Expressão espacial precisa de conferência e transcrição LaTeX; expoentes e frações não são inferidos de texto achatado.',
                                f'page:{pn}',
                                excerpt=line['text'],
                            )
                        )
                    entries.append({**line, 'text': literal(line['text']), 'type': 'text', 'page': pn})
            # Regions already encode column/page reading order. Do not globally
            # sort columns by y, which would interleave independent questions.
            ordered = []
            for region in regions:
                r = fitz.Rect(region['bbox'])
                pn = region['page']
                group = [
                    e
                    for e in entries
                    if e['page'] == pn
                    and r.contains(fitz.Point(e['bbox'][0] + 0.1, e['bbox'][1] + 0.1))
                    and e not in ordered
                ]
                ordered.extend(sorted(group, key=lambda e: (round(e['bbox'][1], 1), e['bbox'][0])))
            explicit = [(i, e['option']) for i, e in enumerate(ordered) if e.get('option')]
            markers = (
                explicit
                if sorted(letter for _, letter in explicit) == list('ABCDE')
                else [
                    (i, m[1])
                    for i, e in enumerate(ordered)
                    if e['type'] == 'text' and (m := re.match(r'^([ABCDE])(?:\s|$)', e['text']))
                ]
            )
            sequences = [k for k in range(len(markers) - 4) if ''.join(x[1] for x in markers[k : k + 5]) == 'ABCDE']
            choices, body = [], ordered
            graphical = {letter: [e for e in ordered if e.get('alternative') == letter] for letter in 'ABCDE'}
            if sorted(letter for _, letter in explicit) == list('ABCDE') and all(
                len(items) == 1 for items in graphical.values()
            ):
                cutoff = min(i for i, e in enumerate(ordered) if e.get('alternative') or e.get('option'))
                body = ordered[:cutoff]
                choices = [
                    {
                        'letter': letter,
                        'text': re.sub(
                            r'^[ABCDE]\s*', '', ordered[next(i for i, a in explicit if a == letter)]['text']
                        ).strip(),
                        'image': graphical[letter][0]['block']['asset'],
                    }
                    for letter in 'ABCDE'
                ]
                issues.append(
                    diagnostic(
                        'graphical_options',
                        'Alternativas gráficas segmentadas pela posição das letras A–E; confira contornos, rótulos e correspondência.',
                        'alternatives',
                    )
                )
            elif len(sequences) == 1:
                found = markers[sequences[0] : sequences[0] + 5]
                body = ordered[: found[0][0]]
                for j, (start, letter) in enumerate(found):
                    chunk = ordered[start : found[j + 1][0] if j < 4 else len(ordered)]
                    text = ' '.join(e['text'] for e in chunk if e['type'] == 'text')
                    text = re.sub(r'^[ABCDE]\s*', '', text).strip()
                    images = [
                        e['block']['asset'] for e in chunk if e['type'] == 'block' and e['block']['type'] == 'image'
                    ]
                    if len(images) > 1:
                        issues.append(
                            diagnostic(
                                'alternative_layout',
                                'Múltiplas figuras em uma alternativa: agrupe e confira manualmente.',
                                f'alternative:{letter}',
                                'error',
                            )
                        )
                    choices.append(
                        {
                            'letter': letter,
                            'text': text or ('' if images else 'Alternativa não extraída; conferir original.'),
                            'image': images[0] if images else None,
                        }
                    )
            else:
                issues.append(
                    diagnostic(
                        'alternative_layout',
                        'Não foi encontrada uma sequência inequívoca A–E. Transcreva as alternativas e remova os fragmentos do enunciado.',
                        'alternatives',
                        'error',
                    )
                )
                choices = [{'letter': a, 'text': 'Alternativa não extraída; conferir original.'} for a in 'ABCDE']
            blocks = []
            for e in body:
                if e['type'] == 'block':
                    blocks.append(e['block'])
                    continue
                text = e['text']
                # Same PDF block, ordinary body text: join physical lines. Equations
                # and small bibliography remain separate to preserve their roles.
                previous = blocks[-1] if blocks else None
                is_reaction = bool(re.search(r'→|⇌|->', text))
                if (
                    previous
                    and previous.get('_group') == (e['page'], e['group'])
                    and not is_reaction
                    and not previous.get('_reaction')
                ):
                    previous['text'] += ' ' + text
                else:
                    blocks.append(
                        {'type': 'paragraph', 'text': text, '_group': (e['page'], e['group']), '_reaction': is_reaction}
                    )
            for b in blocks:
                b.pop('_group', None)
                b.pop('_reaction', None)
            c.update(blocks=blocks, images=[], alternatives=choices, original_layout=False)
            c['statement'] = (
                '\n\n'.join(b['text'] for b in blocks if b['type'] == 'paragraph')
                or 'Conteúdo visual; conferir a figura e o original.'
            )
            c['layout'] = {
                **(c.get('layout') or {}),
                'extraction': {
                    'adapter': 'pdf-geometry-v1',
                    'source_sha256': source_hash,
                    'figures': positions,
                    'issues': issues,
                },
            }
    return data
