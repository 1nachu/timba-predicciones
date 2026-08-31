"""
Integration and Functional Tests for REST API v1
=================================================
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


def test_api_health(client):
    res = client.get('/api/v1/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'ok'
    assert data['version'] == '2.2'
    assert 'timestamp' in data


def test_api_leagues(client):
    res = client.get('/api/v1/leagues')
    assert res.status_code == 200
    data = res.get_json()
    assert data['total'] >= 8
    assert isinstance(data['leagues'], list)
    assert any(l['codigo'] == 'E0' for l in data['leagues'])


def test_api_predict_success(client):
    res = client.get('/api/v1/predict?liga_id=1&local=Arsenal&visitante=Chelsea&odds_home=2.10&odds_draw=3.40&odds_away=3.80')
    assert res.status_code == 200
    data = res.get_json()
    assert data['local'] == 'Arsenal'
    assert data['visitante'] == 'Chelsea'
    assert 'probabilidades' in data
    assert 'local' in data['probabilidades']
    assert 'goles_esperados' in data
    assert 'mercados' in data
    assert 'top_marcadores' in data
    assert isinstance(data['recomendaciones'], list)


def test_api_predict_same_team_error(client):
    res = client.get('/api/v1/predict?liga_id=1&local=Arsenal&visitante=Arsenal')
    assert res.status_code == 400
    data = res.get_json()
    assert 'error' in data


def test_api_predict_missing_params(client):
    res = client.get('/api/v1/predict?liga_id=1')
    assert res.status_code == 400
    data = res.get_json()
    assert 'error' in data


def test_api_fixtures(client):
    res = client.get('/api/v1/fixtures?liga_id=1')
    assert res.status_code == 200
    data = res.get_json()
    assert data['liga_id'] == 1
    assert 'partidos' in data


def test_api_live(client):
    res = client.get('/api/v1/live')
    assert res.status_code == 200
    data = res.get_json()
    assert 'partidos' in data


def test_api_history(client):
    res = client.get('/api/v1/history?liga_id=1&days=7')
    assert res.status_code == 200
    data = res.get_json()
    assert data['liga_id'] == 1
    assert 'estadisticas' in data


def test_api_value_bets(client):
    res = client.get('/api/v1/value-bets?min_ev=0.01')
    assert res.status_code == 200
    data = res.get_json()
    assert 'value_bets' in data
