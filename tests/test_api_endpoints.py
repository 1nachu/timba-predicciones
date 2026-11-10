"""
Integration tests for Flask API-Only Application
=================================================
Verifica que las rutas HTML heredadas (Jinja2) ya no existen en Flask
y que los manejadores de error responden en formato JSON.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_legacy_html_routes_removed_and_return_json_404(client):
    legacy_paths = ['/', '/predict', '/fixtures', '/live', '/history', '/robots.txt', '/sitemap.xml']
    for path in legacy_paths:
        res = client.get(path)
        assert res.status_code == 404, f"Expected 404 for {path}, got {res.status_code}"
        data = res.get_json()
        assert data is not None
        assert 'error' in data


def test_post_predict_removed(client):
    res = client.post('/predict', data={'liga_id': '1', 'local': 'Arsenal', 'visitante': 'Chelsea'})
    assert res.status_code == 404
