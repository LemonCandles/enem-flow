"""The shared admin router must protect every curation and archive endpoint."""

ADMIN_REQUESTS = (
    ("GET", "/admin/exams"),
    ("GET", "/admin/exams/missing"),
    ("GET", "/admin/audit"),
    ("GET", "/admin/archive"),
    ("GET", "/admin/archive/questions?year=2024"),
    ("GET", "/admin/archive/questions/missing"),
    ("GET", "/admin/taxonomy"),
    ("POST", "/admin/imports"),
    ("POST", "/admin/imports/prepare"),
    ("POST", "/admin/reviews/missing"),
    ("PUT", "/admin/questions/missing:1"),
)


def assert_admin_denied(client, status):
    for method, path in ADMIN_REQUESTS:
        response = client.request(method, path, **({"json": {}} if method != "GET" else {}))
        assert response.status_code == status, (method, path, response.text)


def test_all_admin_routes_require_authentication(client):
    assert_admin_denied(client, 401)


def test_all_admin_routes_reject_student(student):
    assert_admin_denied(student, 403)
