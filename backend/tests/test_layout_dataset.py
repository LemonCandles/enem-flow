"""Conjunto da rede de tipos de layout: rótulos fracos, partições sem vazamento e catálogo v2."""

from layout_dataset import catalog_v2, split, weak_label

from experiments.common import read_json
from ingestion.layout import types


def row(number, signature='P Cr P ALT:texto', eligible=True, canonical=None, text=None, support=None):
    labels, _ = weak_label({'eligible': eligible, 'signature': signature})
    return {
        'number': number,
        'signature': signature,
        'eligible': eligible,
        'axes': labels,
        'type': types.identifier(labels) if labels else None,
        'canonical_id': canonical or f'c{number}',
        'text_sha256': text or f't{number}',
        'support_group': support,
    }


def test_weak_labels_only_for_eligible_questions_with_known_signatures():
    assert weak_label({'eligible': True, 'signature': 'P F+Cr P ALT:texto'})[0]['corpo'] == 'texto-figura+credito-texto'
    assert weak_label({'eligible': False, 'signature': 'P ALT:texto'}) == (None, 'nao-elegivel')
    assert weak_label({'eligible': True, 'signature': 'P T|N P ALT:texto'}) == (None, 'assinatura-desconhecida')


def test_split_keeps_identity_text_and_shared_support_groups_together():
    rows = [row(i) for i in range(60)]
    rows += [row(100, canonical='c1'), row(101, text='t2'), row(102, support='apoio'), row(103, support='apoio')]
    rows += [row(200, eligible=False)]
    split(rows, 'semente', 0.15)
    by_group = {}
    for item in rows:
        by_group.setdefault(item['split_group'], set()).add(item['split'])
    assert all(len(splits) == 1 for splits in by_group.values())
    assert {r['split'] for r in rows if r['number'] in (1, 100)} == {rows[1]['split']}
    assert rows[-1]['split'] == 'unlabeled'
    assert {'train', 'development'} <= {r['split'] for r in rows}
    again = [dict(r) for r in rows]
    split(again, 'semente', 0.15)
    assert [r['split'] for r in again] == [r['split'] for r in rows]


def test_catalog_v2_extends_v1_only_with_supported_archive_types():
    reference = read_json('data/datasets/layout-types-reference-v1.json')
    archive = [row(i, 'P T P F P ALT:texto') for i in range(25)] + [row(100 + i, 'T P ALT:texto') for i in range(3)]
    catalog = catalog_v2(archive, reference, 20)
    ids = {entry['id']: entry for entry in catalog['types']}
    v1 = {entry['id'] for entry in read_json('data/catalog/layout-types.json')['types']}
    assert v1 <= set(ids)
    assert ids['texto-tabela-texto-figura-texto.alt-texto']['origin'] == 'acervo'
    assert ids['texto-tabela-texto-figura-texto.alt-texto']['review'] == 'pendente'
    assert 'tabela-texto.alt-texto' not in ids
    assert catalog['counts']['archive_outside_catalog'] == 3
