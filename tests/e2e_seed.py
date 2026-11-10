"""
E2E Seed Data Hook
==================
Provee datos determinísticos en memoria cuando E2E_SEED_DATA=1 está activo,
evitando dependencias de red o bases de datos externas durante tests E2E de Playwright.
"""

from typing import Dict, List, Tuple


SEED_TEAMS = {
    1: ['Arsenal', 'Chelsea', 'Liverpool', 'Manchester City'],
    2: ['Barcelona', 'Real Madrid', 'Atletico Madrid'],
    8: ['Arsenal', 'Barcelona', 'Bayern Munich', 'Real Madrid'],
    10: ['Boca Juniors', 'River Plate', 'Racing Club', 'Independiente'],
}

SEED_FUERZAS = {
    'Arsenal': {
        'Ataque_Casa': 1.35, 'Defensa_Casa': 0.78,
        'Ataque_Fuera': 1.20, 'Defensa_Fuera': 0.85,
        'Goles_Favor_Reciente': 2.1, 'Goles_Contra_Reciente': 0.8,
        'Corners_Casa': 6.5, 'Corners_Fuera': 5.8,
        'Corners_Promedio': 6.2, 'Tarjetas_Am_Promedio': 1.6,
        'Tarjetas_Ro_Promedio': 0.06, 'Eficiencia_Tiro_Promedio_pct': 34.0,
        'BTTS_pct': 52.0, 'Over25_pct': 62.0, 'Goles_2T_Promedio': 1.2,
    },
    'Chelsea': {
        'Ataque_Casa': 1.12, 'Defensa_Casa': 0.94,
        'Ataque_Fuera': 1.04, 'Defensa_Fuera': 1.06,
        'Goles_Favor_Reciente': 1.5, 'Goles_Contra_Reciente': 1.2,
        'Corners_Casa': 5.4, 'Corners_Fuera': 4.8,
        'Corners_Promedio': 5.1, 'Tarjetas_Am_Promedio': 2.1,
        'Tarjetas_Ro_Promedio': 0.08, 'Eficiencia_Tiro_Promedio_pct': 29.0,
        'BTTS_pct': 55.0, 'Over25_pct': 54.0, 'Goles_2T_Promedio': 1.0,
    },
    'Liverpool': {
        'Ataque_Casa': 1.40, 'Defensa_Casa': 0.82,
        'Ataque_Fuera': 1.25, 'Defensa_Fuera': 0.90,
        'Goles_Favor_Reciente': 2.2, 'Goles_Contra_Reciente': 0.9,
        'Corners_Promedio': 6.5, 'Tarjetas_Am_Promedio': 1.4,
        'Tarjetas_Ro_Promedio': 0.04, 'Eficiencia_Tiro_Promedio_pct': 35.0,
        'BTTS_pct': 58.0, 'Over25_pct': 65.0, 'Goles_2T_Promedio': 1.3,
    },
    'Manchester City': {
        'Ataque_Casa': 1.50, 'Defensa_Casa': 0.75,
        'Ataque_Fuera': 1.32, 'Defensa_Fuera': 0.82,
        'Goles_Favor_Reciente': 2.4, 'Goles_Contra_Reciente': 0.7,
        'Corners_Promedio': 7.0, 'Tarjetas_Am_Promedio': 1.3,
        'Tarjetas_Ro_Promedio': 0.03, 'Eficiencia_Tiro_Promedio_pct': 37.0,
        'BTTS_pct': 50.0, 'Over25_pct': 68.0, 'Goles_2T_Promedio': 1.4,
    },
    'Real Madrid': {
        'Ataque_Casa': 1.45, 'Defensa_Casa': 0.80,
        'Ataque_Fuera': 1.28, 'Defensa_Fuera': 0.88,
        'Goles_Favor_Reciente': 2.3, 'Goles_Contra_Reciente': 0.8,
        'Corners_Promedio': 6.0, 'Tarjetas_Am_Promedio': 1.8,
        'Tarjetas_Ro_Promedio': 0.05, 'Eficiencia_Tiro_Promedio_pct': 36.0,
        'BTTS_pct': 54.0, 'Over25_pct': 64.0, 'Goles_2T_Promedio': 1.3,
    },
    'Barcelona': {
        'Ataque_Casa': 1.42, 'Defensa_Casa': 0.84,
        'Ataque_Fuera': 1.24, 'Defensa_Fuera': 0.92,
        'Goles_Favor_Reciente': 2.2, 'Goles_Contra_Reciente': 0.9,
        'Corners_Promedio': 6.1, 'Tarjetas_Am_Promedio': 1.9,
        'Tarjetas_Ro_Promedio': 0.06, 'Eficiencia_Tiro_Promedio_pct': 34.0,
        'BTTS_pct': 56.0, 'Over25_pct': 63.0, 'Goles_2T_Promedio': 1.2,
    },
    'Boca Juniors': {
        'Ataque_Casa': 1.22, 'Defensa_Casa': 0.82,
        'Ataque_Fuera': 1.02, 'Defensa_Fuera': 0.95,
        'Goles_Favor_Reciente': 1.6, 'Goles_Contra_Reciente': 0.8,
        'Corners_Promedio': 5.4, 'Tarjetas_Am_Promedio': 2.5,
        'Tarjetas_Ro_Promedio': 0.10, 'Eficiencia_Tiro_Promedio_pct': 30.0,
        'BTTS_pct': 46.0, 'Over25_pct': 45.0, 'Goles_2T_Promedio': 0.9,
    },
    'River Plate': {
        'Ataque_Casa': 1.35, 'Defensa_Casa': 0.78,
        'Ataque_Fuera': 1.15, 'Defensa_Fuera': 0.88,
        'Goles_Favor_Reciente': 1.9, 'Goles_Contra_Reciente': 0.7,
        'Corners_Promedio': 6.0, 'Tarjetas_Am_Promedio': 2.2,
        'Tarjetas_Ro_Promedio': 0.08, 'Eficiencia_Tiro_Promedio_pct': 33.0,
        'BTTS_pct': 48.0, 'Over25_pct': 52.0, 'Goles_2T_Promedio': 1.1,
    },
}


def apply_e2e_seed() -> None:
    """Inyecta datos determinísticos en los servicios para ejecución E2E."""
    import services.prediction_service as ps
    import services.fixtures_service as fs
    import services.audit_service as aus
    import web.blueprints.api as api_mod
    from timba_core import LIGAS

    def mock_cargar_datos_liga_cached(liga_id: int) -> Tuple[Dict, float, float, List[str]]:
        equipos = SEED_TEAMS.get(liga_id, ['Arsenal', 'Chelsea'])
        fuerzas = {k: SEED_FUERZAS.get(k, SEED_FUERZAS['Arsenal']) for k in equipos}
        return fuerzas, 1.45, 1.15, sorted(list(fuerzas.keys()))

    def mock_obtener_fixtures_cached(liga_id: int) -> List[Dict]:
        equipos = SEED_TEAMS.get(liga_id, ['Arsenal', 'Chelsea'])
        return [
            {
                'local': equipos[0],
                'visitante': equipos[1],
                'fecha': '2026-11-15 16:00',
                'fecha_utc': '2026-11-15T19:00:00Z',
            }
        ]

    def mock_cargar_dashboard_cache():
        return {
            'total_ligas': len(LIGAS),
            'ligas': LIGAS,
            'total_partidos_hoy': 2,
            'updated_at': '2026-11-10T15:00:00Z',
            'partidos_hoy': {
                1: {
                    'nombre': 'Premier League (Inglaterra)',
                    'partidos': [
                        {
                            'local': 'Arsenal',
                            'visitante': 'Chelsea',
                            'hora': '16:00',
                            'fecha_utc': '2026-11-10T19:00:00Z',
                            'recomendacion': '1X',
                            'prediccion': {'local': 54, 'empate': 25, 'visitante': 21},
                        }
                    ],
                },
                10: {
                    'nombre': 'Liga Profesional (Argentina)',
                    'partidos': [
                        {
                            'local': 'Boca Juniors',
                            'visitante': 'River Plate',
                            'hora': '18:00',
                            'fecha_utc': '2026-11-10T21:00:00Z',
                            'recomendacion': 'Under 3.5',
                            'prediccion': {'local': 38, 'empate': 32, 'visitante': 30},
                        }
                    ],
                },
            },
        }

    def mock_obtener_partidos_locales():
        return [
            {
                'status': 'IN_PLAY',
                'seccion': 'live',
                'minute': 62,
                'competition': {'name': 'Premier League', 'area': {'name': 'England'}},
                'homeTeam': {'name': 'Arsenal'},
                'awayTeam': {'name': 'Chelsea'},
                'score': {'fullTime': {'home': 2, 'away': 1}},
                'utcDate': '2026-11-10T19:00:00Z',
                'prediccion_timba': {'prob_local': 65, 'prob_empate': 20, 'prob_visitante': 15, 'over_25': 72},
                'prediccion_live': {
                    'minuto': 62,
                    'prob_local': 78.5,
                    'prob_empate': 15.0,
                    'prob_visitante': 6.5,
                    'xG_restante_local': 0.52,
                    'xG_restante_vis': 0.38,
                    'proximo_gol': {'local': 42.0, 'visitante': 31.0, 'sin_mas_goles': 27.0},
                    'estado_tactico': 'Ventaja Local',
                },
                'prediccion_prematch': {
                    'prob_local': 54.0,
                    'prob_empate': 25.0,
                    'prob_visitante': 21.0,
                    'xg_local': 1.65,
                    'xg_vis': 1.05,
                },
            },
            {
                'status': 'TIMED',
                'seccion': 'proximos',
                'minute': 0,
                'competition': {'name': 'Liga Profesional', 'area': {'name': 'Argentina'}},
                'homeTeam': {'name': 'Boca Juniors'},
                'awayTeam': {'name': 'River Plate'},
                'score': {'fullTime': {'home': 0, 'away': 0}},
                'utcDate': '2026-11-10T21:00:00Z',
                'prediccion_timba': {'prob_local': 38, 'prob_empate': 32, 'prob_visitante': 30, 'over_25': 44},
            },
        ]

    def mock_obtener_historial_audit(liga_id: int, days: int = 7):
        resultados = [
            {
                'fecha': '2026-11-08',
                'local': 'Arsenal',
                'visitante': 'Liverpool',
                'goles_local': 2,
                'goles_visitante': 1,
                'resultado_real': 'HOME_WIN',
                'prediccion_ia': '1X',
                'prediccion_prob': 74,
                'prob_local': 48,
                'prob_empate': 26,
                'prob_visitante': 26,
                'acierto': True,
            },
            {
                'fecha': '2026-11-07',
                'local': 'Chelsea',
                'visitante': 'Manchester City',
                'goles_local': 1,
                'goles_visitante': 1,
                'resultado_real': 'DRAW',
                'prediccion_ia': 'AWAY_WIN',
                'prediccion_prob': 56,
                'prob_local': 22,
                'prob_empate': 22,
                'prob_visitante': 56,
                'acierto': False,
            },
        ]
        stats = {
            'total_partidos': 2,
            'evaluados': 2,
            'aciertos': 1,
            'fallos': 1,
            'sin_prediccion': 0,
            'precision': 50.0,
        }
        return resultados, stats

    ps.cargar_datos_liga_cached = mock_cargar_datos_liga_cached
    ps.obtener_fixtures_cached = mock_obtener_fixtures_cached
    ps.cargar_dashboard_cache = mock_cargar_dashboard_cache
    api_mod.obtener_fixtures_cached = mock_obtener_fixtures_cached
    api_mod.cargar_dashboard_cache = mock_cargar_dashboard_cache
    api_mod.obtener_partidos_locales = mock_obtener_partidos_locales
    api_mod.enriquecer_partidos_con_prediccion = lambda p: p
    api_mod.ordenar_partidos_por_liga = lambda p: p
    api_mod.obtener_historial_audit = mock_obtener_historial_audit
    fs.obtener_partidos_locales = mock_obtener_partidos_locales
    aus.obtener_historial_audit = mock_obtener_historial_audit
