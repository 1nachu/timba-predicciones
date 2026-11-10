"""
Integration and Functional Tests for REST API v1
=================================================
"""

import pytest
import os
import sys
from unittest.mock import patch

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
    assert data['version'] in ['2.2', '3.0']
    assert 'timestamp' in data


def test_api_dashboard_with_cache(client):
    mock_cache = {
        'total_ligas': 9,
        'ligas': {1: {'nombre': 'Premier League', 'codigo': 'E0'}},
        'partidos_hoy': {
            1: {
                'nombre': 'Premier League',
                'partidos': [{'local': 'Arsenal', 'visitante': 'Chelsea', 'hora': '16:00'}],
            }
        },
        'total_partidos_hoy': 1,
        'updated_at': '2026-11-10T12:00:00Z',
    }
    with patch('web.blueprints.api.cargar_dashboard_cache', return_value=mock_cache):
        res = client.get('/api/v1/dashboard')
        assert res.status_code == 200
        data = res.get_json()
        assert data['cache_missing'] is False
        assert data['total_partidos_hoy'] == 1
        assert '1' in data['partidos_hoy']


def test_api_dashboard_without_cache(client):
    with patch('web.blueprints.api.cargar_dashboard_cache', return_value=None):
        res = client.get('/api/v1/dashboard')
        assert res.status_code == 200
        data = res.get_json()
        assert data['cache_missing'] is True
        assert data['total_partidos_hoy'] == 0
        assert data['last_update'] == 'Actualizando...'


def test_api_leagues(client):
    res = client.get('/api/v1/leagues')
    assert res.status_code == 200
    data = res.get_json()
    assert data['total'] >= 8
    assert isinstance(data['leagues'], list)
    assert any(l['codigo'] == 'E0' for l in data['leagues'])


def test_api_league_teams(client):
    res = client.get('/api/v1/leagues/1/teams')
    assert res.status_code == 200
    data = res.get_json()
    assert data['liga_id'] == 1
    assert isinstance(data['equipos'], list)
    assert 'Arsenal' in data['equipos']


def test_api_league_teams_champions(client):
    res = client.get('/api/v1/leagues/8/teams')
    assert res.status_code == 200
    data = res.get_json()
    assert data['liga_id'] == 8
    assert len(data['equipos']) > 5


def test_api_league_teams_not_found(client):
    res = client.get('/api/v1/leagues/999/teams')
    assert res.status_code == 404


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
    assert 'corners' in data
    assert 'total' in data['corners']
    assert 'over_85' in data['corners']
    assert 'tarjetas' in data
    assert 'amarillas_total' in data['tarjetas']
    assert 'over_25' in data['tarjetas']
    assert 'avisos' in data
    assert 'top_marcadores' in data
    assert isinstance(data['recomendaciones'], list)


def test_api_predict_same_team_error(client):
    res = client.get('/api/v1/predict?liga_id=1&local=Arsenal&visitante=Arsenal')
    assert res.status_code == 400
    data = res.get_json()
    assert 'error' in data
    assert isinstance(data.get('avisos'), list)


def test_api_predict_missing_params(client):
    res = client.get('/api/v1/predict?liga_id=1')
    assert res.status_code == 400
    data = res.get_json()
    assert 'error' in data


def test_api_fixtures(client):
    sample_fixtures = [
        {'local': 'Arsenal', 'visitante': 'Chelsea', 'fecha': '2026-09-01 16:00', 'fecha_utc': '2026-09-01T19:00:00Z'}
    ]
    with patch('web.blueprints.api.obtener_fixtures_cached', return_value=sample_fixtures):
        res = client.get('/api/v1/fixtures?liga_id=1')
        assert res.status_code == 200
        data = res.get_json()
        assert data['liga_id'] == 1
        assert 'liga_actual' in data
        assert 'partidos' in data
        assert len(data['partidos']) == 1
        assert data['partidos'][0]['local'] == 'Arsenal'


def test_api_fixtures_not_found(client):
    res = client.get('/api/v1/fixtures?liga_id=999')
    assert res.status_code == 404


def test_api_live(client):
    res = client.get('/api/v1/live')
    assert res.status_code == 200
    data = res.get_json()
    assert 'partidos' in data
    assert 'es_demo' in data


def test_api_history_by_liga_id(client):
    res = client.get('/api/v1/history?liga_id=1&days=7')
    assert res.status_code == 200
    data = res.get_json()
    assert data['liga_id'] == 1
    assert 'estadisticas' in data
    assert 'ligas' in data
    assert 'liga_actual' in data


def test_api_history_by_league_code_and_invalid_code(client):
    res = client.get('/api/v1/history?league_code=SP1&days=14')
    assert res.status_code == 200
    data = res.get_json()
    assert data['league_code'] == 'SP1'
    assert data['days'] == 14

    res_inv = client.get('/api/v1/history?league_code=INVALID_CODE&days=99')
    assert res_inv.status_code == 200
    data_inv = res_inv.get_json()
    assert data_inv['days'] == 7
    assert len(data_inv['avisos']) >= 1


def test_api_value_bets(client):
    sample_fixtures = [
        {'local': 'Arsenal', 'visitante': 'Chelsea', 'fecha': '2026-09-01 16:00'}
    ]
    with patch('web.blueprints.api.obtener_fixtures_cached', return_value=sample_fixtures):
        res = client.get('/api/v1/value-bets?min_ev=0.01')
        assert res.status_code == 200
        data = res.get_json()
        assert 'value_bets' in data


def test_api_cache_control_headers(client):
    res_leagues = client.get('/api/v1/leagues')
    assert 'max-age=300, stale-while-revalidate=3600' in res_leagues.headers.get('Cache-Control', '')

    res_live = client.get('/api/v1/live')
    assert 'no-store' in res_live.headers.get('Cache-Control', '')

    res_history = client.get('/api/v1/history?liga_id=1&days=7')
    assert 'max-age=30, stale-while-revalidate=300' in res_history.headers.get('Cache-Control', '')


def test_ttl_cache_stale_while_revalidate():
    import time
    from services.prediction_service import ttl_cache

    calls = []

    @ttl_cache(max_age_seconds=1, stale_while_revalidate=True)
    def compute_val(x):
        calls.append(x)
        return x * 10 + len(calls)

    # Initial miss -> synchronous call
    v1 = compute_val(5)
    assert v1 == 51
    assert len(calls) == 1

    # Immediate hit -> returns cached without calling
    v2 = compute_val(5)
    assert v2 == 51
    assert len(calls) == 1

    # Wait for TTL expiration -> returns stale immediately and triggers background refresh
    time.sleep(1.1)
    v3 = compute_val(5)
    assert v3 == 51
    time.sleep(0.1)
    assert len(calls) == 2
    assert compute_val(5) == 52


