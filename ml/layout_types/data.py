"""Manifesto `layout-types-archive-v1` → tensores, com o mesmo pré-processamento do pacote publicado."""

from collections import Counter
import json
from pathlib import Path
import random

from PIL import ImageFilter, Image
import torch
from torch.utils.data import Dataset

from enem_layout.preprocess import canvas, fit

from . import ROOT  # noqa: F401  (reexportado para train.py)

MARKS = ['compartilhado', 'linhas-numeradas', 'lado-a-lado']
NO_MARKS = 'nenhuma'
OTHER = 'outro'


def load_manifest(path):
    manifest = json.loads(Path(path).read_text())
    labeled = [item for item in manifest['items'] if item['axes']]
    return manifest, {split: [i for i in labeled if i['split'] == split] for split in ('train', 'development', 'test')}


def vocabulary(train, min_count):
    """Corpo com suporte mínimo no treino (o resto é `outro`); alternativas vistas no treino; marcas fixas."""
    counts = Counter(item['axes']['corpo'] for item in train)
    return {
        'corpo': sorted(label for label, count in counts.items() if count >= min_count) + [OTHER],
        'alternativas': sorted({item['axes']['alternativas'] for item in train}),
        'marcas': list(MARKS),
    }


def marks_of(axes):
    return [] if axes['marcas'] == NO_MARKS else axes['marcas'].split('.')


def target(item, labels):
    """Índices de corpo e alternativas (-100 = ignorar na perda) e vetor das marcas."""
    axes = item['axes']
    corpo = axes['corpo'] if axes['corpo'] in labels['corpo'] else OTHER
    alternatives = (
        labels['alternativas'].index(axes['alternativas']) if axes['alternativas'] in labels['alternativas'] else -100
    )
    marks = marks_of(axes)
    return labels['corpo'].index(corpo), alternatives, torch.tensor([m in marks for m in MARKS], dtype=torch.float32)


def expected_type(item, labels):
    """Tipo que o modelo poderia acertar: corpo fora do vocabulário só pode sair como `outro` (sem tipo)."""
    return item['type'] if item['axes']['corpo'] in labels['corpo'] else None


class QuestionImages(Dataset):
    def __init__(self, items, images, labels, width, height, augment=False):
        self.items, self.images, self.labels = items, Path(images), labels
        self.width, self.height, self.augment = width, height, augment

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        item = self.items[index]
        image = Image.open(self.images / item['image']).convert('L')
        if self.augment:
            # Aumentos leves de impressão e digitalização; nunca espelhar: a orientação define o layout.
            image = fit(image, self.width, self.height, scale=random.uniform(0.85, 1.0))
            if random.random() < 0.3:
                image = image.filter(ImageFilter.GaussianBlur(random.uniform(0.3, 1.0)))
            if random.random() < 0.2:
                image = image.filter(ImageFilter.MinFilter(3))
            tensor = canvas(image, self.width, self.height)
            shift = random.randint(0, 24)
            if shift:
                tensor = torch.cat([torch.zeros(1, shift, self.width), tensor[:, :-shift]], dim=1)
            tensor = (tensor * random.uniform(0.8, 1.1)).clamp(0, 1)
        else:
            tensor = canvas(fit(image, self.width, self.height), self.width, self.height)
        corpo, alternatives, marks = target(item, self.labels)
        return tensor, corpo, alternatives, marks, index


def worker_seed(worker_id):
    seed = torch.initial_seed() % 2**32
    random.seed(seed + worker_id)
