"""Versioned selection of practice questions: reinforcement, review and exploration.

The policies are pure functions over the pool, the student's evidence and the exposure
of each item, so the API and the offline comparison run exactly the same code. Weights
are experiment parameters, not validated values. Evidence is read from finished
attempts only; nothing here estimates proficiency or a TRI score.
"""

from collections import Counter
from dataclasses import dataclass, field
import math
import random

from .diagnostics import identity
from .knowledge import ESTIMATOR, groups_for

ADAPTIVE_V1 = {
    'version': 'adaptive-v1',
    'weights': {
        'reforco': 1.0,
        'revisao': 0.6,
        'exploracao': 0.8,
        'exposicao': 0.5,
        'concentracao': 0.5,
        'dificuldade': 0.1,
    },
    'minimum_evidence': ESTIMATOR['minimum_evidence'],
    'reinforcement_below': 0.6,
    'review_after_days': 14,
    'max_item_exposures': 2,
    'max_theme_share': 0.5,
    'difficulty_min_responses': 5,
    'difficulty_target': 0.6,
    'difficulty_min_success': 0.15,
    'logged_candidates': 25,
}
MAX_ITEMS = 20
FUNCTIONS = ('reforco', 'revisao', 'exploracao')


@dataclass(frozen=True)
class PolicyInput:
    pool: list
    state: dict
    exposures: Counter
    minutes: int
    seed: str
    now: float
    difficulty: dict = field(default_factory=dict)


def requested_items(minutes):
    return min(MAX_ITEMS, minutes // 3)


def evidence_by_group(state):
    """Index the rows of the student state by the same keys used for an item's labels."""
    rows = {}
    for row in state.get('themes', []):
        rows[('theme', row['area'], row['discipline'], row['taxonomy_version'], row['name'])] = row
    for row in state.get('skills', []):
        rows[('skill', row['area'], None, 'official-enem', row['name'])] = row
    return rows


def item_groups(item):
    content = item['content']
    return groups_for(content['area'], content['labels'])


def hits(correct):
    return '1 acerto' if correct == 1 else f'{correct} acertos'


def group_need(key, row, now, params):
    """What a theme or skill asks for now: its function, urgency from 0 to 1, and the reason."""
    label = 'habilidade' if key[0] == 'skill' else 'tema'
    name = key[-1]
    attempts = row['independent_attempts'] if row else 0
    correct = row['independent_correct'] if row else 0
    minimum = params['minimum_evidence']
    if attempts < minimum:
        answered = {0: 'nenhuma resposta independente', 1: '1 resposta independente'}.get(
            attempts, f'{attempts} respostas independentes'
        )
        reason = f'Exploração do {label} {name}: há {answered}, pouco para tirar conclusões.'
        return 'exploracao', 1 - attempts / minimum, reason
    estimate = row['estimate']
    threshold = params['reinforcement_below']
    if estimate < threshold:
        reason = f'Reforço do {label} {name}: {hits(correct)} em {attempts} respostas independentes.'
        return 'reforco', (threshold - estimate) / threshold, reason
    days = (now - row['last_practice']) / 86400 if row.get('last_practice') else params['review_after_days']
    elapsed = 'hoje' if days < 1 else f'há {int(days)} dias'
    reason = (
        f'Revisão do {label} {name}: última prática {elapsed}, com {hits(correct)} em '
        f'{attempts} respostas independentes.'
    )
    return 'revisao', min(1, days / params['review_after_days']), reason


def difficulty_fit(known, params):
    """Closeness to the target success rate; an item without enough answers stays neutral."""
    if not known:
        return 0.5
    return 1 - abs(known['success_rate'] - params['difficulty_target'])


def score_item(item, needs, picks, exposures, difficulty, cap_size, params):
    weights = params['weights']
    components = dict.fromkeys(FUNCTIONS, 0.0)
    chosen = None
    for key in item_groups(item):
        function, urgency, reason = needs[key]
        weighted = weights[function] * urgency
        components[function] = max(components[function], round(weighted, 4))
        if chosen is None or weighted > chosen[0]:
            chosen = (weighted, function, reason, key)
    repeated = exposures[identity(item)] / params['max_item_exposures']
    crowded = max(picks[key] for key in item_groups(item)) / cap_size
    components['exposicao'] = -round(weights['exposicao'] * repeated, 4)
    components['concentracao'] = -round(weights['concentracao'] * crowded, 4)
    components['dificuldade'] = round(
        weights['dificuldade'] * difficulty_fit(difficulty.get(identity(item)), params), 4
    )
    return chosen[1], chosen[2], chosen[3], components, round(sum(components.values()), 4)


def filter_pool(data, params):
    """Exposure always applies; provisional difficulty only while it does not shrink the session."""
    wanted = min(requested_items(data.minutes), len(data.pool))
    allowed = [i for i in data.pool if data.exposures[identity(i)] < params['max_item_exposures']]
    filtered = {'exposicao': len(data.pool) - len(allowed), 'dificuldade': 0}
    feasible = [
        i
        for i in allowed
        if not (known := data.difficulty.get(identity(i))) or known['success_rate'] >= params['difficulty_min_success']
    ]
    if len(feasible) >= wanted:
        filtered['dificuldade'] = len(allowed) - len(feasible)
        allowed = feasible
    return allowed, filtered


def shuffled(pool, seed):
    remaining = sorted(pool, key=lambda i: i['id'])
    random.Random(seed).shuffle(remaining)
    return remaining


def adaptive_policy(data, params=ADAPTIVE_V1):
    allowed, filtered = filter_pool(data, params)
    remaining = shuffled(allowed, data.seed)
    order = {item['id']: position for position, item in enumerate(remaining)}
    rows = evidence_by_group(data.state)
    needs = {key: group_need(key, rows.get(key), data.now, params) for i in remaining for key in item_groups(i)}
    count = min(requested_items(data.minutes), len(remaining))
    cap_size = max(1, math.ceil(params['max_theme_share'] * count))
    picks = Counter()
    chosen, relaxed = [], 0
    for position in range(1, count + 1):
        scored = []
        for item in remaining:
            function, reason, key, components, total = score_item(
                item, needs, picks, data.exposures, data.difficulty, cap_size, params
            )
            over_cap = any(picks[g] >= cap_size for g in item_groups(item) if g[0] == 'theme')
            scored.append((over_cap, -total, order[item['id']], item, function, reason, key, components, total))
        scored.sort(key=lambda row: row[:3])
        over_cap, _, _, item, function, reason, key, components, total = scored[0]
        relaxed += over_cap
        chosen.append(
            {
                'item': item,
                'position': position,
                'function': function,
                'group': key[-1],
                'reason': reason,
                'components': {**components, 'total': total},
                'candidates_total': len(scored),
                'candidates': [
                    {'item_id': row[3]['id'], 'function': row[4], 'total': row[8], 'over_cap': row[0]}
                    for row in scored[: params['logged_candidates']]
                ],
            }
        )
        picks.update(item_groups(item))
        remaining.remove(item)
    return chosen, {'filtered': filtered, 'relaxed_theme_cap': relaxed}


def baseline_entry(item, position, function, reason, candidates_total):
    return {
        'item': item,
        'position': position,
        'function': function,
        'group': item_groups(item)[0][-1],
        'reason': reason,
        'components': {},
        'candidates_total': candidates_total,
        'candidates': [],
    }


def random_policy(data, params=None):
    """Reference for the comparison: any item of the pool, without using the student's evidence."""
    remaining = shuffled(data.pool, data.seed)
    selected = remaining[: requested_items(data.minutes)]
    entries = [
        baseline_entry(item, position, 'aleatoria', 'Seleção aleatória.', len(remaining))
        for position, item in enumerate(selected, 1)
    ]
    return entries, {'filtered': {}, 'relaxed_theme_cap': 0}


def reinforcement_policy(data, params=None):
    """Reference for the comparison: lowest observed estimate first, with no other control."""
    rows = evidence_by_group(data.state)

    def lowest_estimate(item):
        values = [
            rows[key]['estimate'] for key in item_groups(item) if key in rows and rows[key]['estimate'] is not None
        ]
        return min(values) if values else 1.0

    remaining = sorted(shuffled(data.pool, data.seed), key=lowest_estimate)
    selected = remaining[: requested_items(data.minutes)]
    entries = [
        baseline_entry(item, position, 'reforco-simples', 'Menor estimativa observada.', len(remaining))
        for position, item in enumerate(selected, 1)
    ]
    return entries, {'filtered': {}, 'relaxed_theme_cap': 0}


POLICIES = {
    ADAPTIVE_V1['version']: adaptive_policy,
    'random-v1': random_policy,
    'reinforcement-simple-v1': reinforcement_policy,
}
DEFAULT_POLICY = ADAPTIVE_V1['version']


def evidence_summary(data):
    """The evidence behind the session, kept with it so a selection can be audited later."""
    used = {key for item in data.pool for key in item_groups(item)}
    rows = evidence_by_group(data.state)
    summary = []
    for key in sorted(used, key=lambda k: tuple(v or '' for v in k)):
        row = rows.get(key) or {}
        summary.append(
            {
                'kind': key[0],
                'name': key[-1],
                'independent_attempts': row.get('independent_attempts', 0),
                'independent_correct': row.get('independent_correct', 0),
                'estimate': row.get('estimate'),
                'last_practice': row.get('last_practice'),
            }
        )
    return summary


def recommend(data, policy=DEFAULT_POLICY):
    """Run a policy; returns one entry per chosen item and the summary stored with the session."""
    entries, details = POLICIES[policy](data)
    themes = Counter({t: 0 for item in data.pool for t in set(item['content']['labels']['themes'])})
    for entry in entries:
        themes.update(set(entry['item']['content']['labels']['themes']))
    summary = {
        'version': policy,
        'seed': data.seed,
        'generated_at': data.now,
        'requested_items': requested_items(data.minutes),
        'selected_items': len(entries),
        'eligible_items': len(data.pool),
        'themes': dict(sorted(themes.items())),
        'repeated_items': [e['item']['id'] for e in entries if data.exposures[identity(e['item'])]],
        'functions': dict(sorted(Counter(e['function'] for e in entries).items())),
        'parameters': ADAPTIVE_V1 if policy == ADAPTIVE_V1['version'] else {},
        'evidence': evidence_summary(data),
        **details,
    }
    return entries, summary
