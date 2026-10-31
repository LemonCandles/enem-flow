"""Synchronize immutable bundled resources into a persistent content volume."""
import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path


def synchronize(source: Path, destination: Path):
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir(): raise ValueError('Diretório de recursos incluídos ausente.')
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for item in sorted(source.rglob('*')):
        if not item.is_file(): continue
        if item.is_symlink(): raise ValueError('Recurso incluído não pode ser um link simbólico.')
        target = destination / item.relative_to(source)
        if not target.resolve().is_relative_to(destination): raise ValueError('Destino de recurso fora do volume.')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(item.read_bytes()).digest():
                raise ValueError(f'Recurso existente diferente: {item.relative_to(source)}. Publique com um novo nome para preservar versões anteriores.')
            continue
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                temporary = Path(stream.name)
                with item.open('rb') as incoming: shutil.copyfileobj(incoming, stream)
                stream.flush(); os.fsync(stream.fileno())
            temporary.chmod(0o644)
            # Link publishes the complete file without replacing an existing one.
            os.link(temporary, target)
            copied += 1
        finally:
            if temporary: temporary.unlink(missing_ok=True)
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/opt/enem-bundled-assets'))
    parser.add_argument('--destination', type=Path, default=Path('/app/data/assets'))
    args = parser.parse_args()
    print(f'Recursos sincronizados: {synchronize(args.source, args.destination)} novos arquivos; existentes preservados.')


if __name__ == '__main__': main()
