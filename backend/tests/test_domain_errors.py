"""Domain rules stay free of HTTP; the API answers each failure with its own code."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'app'


def test_services_and_installers_do_not_depend_on_the_web_framework():
    modules = [*(ROOT / 'services').glob('*.py'), *(ROOT / 'installers').glob('*.py')]
    assert modules
    assert not [path.name for path in modules if 'fastapi' in path.read_text()]


def test_api_answers_domain_failures_with_their_code_and_message(admin, exam_payload):
    assert admin.post('/admin/imports', json=exam_payload).status_code == 201
    repeated = admin.post('/admin/imports', json=exam_payload)
    assert repeated.status_code == 409
    assert repeated.json() == {'detail': 'Esta prova já foi importada. Use a edição versionada.'}
