"""Treino da rede de tipos de layout; usa o pacote publicado (`huggingface/enem_layout`) e o projeto."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / 'huggingface', ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
