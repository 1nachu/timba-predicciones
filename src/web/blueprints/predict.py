"""
Predict Blueprint
=================
Formulario y cálculo de predicciones manuales entre equipos.
"""

from flask import Blueprint, render_template, request, flash, current_app
from timba_core import LIGAS, CHAMPIONS_EQUIPO_LIGA, emparejar_equipo, predecir_partido
from utils.markets import generar_recomendaciones, evaluar_value_bets
from services.prediction_service import cargar_datos_liga, predecir_partido_cached

predict_bp = Blueprint('predict', __name__)


@predict_bp.route('/predict', methods=['GET', 'POST'], endpoint='predict')
def predict():
    """Formulario de predicción manual con normalización y mercados."""
    
    liga_id = int(request.args.get('liga_id', request.form.get('liga_id', 1)))
    
    if liga_id == 8:
        equipos = sorted(CHAMPIONS_EQUIPO_LIGA.keys())
        df, fuerzas, media_local, media_vis = None, {}, 0.0, 0.0
    else:
        df, fuerzas, media_local, media_vis, equipos = cargar_datos_liga(liga_id)

    if not equipos:
        flash("⚠️ No se pudieron cargar datos de la liga. Verifica tu conexión.", "warning")
    
    prediction = None
    recomendaciones = []
    seleccion_local = None
    seleccion_visita = None
    
    if request.method == 'POST':
        seleccion_local = request.form.get('local')
        seleccion_visita = request.form.get('visitante')
    else:
        seleccion_local = request.args.get('local')
        seleccion_visita = request.args.get('visitante')
    
    if seleccion_local and seleccion_visita and seleccion_local != seleccion_visita:
        if liga_id == 8:
            prediction = predecir_partido_cached(liga_id, seleccion_local, seleccion_visita)
            if prediction:
                recomendaciones = generar_recomendaciones(prediction)
            else:
                flash("❌ No se pudo generar predicción para Champions League.", "danger")
        else:
            equipos_validos = list(fuerzas.keys()) if fuerzas else []
            if equipos_validos:
                local_norm = emparejar_equipo(seleccion_local, equipos_validos)
                vis_norm = emparejar_equipo(seleccion_visita, equipos_validos)
                
                if local_norm in fuerzas and vis_norm in fuerzas:
                    prediction = predecir_partido(local_norm, vis_norm, fuerzas, media_local, media_vis)
                    if prediction:
                        recomendaciones = generar_recomendaciones(prediction)
                        if local_norm != seleccion_local:
                            flash(f"ℹ️ '{seleccion_local}' normalizado a '{local_norm}'", "info")
                        if vis_norm != seleccion_visita:
                            flash(f"ℹ️ '{seleccion_visita}' normalizado a '{vis_norm}'", "info")
                        seleccion_local = local_norm
                        seleccion_visita = vis_norm
                else:
                    errores = []
                    if local_norm not in fuerzas:
                        errores.append(f"'{seleccion_local}' → no encontrado (intenté: '{local_norm}')")
                    if vis_norm not in fuerzas:
                        errores.append(f"'{seleccion_visita}' → no encontrado (intenté: '{vis_norm}')")
                    flash(f"❌ Equipos no encontrados en BD: {', '.join(errores)}", "danger")
            else:
                flash("❌ No hay datos de equipos disponibles para esta liga.", "danger")
                
    elif seleccion_local and seleccion_visita and seleccion_local == seleccion_visita:
        flash("⚠️ Debes seleccionar dos equipos diferentes.", "warning")

    return render_template(
        'predict.html',
        equipos=equipos,
        prediction=prediction,
        recomendaciones=recomendaciones,
        seleccion_local=seleccion_local,
        seleccion_visita=seleccion_visita,
        liga_id=liga_id,
        liga_actual=LIGAS.get(liga_id, {})
    )
