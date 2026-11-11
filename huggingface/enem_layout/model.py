"""Rede convolucional com três cabeças: corpo, alternativas e marcas.

O tronco reduz a imagem a uma grade de posições verticais (a ordem dos blocos de cima para baixo é
o que define o layout) e as cabeças classificam cada eixo. Corpo e alternativas são classes
exclusivas; marcas são independentes (multirrótulo). Os pesos ficam em safetensors e a configuração
(rótulos, tamanho da imagem, temperaturas e limiares) em config.json.
"""

from huggingface_hub import PyTorchModelHubMixin
import torch
from torch import nn

GITHUB = 'https://github.com/LemonCandles/enem-flow'


def block(inputs, outputs):
    return nn.Sequential(
        nn.Conv2d(inputs, outputs, 3, padding=1, bias=False),
        nn.BatchNorm2d(outputs),
        nn.ReLU(inplace=True),
        nn.Conv2d(outputs, outputs, 3, padding=1, bias=False),
        nn.BatchNorm2d(outputs),
        nn.ReLU(inplace=True),
        nn.MaxPool2d(2),
    )


class EnemLayoutClassifier(
    nn.Module,
    PyTorchModelHubMixin,
    library_name='pytorch',
    repo_url=GITHUB,
    license='mit',
    pipeline_tag='image-classification',
    tags=['enem', 'layout', 'document-layout', 'portuguese'],
):
    def __init__(
        self,
        corpo,
        alternativas,
        marcas,
        width=384,
        height=1024,
        channels=(24, 48, 96, 160, 256),
        rows=32,
        hidden=512,
        dropout=0.3,
        temperature=None,
        mark_threshold=0.5,
        review_threshold=0.0,
        catalog_version='layout-types-v2',
        model_version='enem-layout-types-1.0.0',
    ):
        super().__init__()
        self.labels = {'corpo': list(corpo), 'alternativas': list(alternativas), 'marcas': list(marcas)}
        self.width, self.height = width, height
        self.temperature = dict(temperature or {'corpo': 1.0, 'alternativas': 1.0, 'marcas': 1.0})
        self.mark_threshold, self.review_threshold = mark_threshold, review_threshold
        self.catalog_version, self.model_version = catalog_version, model_version
        # Entrada com passo 2: a tipografia fina não importa, a disposição dos blocos sim.
        layers = [
            nn.Sequential(
                nn.Conv2d(1, channels[0], 5, stride=2, padding=2, bias=False),
                nn.BatchNorm2d(channels[0]),
                nn.ReLU(inplace=True),
            )
        ]
        previous = channels[0]
        for size in channels:
            layers.append(block(previous, size))
            previous = size
        self.trunk = nn.Sequential(*layers)
        # Grade de `rows` posições verticais por 2 horizontais: preserva a ordem dos blocos.
        self.pool = nn.AdaptiveAvgPool2d((rows, 2))
        self.neck = nn.Sequential(
            nn.Flatten(), nn.Dropout(dropout), nn.Linear(previous * rows * 2, hidden), nn.ReLU(inplace=True)
        )
        self.heads = nn.ModuleDict({axis: nn.Linear(hidden, len(values)) for axis, values in self.labels.items()})

        self._architecture = {'channels': list(channels), 'rows': rows, 'hidden': hidden, 'dropout': dropout}

    def current_config(self):
        """Configuração atual, inclusive temperatura e limiares calibrados depois da construção."""
        return {
            **self.labels,
            **self._architecture,
            'width': self.width,
            'height': self.height,
            'temperature': self.temperature,
            'mark_threshold': self.mark_threshold,
            'review_threshold': self.review_threshold,
            'catalog_version': self.catalog_version,
            'model_version': self.model_version,
        }

    def save_pretrained(self, save_directory, **kwargs):
        kwargs['config'] = self.current_config()
        return super().save_pretrained(save_directory, **kwargs)

    def forward(self, images):
        features = self.neck(self.pool(self.trunk(images)))
        return {axis: head(features) for axis, head in self.heads.items()}

    @torch.no_grad()
    def probabilities(self, images):
        """Probabilidades calibradas por eixo (softmax em corpo e alternativas, sigmoide em marcas)."""
        logits = self.forward(images)
        return {
            'corpo': torch.softmax(logits['corpo'] / self.temperature['corpo'], dim=-1),
            'alternativas': torch.softmax(logits['alternativas'] / self.temperature['alternativas'], dim=-1),
            'marcas': torch.sigmoid(logits['marcas'] / self.temperature['marcas']),
        }
