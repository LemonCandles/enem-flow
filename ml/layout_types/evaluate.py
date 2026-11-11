"""Previsões e métricas: tipo exato, macro-F1 por eixo, intervalos por bootstrap, calibração e fatias."""

from collections import Counter
import random

import torch
from torch.utils.data import DataLoader

from enem_layout.predict import decode
from experiments.common import classification_metrics

from .data import QuestionImages, expected_type


@torch.no_grad()
def predict(model, items, images, batch_size=16, device='cpu', workers=4, mixed=False):
    """Uma previsão (formato do pacote publicado) e os logits por eixo para cada item."""
    model.eval()
    loader = DataLoader(
        QuestionImages(items, images, model.labels, model.width, model.height),
        batch_size=batch_size,
        num_workers=workers,
    )
    outputs, logits = [], {axis: [] for axis in model.labels}
    for tensors, *_ in loader:
        with torch.autocast(device_type=device, enabled=device == 'cuda' and mixed):
            raw = model(tensors.to(device))
        raw = {axis: value.float().cpu() for axis, value in raw.items()}
        for axis, value in raw.items():
            logits[axis].append(value)
        probabilities = {
            'corpo': torch.softmax(raw['corpo'] / model.temperature['corpo'], -1),
            'alternativas': torch.softmax(raw['alternativas'] / model.temperature['alternativas'], -1),
            'marcas': torch.sigmoid(raw['marcas'] / model.temperature['marcas']),
        }
        outputs += [decode(model, probabilities, i, {}) for i in range(len(tensors))]
    return outputs, {axis: torch.cat(values) for axis, values in logits.items()}


def axis_metrics(items, outputs, axis):
    expected = [item['axes'][axis] for item in items]
    predicted = [output['axes'][axis] for output in outputs]
    return classification_metrics(expected, predicted, sorted(set(expected) | set(predicted)))


def bootstrap(hits, samples=1000, seed=0):
    """Intervalo de 95% da média de acertos por reamostragem com reposição."""
    if not hits:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(hits, k=len(hits))) / len(hits) for _ in range(samples))
    return [means[int(0.025 * samples)], means[int(0.975 * samples) - 1]]


def calibration_error(confidences, hits, bins=10):
    """ECE: diferença média entre confiança e acerto, ponderada pelo tamanho de cada faixa."""
    total, error = len(hits), 0.0
    for b in range(bins):
        low, high = b / bins, (b + 1) / bins
        members = [i for i, c in enumerate(confidences) if low < c <= high or (b == 0 and c == 0)]
        if members:
            accuracy = sum(hits[i] for i in members) / len(members)
            confidence = sum(confidences[i] for i in members) / len(members)
            error += len(members) / total * abs(accuracy - confidence)
    return error


def report(items, outputs, labels, baselines=None, review_threshold=0.0):
    """Métricas de uma partição; `baselines` mapeia nome → tipo previsto por item."""
    hits = [int(output['type'] == item['type']) for item, output in zip(items, outputs)]
    confidences = [output['confidence'] for output in outputs]
    accepted = [h for h, c in zip(hits, confidences) if c >= review_threshold]

    def accuracy(subset):
        selected = [h for item, h in zip(items, hits) if subset(item)]
        return {'samples': len(selected), 'accuracy': sum(selected) / len(selected) if selected else None}

    result = {
        'samples': len(items),
        'type_accuracy': sum(hits) / len(hits) if hits else None,
        'type_accuracy_ci95': bootstrap(hits),
        'reachable_type_accuracy': accuracy(lambda item: expected_type(item, labels) is not None),
        'type': classification_metrics(
            [item['type'] for item in items],
            [output['type'] or 'outro' for output in outputs],
            sorted({item['type'] for item in items} | {output['type'] or 'outro' for output in outputs}),
        ),
        'axes': {axis: axis_metrics(items, outputs, axis) for axis in labels},
        'calibration_error': calibration_error(confidences, hits),
        'review': {
            'threshold': review_threshold,
            'coverage': len(accepted) / len(hits) if hits else None,
            'accuracy_accepted': sum(accepted) / len(accepted) if accepted else None,
        },
        'slices': {
            **{
                f'ano:{year}': accuracy(lambda i, y=year: i['year'] == y) for year in sorted({i['year'] for i in items})
            },
            **{
                f'rotulo:{origin}': accuracy(lambda i, o=origin: i['label_origin'] == o)
                for origin in sorted({i['label_origin'] for i in items})
            },
            **{
                f'conteudo:{form}': accuracy(lambda i, f=form: i['content_form'] == f)
                for form in sorted({i['content_form'] for i in items})
            },
        },
    }
    if baselines:
        result['baselines'] = {}
        for name, predicted in baselines.items():
            base_hits = [int(p == item['type']) for item, p in zip(items, predicted)]
            result['baselines'][name] = {
                'type_accuracy': sum(base_hits) / len(base_hits),
                'type_accuracy_ci95': bootstrap(base_hits),
            }
    return result


def support(items):
    return dict(sorted(Counter(item['type'] for item in items).items(), key=lambda kv: (-kv[1], kv[0])))
