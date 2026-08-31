"""
Unit tests for Centralized League and Competition Configuration
==============================================================
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from config.leagues import (
    LIGAS,
    URLS_FIXTURE,
    CSV_A_LIGA_ID,
    get_league_by_id,
    get_league_by_code,
    get_all_leagues,
)
from timba_core import LIGAS as CORE_LIGAS, URLS_FIXTURE as CORE_FIXTURES


def test_ligas_canonical_structure():
    """Verifica que LIGAS contenga todas las ligas esperadas con los atributos requeridos."""
    assert len(LIGAS) >= 9
    
    expected_ids = [1, 2, 3, 4, 5, 6, 7, 8, 10]
    for lid in expected_ids:
        assert lid in LIGAS
        info = LIGAS[lid]
        assert 'nombre' in info
        assert 'codigo' in info
        assert 'bandera' in info


def test_urls_fixture_mapping():
    """Verifica que todos los fixtures apunten a URLs válidas."""
    for lid in [1, 2, 3, 4, 5, 6, 7, 8, 10]:
        assert lid in URLS_FIXTURE
        assert 'url' in URLS_FIXTURE[lid]
        assert URLS_FIXTURE[lid]['url'].startswith('http')


def test_csv_to_liga_id_consistency():
    """Verifica consistencia bidireccional entre códigos CSV y IDs de liga."""
    assert CSV_A_LIGA_ID['E0'] == 1
    assert CSV_A_LIGA_ID['SP1'] == 2
    assert CSV_A_LIGA_ID['I1'] == 3
    assert CSV_A_LIGA_ID['D1'] == 4
    assert CSV_A_LIGA_ID['F1'] == 5
    assert CSV_A_LIGA_ID['P1'] == 6
    assert CSV_A_LIGA_ID['N1'] == 7
    assert CSV_A_LIGA_ID['CL'] == 8
    assert CSV_A_LIGA_ID['ARG'] == 10


def test_helper_functions():
    """Verifica las funciones helper de búsqueda."""
    premier = get_league_by_id(1)
    assert premier is not None
    assert premier['codigo'] == 'E0'
    
    laliga = get_league_by_code('SP1')
    assert laliga is not None
    assert laliga['nombre'].startswith('La Liga')
    
    all_l = get_all_leagues()
    assert len(all_l) == len(LIGAS)


def test_timba_core_backward_compatibility():
    """Verifica que timba_core exponga exactamente los mismos objetos."""
    assert CORE_LIGAS is LIGAS
    assert CORE_FIXTURES is URLS_FIXTURE
