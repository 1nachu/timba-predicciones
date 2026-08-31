"""
Frontend and UI Verification Tests
===================================
"""

import pytest
import os
import sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from app import app, LIGAS


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_base_layout_structure(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    
    # Assert core layout components
    assert soup.find('nav', class_='navbar-promiedos') is not None
    assert soup.find('aside', class_='sidebar') is not None
    assert soup.find('main', class_='main-content') is not None
    assert soup.find('footer') is not None
    assert soup.find('div', id='bitcoinModal') is not None
    assert soup.find('script', src=lambda s: s and 'htmx' in s) is not None


def test_predict_form_page_and_leagues(client):
    response = client.get('/predict')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    
    # Selectors for local and visitante exist
    select_local = soup.find('select', attrs={'name': 'local'})
    select_vis = soup.find('select', attrs={'name': 'visitante'})
    assert select_local is not None
    assert select_vis is not None


def test_predict_post_submission(client):
    response = client.post('/predict', data={
        'liga_id': '1',
        'local': 'Arsenal',
        'visitante': 'Chelsea'
    })
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    
    assert 'Arsenal' in html
    assert 'Chelsea' in html
    assert 'Victoria Local' in html or 'Prob_Local' in html or '%' in html


def test_predict_same_team_warning(client):
    response = client.post('/predict', data={
        'liga_id': '1',
        'local': 'Arsenal',
        'visitante': 'Arsenal'
    }, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Debes seleccionar dos equipos diferentes' in html or 'warning' in html


from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_external_network_calls():
    """Mock external scraping calls to keep test suite fast and deterministic."""
    sample_fixtures = [
        {'local': 'Arsenal', 'visitante': 'Chelsea', 'fecha': '2026-09-01 16:00', 'fecha_utc': '2026-09-01T19:00:00Z'},
        {'local': 'Real Madrid', 'visitante': 'Barcelona', 'fecha': '2026-09-02 20:00', 'fecha_utc': '2026-09-02T23:00:00Z'},
        {'local': 'Boca Juniors', 'visitante': 'River Plate', 'fecha': '2026-09-03 18:00', 'fecha_utc': '2026-09-03T21:00:00Z'}
    ]
    with patch('app.obtener_proximos_partidos', return_value=sample_fixtures):
        yield


def test_fixtures_all_supported_leagues(client):
    for liga_id in [1, 2, 3, 4, 5, 6, 7, 8, 10]:
        res = client.get(f'/fixtures?liga_id={liga_id}')
        assert res.status_code == 200
        html = res.data.decode('utf-8')
        assert 'Próximos Partidos' in html
        assert '{{' not in html and '{%' not in html


def test_history_all_views(client):
    for code in ['E0', 'SP1', 'ARG']:
        res = client.get(f'/history?league_code={code}&days=7')
        assert res.status_code == 200
        html = res.data.decode('utf-8')
        assert 'Auditoría' in html or 'Historial' in html
        assert '{{' not in html and '{%' not in html


def test_live_scores_view(client):
    res = client.get('/live')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'PARTIDOS EN VIVO' in html or 'Resultados' in html or 'live' in html
    assert '{{' not in html and '{%' not in html


def test_static_files_served_properly(client):
    assets = [
        '/static/style.css',
        '/static/htmx.min.js',
        '/static/bootstrap.min.css',
        '/static/bootstrap.bundle.min.js',
        '/static/fonts/bootstrap-icons.woff2',
        '/static/favicon.png'
    ]
    for asset in assets:
        r = client.get(asset)
        assert r.status_code == 200, f"Failed to load {asset}: status {r.status_code}"
