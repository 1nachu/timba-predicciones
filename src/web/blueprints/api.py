"""
REST API v1 Blueprint
======================
Endpoints REST JSON para consumo de predicciones, fixtures, marcadores en vivo y auditoría.
"""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from timba_core import LIGAS, URLS_FIXTURE, emparejar_equipo
from utils.markets import generar_recomendaciones, evaluar_value_bets, obtener_mejor_recomendacion
from services.fixtures_service import obtener_partidos_locales, enriquecer_partidos_con_prediccion, ordenar_partidos_por_liga
from services.audit_service import obtener_historial_audit

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.route('/health', methods=['GET'])
def health():
    """Health check del servicio API."""
    return jsonify({
        'status': 'ok',
        'version': '2.2',
        'service': 'Timba Predictor API',
        'timestamp': datetime.now(timezone.utc).isoformat()
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
    from app import predecir_partido_cached, cargar_datos_liga, predecir_partido
    
    liga_id = request.args.get('liga_id', type=int)
    local = request.args.get('local', type=str)
    visitante = request.args.get('visitante', type=str)
    
    if not liga_id or not local or not visitante:
        return jsonify({'error': 'Parámetros requeridos: liga_id, local, visitante'}), 400
        
    if local == visitante:
        return jsonify({'error': 'Los equipos local y visitante deben ser diferentes'}), 400

    pred = predecir_partido_cached(liga_id, local, visitante)
    if not pred:
        return jsonify({'error': f'No se encontraron datos o equipos para {local} vs {visitante} en liga {liga_id}'}), 404
        
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

    return jsonify({
        'local': local,
        'visitante': visitante,
        'liga_id': liga_id,
        'probabilidades': {
            'local': round(pred.get('Prob_Local', 0) * 100, 2),
            'empate': round(pred.get('Prob_Empate', 0) * 100, 2),
            'visitante': round(pred.get('Prob_Vis', 0) * 100, 2),
            'doble_oportunidad': {
                '1X': round(pred.get('Prob_1X', 0) * 100, 2),
                'X2': round(pred.get('Prob_X2', 0) * 100, 2),
                '12': round(pred.get('Prob_12', 0) * 100, 2)
            }
        },
        'goles_esperados': {
            'local': round(pred.get('xG_Local', 0), 2),
            'visitante': round(pred.get('xG_Vis', 0), 2),
            'total': round(pred.get('xG_Local', 0) + pred.get('xG_Vis', 0), 2)
        },
        'mercados': {
            'over_15': round(pred.get('Over_15', 0) * 100, 2),
            'over_25': round(pred.get('Over_25', 0) * 100, 2),
            'under_35': round(pred.get('Under_35', 0) * 100, 2),
            'corners_promedio': round(pred.get('Corners_Lambda_Total', 0), 1),
            'tarjetas_promedio': round(pred.get('Tarjetas_Am_Total', 0), 1),
            'prob_tarjeta_roja': round(pred.get('Prob_Red_Card', 0) * 100, 2)
        },
        'top_marcadores': pred.get('Top_3_Marcadores', []),
        'recomendaciones': recomendaciones,
        'value_bets': value_bets
    })


@api_bp.route('/fixtures', methods=['GET'])
def get_fixtures():
    """Obtiene próximos fixtures de una liga con predicciones enriquecidas."""
    from app import obtener_fixtures_cached, predecir_partido_cached
    liga_id = request.args.get('liga_id', 1, type=int)
    
    if liga_id not in LIGAS:
        return jsonify({'error': f'Liga {liga_id} no encontrada'}), 404
        
    fixtures_raw = obtener_fixtures_cached(liga_id)
    enriched = []
    
    for f in fixtures_raw:
        item = {
            'local': f.get('local'),
            'visitante': f.get('visitante'),
            'fecha': f.get('fecha'),
            'fecha_utc': f.get('fecha_utc'),
            'prediccion': None,
            'mejor_recomendacion': None
        }
        pred = predecir_partido_cached(liga_id, f.get('local', ''), f.get('visitante', ''))
        if pred:
            item['prediccion'] = {
                'local': round(pred.get('Prob_Local', 0) * 100, 1),
                'empate': round(pred.get('Prob_Empate', 0) * 100, 1),
                'visitante': round(pred.get('Prob_Vis', 0) * 100, 1)
            }
            item['mejor_recomendacion'] = obtener_mejor_recomendacion(pred)
        enriched.append(item)
        
    return jsonify({
        'liga_id': liga_id,
        'liga': LIGAS[liga_id].get('nombre', ''),
        'total': len(enriched),
        'partidos': enriched
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
        'partidos': partidos
    })


@api_bp.route('/history', methods=['GET'])
def get_history():
    """Obtiene historial de auditoría de predicciones."""
    liga_id = request.args.get('liga_id', 1, type=int)
    days = request.args.get('days', 7, type=int)
    
    resultados, stats = obtener_historial_audit(liga_id, days)
    return jsonify({
        'liga_id': liga_id,
        'days': days,
        'estadisticas': stats,
        'resultados': resultados
    })
