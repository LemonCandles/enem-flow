"""Tutor in practice: approved material, help requests and material generation.

Help exists only in practice sessions and only from approved material for the exact content
of the item. Material comes from a curator or from the provider; provider material is approved
automatically when it passes the rules in `generate_material`, without human review. The provider may rephrase that material for the student; when
it is not configured, fails, exceeds a limit or answers outside the rules, the approved
text itself is delivered. Without approved material there is no help and the practice
keeps its current presentation. Every request is recorded; only delivered help counts.
"""

from dataclasses import replace
import hashlib
import json
import re
import time
import unicodedata

from sqlalchemy import func, or_, select

from ..core.config import tutor_settings
from ..models import Exam, HelpEvent, QuestionVersion, Review, TutorMaterial
from ..schemas import QuestionContent
from . import attempts, tutor_provider
from .attempts import PRACTICE
from .errors import Conflict, InvalidContent, NotFound, Unavailable
from .presentation import readable_content
from .service_account import service_reviewer

LEVELS = ('orientation', 'hint', 'solution')
LEVEL_NAMES = {'orientation': 'Orientação', 'hint': 'Pista', 'solution': 'Resolução'}
MAX_LEVEL_TEXT = 3000
MAX_MESSAGE = 1500


def material_fingerprint(content):
    """What the material depends on: text, figures, alternatives and answer key; not labels or layout."""
    data = QuestionContent.model_validate(content).model_dump()
    relevant = {k: data[k] for k in ('statement', 'blocks', 'images', 'alternatives', 'correct_answer', 'annulled')}
    return hashlib.sha256(
        json.dumps(relevant, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()


def plain(text):
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9$\\{}^_=+\-*/., ]', ' ', text)).strip(' .')


def reveals_answer(text, content):
    """Whether a text below the solution level points to the answer of the item."""
    letter = content.get('correct_answer')
    if not letter or content.get('annulled'):
        return False
    # Letters of alternatives are capitals ("alternativa C"); the article "a" is not.
    named = (
        r'(?i:\b(?:alternativas?|letra|op[çc][ãa]o|resposta|item|gabarito)\b)'
        r'\s*(?i:corretas?\s*)?(?i:(?:[ée]|seria|:|-)\s*)?(?i:a\s+)?(?i:letra\s+)?'
        rf'\(?{letter}\)?(?![A-Za-zÀ-ÿ0-9])'
    )
    if re.search(named, text or ''):
        return True
    correct = plain(next((a['text'] for a in content['alternatives'] if a['letter'] == letter), ''))
    return len(correct) >= 15 and correct in plain(text)


def question_text(content):
    """The question as plain text for the provider: statement, tables, formulas and figure descriptions."""
    parts = []
    for block in content.get('blocks') or []:
        if block['type'] == 'paragraph':
            parts.append(block['text'])
        elif block['type'] == 'math':
            parts.append(f'$${block["tex"]}$$')
        elif block['type'] == 'table':
            rows = [block['headers'], *block['rows']]
            parts.append('Tabela: ' + ' / '.join(' | '.join(row) for row in rows))
        elif block['type'] == 'image':
            described = ' '.join(x for x in (block.get('caption'), block['asset'].get('alt')) if x)
            parts.append(f'[Figura: {described}]')
    if not parts:
        parts.append(content.get('statement') or '')
    alternatives = '\n'.join(
        f'{a["letter"]}) {a["text"] or "[alternativa em figura]"}' for a in content['alternatives']
    )
    return '\n\n'.join(parts) + '\n\nAlternativas:\n' + alternatives


def validate_levels(levels, content):
    """Material approval rules, independent of who wrote it."""
    if set(levels) != set(LEVELS):
        raise InvalidContent('Informe orientação, pista e resolução.')
    for level in LEVELS:
        text = levels[level]
        if not isinstance(text, str) or not text.strip():
            raise InvalidContent(f'{LEVEL_NAMES[level]} está vazia.')
        if len(text) > MAX_LEVEL_TEXT:
            raise InvalidContent(f'{LEVEL_NAMES[level]} excede {MAX_LEVEL_TEXT} caracteres.')
    for level in ('orientation', 'hint'):
        if reveals_answer(levels[level], content):
            raise InvalidContent(f'{LEVEL_NAMES[level]} revela o gabarito; reserve a resposta para a resolução.')


# ---- material lookup ----


def approved_material(db, item):
    fingerprint = material_fingerprint(item['content'])
    canonical = item.get('canonical_id')
    owners = [TutorMaterial.question_id == item['question_id']]
    if canonical:
        owners.append(TutorMaterial.canonical_id == canonical)
    return db.scalar(
        select(TutorMaterial)
        .where(TutorMaterial.status == 'approved', TutorMaterial.content_sha256 == fingerprint, or_(*owners))
        .order_by(TutorMaterial.reviewed_at.desc())
        .limit(1)
    )


def delivered_events(db, session_id):
    return list(
        db.scalars(
            select(HelpEvent)
            .where(HelpEvent.session_id == session_id, HelpEvent.outcome == 'delivered')
            .order_by(HelpEvent.delivered_at)
        )
    )


def event_data(event):
    return {
        'id': event.id,
        'session_id': event.session_id,
        'item_id': event.item_id,
        'content_version': event.content_version,
        'level': event.level,
        'outcome': event.outcome,
        'mode': event.mode,
        'message': event.message,
        'material_id': event.material_id,
        'requested_at': event.requested_at,
        'delivered_at': event.delivered_at,
        'provider': event.provider,
    }


def help_state(db, session):
    """Per item: whether help exists and what this student already received."""
    events = delivered_events(db, session.id)
    finished = session.finished_at is not None
    state = {}
    for item in session.items:
        received = [e for e in events if e.item_id == item['id']]
        levels = [e.level for e in received]
        upcoming = next((level for level in LEVELS if level not in levels), None)
        available = not finished and approved_material(db, item) is not None
        state[item['id']] = {
            'available': available,
            'next_level': upcoming if available else None,
            'delivered': [
                {'level': e.level, 'message': e.message, 'mode': e.mode, 'delivered_at': e.delivered_at}
                for e in received
            ],
        }
    return state


# ---- help request ----


def request_help(db, user_id, session_id, item_id, level, key, settings=None, complete=None):
    """Idempotent help: a repeated key or an already delivered level never calls the provider again."""
    if level not in LEVELS:
        raise InvalidContent('Nível de ajuda desconhecido.')
    session = attempts.owned(db, PRACTICE, session_id, user_id, lock=True)
    event = db.scalar(select(HelpEvent).where(HelpEvent.user_id == user_id, HelpEvent.request_key == key))
    if event is not None:
        if (event.session_id, event.item_id, event.level) != (session.id, item_id, level):
            raise Conflict('Esta chave já foi usada para outro pedido de ajuda.')
        if event.outcome == 'delivered':
            return event
    if session.finished_at is not None:
        raise Conflict('Esta prática já foi finalizada; a ajuda fica disponível durante a resolução.')
    item = next((i for i in session.items if i['id'] == item_id), None)
    if item is None:
        raise NotFound(PRACTICE.foreign_item)
    delivered = {e.level: e for e in delivered_events(db, session.id) if e.item_id == item_id}
    if level in delivered:
        return delivered[level]
    previous = LEVELS[: LEVELS.index(level)]
    if any(p not in delivered for p in previous):
        raise Conflict('Peça os níveis de ajuda em ordem: orientação, pista e resolução.')
    material = approved_material(db, item)
    if material is None:
        raise NotFound('Ainda não há material de ajuda aprovado para esta questão.')
    if event is None:
        event = HelpEvent(
            user_id=user_id,
            session_id=session.id,
            item_id=item_id,
            content_version=item['version'],
            level=level,
            request_key=key,
            material_id=material.id,
            outcome='requested',
            provider={},
        )
        db.add(event)
    # The request is recorded before the provider is called, and the attempt lock is released:
    # a call that never returns stays "requested" and does not count as help.
    db.commit()
    message, mode, provider = deliver(db, user_id, item, level, material, settings, complete)
    event.message, event.mode, event.provider = message, mode, provider
    event.outcome, event.delivered_at = 'delivered', time.time()
    db.flush()
    return event


def help_messages(item, level, material):
    """Only the material allowed at this level reaches the provider; lower levels never carry the answer."""
    content = readable_content(item['question_id'], item['content'])
    allowed = LEVELS[: LEVELS.index(level) + 1]
    material_text = '\n\n'.join(f'{LEVEL_NAMES[name]} aprovada:\n{material.levels[name]}' for name in allowed)
    rules = {
        'orientation': 'Ajude o aluno a entender o que a questão pede e qual conceito usar. Não indique alternativa.',
        'hint': 'Dê uma pista sobre o próximo passo do raciocínio. Não indique a alternativa correta nem a elimine por completo.',
        'solution': 'Explique a resolução passo a passo e indique a alternativa correta, seguindo o material.',
    }[level]
    system = (
        'Você é o tutor do Enem Flow, uma plataforma de estudos para o ENEM. Responda em português do Brasil, '
        'com no máximo 120 palavras, de forma acolhedora e direta. Use somente o material aprovado como fonte: '
        'não acrescente fatos, números ou resoluções que não estejam nele. Fórmulas em LaTeX entre $...$. '
        f'{rules} Responda apenas com JSON no formato {{"mensagem": "..."}}.'
    )
    user = f'Questão:\n{question_text(content)}\n\n{material_text}\n\nNível pedido: {LEVEL_NAMES[level]}.'
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]


def deliver(db, user_id, item, level, material, settings=None, complete=None):
    """The provider's message when it follows the rules; otherwise the approved text."""
    settings = settings or tutor_settings()
    complete = complete or tutor_provider.complete_json
    fallback = material.levels[level]
    record = {
        'prompt_version': tutor_provider.PROMPT_VERSION,
        'tools': list(tutor_provider.TOOLS),
        'model': settings.model or None,
        'base_url': settings.base_url,
    }
    if not settings.enabled:
        return fallback, 'material', {**record, 'status': 'disabled', 'missing': settings.missing}
    since = time.time() - 86400
    used = db.scalar(
        select(func.count())
        .select_from(HelpEvent)
        .where(HelpEvent.user_id == user_id, HelpEvent.mode == 'tutor', HelpEvent.delivered_at >= since)
    )
    if used >= settings.daily_limit:
        return fallback, 'material', {**record, 'status': 'daily_limit'}
    messages = help_messages(item, level, material)
    estimate = tutor_provider.maximum_cost(settings, messages)
    if estimate > settings.max_cost_usd:
        return fallback, 'material', {**record, 'status': 'cost_limit', 'estimated_cost_usd': estimate}
    result = complete(settings, messages)
    record.update(
        status=result.status,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=tutor_provider.cost_usd(settings, result.input_tokens, result.output_tokens),
    )
    if result.error:
        record['error'] = result.error
    if result.status != 'ok':
        return fallback, 'material', record
    message = result.data.get('mensagem')
    content = readable_content(item['question_id'], item['content'])
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE:
        record.update(status='invalid', error='Mensagem ausente ou longa demais.')
        return fallback, 'material', record
    if level != 'solution' and reveals_answer(message, content):
        record.update(status='invalid', error='A mensagem revelava o gabarito antes da resolução.')
        return fallback, 'material', record
    return message.strip(), 'tutor', record


def my_help_events(db, user_id):
    return [
        event_data(e)
        for e in db.scalars(select(HelpEvent).where(HelpEvent.user_id == user_id).order_by(HelpEvent.requested_at))
    ]


# ---- curation ----


def material_data(material, current_fingerprint=None):
    return {
        'id': material.id,
        'question_id': material.question_id,
        'canonical_id': material.canonical_id,
        'version': material.version,
        'status': material.status,
        'origin': material.origin,
        'levels': material.levels,
        'provenance': material.provenance,
        'created_at': material.created_at,
        'reviewed_at': material.reviewed_at,
        'review_reason': material.review_reason,
        'current': current_fingerprint is not None and material.content_sha256 == current_fingerprint,
    }


def question_or_404(db, version_id):
    question = db.get(QuestionVersion, version_id)
    if question is None:
        raise NotFound('Versão da questão não encontrada.')
    return question


def materials_of(db, question):
    fingerprint = material_fingerprint(question.content)
    rows = db.scalars(
        select(TutorMaterial).where(TutorMaterial.question_id == question.question_id).order_by(TutorMaterial.version)
    )
    return [material_data(m, fingerprint) for m in rows]


def material_status(db, question):
    """Summary for the curation list: approved, proposal, outdated or none."""
    fingerprint = material_fingerprint(question.content)
    rows = list(db.scalars(select(TutorMaterial).where(TutorMaterial.question_id == question.question_id)))
    current = [m for m in rows if m.content_sha256 == fingerprint]
    if any(m.status == 'approved' for m in current):
        return 'approved'
    if any(m.status == 'proposal' for m in current):
        return 'proposal'
    return 'outdated' if rows else 'none'


def add_material(db, question, levels, user_id, origin='human', provenance=None):
    content = readable_content(question.question_id, question.content)
    clean = {level: (levels.get(level) or '').strip() for level in LEVELS}
    if origin == 'human':
        validate_levels(clean, content)
    number = (
        db.scalar(select(func.max(TutorMaterial.version)).where(TutorMaterial.question_id == question.question_id)) or 0
    ) + 1
    material = TutorMaterial(
        question_id=question.question_id,
        canonical_id=question.canonical_id,
        content_sha256=material_fingerprint(question.content),
        version=number,
        status='proposal',
        origin=origin,
        levels=clean,
        provenance=provenance or {},
        created_by=user_id,
    )
    db.add(material)
    db.flush()
    return material


# Three levels of about 150 words each do not fit the limit of a single help message.
DRAFT_OUTPUT_TOKENS = 1500
AUTO_APPROVAL = (
    'Aprovação automática por decisão da equipe (sem revisão humana): níveis completos, orientação e pista '
    'sem o gabarito, resolução coerente com o gabarito oficial.'
)


def generate_material(db, question, settings=None, complete=None):
    """Material written by the provider and approved by the automatic rules, without human review.

    The rules: all levels present, orientation and hint without the answer, and the solution
    pointing to the official answer. Anything else raises Unavailable and leaves no material.
    """
    settings = settings or tutor_settings()
    complete = complete or tutor_provider.complete_json
    if not settings.enabled:
        raise Unavailable('Configure o provedor no .env antes de gerar material: ' + ', '.join(settings.missing) + '.')
    content = readable_content(question.question_id, question.content)
    if content['annulled']:
        raise InvalidContent('Questão anulada: não há gabarito para a resolução.')
    settings = replace(settings, max_output_tokens=max(settings.max_output_tokens, DRAFT_OUTPUT_TOKENS))
    messages = [
        {
            'role': 'system',
            'content': (
                'Você prepara material de tutoria para questões do ENEM. Escreva em português do Brasil, '
                'com fórmulas em LaTeX entre $...$. Produza três níveis: '
                '"orientacao" (o que a questão pede e qual conceito usar, sem indicar alternativa), '
                '"pista" (o próximo passo do raciocínio, sem citar letra de alternativa nem o texto da correta) '
                'e "resolucao" (passo a passo, terminando com a frase "Alternativa X." com a letra do gabarito). '
                'Até 150 palavras por nível. Se a questão depender de uma figura sem descrição, oriente a leitura '
                'da figura sem inventar valores que não estejam no texto. '
                'Responda apenas com JSON: {"orientacao": "...", "pista": "...", "resolucao": "..."}.'
            ),
        },
        {
            'role': 'user',
            'content': f'Questão:\n{question_text(content)}\n\nGabarito oficial: {content["correct_answer"]}.',
        },
    ]
    estimate = tutor_provider.maximum_cost(settings, messages)
    if estimate > settings.max_cost_usd:
        raise Unavailable('O custo estimado do material excede TUTOR_MAX_COST_USD.')
    result = complete(settings, messages)
    if result.status != 'ok':
        raise Unavailable(f'O provedor não gerou o material ({result.error or result.status}).')
    levels = {
        'orientation': result.data.get('orientacao'),
        'hint': result.data.get('pista'),
        'solution': result.data.get('resolucao'),
    }
    if not all(isinstance(v, str) and v.strip() for v in levels.values()):
        raise Unavailable('O provedor respondeu fora do formato combinado.')
    levels = {k: v.strip() for k, v in levels.items()}
    try:
        validate_levels(levels, content)
    except InvalidContent as error:
        raise Unavailable(f'Material recusado pelas regras automáticas: {error.detail}')
    if not reveals_answer(levels['solution'], content):
        raise Unavailable('Material recusado pelas regras automáticas: a resolução não chega ao gabarito oficial.')
    provenance = {
        'prompt_version': tutor_provider.DRAFT_PROMPT_VERSION,
        'model': settings.model,
        'base_url': settings.base_url,
        'latency_ms': result.latency_ms,
        'input_tokens': result.input_tokens,
        'output_tokens': result.output_tokens,
        'cost_usd': tutor_provider.cost_usd(settings, result.input_tokens, result.output_tokens),
        'source_version': question.id,
        'approval': 'automatic',
    }
    reviewer = service_reviewer(db)
    material = add_material(db, question, levels, reviewer.id, origin='llm', provenance=provenance)
    supersede(db, material)
    material.status = 'approved'
    material.reviewed_by, material.reviewed_at, material.review_reason = reviewer.id, time.time(), AUTO_APPROVAL
    db.add(Review(user_id=reviewer.id, target_id=material.id, action='tutor_approve', reason=AUTO_APPROVAL))
    db.flush()
    return material


def supersede(db, material):
    for previous in db.scalars(
        select(TutorMaterial).where(
            TutorMaterial.question_id == material.question_id,
            TutorMaterial.content_sha256 == material.content_sha256,
            TutorMaterial.status == 'approved',
            TutorMaterial.id != material.id,
        )
    ):
        previous.status = 'superseded'


def pending_items(db, exam_id=None):
    """Published questions without approved material for their current content, one per identity."""
    seen, pending = set(), []
    query = select(Exam).where(Exam.status == 'published').order_by(Exam.id)
    if exam_id:
        query = query.where(Exam.id == exam_id)
    for exam in db.scalars(query):
        for key in exam.items:
            question = db.get(QuestionVersion, key)
            item = {
                'id': question.id,
                'question_id': question.question_id,
                'canonical_id': question.canonical_id,
                'content': question.content,
            }
            identity = (question.canonical_id or question.question_id, material_fingerprint(question.content))
            if identity in seen or question.content['annulled']:
                continue
            seen.add(identity)
            if approved_material(db, item) is None:
                pending.append(question)
    return pending


def generate_all(db, exam_id=None, limit=None, pause=2.0, settings=None, complete=None, log=print, sleep=time.sleep):
    """Material for every published question, committed one by one so an interruption keeps the progress.

    Rate limits wait and retry; repeated failures stop the run, which can be resumed later.
    """
    pending = pending_items(db, exam_id)
    if limit is not None:
        pending = pending[:limit]
    log(f'{len(pending)} questões sem material aprovado.')
    done, failed, consecutive = 0, [], 0
    for position, question in enumerate(pending, 1):
        for attempt in range(4):
            try:
                generate_material(db, question, settings, complete)
                db.commit()
                done, consecutive = done + 1, 0
                log(f'[{position}/{len(pending)}] {question.id}: aprovado')
                break
            except Unavailable as error:
                db.rollback()
                limited = any(word in error.detail for word in ('RateLimit', 'Timeout', 'Tempo limite', 'Connection'))
                if limited and attempt < 3:
                    wait = pause * 10 * (attempt + 1)
                    log(
                        f'[{position}/{len(pending)}] {question.id}: limite do provedor, nova tentativa em {wait:.0f} s'
                    )
                    sleep(wait)
                    continue
                if 'regras automáticas' in error.detail and attempt < 1:
                    continue  # A second answer of the provider may follow the rules.
                failed.append({'id': question.id, 'reason': error.detail})
                consecutive += 1
                log(f'[{position}/{len(pending)}] {question.id}: sem material ({error.detail})')
                break
        if consecutive >= 5:
            log('Cinco falhas seguidas: execução interrompida. Rode o comando de novo para continuar.')
            break
        sleep(pause)
    return {'approved': done, 'failed': failed, 'remaining': len(pending_items(db, exam_id))}


def review_material(db, material_id, action, reason, user_id):
    """Approval checks the content again: the question may have changed since the proposal."""
    material = db.get(TutorMaterial, material_id)
    if material is None:
        raise NotFound('Material não encontrado.')
    if material.status != 'proposal':
        raise Conflict('Somente propostas podem ser revisadas.')
    if action == 'approve':
        published = db.scalars(
            select(QuestionVersion).where(
                QuestionVersion.question_id == material.question_id, QuestionVersion.status == 'approved'
            )
        )
        current = next((q for q in published if material_fingerprint(q.content) == material.content_sha256), None)
        if current is None:
            raise Conflict('O conteúdo da questão mudou desde a proposta; gere ou escreva um novo material.')
        validate_levels(material.levels, readable_content(current.question_id, current.content))
        supersede(db, material)
        material.status = 'approved'
    elif action == 'reject':
        material.status = 'rejected'
    else:
        raise InvalidContent('Ação desconhecida.')
    material.reviewed_by, material.reviewed_at, material.review_reason = user_id, time.time(), reason
    db.add(Review(user_id=user_id, target_id=material.id, action=f'tutor_{action}', reason=reason))
    db.flush()
    return material
