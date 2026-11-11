"""Imagem da questão → tensor: tons de cinza, largura fixa, proporção preservada, tela branca.

A tinta vale 1 e o papel 0. A imagem é alinhada no canto superior esquerdo da tela; se ficar mais alta
que a tela, é reduzida até caber, o que preserva a ordem vertical dos blocos, que é o que importa.
"""

import numpy as np
from PIL import Image
import torch


def fit(image, width, height, scale=1.0):
    """Imagem em tons de cinza redimensionada para caber em width × height (escala opcional, para aumento)."""
    image = image.convert('L')
    factor = min(width * scale / image.width, height / image.height)
    size = (max(1, round(image.width * factor)), max(1, round(image.height * factor)))
    return image.resize(size, Image.Resampling.BILINEAR)


def canvas(image, width, height):
    """Tensor 1 × height × width com a imagem no canto superior esquerdo; tinta = 1."""
    pixels = np.asarray(image, dtype=np.float32)[:height, :width]
    result = np.zeros((height, width), dtype=np.float32)
    result[: pixels.shape[0], : pixels.shape[1]] = 1.0 - pixels / 255.0
    return torch.from_numpy(result).unsqueeze(0)


def to_tensor(image, width, height):
    return canvas(fit(image, width, height), width, height)
