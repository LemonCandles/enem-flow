"""Proveniência, métricas e arquivos dos experimentos, sem serviços externos."""
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
from contextlib import contextmanager
import signal

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def deadline(seconds):
    """Bound pathological PDF geometry in local worker processes (Unix)."""
    def expired(*_):raise TimeoutError(f'Geometria excedeu {seconds}s; preservar fonte para revisão.')
    previous=signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda value: invalid_number(value))


def invalid_number(value):
    raise ValueError(f'Número JSON não finito: {value}')


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def source_path(relative, expected_hash):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('Fonte fora do projeto.')
    if not path.is_file():
        raise FileNotFoundError(relative)
    if file_digest(path) != expected_hash:
        raise ValueError(f'Hash divergente: {relative}')
    return path


def provenance(config, inputs):
    paths = [*(ROOT / 'experiments').glob('*.py'), *(ROOT / 'backend/app').rglob('*.py'),
             ROOT / 'scripts/run_experiments.py', ROOT / 'scripts/exam_pdf.py', ROOT / 'scripts/pdf_headings.py']
    code = {str(p.relative_to(ROOT)): file_digest(p) for p in sorted(paths)}
    return {'config': config, 'config_sha256': digest(config), 'inputs': inputs,
            'code_sha256': digest(code), 'code_files': code,
            'python': platform.python_version(), 'platform': platform.platform(),
            'packages': {name: importlib.metadata.version(name) for name in ('pymupdf', 'pydantic')},
            'review_status': 'proposed', 'independent_review': False}


def classification_metrics(expected, predicted, labels):
    if len(expected) != len(predicted):
        raise ValueError('Cada exemplo precisa de uma previsão.')
    if any(value not in labels for value in [*expected, *predicted]):
        raise ValueError('Classe fora do vocabulário da avaliação.')
    matrix = {label: dict.fromkeys(labels, 0) for label in labels}
    for target, output in zip(expected, predicted):
        matrix[target][output] += 1
    per_class = {}
    for label in labels:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        emitted = sum(row[label] for row in matrix.values())
        precision = tp / emitted if emitted else 0.0
        recall = tp / support if support else 0.0
        per_class[label] = {'precision': precision, 'recall': recall,
                            'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                            'support': support, 'predicted': emitted}
    supported = [row for row in per_class.values() if row['support']]
    return {'samples': len(expected), 'accuracy': sum(a == b for a, b in zip(expected, predicted)) / len(expected) if expected else None,
            'macro_f1': sum(row['f1'] for row in supported) / len(supported) if supported else None,
            'macro_precision': sum(row['precision'] for row in supported) / len(supported) if supported else None,
            'macro_recall': sum(row['recall'] for row in supported) / len(supported) if supported else None,
            'macro_policy': 'Média das classes com suporte; classes ausentes continuam na matriz.',
            'per_class': per_class, 'confusion_matrix': matrix}


def latency_summary(values):
    ordered = sorted(values)
    return {'samples': len(ordered), 'p50_ms': ordered[len(ordered) // 2] if ordered else None,
            'p95_ms': ordered[max(0, math.ceil(len(ordered) * .95) - 1)] if ordered else None,
            'total_ms': sum(ordered)}


def human_timings(path, valid_targets):
    """Não inventa tempo humano: só aceita registros explícitos, vinculados ao conteúdo."""
    if path is None:
        return {'measured': False, 'records': 0, 'median_seconds': None, 'total_seconds': None}
    from .contracts import CorrectionLog
    log = CorrectionLog.model_validate(read_json(path))
    seen, values = set(), []
    for record in log.records:
        key = (record.target_id, record.method)
        if key in seen or valid_targets.get(record.target_id) != record.content_sha256:
            raise ValueError('Tempo duplicado ou referente a outra versão de conteúdo.')
        seen.add(key)
        values.append(record.seconds)
    ordered = sorted(values)
    return {'measured': bool(values), 'records': len(values),
            'median_seconds': ordered[len(ordered) // 2] if ordered else None,
            'total_seconds': sum(values) if values else None,
            'log_sha256': file_digest(path),
            'by_method': {method: {'records': sum(r.method == method for r in log.records),
                                  'total_seconds': sum(r.seconds for r in log.records if r.method == method)}
                          for method in sorted({r.method for r in log.records})}}
