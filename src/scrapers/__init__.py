"""
Módulo de scrapers para recolección de fixtures y partidos.
"""

from .fixtures_scraper import obtener_proximos_partidos, _scrape_promiedos

__all__ = [
    'obtener_proximos_partidos',
    '_scrape_promiedos',
]
