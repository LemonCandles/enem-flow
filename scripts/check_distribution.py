"""Validate all shipped exams and assets without touching the application database."""

import _bootstrap  # noqa: F401
import hashlib
import json
import subprocess
from pathlib import Path
from backend.app.schemas import ExamImport
from backend.app.services.content import validate_assets
from backend.app.preparation import blocking_issues

ROOT = Path(__file__).resolve().parents[1]


def check():
    hashes = json.loads((ROOT / 'data/catalog/distribution-hashes.json').read_text())
    profiles = json.loads((ROOT / 'data/catalog/profiles.json').read_text())
    curated = json.loads((ROOT / 'data/catalog/manifest.json').read_text())
    reviewed_ids = {json.loads((ROOT / entry['path']).read_text())['id'] for entry in curated['exams']}
    if set(profiles['docker']['reviewed']) != reviewed_ids or not set(profiles['local']['reviewed']) <= reviewed_ids:
        raise ValueError('Perfis local/Docker divergem do catálogo conferido.')
    verified = {f'data/derived/exams/{key}.json' for key in profiles['local'].get('verified', [])}
    if not set(profiles['local'].get('verified', [])) <= set(profiles['local']['automatic']):
        raise ValueError('Provas conferidas precisam fazer parte do catálogo automático local.')
    expected_paths = {entry['path'] for entry in curated['exams']}
    expected_paths.update(f'data/derived/exams/{key}.json' for key in profiles['local']['automatic'])
    actual_paths = {name for name in hashes if name.endswith('.json')}
    if actual_paths != expected_paths:
        raise ValueError('Manifesto de hashes não cobre exatamente os catálogos distribuídos.')
    for name, expected in hashes.items():
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(
                f'Conteúdo distribuído ausente ou alterado: {name}. Revise a mudança e o manifesto de hashes.'
            )
        if path.suffix != '.json':
            continue
        exam = ExamImport.model_validate_json(path.read_text())
        pending = []
        for question in exam.questions:
            content = question.content.model_dump()
            validate_assets(content)
            if blocking_issues(content):
                pending.append(question.question_id)
        if pending and name in verified:
            raise ValueError(f'{exam.id} está registrada como conferida, mas tem pendências: {pending}')
        subprocess.run(['node', 'frontend/scripts/validate-latex.cjs', str(path)], cwd=ROOT, check=True)
        print(f'{exam.id}: {len(exam.questions)} posições; pendências preservadas: {pending}')
    if json.loads((ROOT / 'docs/content-schema.json').read_text()) != ExamImport.model_json_schema():
        raise ValueError('docs/content-schema.json diverge do contrato de importação.')


if __name__ == '__main__':
    check()
