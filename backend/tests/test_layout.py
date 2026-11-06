"""Layout proposals: the versioned adapter, its refusals and the reviewed draft it may create."""

import copy

import pytest

from backend.app.services.layout_adapter import ADAPTER_VERSION, version_fingerprint

FIGURE = '/assets/enem-2024-dia2-azul/native/q100-figure-1.png'


def block(id, order, type, text='', alternative=None, **extra):
    return {
        'id': id,
        'order': order,
        'type': type,
        'text': text,
        'alternative': alternative,
        'page': 2,
        'bbox': [40, 60 + 20 * order, 280, 75 + 20 * order],
        'group': f'option-{alternative}' if alternative else 'stem',
        **extra,
    }


def proposal(version, content, **changes):
    blocks = [
        block('b0', 0, 'paragraph', content['statement']),
        block('b1', 1, 'image', asset=FIGURE, alt='Figura de teste'),
        block('b2', 2, 'caption', 'Figura 1 — esquema de teste'),
        block('b3', 3, 'credit', 'Disponível em: https://example.com. Acesso em: 1 jan. 2024.'),
        block('b4', 4, 'math', 'x = \\dfrac{1}{2}'),
        *[
            block(f'b{5 + i}', 5 + i, 'alternative', f'{letter} Opção {letter}', letter)
            for i, letter in enumerate('ABCDE')
        ],
    ]
    data = {
        'schema_version': '1.0',
        'question_version': version,
        'source_sha256': 'a' * 64,
        'content_sha256': version_fingerprint(content),
        'regions': [{'page': 2, 'bbox': [30, 50, 300, 400]}],
        'blocks': blocks,
        'links': [
            {'source': 'b2', 'target': 'b1', 'relation': 'caption_of'},
            {'source': 'b3', 'target': 'b1', 'relation': 'credit_of'},
        ],
        'table_structures': [],
        'origin': {'method': 'geometry'},
        'review_status': 'proposed',
        'needs_review': True,
    }
    data.update(changes)
    return data


@pytest.fixture
def target(admin, published):
    exam = admin.get('/admin/exams/prova-teste').json()
    question = exam['items'][0]
    return question['id'], question['content']


def test_valid_proposal_is_converted_without_touching_published_content(admin, target):
    version, content = target
    response = admin.post('/admin/layout/proposals', json=proposal(version, content))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data['status'] == 'proposal' and data['adapter_version'] == ADAPTER_VERSION and not data['errors']
    blocks = data['converted']['blocks']
    assert [b['type'] for b in blocks] == ['paragraph', 'image', 'math']
    assert blocks[1]['caption'] == 'Figura 1 — esquema de teste' and blocks[1]['credit'].startswith('Disponível')
    assert [a['text'] for a in data['converted']['alternatives']] == [f'Opção {x}' for x in 'ABCDE']
    assert data['converted']['correct_answer'] == content['correct_answer']
    assert data['comparison']['missing_words'] == 0 and data['comparison']['preserved_ratio'] == 1
    assert data['comparison']['figures_before'] == 0 and data['comparison']['figures_after'] == 1
    current = admin.get('/admin/exams/prova-teste').json()
    assert current['status'] == 'published' and current['items'][0]['content'] == content


@pytest.mark.parametrize(
    'change, reason',
    [
        (lambda p: p.update(source_sha256='c' * 64), 'fonte da proposta difere'),
        (lambda p: p.update(content_sha256='d' * 64), 'outro conteúdo'),
        (lambda p: p['blocks'][1].update(asset='/assets/inexistente.png'), 'sem recurso'),
        (lambda p: p['links'].append({'source': 'b0', 'target': 'b1', 'relation': 'caption_of'}), 'Vínculo inválido'),
        (lambda p: p['blocks'][4].update(order=40), 'ordem de leitura'),
        (lambda p: p['blocks'].pop(), 'de A a E'),
        (lambda p: p['blocks'][4].update(text='x = \\dfrac{1}{2'), 'LaTeX'),
    ],
)
def test_refused_proposals_keep_their_reasons(admin, target, change, reason):
    version, content = target
    data = proposal(version, content)
    change(data)
    response = admin.post('/admin/layout/proposals', json=data)
    assert response.status_code == 201
    assert response.json()['status'] == 'invalid'
    assert any(reason in error for error in response.json()['errors']), response.json()['errors']
    assert admin.get(f'/admin/layout/questions/{version}').json()['proposals'][0]['status'] == 'invalid'


def test_alternative_figures_cannot_disappear(admin, published, database):
    from backend.app.models import QuestionVersion

    exam = admin.get('/admin/exams/prova-teste').json()
    version = exam['items'][1]
    with database.begin() as db:
        stored = db.get(QuestionVersion, version['id'])
        content = copy.deepcopy(stored.content)
        content['alternatives'][0]['image'] = {'path': FIGURE, 'alt': 'Gráfico A'}
        stored.content = content
    data = proposal(version['id'], content)
    response = admin.post('/admin/layout/proposals', json=data).json()
    assert response['status'] == 'invalid'
    assert any('alternativa A tem figura' in error for error in response['errors'])


def test_approval_requires_comparison_and_creates_a_reviewed_draft(admin, student, target):
    version, content = target
    run = student.post('/exam-runs', json={'exam_id': 'prova-teste', 'idempotency_key': 'layout-run-0001'}).json()
    created = admin.post('/admin/layout/proposals', json=proposal(version, content)).json()
    path = f"/admin/layout/proposals/{created['id']}/review"
    reason = {'action': 'approve', 'reason': 'Conferido com a página 2 do original'}
    refused = admin.post(path, json=reason)
    assert refused.status_code == 422 and 'Compare a proposta' in refused.json()['detail']
    approved = admin.post(path, json={**reason, 'compared_with_source': True})
    assert approved.status_code == 200, approved.text
    result = approved.json()
    assert result['status'] == 'approved' and result['result_version_id'].endswith(':2')
    exam = admin.get('/admin/exams/prova-teste').json()
    assert exam['status'] == 'in_review'
    draft = next(q for q in exam['items'] if q['id'] == result['result_version_id'])
    assert draft['status'] == 'draft' and draft['content']['layout']['adapter']['version'] == ADAPTER_VERSION
    assert [b['type'] for b in draft['content']['blocks']] == ['paragraph', 'image', 'math']
    # The open attempt keeps the snapshot it started with.
    assert student.get(f"/exam-runs/{run['id']}").json()['items'][0]['id'] == version
    assert admin.post(path, json={**reason, 'compared_with_source': True}).status_code == 409
    audit = admin.get('/admin/audit').json()
    assert {'layout', 'layout_approve'} <= {row['action'] for row in audit}


def test_outdated_proposal_cannot_be_approved(admin, target):
    version, content = target
    created = admin.post('/admin/layout/proposals', json=proposal(version, content)).json()
    edited = dict(content, statement=content['statement'] + ' Corrigida.')
    assert (
        admin.put(f'/admin/questions/{version}', json={'content': edited, 'reason': 'Correção manual do enunciado'})
    ).status_code == 200
    response = admin.post(
        f"/admin/layout/proposals/{created['id']}/review",
        json={'action': 'approve', 'reason': 'Tentativa de aprovar proposta antiga', 'compared_with_source': True},
    )
    assert response.status_code == 409


def test_rejection_keeps_the_published_blocks(admin, target):
    version, content = target
    created = admin.post('/admin/layout/proposals', json=proposal(version, content)).json()
    response = admin.post(
        f"/admin/layout/proposals/{created['id']}/review",
        json={'action': 'reject', 'reason': 'Ordem diferente da página original'},
    )
    assert response.json()['status'] == 'rejected'
    assert admin.get('/admin/exams/prova-teste').json()['items'][0]['content'] == content
