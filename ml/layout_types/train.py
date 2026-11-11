"""Treina e avalia a rede de tipos de layout; várias seeds, escolha pelo desenvolvimento.

    cd ml && .venv/bin/python -m layout_types.train --output ../tmp/experiments/layout-neural-01

O teste (as 370 questões revisadas de 2024 e 2025) só é medido depois da escolha: não escolhe
seed, época, temperatura nem limiar. Saídas: run.json (proveniência e status), report.json
(métricas e linhas de base), predictions.json e model/ (safetensors + config.json) de cada seed.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from enem_layout.model import EnemLayoutClassifier

from .data import ROOT, QuestionImages, load_manifest, marks_of, target, vocabulary, worker_seed
from .evaluate import predict, report, support

CONFIG = {
    'width': 384,
    'height': 1024,
    'min_corpo_count': 10,
    'epochs': 40,
    'mark_pos_weight_cap': 5.0,
    'batch_size': 12,
    'learning_rate': 2e-3,
    'weight_decay': 1e-4,
    'review_target_accuracy': 0.95,
    'workers': 6,
    # Precisão mista gera NaN na GTX 1650 (série 16 sem fp16 estável no cuDNN); fp32 cabe em 4 GB.
    'mixed_precision': False,
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def class_weights(indices, size):
    """Peso inverso à raiz da frequência: classes raras pesam mais sem dominar a perda."""
    counts = Counter(i for i in indices if i >= 0)
    weights = torch.tensor([1 / math.sqrt(counts.get(i, 0) + 1) for i in range(size)])
    return weights / weights.mean()


def type_score(items, outputs):
    """Média do macro-F1 dos três eixos: critério de escolha da época e da seed."""
    from .evaluate import axis_metrics

    return sum(axis_metrics(items, outputs, axis)['macro_f1'] or 0 for axis in ('corpo', 'alternativas', 'marcas')) / 3


def calibrate(logits, items, labels):
    """Temperatura por eixo que minimiza a perda logarítmica no desenvolvimento (grade simples)."""
    corpo = torch.tensor(
        [
            labels['corpo'].index(i['axes']['corpo'])
            if i['axes']['corpo'] in labels['corpo']
            else len(labels['corpo']) - 1
            for i in items
        ]
    )
    options = [
        labels['alternativas'].index(i['axes']['alternativas'])
        if i['axes']['alternativas'] in labels['alternativas']
        else -100
        for i in items
    ]
    options = torch.tensor(options)
    marks = torch.tensor([[m in marks_of(i['axes']) for m in labels['marcas']] for i in items], dtype=torch.float32)
    grid = [0.5 + 0.1 * k for k in range(46)]

    def best(loss):
        return min(grid, key=lambda t: (loss(t), abs(t - 1)))

    return {
        'corpo': best(lambda t: nn.functional.cross_entropy(logits['corpo'] / t, corpo).item()),
        'alternativas': best(
            lambda t: nn.functional.cross_entropy(logits['alternativas'] / t, options, ignore_index=-100).item()
        ),
        'marcas': best(lambda t: nn.functional.binary_cross_entropy_with_logits(logits['marcas'] / t, marks).item()),
    }


def mark_threshold(logits, items, model):
    """Limiar das marcas que maximiza o macro-F1 do eixo no desenvolvimento (com a temperatura já aplicada)."""
    from experiments.common import classification_metrics

    probabilities = torch.sigmoid(logits['marcas'] / model.temperature['marcas'])
    expected = [item['axes']['marcas'] for item in items]

    def score(threshold):
        predicted = [
            '.'.join(m for m, p in zip(model.labels['marcas'], row.tolist()) if p >= threshold) or 'nenhuma'
            for row in probabilities
        ]
        return classification_metrics(expected, predicted, sorted(set(expected) | set(predicted)))['macro_f1']

    return max([0.5 + 0.05 * k for k in range(10)], key=lambda t: (score(t), -abs(t - 0.5)))


def review_threshold(items, outputs, target):
    """Menor confiança que mantém a acurácia das questões aceitas no alvo, no desenvolvimento."""
    pairs = sorted(((o['confidence'], int(o['type'] == i['type'])) for i, o in zip(items, outputs)), reverse=True)
    threshold, correct = 1.0, 0
    for count, (confidence, hit) in enumerate(pairs, 1):
        correct += hit
        if correct / count >= target:
            threshold = confidence
    return threshold


def train_seed(seed, splits, images, output, device):
    seed_everything(seed)
    labels = vocabulary(splits['train'], CONFIG['min_corpo_count'])
    model = EnemLayoutClassifier(
        corpo=labels['corpo'],
        alternativas=labels['alternativas'],
        marcas=labels['marcas'],
        width=CONFIG['width'],
        height=CONFIG['height'],
    ).to(device)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        QuestionImages(splits['train'], images, labels, CONFIG['width'], CONFIG['height'], augment=True),
        batch_size=CONFIG['batch_size'],
        shuffle=True,
        num_workers=CONFIG['workers'],
        worker_init_fn=worker_seed,
        generator=generator,
        drop_last=True,
        persistent_workers=True,
    )
    indices = [target(item, labels) for item in splits['train']]
    corpo_loss = nn.CrossEntropyLoss(weight=class_weights([c for c, _, _ in indices], len(labels['corpo'])).to(device))
    option_loss = nn.CrossEntropyLoss(
        weight=class_weights([a for _, a, _ in indices], len(labels['alternativas'])).to(device), ignore_index=-100
    )
    positives = torch.stack([m for _, _, m in indices]).sum(0)
    mark_loss = nn.BCEWithLogitsLoss(
        pos_weight=((len(indices) - positives) / positives.clamp(min=1))
        .clamp(max=CONFIG['mark_pos_weight_cap'])
        .to(device)
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG['learning_rate'], weight_decay=CONFIG['weight_decay'])
    schedule = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=CONFIG['learning_rate'], total_steps=CONFIG['epochs'] * len(loader)
    )
    scaler = torch.amp.GradScaler(enabled=device == 'cuda' and CONFIG['mixed_precision'])
    history, best = [], ((-1.0, -1.0), None, -1)
    for epoch in range(CONFIG['epochs']):
        model.train()
        started, total, batches = time.perf_counter(), 0.0, 0
        for tensors, corpo, options, marks, _ in loader:
            tensors, corpo, options, marks = (t.to(device) for t in (tensors, corpo, options, marks))
            with torch.autocast(device_type=device, enabled=device == 'cuda' and CONFIG['mixed_precision']):
                logits = model(tensors)
                loss = (
                    corpo_loss(logits['corpo'].float(), corpo)
                    + option_loss(logits['alternativas'].float(), options)
                    + mark_loss(logits['marcas'].float(), marks)
                )
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            schedule.step()
            total, batches = total + loss.item(), batches + 1
        outputs, _ = predict(
            model,
            splits['development'],
            images,
            device=device,
            workers=CONFIG['workers'],
            mixed=CONFIG['mixed_precision'],
        )
        score = type_score(splits['development'], outputs)
        accuracy = sum(o['type'] == i['type'] for i, o in zip(splits['development'], outputs)) / len(outputs)
        history.append(
            {
                'epoch': epoch + 1,
                'train_loss': total / batches,
                'development_mean_macro_f1': score,
                'development_type_accuracy': accuracy,
                'seconds': time.perf_counter() - started,
            }
        )
        print(
            f'seed {seed} época {epoch + 1}: perda {total / batches:.4f}, dev F1 {score:.4f}, tipo {accuracy:.4f}',
            flush=True,
        )
        # Escolha pela acurácia do tipo exato no desenvolvimento; o macro-F1 desempata (classes de 2–3 exemplos oscilam).
        if (accuracy, score) > best[0]:
            best = ((accuracy, score), {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, epoch + 1)
    model.load_state_dict(best[1])
    _, logits = predict(
        model, splits['development'], images, device=device, workers=CONFIG['workers'], mixed=CONFIG['mixed_precision']
    )
    model.temperature = calibrate(logits, splits['development'], labels)
    model.mark_threshold = mark_threshold(logits, splits['development'], model)
    outputs, _ = predict(
        model, splits['development'], images, device=device, workers=CONFIG['workers'], mixed=CONFIG['mixed_precision']
    )
    model.review_threshold = review_threshold(splits['development'], outputs, CONFIG['review_target_accuracy'])
    model.cpu()
    model.save_pretrained(output / 'model')
    return model, {
        'history': history,
        'best_epoch': best[2],
        'development_type_accuracy_at_best': best[0][0],
        'development_mean_macro_f1': best[0][1],
    }


def provenance(manifest_path):
    code = {
        str(p.relative_to(ROOT)): file_digest(p)
        for p in sorted([*(ROOT / 'ml/layout_types').glob('*.py'), *(ROOT / 'huggingface/enem_layout').glob('*.py')])
    }
    return {
        'config': CONFIG,
        'manifest': str(Path(manifest_path).resolve().relative_to(ROOT)),
        'manifest_sha256': file_digest(manifest_path),
        'code_files': code,
        'code_sha256': digest(code),
        'python': platform.python_version(),
        'packages': {name: importlib.metadata.version(name) for name in ('torch', 'torchvision', 'pillow', 'numpy')},
        'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'data/datasets/layout-types-archive-v1.json')
    parser.add_argument('--images', type=Path, default=ROOT / 'tmp/layout-dataset/layout-types-archive-v1/images')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=[1, 2, 3])
    parser.add_argument('--epochs', type=int, default=CONFIG['epochs'])
    parser.add_argument('--sem-teste', action='store_true', help='Rodada de ajuste: não mede o teste.')
    args = parser.parse_args()
    CONFIG['epochs'] = args.epochs
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / 'tmp').resolve()):
        parser.error('Use uma pasta de resultados em tmp/.')
    if output.exists() and any(output.iterdir()):
        parser.error('Saída não vazia: escolha outra pasta.')
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    manifest, splits = load_manifest(args.manifest)
    metadata = {**provenance(args.manifest), 'seeds': args.seeds, 'status': 'running'}
    metadata['started_at'] = datetime.now(timezone.utc).isoformat()
    write(output / 'run.json', metadata)
    train_types = Counter(item['type'] for item in splits['train'])
    majority = min(train_types, key=lambda t: (-train_types[t], t))
    runs = {}
    for seed in args.seeds:
        folder = output / f'seed-{seed}'
        model, training = train_seed(seed, splits, args.images, folder, device)
        model.to(device)
        results = {}
        for split in ('development',) if args.sem_teste else ('development', 'test'):
            items = splits[split]
            outputs, _ = predict(
                model, items, args.images, device=device, workers=CONFIG['workers'], mixed=CONFIG['mixed_precision']
            )
            baselines = None
            if split == 'test':
                baselines = {
                    'majority': [majority] * len(items),
                    'rule_json': [item['baselines']['rule'] for item in items],
                    'adapter': [item['baselines']['adapter'] for item in items],
                }
            results[split] = report(items, outputs, model.labels, baselines, model.review_threshold)
            write(
                folder / f'predictions-{split}.json',
                [{'id': item['id'], 'expected': item['type'], **o} for item, o in zip(items, outputs)],
            )
        runs[seed] = {**training, **results, 'model_sha256': file_digest(folder / 'model/model.safetensors')}
        write(folder / 'report.json', runs[seed])
        model.cpu()
        del model
        torch.cuda.empty_cache()
    # A seed publicada é a melhor no desenvolvimento; o teste só é reportado.
    selected = max(
        args.seeds,
        key=lambda s: (runs[s]['development_type_accuracy_at_best'], runs[s]['development_mean_macro_f1'], -s),
    )
    tests = [runs[s]['test']['type_accuracy'] if 'test' in runs[s] else 0.0 for s in args.seeds]
    mean = sum(tests) / len(tests)
    summary = {
        'selected_seed': selected,
        'test_measured': not args.sem_teste,
        'selection': 'maior acurácia do tipo exato no desenvolvimento (macro-F1 médio desempata); teste não usado',
        'model_config': json.loads((output / f'seed-{selected}/model/config.json').read_text()),
        'counts': {split: len(items) for split, items in splits.items()},
        'train_support': support(splits['train']),
        'test_support': support(splits['test']),
        'majority_type': majority,
        'test_type_accuracy_by_seed': dict(zip(map(str, args.seeds), tests)),
        'test_type_accuracy_mean': mean,
        'test_type_accuracy_std': math.sqrt(sum((t - mean) ** 2 for t in tests) / len(tests)),
        'runs': {str(seed): run for seed, run in runs.items()},
        'dataset': {k: manifest[k] for k in ('version', 'catalog_version', 'reference_version', 'adapter', 'counts')},
    }
    write(output / 'report.json', summary)
    metadata.update(
        status='complete',
        finished_at=datetime.now(timezone.utc).isoformat(),
        report_sha256=digest(summary),
        selected_seed=selected,
    )
    write(output / 'run.json', metadata)
    print(
        f'Concluído: seed {selected}; tipo exato no desenvolvimento {runs[selected]["development"]["type_accuracy"]:.4f}'
    )


if __name__ == '__main__':
    main()
