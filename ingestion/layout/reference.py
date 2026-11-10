"""Referência rotulada (`layout-types-reference-v1`) e catálogo (`layout-types-v1`) dos tipos de layout.

O rótulo automático vem da assinatura do adaptador e só vale para questão elegível (os dois canais
concordam e nenhuma invariante falha). As demais recebem a decisão manual registrada no arquivo de
decisões, com justificativa; uma decisão só vale para o conteúdo e a fonte exatos em que foi tomada.
"""

from collections import Counter, defaultdict

from . import types

REFERENCE_VERSION = 'layout-types-reference-v1'
DECISIONS_VERSION = 'layout-types-decisions-v1'
DECISIONS = {
    'tipo-legitimo': 'A assinatura do adaptador está correta; a questão não é elegível por outro motivo.',
    'correcao-manual': 'A assinatura do adaptador está errada; a assinatura registrada vem da leitura do caderno.',
}
FIELDS = {'question_id', 'source_sha256', 'content_sha256', 'observed_signature', 'signature', 'decision'}
POLICY = (
    'Rótulo automático só para questão elegível ao adaptador; demais por decisão manual justificada. '
    'Rótulos técnicos, sem segunda revisão independente. O tipo descreve o layout impresso no caderno, '
    'mesmo quando o JSON de conteúdo ainda não o reproduz.'
)
FUSION = (
    'Duas assinaturas viram um tipo quando diferem só por algo que não muda a apresentação: repetição '
    'imediata de um bloco ou de um par de blocos (P Cr P Cr P = P Cr P), numeração de linhas e blocos lado a '
    'lado, que passam a marcas. A assinatura exata continua guardada por questão.'
)


class LabelError(ValueError):
    """A referência não cumpre o critério de saída: questão sem tipo, decisão inválida ou desatualizada."""


def validate_decisions(data):
    if data.get('version') != DECISIONS_VERSION:
        raise LabelError(f'Arquivo de decisões precisa ser {DECISIONS_VERSION}.')
    seen = set()
    for decision in data['decisions']:
        key = decision.get('question_id')
        if not FIELDS <= decision.keys():
            raise LabelError(f'{key}: decisão sem {sorted(FIELDS - decision.keys())}.')
        if key in seen:
            raise LabelError(f'{key}: decisão duplicada.')
        seen.add(key)
        if decision['decision'] not in DECISIONS:
            raise LabelError(f'{key}: tipo de decisão desconhecido {decision["decision"]!r}.')
        if len(decision.get('justification', '').strip()) < 20:
            raise LabelError(f'{key}: decisão manual sem justificativa.')
        if decision['decision'] == 'tipo-legitimo' and decision['signature'] != decision['observed_signature']:
            raise LabelError(f'{key}: tipo legítimo confirma a assinatura observada; para mudá-la use correção.')
        types.axes(decision['signature'])
    return {d['question_id']: d for d in data['decisions']}


def label(rows, decisions):
    """Itens da referência; falha se alguma questão ficar sem tipo ou alguma decisão não se aplicar."""
    pending = validate_decisions(decisions)
    items, problems = [], []
    for row in rows:
        decision = pending.pop(row['question_id'], None)
        if decision and (
            decision['content_sha256'] != row['content_sha256'] or decision['source_sha256'] != row['source_sha256']
        ):
            problems.append(f'{row["question_id"]}: conteúdo ou fonte mudou desde a decisão manual; revise-a.')
            continue
        if decision:
            signature = decision['signature']
            provenance = {
                'origin': 'manual',
                'decision': decision['decision'],
                'justification': decision['justification'],
                'observed_signature': decision['observed_signature'],
                'independent_review': False,
            }
            if decision['observed_signature'] != row['signature']:
                provenance['adapter_signature_changed'] = True
        elif row['eligible']:
            signature, provenance = row['signature'], {'origin': 'automatic', 'independent_review': False}
        else:
            problems.append(f'{row["question_id"]}: não elegível ({row["signature"]}) e sem decisão manual.')
            continue
        value = types.axes(signature)
        items.append(
            {
                'question_id': row['question_id'],
                'exam': row['exam'],
                'number': row['number'],
                'occurrences': row['occurrence_ids'],
                'type': types.identifier(types.labels(value)),
                'signature': signature,
                'adapter_signature': row['signature'],
                'axes': types.labels(value),
                'eligible': row['eligible'],
                'blocking_issues': sorted({i['code'] for i in row['issues'] if i['severity'] == 'error'}),
                'content_form': row['content_form'],
                'support_group': row['support_group'],
                'figures': row['figures'],
                'source_sha256': row['source_sha256'],
                'content_sha256': row['content_sha256'],
                'adapter': row['adapter'],
                'provenance': provenance,
            }
        )
    problems += [f'{key}: decisão manual para questão fora das provas analisadas.' for key in sorted(pending)]
    if problems:
        raise LabelError('Referência incompleta:\n- ' + '\n- '.join(problems))
    return sorted(items, key=lambda item: (item['exam'], item['number']))


def reference(items, sources, adapter, decisions_sha256):
    origins = Counter(item['provenance']['origin'] for item in items)
    return {
        'version': REFERENCE_VERSION,
        'catalog_version': types.VERSION,
        'adapter': adapter,
        'policy': POLICY,
        'decisions_sha256': decisions_sha256,
        'sources': sources,
        'counts': {
            'questions': len(items),
            'occurrences': sum(len(item['occurrences']) for item in items),
            'types': len({item['type'] for item in items}),
            'automatic': origins['automatic'],
            'manual': origins['manual'],
            'single_image_content': sum(item['content_form'] == 'imagem-unica' for item in items),
        },
        'items': items,
    }


def catalog(items, adapter):
    """Catálogo fechado: cada tipo com eixos, descrição, assinaturas abrangidas e contagens."""
    grouped = defaultdict(list)
    for item in items:
        grouped[item['type']].append(item)
    entries = []
    for type_id, members in grouped.items():
        value = types.parse_identifier(type_id)
        reasons = types.unrepresentable(value)
        origins = Counter(member['provenance']['origin'] for member in members)
        entries.append(
            {
                'id': type_id,
                'axes': value,
                'labels': types.labels(value),
                'description': types.description(value),
                'signatures': dict(sorted(Counter(member['signature'] for member in members).items())),
                'questions': len(members),
                'automatic': origins['automatic'],
                'manual': origins['manual'],
                'representable': not reasons,
                'reasons': reasons,
            }
        )
    entries.sort(key=lambda entry: (-entry['questions'], entry['id']))
    return {
        'version': types.VERSION,
        'reference': REFERENCE_VERSION,
        'adapter': adapter,
        'axes': {
            'corpo': {token: types.BODY_PT[token] for token in types.BODY},
            'alternativas': types.ALTERNATIVES,
            'marcas': types.MARKS,
        },
        'fusion_rule': FUSION,
        'representable_policy': 'Representável: o contrato de conteúdo atual já tem os elementos do tipo.',
        'counts': {
            'types': len(entries),
            'questions': len(items),
            'representable_types': sum(entry['representable'] for entry in entries),
            'single_question_types': sum(entry['questions'] == 1 for entry in entries),
        },
        'types': entries,
    }
