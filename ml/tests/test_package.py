"""Pacote publicado: pré-processamento, formato da saída e ida e volta de save/from_pretrained."""

import json

from PIL import Image, ImageDraw
import pytest
import torch

import layout_types  # noqa: F401  (ajusta o caminho para huggingface/)
from enem_layout.model import EnemLayoutClassifier
from enem_layout.predict import main, predict_images
from enem_layout.preprocess import to_tensor
from layout_types.data import OTHER, target, vocabulary
from layout_types.evaluate import bootstrap, calibration_error

LABELS = {
    'corpo': ['texto', 'texto-figura-texto', OTHER],
    'alternativas': ['figura', 'texto'],
    'marcas': ['compartilhado', 'linhas-numeradas', 'lado-a-lado'],
}


def question(height=900):
    image = Image.new('L', (520, height), 255)
    draw = ImageDraw.Draw(image)
    for y in range(20, height - 40, 30):
        draw.rectangle([10, y, 500, y + 12], fill=0)
    return image


def test_preprocess_keeps_aspect_and_marks_ink_as_one():
    tensor = to_tensor(question(), 384, 1024)
    assert tensor.shape == (1, 1024, 384)
    assert tensor.max() == 1.0 and tensor[0, -1, -1] == 0.0
    tall = to_tensor(question(4000), 384, 1024)
    assert tall.shape == (1, 1024, 384) and tall[0, :, 300:].sum() == 0


def model():
    torch.manual_seed(0)
    return EnemLayoutClassifier(**LABELS, width=128, height=256, channels=(8, 8, 8, 8, 8), rows=4, hidden=16)


def test_prediction_json_has_type_axes_probabilities_and_review_flag():
    catalog = {'texto.alt-texto': {'representable': True, 'reasons': [], 'description': 'x'}}
    output = predict_images(model(), [question()], catalog)[0]
    assert set(output) >= {'type', 'axes', 'probabilities', 'confidence', 'needs_review', 'in_catalog', 'representable'}
    assert set(output['probabilities']) == {'corpo', 'alternativas', 'marcas'}
    assert abs(sum(output['probabilities']['corpo'].values()) - 1) < 1e-3
    if output['axes']['corpo'] == OTHER:
        assert output['type'] is None and output['needs_review']
    json.dumps(output)


def test_save_and_from_pretrained_give_identical_predictions(tmp_path, capsys):
    original = model()
    original.temperature = {'corpo': 1.5, 'alternativas': 0.8, 'marcas': 1.0}
    original.save_pretrained(tmp_path)
    loaded = EnemLayoutClassifier.from_pretrained(tmp_path)
    assert loaded.temperature == original.temperature and loaded.labels == original.labels
    images = [question(), question(500)]
    assert predict_images(original, images) == predict_images(loaded, images)
    question().save(tmp_path / 'q.png')
    capsys.readouterr()
    main([str(tmp_path / 'q.png'), '--model', str(tmp_path)])
    assert json.loads(capsys.readouterr().out)['image'] == 'q.png'


def test_rare_bodies_become_other_and_unknown_alternatives_are_ignored():
    train = [{'axes': {'corpo': 'texto', 'alternativas': 'texto', 'marcas': 'nenhuma'}}] * 3
    train += [{'axes': {'corpo': 'texto-tabela-texto', 'alternativas': 'texto', 'marcas': 'lado-a-lado'}}]
    labels = vocabulary(train, 2)
    assert labels['corpo'] == ['texto', OTHER]
    corpo, option, marks = target(
        {'axes': {'corpo': 'texto-tabela-texto', 'alternativas': 'grade', 'marcas': 'lado-a-lado'}}, labels
    )
    assert labels['corpo'][corpo] == OTHER and option == -100 and marks.tolist() == [0, 0, 1]


@pytest.mark.parametrize('hits', [[1] * 10, [0, 1] * 20])
def test_bootstrap_interval_contains_the_mean_and_calibration_is_bounded(hits):
    low, high = bootstrap(hits)
    assert low <= sum(hits) / len(hits) <= high
    assert 0 <= calibration_error([0.9] * len(hits), hits) <= 1
