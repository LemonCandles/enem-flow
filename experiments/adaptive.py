"""Comparação offline da política adaptativa com referências, em alunos simulados.

Mede cobertura, exposição, concentração e coerência das escolhas. Os alunos são
sintéticos: isso avalia o comportamento da seleção, sem demonstrar ganho de aprendizagem.
"""

from collections import Counter
import random
import statistics

from backend.app.services.adaptive import PolicyInput, recommend
from backend.app.services.diagnostics import identity

from .common import ROOT, read_json, write_json

LIMITS = (
    'Alunos simulados com probabilidades de acerto fixadas por tema, sem aprendizagem entre as sessões. '
    'Os resultados descrevem o comportamento da seleção em cenários definidos; não indicam ganho de '
    'aprendizagem nem a melhor combinação de pesos. Pesos e cenários foram definidos pela mesma frente técnica.'
)
DAY = 86_400
START = 1_800_000_000.0


def load_pool(path):
    reference = read_json(ROOT / path)
    return [
        {
            'id': f'{row["question_id"]}:1',
            'question_id': row['question_id'],
            'canonical_id': row['canonical_id'],
            'version': 1,
            'content': {
                'area': 'Matemática',
                'labels': {
                    'discipline': row['discipline'],
                    'themes': row['themes'],
                    'skills': [],
                    'taxonomy_version': row['taxonomy_version'],
                },
            },
        }
        for row in reference['items']
    ]


class SimulatedStudent:
    """Keeps evidence like the real estimator: only the first answer per identity is independent."""

    def __init__(self, scenario, pool, seed):
        self.success = scenario['success']
        self.default = scenario['default_success']
        self.rng = random.Random(seed)
        self.rows = {}
        self.answered = set()
        taxonomy = {t for i in pool for t in [i['content']['labels']['taxonomy_version']]}.pop()
        self.namespace = ('Matemática', pool[0]['content']['labels']['discipline'], taxonomy)
        for theme, (attempts, correct, days_ago) in scenario.get('history', {}).items():
            row = self.row(theme)
            row.update(independent_attempts=attempts, independent_correct=correct, last_practice=START - days_ago * DAY)

    def row(self, theme):
        area, discipline, taxonomy = self.namespace
        return self.rows.setdefault(
            theme,
            {
                'area': area,
                'discipline': discipline,
                'taxonomy_version': taxonomy,
                'name': theme,
                'independent_attempts': 0,
                'independent_correct': 0,
                'last_practice': None,
            },
        )

    def state(self):
        themes = []
        for row in self.rows.values():
            n, correct = row['independent_attempts'], row['independent_correct']
            themes.append({**row, 'estimate': (1 + correct) / (2 + n) if n else None})
        return {'themes': themes, 'skills': []}

    def answer(self, item, now):
        themes = item['content']['labels']['themes']
        hit = self.rng.random() < min(self.success.get(t, self.default) for t in themes)
        first = identity(item) not in self.answered
        self.answered.add(identity(item))
        for theme in set(themes):
            row = self.row(theme)
            row['last_practice'] = now
            if first:
                row['independent_attempts'] += 1
                row['independent_correct'] += int(hit)


def gini(values):
    values = sorted(values)
    total = sum(values)
    if not total:
        return 0.0
    weighted = sum((i + 1) * v for i, v in enumerate(values))
    return 2 * weighted / (len(values) * total) - (len(values) + 1) / len(values)


def simulate(policy, scenario, pool, seed, adaptive_config):
    """Run the sessions of one simulated student and return its behaviour metrics."""
    if scenario.get('themes'):
        pool = [i for i in pool if set(i['content']['labels']['themes']) & set(scenario['themes'])]
    pool = pool[: scenario['pool_limit']] if scenario.get('pool_limit') else pool
    student = SimulatedStudent(scenario, pool, f'aluno:{seed}')
    exposures, picks_per_item = Counter(), Counter()
    weak = set(scenario.get('weak_themes', []))
    themes_seen, shares, functions = set(), [], Counter()
    picks = repeated = short = without_reason = 0
    weak_after, total_after = 0, 0
    first_session_themes = 0
    minimum = adaptive_config['minimum_evidence']
    for session in range(scenario['sessions']):
        now = START + session * scenario['days_between'] * DAY
        data = PolicyInput(pool, student.state(), exposures, scenario['minutes'], f'{seed}:{session}', now)
        weak_known = weak and all(student.row(t)['independent_attempts'] >= minimum for t in weak)
        entries, summary = recommend(data, policy)
        short += summary['selected_items'] < min(summary['requested_items'], len(pool))
        counts = Counter(t for e in entries for t in set(e['item']['content']['labels']['themes']))
        if entries:
            shares.append(max(counts.values()) / len(entries))
        if session == 0:
            first_session_themes = len(counts)
        for entry in entries:
            item = entry['item']
            themes = set(item['content']['labels']['themes'])
            repeated += exposures[identity(item)] > 0
            exposures[identity(item)] += 1
            picks_per_item[identity(item)] += 1
            picks += 1
            themes_seen |= themes
            functions[entry['function']] += 1
            without_reason += not entry['reason']
            if weak_known:
                total_after += 1
                weak_after += bool(themes & weak)
            student.answer(item, now)
    pool_themes = {t for i in pool for t in i['content']['labels']['themes']}
    item_counts = [picks_per_item[identity(i)] for i in pool]
    top = sorted(item_counts, reverse=True)[: max(1, len(item_counts) // 10)]
    return {
        'picks': picks,
        'theme_coverage': len(themes_seen & pool_themes) / len(pool_themes),
        'first_session_themes': first_session_themes,
        'max_theme_share': statistics.fmean(shares) if shares else 0.0,
        'repeated_share': repeated / picks if picks else 0.0,
        'distinct_items': sum(1 for count in item_counts if count),
        'item_gini': gini(item_counts),
        'top_decile_share': sum(top) / picks if picks else 0.0,
        'weak_share_after_evidence': weak_after / total_after if total_after else None,
        'short_sessions': short,
        'without_reason': without_reason,
        'functions': functions,
    }


def aggregate(rows):
    report = {}
    for key in rows[0]:
        if key == 'functions':
            continue
        values = [row[key] for row in rows if row[key] is not None]
        report[key] = (
            {'mean': round(statistics.fmean(values), 4), 'stdev': round(statistics.pstdev(values), 4)}
            if values
            else None
        )
    functions = Counter()
    for row in rows:
        functions.update(row['functions'])
    total = sum(functions.values())
    report['function_share'] = {k: round(v / total, 4) for k, v in sorted(functions.items())} if total else {}
    return report


def run(config, seed, output):
    from backend.app.services.adaptive import ADAPTIVE_V1

    pool = load_pool(config['reference'])
    scenarios = {}
    for name, scenario in config['scenarios'].items():
        scenarios[name] = {
            'description': scenario['description'],
            'policies': {
                policy: aggregate(
                    [
                        simulate(policy, scenario, pool, f'{seed}:{name}:{repetition}', ADAPTIVE_V1)
                        for repetition in range(config['repetitions'])
                    ]
                )
                for policy in config['policies']
            },
        }
    report = {
        'schema_version': '1.0',
        'parameters': ADAPTIVE_V1,
        'pool_items': len(pool),
        'repetitions': config['repetitions'],
        'limits': LIMITS,
        'scenarios': scenarios,
    }
    write_json(output / 'adaptive-report.json', report)
    return report
