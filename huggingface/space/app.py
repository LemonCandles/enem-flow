"""Demonstração: envie a imagem de uma questão do ENEM e receba o JSON com o tipo de layout."""

import os

import gradio as gr

from enem_layout.model import EnemLayoutClassifier
from enem_layout.predict import load_catalog, predict_images
from huggingface_hub import snapshot_download

REPO = os.environ.get('MODEL_REPO', '{repo_id}')
folder = snapshot_download(REPO)
model = EnemLayoutClassifier.from_pretrained(folder)
catalog = load_catalog(folder)
examples = sorted(os.path.join('exemplos', name) for name in os.listdir('exemplos') if name.endswith('.png'))


def classify(image):
    if image is None:
        return {}
    return predict_images(model, [image], catalog)[0]


demo = gr.Interface(
    fn=classify,
    inputs=gr.Image(type='pil', label='Imagem de uma questão inteira'),
    outputs=gr.JSON(label='Tipo de layout'),
    examples=examples,
    title='Enem Flow — tipos de layout',
    description=(
        'Rede neural que classifica o layout de impressão de uma questão do ENEM. '
        'Projeto Enem Flow, de Cassio Lima Silva e Diogo Vieira de Castro: '
        'https://github.com/LemonCandles/enem-flow'
    ),
)

if __name__ == '__main__':
    demo.launch()
