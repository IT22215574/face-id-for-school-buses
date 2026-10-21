"""Smoke checks for the built React entry point and protected admin APIs."""
import pytest
from fastapi.testclient import TestClient
from app.main import app, admin_web


def test_admin_web_entry_point():
    if not (admin_web / 'index.html').exists():
        pytest.skip('Build admin-web first with npm run build')
    client = TestClient(app)
    response = client.get('/admin-web/')
    assert response.status_code == 200
    assert 'admin-web' in response.text
    assert '/admin-web/assets/' in response.text
    # A source file or npm manifest must never be served by the production mount.
    assert client.get('/admin-web/package.json').status_code == 404


@pytest.mark.parametrize('path', ['/admin/buses', '/admin/driver-registrations'])
def test_admin_api_requires_authentication(path):
    response = TestClient(app).get(path)
    assert response.status_code in (401, 403)
