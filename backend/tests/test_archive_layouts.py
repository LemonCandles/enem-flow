from scripts.archive_enem import parse_year


def test_archive_accepts_spaced_accessibility_headings(tmp_path):
    import pymupdf as fitz
    from scripts.build_bank import boundaries
    path=tmp_path/'ledor.pdf'
    with fitz.open() as doc:
        page=doc.new_page();page.insert_text((30,80),'Q U E S T Ã O 1 3 6');page.insert_text((30,110),'Texto selecionavel da questao.');doc.save(path)
    with fitz.open(path) as doc:heads,_=boundaries(doc,2025)
    assert [h['number'] for h in heads]==[136]

    combined='<div id="parent-fieldname-text"><p class="callout">1º Dia – Caderno 1 – Azul</p><a href="https://download.inep.gov.br/2016_CH_CN.pdf">Prova</a></div>'
    assert parse_year(combined,2016,'https://www.gov.br/exemplo')[0]['section'] is None
