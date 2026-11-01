from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from backend.app.main import app
from backend.app.models import User
from backend.app.core.security import hash_password

PROXY = '172.30.246.254'


def test_trusted_gateway_keeps_client_limits_independent(database):
    with database.begin() as db:
        db.add(User(name='Usuário legítimo',email='proxy@example.com',password_hash=hash_password('senha-valida-para-teste')))
    wrapped=ProxyHeadersMiddleware(app,trusted_hosts=[PROXY])
    with TestClient(wrapped,client=(PROXY,43210)) as client:
        for _ in range(30):
            response=client.post('/auth/login',headers={'X-Forwarded-For':'198.51.100.1'},json=dict(email='unknown@example.com',password='senha-incorreta-para-teste'))
            assert response.status_code==401
        assert client.post('/auth/login',headers={'X-Forwarded-For':'198.51.100.1'},json=dict(email='proxy@example.com',password='senha-valida-para-teste')).status_code==429
        assert client.post('/auth/login',headers={'X-Forwarded-For':'198.51.100.2'},json=dict(email='proxy@example.com',password='senha-valida-para-teste')).status_code==200


def test_untrusted_peer_cannot_rotate_forwarding_headers_to_evade_limit(database):
    wrapped=ProxyHeadersMiddleware(app,trusted_hosts=[PROXY])
    with TestClient(wrapped,client=('172.30.246.99',43210)) as client:
        for i in range(31):
            response=client.post('/auth/login',headers={'X-Forwarded-For':f'198.51.100.{i+1}'},json=dict(email='unknown@example.com',password='senha-incorreta-para-teste'))
            assert response.status_code==(401 if i<30 else 429)
