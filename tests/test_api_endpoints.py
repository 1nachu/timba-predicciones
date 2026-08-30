"""
Integration tests for Flask Web Application & Endpoints
=======================================================
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


def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Timba' in response.data or b'Predicci' in response.data or b'html' in response.data


def test_predict_route(client):
    response = client.get('/predict')
    assert response.status_code in [200, 302]


def test_fixtures_route(client):
    response = client.get('/fixtures')
    assert response.status_code in [200, 302]


def test_live_route(client):
    response = client.get('/live')
    assert response.status_code in [200, 302]


def test_history_route(client):
    response = client.get('/history')
    assert response.status_code in [200, 302]
