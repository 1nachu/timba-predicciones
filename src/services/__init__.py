"""
Services Package - Timba Predictor
===================================
Lógica de negocio desacoplada para auditoría, fixtures, predicciones y marcadores en vivo.
"""

from services.audit_service import (
    determinar_resultado_real,
    determinar_prediccion_ia,
    validar_acierto,
    obtener_historial_audit,
    sincronizar_resultados_audit,
)
from services.fixtures_service import (
    obtener_partidos_locales,
    limpiar_partidos_viejos,
    ordenar_partidos_por_liga,
    enriquecer_partidos_con_prediccion,
    normalizar_nombre_equipo,
    get_team_normalizer,
)
from services.prediction_service import (
    cargar_dashboard_cache,
    obtener_last_update,
)
