"""
REST API v1 Blueprint
======================
Endpoints REST JSON para consumo de predicciones, fixtures, marcadores en vivo, dashboard y auditoría.
"""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from timba_core import LIGAS, URLS_FIXTURE, predecir_partido_en_vivo
from utils.markets import generar_recomendaciones, evaluar_value_bets, obtener_mejor_recomendacion
from services.fixtures_service import (
    obtener_partidos_locales,
    enriquecer_partidos_con_prediccion,
    ordenar_partidos_por_liga,
)
from services.audit_service import obtener_historial_audit
from services.prediction_service import (
    predecir_partido_cached,
    obtener_fixtures_cached,
    cargar_dashboard_cache,
    obtener_last_update,
    obtener_equipos_liga,
    predecir_manual,
)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.after_request
def add_cache_headers(response):
    """Agrega cabeceras Cache-Control óptimas según la frecuencia de cambio de cada endpoint."""
    if response.status_code != 200:
        return response
    path = request.path
    if path.endswith('/live') or path.endswith('/health'):
        response.headers['Cache-Control'] = 'no-store'
    elif '/leagues' in path:
        response.headers['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=3600'
    else:
        response.headers['Cache-Control'] = 'public, max-age=30, stale-while-revalidate=300'
    return response

LIGAS_HISTORY = {
    liga['codigo']: {
        'nombre': liga['nombre'],
        'bandera': liga.get('bandera', '⚽'),
        'liga_id': liga_id,
        'codigo': liga['codigo'],
    }
    for liga_id, liga in LIGAS.items()
    if liga.get('url') is not None and liga.get('codigo')
}


@api_bp.route('/health', methods=['GET'])
def health():
    """Health check del servicio API."""
    return jsonify({
        'status': 'ok',
        'version': '3.0',
        'service': 'Timba Predictor API',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@api_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Obtiene los datos del dashboard principal con partidos del día."""
    cache_data = cargar_dashboard_cache()

    if cache_data:
        return jsonify({
            'total_ligas': cache_data.get('total_ligas', len(LIGAS)),
            'ligas': cache_data.get('ligas', LIGAS),
            'partidos_hoy': cache_data.get('partidos_hoy', {}),
            'total_partidos_hoy': cache_data.get('total_partidos_hoy', 0),
            'last_update': obtener_last_update(),
            'updated_at': cache_data.get('updated_at', ''),
            'cache_missing': False,
        })

    return jsonify({
        'total_ligas': len(LIGAS),
        'ligas': LIGAS,
        'partidos_hoy': {},
        'total_partidos_hoy': 0,
        'last_update': 'Actualizando...',
        'updated_at': '',
        'cache_missing': True,
    })


@api_bp.route('/leagues', methods=['GET'])
def get_leagues():
    """Lista de ligas soportadas y metadatos."""
    ligas_list = []
    for liga_id, info in LIGAS.items():
        ligas_list.append({
            'id': liga_id,
            'nombre': info.get('nombre', ''),
            'codigo': info.get('codigo', ''),
            'bandera': info.get('bandera', '⚽'),
            'has_fixture': liga_id in URLS_FIXTURE
        })
    return jsonify({'total': len(ligas_list), 'leagues': ligas_list})


@api_bp.route('/leagues/<int:liga_id>/teams', methods=['GET'])
def get_league_teams(liga_id: int):
    """Lista ordenada de equipos disponibles para una liga."""
    if liga_id not in LIGAS:
        return jsonify({'error': f'Liga {liga_id} no encontrada'}), 404

    equipos = obtener_equipos_liga(liga_id)
    avisos = []
    if not equipos:
        avisos.append({
            'nivel': 'warning',
            'mensaje': 'No se pudieron cargar datos de la liga. Verifica tu conexión.'
        })

    return jsonify({
        'liga_id': liga_id,
        'liga': LIGAS[liga_id].get('nombre', ''),
        'equipos': equipos,
        'avisos': avisos,
    })


@api_bp.route('/predict', methods=['GET'])
def predict_match():
    """
    Calcula predicción para un partido.
    Query params:
        - liga_id (int): ID de la liga (ej: 1)
        - local (str): Nombre del equipo local
        - visitante (str): Nombre del equipo visitante
        - odds_home (float, opcional): Cuota local para cálculo de EV
        - odds_draw (float, opcional): Cuota empate
        - odds_away (float, opcional): Cuota visitante
    """
    liga_id = request.args.get('liga_id', type=int)
    local = request.args.get('local', type=str)
    visitante = request.args.get('visitante', type=str)

    if not liga_id or not local or not visitante:
        return jsonify({
            'error': 'Parámetros requeridos: liga_id, local, visitante',
            'avisos': [{'nivel': 'warning', 'mensaje': 'Parámetros requeridos: liga_id, local, visitante'}]
        }), 400

    if local == visitante:
        return jsonify({
            'error': 'Los equipos local y visitante deben ser diferentes',
            'avisos': [{'nivel': 'warning', 'mensaje': 'Debes seleccionar dos equipos diferentes.'}]
        }), 400

    pred, avisos, local_norm, vis_norm = predecir_manual(liga_id, local, visitante)
    if not pred:
        err_msg = avisos[-1]['mensaje'] if avisos else f'No se encontraron datos o equipos para {local} vs {visitante} en liga {liga_id}'
        return jsonify({
            'error': err_msg,
            'avisos': avisos
        }), 404

    # Cuotas opcionales para Value Betting
    cuotas = {}
    if request.args.get('odds_home'):
        cuotas['B365H'] = request.args.get('odds_home', type=float)
    if request.args.get('odds_draw'):
        cuotas['B365D'] = request.args.get('odds_draw', type=float)
    if request.args.get('odds_away'):
        cuotas['B365A'] = request.args.get('odds_away', type=float)

    value_bets = evaluar_value_bets(pred, cuotas) if cuotas else []
    recomendaciones = generar_recomendaciones(pred)

    # Predicción Live In-Play opcional
    is_live = request.args.get('live', 'false').lower() in ['true', '1'] or request.args.get('minute') is not None
    pred_live = None
    if is_live:
        h_score = request.args.get('home_score', 0, type=int)
        a_score = request.args.get('away_score', 0, type=int)
        minute = request.args.get('minute', 0, type=int)
        red_h = request.args.get('red_cards_home', 0, type=int)
        red_a = request.args.get('red_cards_away', 0, type=int)

        pred_live = predecir_partido_en_vivo(
            local_norm, vis_norm, {}, 0.0, 0.0,
            home_score=h_score, away_score=a_score,
            minute=minute, red_cards_home=red_h, red_cards_away=red_a,
            pred_prematch=pred
        )

    def _sf(val, default=0.0) -> float:
        if val is None:
            return default
        try:
            f = float(val)
            return default if (f != f or f == float('inf') or f == float('-inf')) else f
        except (ValueError, TypeError):
            return default

    prob_pre = {
        'local': round(_sf(pred.get('Prob_Local', 0)) * 100, 2),
        'empate': round(_sf(pred.get('Prob_Empate', 0)) * 100, 2),
        'visitante': round(_sf(pred.get('Prob_Vis', 0)) * 100, 2),
        'doble_oportunidad': {
            '1X': round(_sf(pred.get('Prob_1X', 0)) * 100, 2),
            'X2': round(_sf(pred.get('Prob_X2', 0)) * 100, 2),
            '12': round(_sf(pred.get('Prob_12', 0)) * 100, 2)
        }
    }
    xg_pre = {
        'local': round(_sf(pred.get('xG_Local', 0)), 2),
        'visitante': round(_sf(pred.get('xG_Vis', 0)), 2),
        'total': round(_sf(pred.get('xG_Local', 0)) + _sf(pred.get('xG_Vis', 0)), 2)
    }

    corners_data = {
        'total': round(_sf(pred.get('Corners_Lambda_Total', 0)), 1),
        'local': round(_sf(pred.get('Corners_Local', 0)), 1),
        'visitante': round(_sf(pred.get('Corners_Vis', 0)), 1),
        'prob_local_mas_corners': round(_sf(pred.get('Prob_Local_Mas_Corners', 0)) * 100, 1),
        'over_85': round(_sf(pred.get('Over_85', 0)) * 100, 1),
        'over_95': round(_sf(pred.get('Over_95', 0)) * 100, 1),
    }

    tarjetas_data = {
        'amarillas_total': round(_sf(pred.get('Tarjetas_Am_Total', 0)), 1),
        'amarillas_local': round(_sf(pred.get('Tarjetas_Am_Local', 0)), 1),
        'amarillas_visitante': round(_sf(pred.get('Tarjetas_Am_Vis', 0)), 1),
        'rojas_local': round(_sf(pred.get('Tarjetas_Ro_Local', 0)), 2),
        'rojas_visitante': round(_sf(pred.get('Tarjetas_Ro_Vis', 0)), 2),
        'prob_roja': round(_sf(pred.get('Prob_Red_Card', 0)) * 100, 1),
        'over_25': round(_sf(pred.get('Over_25_Cards', 0)) * 100, 0),
        'over_35': round(_sf(pred.get('Over_35_Cards', 0)) * 100, 0),
        'over_45': round(_sf(pred.get('Over_45_Cards', 0)) * 100, 0),
        'under_55': round(_sf(pred.get('Under_55_Cards', 0)) * 100, 0),
    }

    liga_info = LIGAS.get(liga_id, {})

    return jsonify({
        'local': local_norm,
        'visitante': vis_norm,
        'liga_id': liga_id,
        'liga': liga_info.get('nombre', ''),
        'avisos': avisos,
        'prediccion_prematch': {
            'probabilidades': prob_pre,
            'goles_esperados': xg_pre,
            'top_marcadores': pred.get('Top_3_Marcadores', []),
            'recomendaciones': recomendaciones,
            'value_bets': value_bets
        },
        'prediccion_live': pred_live,
        'probabilidades': prob_pre,
        'goles_esperados': xg_pre,
        'mercados': {
            'over_15': round(_sf(pred.get('Over_15', 0)) * 100, 2),
            'over_25': round(_sf(pred.get('Over_25', 0)) * 100, 2),
            'under_35': round(_sf(pred.get('Under_35', 0)) * 100, 2),
            'corners_promedio': round(_sf(pred.get('Corners_Lambda_Total', 0)), 1),
            'tarjetas_promedio': round(_sf(pred.get('Tarjetas_Am_Total', 0)), 1),
            'prob_tarjeta_roja': round(_sf(pred.get('Prob_Red_Card', 0)) * 100, 2)
        },
        'corners': corners_data,
        'tarjetas': tarjetas_data,
        'top_marcadores': pred.get('Top_3_Marcadores', []),
        'recomendaciones': recomendaciones,
        'value_bets': value_bets
    })


@api_bp.route('/fixtures', methods=['GET'])
def get_fixtures():
    """Obtiene próximos fixtures de una liga con predicciones enriquecidas."""
    liga_id = request.args.get('liga_id', 1, type=int)

    if liga_id not in LIGAS:
        return jsonify({'error': f'Liga {liga_id} no encontrada'}), 404

    liga_info = LIGAS[liga_id]
    fixtures_raw = obtener_fixtures_cached(liga_id)
    enriched = []
    avisos = []

    if not fixtures_raw:
        avisos.append({
            'nivel': 'info',
            'mensaje': f"📭 No se encontraron partidos próximos para {liga_info['nombre']}"
        })

    for f in fixtures_raw:
        item = {
            'local': f.get('local'),
            'visitante': f.get('visitante'),
            'fecha': f.get('fecha', 'Próximamente'),
            'fecha_utc': f.get('fecha_utc'),
            'prediccion': None,
            'mejor_recomendacion': None,
            'recomendacion': None,
            'error': None,
        }
        try:
            pred = predecir_partido_cached(liga_id, f.get('local', ''), f.get('visitante', ''))
            if pred:
                item['prediccion'] = {
                    'local': round(pred.get('Prob_Local', 0) * 100, 1),
                    'empate': round(pred.get('Prob_Empate', 0) * 100, 1),
                    'visitante': round(pred.get('Prob_Vis', 0) * 100, 1)
                }
                reco = obtener_mejor_recomendacion(pred)
                item['mejor_recomendacion'] = reco
                item['recomendacion'] = reco
            else:
                item['error'] = f"No encontrado: {f.get('local')}"
        except Exception as e:
            item['error'] = str(e)[:30]
        enriched.append(item)

    return jsonify({
        'liga_id': liga_id,
        'liga': liga_info.get('nombre', ''),
        'liga_actual': {
            'id': liga_id,
            'nombre': liga_info.get('nombre', ''),
            'codigo': liga_info.get('codigo', ''),
            'bandera': liga_info.get('bandera', '⚽'),
        },
        'total': len(enriched),
        'partidos': enriched,
        'avisos': avisos,
    })


@api_bp.route('/live', methods=['GET'])
def get_live():
    """Obtiene partidos en vivo y programados de hoy con predicciones."""
    partidos = obtener_partidos_locales()
    if partidos:
        try:
            partidos = enriquecer_partidos_con_prediccion(partidos)
            partidos = ordenar_partidos_por_liga(partidos)
        except Exception:
            pass
    return jsonify({
        'total': len(partidos),
        'partidos': partidos,
        'es_demo': False,
    })


@api_bp.route('/history', methods=['GET'])
def get_history():
    """Obtiene historial de auditoría de predicciones."""
    default_league_code = next(iter(LIGAS_HISTORY)) if LIGAS_HISTORY else 'E0'
    league_code_param = request.args.get('league_code', type=str)
    liga_id_param = request.args.get('liga_id', type=int)
    days = request.args.get('days', 7, type=int)

    avisos = []
    if days not in [7, 14, 30]:
        days = 7

    if league_code_param:
        code = league_code_param.upper()
        if code not in LIGAS_HISTORY:
            avisos.append({
                'nivel': 'warning',
                'mensaje': f"⚠️ Liga '{code}' no soportada."
            })
            code = default_league_code
        liga_info = LIGAS_HISTORY[code]
        liga_id = liga_info['liga_id']
        league_code = code
    elif liga_id_param and liga_id_param in LIGAS:
        liga_id = liga_id_param
        raw_info = LIGAS[liga_id]
        league_code = raw_info.get('codigo') or default_league_code
        liga_info = LIGAS_HISTORY.get(league_code, {
            'nombre': raw_info.get('nombre', ''),
            'bandera': raw_info.get('bandera', '⚽'),
            'liga_id': liga_id,
            'codigo': league_code,
        })
    else:
        league_code = default_league_code
        liga_info = LIGAS_HISTORY[league_code]
        liga_id = liga_info['liga_id']

    es_demo = False
    try:
        resultados, stats = obtener_historial_audit(liga_id, days)
    except Exception:
        es_demo = True
        resultados = []
        stats = {
            'total_partidos': 0,
            'evaluados': 0,
            'aciertos': 0,
            'fallos': 0,
            'sin_prediccion': 0,
            'precision': 0.0
        }

    return jsonify({
        'liga_id': liga_id,
        'league_code': league_code,
        'days': days,
        'liga_actual': liga_info,
        'ligas': LIGAS_HISTORY,
        'es_demo': es_demo,
        'avisos': avisos,
        'estadisticas': stats,
        'resultados': resultados
    })


@api_bp.route('/value-bets', methods=['GET'])
def get_value_bets():
    """
    Escanea y retorna oportunidades de Value Betting (EV > 3%)
    para los próximos fixtures o partidos disponibles.
    """
    min_ev = request.args.get('min_ev', 0.03, type=float)
    detected_value_bets = []

    for liga_id, info in LIGAS.items():
        if not info.get('url'):
            continue
        fixtures_raw = obtener_fixtures_cached(liga_id)
        for f in fixtures_raw[:10]:
            local = f.get('local')
            vis = f.get('visitante')
            if not local or not vis:
                continue
            pred = predecir_partido_cached(liga_id, local, vis)
            if not pred:
                continue

            # Si hay cuotas asociadas en fixture
            odds = f.get('odds', {})
            if not odds:
                # Generar cuotas de referencia si no vienen en feed
                p_l = pred.get('Prob_Local', 0.33)
                p_v = pred.get('Prob_Vis', 0.33)
                p_x = pred.get('Prob_Empate', 0.34)
                # Estimación de mercado con margen 5%
                odds = {
                    'B365H': round(1.0 / (p_l * 0.95), 2) if p_l > 0 else 2.0,
                    'B365D': round(1.0 / (p_x * 0.95), 2) if p_x > 0 else 3.0,
                    'B365A': round(1.0 / (p_v * 0.95), 2) if p_v > 0 else 3.0,
                }

            vb = evaluar_value_bets(pred, odds, min_ev=min_ev)
            for item in vb:
                detected_value_bets.append({
                    'liga': info.get('nombre'),
                    'liga_id': liga_id,
                    'partido': f"{local} vs {vis}",
                    'fecha': f.get('fecha', 'Próximo'),
                    **item
                })

    detected_value_bets.sort(key=lambda x: x.get('ev_pct', 0), reverse=True)
    return jsonify({
        'total_value_bets': len(detected_value_bets),
        'min_ev_threshold': min_ev,
        'value_bets': detected_value_bets[:30]
    })
