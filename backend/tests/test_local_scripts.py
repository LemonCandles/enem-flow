import importlib.util
from pathlib import Path
import sqlite3

import pytest

spec = importlib.util.spec_from_file_location('local_commands', Path('scripts/local.py'))
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


def test_local_setup_rejects_remote_database_before_installing(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://localhost/user_database')
    monkeypatch.setattr(local, 'prerequisites', lambda: None)
    monkeypatch.setattr(local, 'run', lambda *args: pytest.fail('Não deve instalar antes de validar destino'))
    with pytest.raises(RuntimeError, match='SQLite'):
        local.setup()


def test_backup_failure_prevents_migration(tmp_path, monkeypatch):
    source = tmp_path / 'existing.db'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE preserved (id INTEGER)')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(source))
    monkeypatch.setattr(local, 'prerequisites', lambda: None)
    calls = []

    def run(*args):
        calls.append(tuple(map(str, args)))
        if 'scripts/backup_sqlite.py' in args:
            raise OSError('backup indisponível')

    monkeypatch.setattr(local, 'run', run)
    with pytest.raises(OSError):
        local.setup()
    assert not any('upgrade' in args or 'local-catalog' in args for args in calls)
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='preserved'").fetchone()


@pytest.mark.parametrize('missing', ['git', 'make', 'node', 'npm'])
def test_missing_tool_explains_how_to_resume(monkeypatch, missing):
    monkeypatch.setattr(local.shutil, 'which', lambda name: None if name == missing else '/bin/' + name)
    with pytest.raises(RuntimeError, match=f'Instale {missing}'):
        local.prerequisites()


@pytest.mark.parametrize('failed_step', ['pip', 'npm'])
def test_download_failure_never_migrates_and_can_be_retried(tmp_path, monkeypatch, failed_step):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'new.db'))
    monkeypatch.setattr(local, 'prerequisites', lambda: None)
    monkeypatch.setattr(local, 'doctor', lambda: None)
    calls = []
    fail = True

    def run(*args):
        calls.append(tuple(map(str, args)))
        if fail and failed_step in args:
            raise local.subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(local, 'run', run)
    with pytest.raises(local.subprocess.CalledProcessError):
        local.setup()
    assert not any('upgrade' in args or 'local-catalog' in args for args in calls)
    fail = False
    local.setup()
    assert sum('upgrade' in args for args in calls) == 1
    assert sum('local-catalog' in args for args in calls) == 1


def test_occupied_port_does_not_start_services(monkeypatch):
    monkeypatch.setattr(local, 'doctor', lambda: None)

    class Occupied:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def bind(self, address):
            raise OSError('address in use')

    monkeypatch.setattr(local.socket, 'socket', Occupied)
    monkeypatch.setattr(local.subprocess, 'Popen', lambda *a, **k: pytest.fail('Porta ocupada deve impedir início'))
    with pytest.raises(RuntimeError, match='Porta 8000 ocupada'):
        local.dev()


def test_readiness_retries_until_http_is_available(monkeypatch):
    import io

    attempts = []
    clock = iter([0, 0, 0, 1, 1, 1, 2])
    monkeypatch.setattr(local.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(local.time, 'sleep', lambda _: None)

    def open_url(url, timeout):
        attempts.append(url)
        if len(attempts) == 1:
            raise OSError('not ready')
        return io.BytesIO()

    monkeypatch.setattr(local.urllib.request, 'urlopen', open_url)
    local.wait_ready('http://localhost:3000', [], 'Frontend')
    assert len(attempts) == 2


def test_readiness_timeout_and_early_exit(monkeypatch):
    clock = iter([0, 61])
    monkeypatch.setattr(local.time, 'monotonic', lambda: next(clock))
    with pytest.raises(RuntimeError, match='Frontend não ficou disponível'):
        local.wait_ready('http://localhost:3000', [], 'Frontend')
    monkeypatch.setattr(local.time, 'monotonic', lambda: 0)

    class Dead:
        def poll(self):
            return 1

    with pytest.raises(RuntimeError, match='encerrou durante'):
        local.wait_ready('http://localhost:3000', [Dead()], 'Frontend')


def test_frontend_failure_stops_both_owned_processes(monkeypatch, capsys):
    monkeypatch.setattr(local, 'doctor', lambda: None)
    monkeypatch.setattr(local.signal, 'signal', lambda *args: None)
    processes = []
    stopped = []

    class FreePort:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def bind(self, address):
            return None

    monkeypatch.setattr(local.socket, 'socket', FreePort)

    def spawn(*args, **kwargs):
        process = object()
        processes.append(process)
        return process

    def ready(url, children, label):
        if label == 'Frontend':
            raise RuntimeError('Frontend indisponível')

    monkeypatch.setattr(local.subprocess, 'Popen', spawn)
    monkeypatch.setattr(local, 'wait_ready', ready)
    monkeypatch.setattr(local, 'stop_processes', lambda children: stopped.extend(children))
    with pytest.raises(RuntimeError, match='Frontend indisponível'):
        local.dev()
    assert len(processes) == 2 and stopped == processes
    assert 'Site:' not in capsys.readouterr().out


def test_shutdown_only_signals_owned_process_groups():
    import subprocess
    import sys

    owned = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
    try:
        local.stop_processes([owned])
        assert owned.poll() is not None
        assert unrelated.poll() is None
    finally:
        for process in (owned, unrelated):
            if process.poll() is None:
                process.kill()
            process.wait()
