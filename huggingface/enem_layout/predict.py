"""Imagem(ns) de questão → JSON com o tipo de layout.

python -m enem_layout.predict questao.png --model CONTA/enem-layout-types
python -m enem_layout.predict pasta/*.png --model caminho/local
"""

import argparse
import contextlib
import json
from pathlib import Path
import sys

from PIL import Image
import torch

from .model import EnemLayoutClassifier
from .preprocess import to_tensor

NO_MARKS = 'nenhuma'
OTHER = 'outro'


def load_catalog(model_dir):
    path = Path(model_dir) / 'layout-types.json'
    if not path.is_file():
        return {}
    return {entry['id']: entry for entry in json.loads(path.read_text())['types']}


def decode(model, probabilities, index, catalog):
    corpo = probabilities['corpo'][index]
    alternatives = probabilities['alternativas'][index]
    marks = probabilities['marcas'][index]
    body = model.labels['corpo'][int(corpo.argmax())]
    option = model.labels['alternativas'][int(alternatives.argmax())]
    chosen = [m for m, p in zip(model.labels['marcas'], marks.tolist()) if p >= model.mark_threshold]
    confidence = float(corpo.max() * alternatives.max())
    for p in marks.tolist():
        confidence *= p if p >= model.mark_threshold else 1 - p
    axes = {'corpo': body, 'alternativas': option, 'marcas': '.'.join(chosen) or NO_MARKS}
    kind = None if body == OTHER else '.'.join([body, 'alt-' + option, *chosen])
    entry = catalog.get(kind) if kind else None
    return {
        'type': kind,
        'axes': axes,
        'probabilities': {
            'corpo': dict(zip(model.labels['corpo'], [round(p, 4) for p in corpo.tolist()])),
            'alternativas': dict(zip(model.labels['alternativas'], [round(p, 4) for p in alternatives.tolist()])),
            'marcas': dict(zip(model.labels['marcas'], [round(p, 4) for p in marks.tolist()])),
        },
        'confidence': round(confidence, 4),
        'needs_review': kind is None or entry is None or confidence < model.review_threshold,
        'in_catalog': entry is not None,
        'representable': entry['representable'] if entry else None,
        'unrepresentable_reasons': entry['reasons'] if entry else [],
        'description': entry['description'] if entry else None,
        'model_version': model.model_version,
        'catalog_version': model.catalog_version,
    }


def predict_images(model, images, catalog=None, batch_size=8):
    """Uma predição por imagem (PIL.Image), na ordem recebida."""
    model.eval()
    device = next(model.parameters()).device
    results = []
    for start in range(0, len(images), batch_size):
        batch = torch.stack(
            [to_tensor(image, model.width, model.height) for image in images[start : start + batch_size]]
        )
        probabilities = model.probabilities(batch.to(device))
        probabilities = {axis: values.float().cpu() for axis, values in probabilities.items()}
        results += [decode(model, probabilities, i, catalog or {}) for i in range(len(batch))]
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prevê o tipo de layout de questões do ENEM a partir da imagem.')
    parser.add_argument('images', nargs='+', type=Path, help='PNG/JPEG de uma questão inteira, sem o resto da página.')
    parser.add_argument(
        '--model', default=str(Path(__file__).resolve().parents[1]), help='Repositório do Hub ou pasta.'
    )
    args = parser.parse_args(argv)
    torch.manual_seed(0)
    # Mensagens da biblioteca vão para stderr: stdout é só o JSON.
    with contextlib.redirect_stdout(sys.stderr):
        model = EnemLayoutClassifier.from_pretrained(args.model)
    local = Path(args.model)
    if local.is_dir():
        catalog = load_catalog(local)
    else:
        from huggingface_hub import hf_hub_download

        catalog = load_catalog(Path(hf_hub_download(args.model, 'layout-types.json')).parent)
    outputs = predict_images(model, [Image.open(path) for path in args.images], catalog)
    payload = [{'image': path.name, **output} for path, output in zip(args.images, outputs)]
    json.dump(payload[0] if len(payload) == 1 else payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
