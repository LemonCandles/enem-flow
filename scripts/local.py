"""Prepare, diagnose and run the local six-exam installation (Linux/WSL)."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv/bin/python'


def run(*args):
    print('→ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True)


def prerequisites():
    if sys.version_info[:2] not in {(3, 13), (3, 14)}:
        raise RuntimeError('Use Python 3.13 ou 3.14 (python3).')
    for command in ('git', 'make', 'node', 'npm'):
        if not shutil.which(command):
            raise RuntimeError(f'Instale {command} e execute novamente.')
    if subprocess.check_output(['node', '--version'], text=True).split('.')[0] != 'v22':
        raise RuntimeError('Instale Node.js 22 com npm e execute novamente.')


def database_path():
    url = os.getenv('DATABASE_URL', 'sqlite:///' + str(ROOT / 'enem-flow.db'))
    if not url.startswith('sqlite:///') or '?' in url or url.endswith(':memory:'):
        raise RuntimeError(
            'setup/doctor/dev locais exigem SQLite em arquivo. Para PostgreSQL, use o fluxo Docker documentado.'
        )
    path = Path(url.removeprefix('sqlite:///'))
    return path if path.is_absolute() else ROOT / path


def setup():
    prerequisites()
    database = database_path()
    if not PYTHON.exists():
        run(sys.executable, '-m', 'venv', ROOT / '.venv')
    run(PYTHON, '-m', 'ensurepip', '--upgrade')
    run(PYTHON, '-m', 'pip', 'install', '-r', 'backend/requirements-dev.lock')
    run('npm', '--prefix', 'frontend', 'ci')
    run(PYTHON, 'scripts/check_distribution.py')
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        run(PYTHON, 'scripts/backup_sqlite.py', ROOT / 'backups' / f'before-setup-{stamp}.db', '--source', database)
    run(ROOT / '.venv/bin/alembic', 'upgrade', 'head')
    run(PYTHON, '-m', 'backend.app.cli', 'local-catalog')
    doctor()
    print('Preparação concluída. Execute make dev; crie sua conta no site.')


def doctor():
    prerequisites()
    if not PYTHON.exists() or not (ROOT / 'frontend/node_modules/next/package.json').exists():
        raise RuntimeError('Dependências ausentes. Execute make setup.')
    run(PYTHON, '-m', 'pip', 'check')
    run('npm', '--prefix', 'frontend', 'ls', '--depth=0')
    run(PYTHON, 'scripts/check_distribution.py')
    path = database_path()
    if not path.is_file():
        raise RuntimeError('Banco ausente. Execute make setup.')
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as db:
        revision = db.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        heads = subprocess.check_output([str(ROOT / '.venv/bin/alembic'), 'heads'], cwd=ROOT, text=True)
        if revision not in heads.split():
            raise RuntimeError('Banco desatualizado. Execute make setup.')
        rows = db.execute('SELECT id, status FROM exams').fetchall()
        print('Catálogo instalado (decisões manuais preservadas):', rows)
        profile = json.loads((ROOT / 'data/catalog/profiles.json').read_text())['local']
        expected = set(profile['reviewed'] + profile['automatic'])
        published = {key for key, status in rows if status == 'published'}
        print(
            'Diferenças do perfil novo:',
            {'ausentes_ou_retiradas': sorted(expected - published), 'adicionais': sorted(published - expected)},
        )
    print('Diagnóstico concluído.')


def wait_ready(url, processes, label, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError(f'Um serviço encerrou durante a inicialização de {label}.')
        try:
            with urllib.request.urlopen(url, timeout=min(1, max(0.01, deadline - time.monotonic()))):
                return
        except OSError:
            time.sleep(min(0.5, max(0, deadline - time.monotonic())))
    raise RuntimeError(f'{label} não ficou disponível em {timeout} segundos.')


def stop_processes(processes):
    # Each child owns its process group; never signal a process we did not start.
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for process in processes:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def dev():
    doctor()
    for port in (8000, 3000):
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', port))
            except OSError as error:
                raise RuntimeError(
                    f'Porta {port} ocupada; encerre o serviço correspondente antes de make dev.'
                ) from error
    processes = []

    def stop(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        processes.append(
            subprocess.Popen(
                [
                    str(ROOT / '.venv/bin/uvicorn'),
                    'backend.app.main:app',
                    '--reload',
                    '--host',
                    '127.0.0.1',
                    '--port',
                    '8000',
                ],
                cwd=ROOT,
                start_new_session=True,
            )
        )
        wait_ready('http://127.0.0.1:8000/health', processes, 'API')
        processes.append(
            subprocess.Popen(['npm', '--prefix', 'frontend', 'run', 'dev'], cwd=ROOT, start_new_session=True)
        )
        wait_ready('http://127.0.0.1:3000', processes, 'Frontend')
        print('Site: http://localhost:3000 · API: http://localhost:8000/docs · Ctrl+C encerra ambos.', flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        raise RuntimeError('Um serviço encerrou; os demais serão finalizados.')
    finally:
        stop_processes(processes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup', 'doctor', 'dev'])
    args = parser.parse_args()
    try:
        globals()[args.command]()
    except KeyboardInterrupt:
        print('\nServiços encerrados.')
    except (OSError, RuntimeError, subprocess.CalledProcessError, sqlite3.Error) as error:
        print(f'Falha em {args.command}: {error}\nCorrija a causa e repita make {args.command}.', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
