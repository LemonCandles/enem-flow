"""Take a consistent SQLite snapshot without stopping the local API."""
import argparse
import sqlite3
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "enem-flow.db")
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Banco de origem não encontrado.")
    if args.destination.exists():
        raise SystemExit("O destino já existe. Escolha outro arquivo para preservar os backups anteriores.")
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{args.source.resolve()}?mode=ro", uri=True) as source:
        with sqlite3.connect(args.destination) as destination:
            source.backup(destination)
            assert destination.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    print(f"Snapshot íntegro criado em {args.destination}.")


if __name__ == "__main__":
    main()
