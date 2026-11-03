"""Layouts found while preparing other booklets, reproduced in synthetic PDFs."""
import hashlib

import pymupdf
import pytest

from scripts.exam_pdf import extract_exam, from_manifest, lines

TEXT = 'Considere a situação descrita e escolha a alternativa que melhor a representa.'


def manifest(numbers, **extra):
    return dict(id='layout-sintetico', title='Layout sintético', year=2024, application='Regular', booklet='Sintético', day=1,
                kind='collection', expected_items=len(numbers), duration_minutes=10,
                source=dict(url='https://example.com/prova.pdf', answer_key_url='https://example.com/gabarito.pdf', publisher='Fixture',
                            answer_key_sha256='b' * 64),
                layout=dict(pages=[1, 1], top=40, bottom=760, columns='auto'),
                areas=[dict(first=1, last=90, area='Linguagens')], answers={str(n): 'A' for n in numbers}, **extra)


def question(page, y, number, text=TEXT):
    page.insert_text((40, y), f'QUESTAO {number:02d}', fontname='hebo', fontsize=10)
    page.insert_text((40, y + 18), text[:60], fontsize=9)
    return y + 60


def options_column(page, y, letters='ABCDE'):
    for letter in letters:
        page.insert_text((40, y + 10), letter, fontname='cour', fontsize=10)
        page.draw_rect(pymupdf.Rect(60, y, 200, y + 40), color=(0, 0, 0), width=1)
        y += 50
    return y


def save(doc, tmp_path):
    path = tmp_path / 'prova.pdf'
    doc.save(path)
    return path


def test_language_option_keeps_only_the_declared_language(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=569, height=781)
    y = 60
    page.insert_text((40, y), 'Questões de 01 a 02 (opção inglês)', fontsize=9); y += 20
    y = question(page, y, 1, 'Read the text about climate change and answer.')
    y = question(page, y, 2, 'The poem uses irony to describe the city.')
    page.insert_text((40, y), 'Questões de 01 a 02 (opção espanhol)', fontsize=9); y += 20
    y = question(page, y, 1, 'Lee el texto sobre el cambio climático y responde.')
    y = question(page, y, 2, 'El poema usa ironía para describir la ciudad.')
    question(page, y, 3, 'Texto comum às duas opções de língua.')
    pdf = save(doc, tmp_path)

    exam = from_manifest(manifest([1, 2, 3], language='Espanhol'), pdf)
    statements = {q['content']['number']: q['content']['statement'] for q in exam['questions']}
    assert 'Lee el texto' in statements[1] and 'El poema' in statements[2] and 'Read the text' not in statements[1]
    assert 'opção espanhol' not in statements[2] and 'Texto comum' in statements[3]
    assert [q['content']['layout'].get('language') for q in exam['questions']] == ['espanhol', 'espanhol', None]
    with pytest.raises(ValueError, match='declare "language"'):
        from_manifest(manifest([1, 2, 3]), pdf)
    with pytest.raises(ValueError, match='não encontrada'):
        from_manifest(manifest([1, 2, 3], language='francês'), pdf)


def test_option_glyph_below_its_text_does_not_shift_answers(tmp_path):
    doc=pymupdf.open();page=doc.new_page(width=569,height=781)
    y=question(page,60,1)
    for i,letter in enumerate('ABCDE'):
        page.insert_text((40,y+i*28+2),letter,fontname='cour',fontsize=10)
        page.insert_text((65,y+i*28),f'Conteudo exclusivo {i+10}',fontsize=10)
    pdf=save(doc,tmp_path)
    content=extract_exam(from_manifest(manifest([1]),pdf),pdf,tmp_path/'assets')['questions'][0]['content']
    assert [a['text'] for a in content['alternatives']]==[f'Conteudo exclusivo {i+10}' for i in range(5)]
    assert 'Conteudo exclusivo' not in content['statement']


def test_shared_passage_is_removed_from_previous_and_copied_to_every_target(tmp_path):
    doc=pymupdf.open();page=doc.new_page(width=569,height=781)
    question(page,60,1,'Enunciado anterior.')
    page.insert_text((40,160),'Texto para as questões 2 e 3',fontsize=10)
    page.insert_text((40,180),'Contexto indispensavel para as duas respostas.',fontsize=10)
    question(page,240,2,'Primeira pergunta dependente do contexto.')
    question(page,350,3,'Segunda pergunta dependente do contexto.')
    pdf=save(doc,tmp_path)
    result=from_manifest(manifest([1,2,3]),pdf)
    c=[q['content'] for q in result['questions']]
    assert 'Contexto indispensavel' not in c[0]['statement']
    assert all('Contexto indispensavel' in q['statement'] for q in c[1:])
    assert all(q['layout']['blocks'][0]['shared_for']==[2,3] for q in c[1:])


def test_essay_section_is_not_appended_to_the_previous_answer(tmp_path):
    doc=pymupdf.open();page=doc.new_page(width=569,height=781)
    question(page,60,1,'Pergunta sobre um texto literario.')
    page.insert_text((40,170),'PROPOSTA DE REDAÇÃO',fontsize=12)
    page.insert_text((40,200),'Um tema que nao pertence a nenhuma alternativa.',fontsize=9)
    question(page,400,2,'Pergunta de outra area do conhecimento.')
    pdf=save(doc,tmp_path)
    result=from_manifest(manifest([1,2]),pdf)
    assert all('Um tema' not in q['content']['statement'] for q in result['questions'])
    assert 'Pergunta de outra' in result['questions'][1]['content']['statement']


def test_centered_single_column_with_large_left_margin_stays_whole(tmp_path):
    doc=pymupdf.open();page=doc.new_page(width=842,height=1100)
    page.insert_text((290,80),'QUESTAO 1',fontsize=12)
    for i in range(4):page.insert_text((290,110+18*i),'Texto longo que cruza o centro e ocupa menos de sessenta e cinco por cento.',fontsize=10)
    config=manifest([1]);config['layout'].update(bottom=1050)
    pdf=save(doc,tmp_path)
    c=from_manifest(config,pdf)['questions'][0]['content']
    assert len(c['layout']['blocks'])==1 and c['layout']['blocks'][0]['bbox'][2]==842


def test_empty_graph_grid_is_not_reinterpreted_as_a_data_table(tmp_path):
    doc=pymupdf.open();page=doc.new_page(width=569,height=781)
    y=question(page,60,1)
    page.draw_rect(pymupdf.Rect(60,y,200,y+120))
    page.draw_line((130,y),(130,y+120));page.draw_line((60,y+60),(200,y+60))
    page.insert_text((135,y+58),'O',fontsize=9)
    for i,letter in enumerate('ABCDE'):page.insert_text((40,y+160+20*i),f'{letter} Opcao {letter}',fontsize=10)
    pdf=save(doc,tmp_path)
    c=extract_exam(from_manifest(manifest([1]),pdf),pdf,tmp_path/'assets')['questions'][0]['content']
    assert not any(b['type']=='table' for b in c['blocks'])
    assert any(b['type']=='image' for b in c['blocks'])


def test_rotated_repeated_watermark_is_dropped_but_rotated_labels_stay(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=569, height=781)
    page.insert_text((284, 700), 'ENEM2024ENEM2024ENEM2024ENEM2024', fontsize=8, rotate=90)
    page.insert_text((100, 400), 'Tempo de reação (s)', fontsize=8, rotate=90)
    found = [line['text'] for line in lines(page, page.rect)]
    assert 'Tempo de reação (s)' in found and not any('ENEM2024' in text for text in found)


def test_bare_letters_in_a_grid_split_figures_by_marker_font(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=569, height=781)
    y = question(page, 60, 1)
    # A figure in the stem labels its points A, B and C with the text font.
    page.draw_rect(pymupdf.Rect(60, y, 200, y + 60), color=(0, 0, 0), width=1)
    for letter, x in zip('ABC', (70, 120, 170)):
        page.insert_text((x, y + 30), letter, fontsize=9)
    y += 80
    # Options in a grid read A D / B E / C; their markers use another font.
    for row, pair in enumerate(['AD', 'BE', 'C']):
        for column, letter in enumerate(pair):
            x = 40 + column * 120
            page.insert_text((x, y + row * 60 + 20), letter, fontname='cour', fontsize=10)
            page.draw_rect(pymupdf.Rect(x + 15, y + row * 60, x + 105, y + row * 60 + 40), color=(0, 0, 0), width=1)
    # A thin bar along the margin decorates the page and is not a figure.
    page.draw_rect(pymupdf.Rect(8, 60, 24, 700), color=(0, 0, 0), fill=(0, 0, 0))
    pdf = save(doc, tmp_path)

    exam = extract_exam(from_manifest(manifest([1]), pdf), pdf, tmp_path / 'assets')
    content = exam['questions'][0]['content']
    issues = content['layout']['extraction']['issues']
    assert not any(i['code'] == 'alternative_layout' for i in issues)
    boxes = {f['asset']: f['bbox'] for f in content['layout']['extraction']['figures']}
    cells = {'A': (55, 0), 'D': (175, 0), 'B': (55, 1), 'E': (175, 1), 'C': (55, 2)}
    for alternative in content['alternatives']:
        box = boxes[alternative['image']['path']]
        x, row = cells[alternative['letter']]
        assert abs(box[0] - x) < 6 and abs(box[1] - (y + row * 60)) < 6
    assert not any(box[2] - box[0] < 30 for box in boxes.values())


def test_single_column_figures_stay_whole_beside_their_marker(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=569, height=781)
    y = question(page, 60, 1)
    options_column(page, y)
    pdf = save(doc, tmp_path)

    exam = extract_exam(from_manifest(manifest([1]), pdf), pdf, tmp_path / 'assets')
    content = exam['questions'][0]['content']
    assert not any(i['code'] == 'alternative_layout' for i in content['layout']['extraction']['issues'])
    heights = [box[3] - box[1] for box in (f['bbox'] for f in content['layout']['extraction']['figures'])]
    assert len(heights) == 5 and all(h >= 40 for h in heights)


def test_missing_headings_outside_the_margins_are_named(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=569, height=781)
    question(page, 55, 1)
    question(page, 200, 2)
    pdf = save(doc, tmp_path)
    narrow = manifest([1, 2])
    narrow['layout']['top'] = 64
    with pytest.raises(ValueError, match=r'fora das margens.*1 \(página 1'):
        from_manifest(narrow, pdf)
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == from_manifest(manifest([1, 2]), pdf)['source']['sha256']


def test_broken_text_encoding_blocks_the_question(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=569, height=781)
    y = question(page, 60, 1)
    page.insert_text((40, y), 'fÜ éîèÜèê èê q† nÜ¶ó†2 Ü§ îóìÜ§ èê éÜó†£', fontsize=9)
    question(page, y + 40, 2)
    pdf = save(doc, tmp_path)

    exam = extract_exam(from_manifest(manifest([1, 2]), pdf), pdf, tmp_path / 'assets')
    issues = {q['content']['number']: q['content']['layout']['extraction']['issues'] for q in exam['questions']}
    assert any(i['code'] == 'garbled_text' and i['severity'] == 'error' for i in issues[1])
    assert not any(i['code'] == 'garbled_text' for i in issues[2])
