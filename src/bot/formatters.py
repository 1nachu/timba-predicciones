"""
Telegram Bot Message Formatters
================================
Construye mensajes formateados en HTML para el bot de Telegram con escape seguro de entidades.
"""

import html
from typing import Dict, List, Any, Optional


def format_progress_bar(percentage: float, width: int = 10) -> str:
    """Genera una barra de progreso visual (ej: [██████░░░░] 60%)."""
    pct = max(0.0, min(100.0, float(percentage)))
    filled = int(round((pct / 100.0) * width))
    empty = width - filled
    return f"{'█' * filled}{'░' * empty}"


def format_welcome_message() -> str:
    """Genera mensaje de bienvenida."""
    return (
        "⚽ <b>¡Bienvenido a Timba Predictor Bot!</b> 🎯\n\n"
        "Sistema de análisis cuantitativo y predicción de fútbol basado en "
        "<b>Distribución de Poisson</b>, <b>Ajuste Dixon-Coles</b> y <b>Modelado In-Play Dinámico</b>.\n\n"
        "📌 <b>Comandos Principales:</b>\n"
        "• /live - Partidos en vivo y predicciones In-Play ⚡\n"
        "• /proximos - Fixture y pronósticos de hoy 📅\n"
        "• /predecir <code>&lt;Local&gt; vs &lt;Visitante&gt;</code> - Análisis pre-partido 🔮\n"
        "• /inplay <code>&lt;Local&gt; vs &lt;Vis&gt; 2-1 min 70 rojas 0-1</code> - Simular en vivo ⏱️\n"
        "• /valuebets - Apuestas de valor (Kelly Criterion) 💎\n"
        "• /ligas - Ver ligas soportadas 🏆\n"
        "• /help - Ayuda detallada ℹ️\n\n"
        "<i>Selecciona una opción del menú inferior para comenzar:</i>"
    )


def format_leagues_list(ligas: Dict[int, Dict[str, Any]]) -> str:
    """Genera mensaje de lista de ligas soportadas."""
    msg = "🏆 <b>Ligas y Competiciones Disponibles</b>\n\n"
    for lid, linfo in ligas.items():
        flag = linfo.get('flag', '⚽')
        nombre = html.escape(str(linfo.get('nombre', f"Liga {lid}")))
        temporadas = linfo.get('temporadas', 2)
        msg += f"<b>{lid}.</b> {flag} <b>{nombre}</b> <i>({temporadas} temp.)</i>\n"
    msg += "\n💡 <i>Usa /proximos &lt;ID&gt; para ver partidos de una liga específica.</i>"
    return msg


def format_prediction_card(
    local: str,
    visitante: str,
    pred: Dict[str, Any],
    liga_nombre: str = "Competición"
) -> str:
    """Formatea la tarjeta de predicción pre-partido completa."""
    local_esc = html.escape(str(local))
    vis_esc = html.escape(str(visitante))
    liga_esc = html.escape(str(liga_nombre))

    p_loc = round(float(pred.get('Prob_Local', 0)) * 100, 1)
    p_emp = round(float(pred.get('Prob_Empate', 0)) * 100, 1)
    p_vis = round(float(pred.get('Prob_Vis', 0)) * 100, 1)
    
    p_1x = round(float(pred.get('Prob_1X', 0)) * 100, 1)
    p_x2 = round(float(pred.get('Prob_X2', 0)) * 100, 1)
    p_12 = round(float(pred.get('Prob_12', 0)) * 100, 1)
    
    xg_l = round(float(pred.get('xG_Local', 0)), 2)
    xg_v = round(float(pred.get('xG_Vis', 0)), 2)
    xg_tot = round(xg_l + xg_v, 2)
    
    o15 = round(float(pred.get('Over_15', 0)) * 100, 1)
    o25 = round(float(pred.get('Over_25', 0)) * 100, 1)
    u35 = round(float(pred.get('Under_35', 0)) * 100, 1)
    btts = round(float(pred.get('BTTS_Prob', 0)) * 100, 1)
    
    # Pronóstico principal
    if p_loc >= 50.0:
        pronostico = f"🏠 Gana {local_esc}"
    elif p_vis >= 45.0:
        pronostico = f"🚀 Gana {vis_esc}"
    elif p_1x >= 70.0:
        pronostico = f"🛡️ Doble Oportunidad {local_esc} o Empate (1X)"
    elif p_x2 >= 70.0:
        pronostico = f"🛡️ Doble Oportunidad Empate o {vis_esc} (X2)"
    else:
        pronostico = "⚖️ Partido Muy Parejo / Empate Probable"

    msg = (
        f"🎯 <b>ANÁLISIS PRE-PARTIDO</b>\n"
        f"🏆 <i>{liga_esc}</i>\n"
        f"⚽ <b>{local_esc}</b> vs <b>{vis_esc}</b>\n\n"
        f"📊 <b>Probabilidades 1X2:</b>\n"
        f"• <b>1</b> ({local_esc}): <code>{p_loc}%</code> [{format_progress_bar(p_loc)}]\n"
        f"• <b>X</b> (Empate): <code>{p_emp}%</code> [{format_progress_bar(p_emp)}]\n"
        f"• <b>2</b> ({vis_esc}): <code>{p_vis}%</code> [{format_progress_bar(p_vis)}]\n\n"
        f"🛡️ <b>Doble Oportunidad:</b>\n"
        f"• <b>1X:</b> <code>{p_1x}%</code> | <b>X2:</b> <code>{p_x2}%</code> | <b>12:</b> <code>{p_12}%</code>\n\n"
        f"⚽ <b>Goles Esperados (xG):</b>\n"
        f"• {local_esc}: <code>{xg_l}</code> | {vis_esc}: <code>{xg_v}</code> | Total: <code>{xg_tot}</code>\n\n"
        f"📈 <b>Mercados de Goles:</b>\n"
        f"• Over 1.5: <code>{o15}%</code> | Over 2.5: <code>{o25}%</code>\n"
        f"• Under 3.5: <code>{u35}%</code> | Ambos Marcan (BTTS): <code>{btts}%</code>\n"
    )

    top_m = pred.get('Top_3_Marcadores', [])
    if top_m:
        msg += "\n🎲 <b>Marcadores Más Probables:</b>\n"
        for m in top_m:
            marcador = html.escape(str(m.get('marcador', '')))
            prob = round(float(m.get('prob', 0)) * 100, 1)
            msg += f"• <code>{marcador}</code> <i>({prob}%)</i>\n"

    msg += f"\n💡 <b>Sugerencia IA:</b> <b>{pronostico}</b>"
    return msg


def format_live_prediction_card(
    local: str,
    visitante: str,
    pred_live: Dict[str, Any],
    pred_prematch: Optional[Dict[str, Any]] = None
) -> str:
    """Formatea la tarjeta de predicción In-Play en vivo."""
    local_esc = html.escape(str(local))
    vis_esc = html.escape(str(visitante))

    minuto = pred_live.get('minuto', 0)
    g_loc = pred_live.get('goles_local', 0)
    g_vis = pred_live.get('goles_vis', 0)
    rojas_l = pred_live.get('rojas_local', 0)
    rojas_v = pred_live.get('rojas_vis', 0)
    
    p_loc = round(float(pred_live.get('prob_local', 0)), 1)
    p_emp = round(float(pred_live.get('prob_empate', 0)), 1)
    p_vis = round(float(pred_live.get('prob_visitante', 0)), 1)
    
    xg_rem_l = round(float(pred_live.get('xG_restante_local', 0)), 2)
    xg_rem_v = round(float(pred_live.get('xG_restante_vis', 0)), 2)
    xg_tot = round(float(pred_live.get('xG_total_esperado', 0)), 2)
    
    t_rest = pred_live.get('tiempo_restante_pct', 0)
    estado = html.escape(str(pred_live.get('estado_tactico', '')))
    
    msg = (
        f"⚡ <b>PREDICCIÓN EN VIVO (IN-PLAY)</b>\n"
        f"⏱️ <b>Minuto:</b> <code>{minuto}'</code> (Restante: {t_rest}%)\n"
        f"⚽ <b>{local_esc} {g_loc} - {g_vis} {vis_esc}</b>\n"
    )

    if rojas_l > 0 or rojas_v > 0:
        msg += f"🟥 <b>Tarjetas Rojas:</b> {local_esc} ({rojas_l}) | {vis_esc} ({rojas_v})\n"
    
    msg += f"🏷️ <i>{estado}</i>\n\n"

    msg += (
        f"📊 <b>Probabilidades 1X2 en Vivo (Final):</b>\n"
        f"• <b>1</b> ({local_esc}): <code>{p_loc}%</code> [{format_progress_bar(p_loc)}]\n"
        f"• <b>X</b> (Empate): <code>{p_emp}%</code> [{format_progress_bar(p_emp)}]\n"
        f"• <b>2</b> ({vis_esc}): <code>{p_vis}%</code> [{format_progress_bar(p_vis)}]\n\n"
        f"🎯 <b>Goles Restantes Proyectados:</b>\n"
        f"• xG remanente: {local_esc} <code>{xg_rem_l}</code> vs <code>{xg_rem_v}</code> {vis_esc}\n"
        f"• Total final esperado: <code>{xg_tot}</code> goles\n\n"
    )

    pg = pred_live.get('proximo_gol')
    if pg:
        msg += (
            f"🔥 <b>Mercado Próximo Gol:</b>\n"
            f"• Gol {local_esc}: <code>{pg.get('local', 0)}%</code>\n"
            f"• Gol {vis_esc}: <code>{pg.get('visitante', 0)}%</code>\n"
            f"• Sin más goles: <code>{pg.get('sin_mas_goles', 0)}%</code>\n\n"
        )

    top_m = pred_live.get('top_marcadores_finales', [])
    if top_m:
        msg += "🎲 <b>Marcador Final Más Probable:</b>\n"
        for m in top_m:
            marcador_esc = html.escape(str(m.get('marcador', '')))
            msg += f"• <code>{marcador_esc}</code> <i>({m.get('prob', 0)}%)</i>\n"

    if pred_prematch:
        p_pre_l = round(float(pred_prematch.get('prob_local', 0)), 1)
        p_pre_x = round(float(pred_prematch.get('prob_empate', 0)), 1)
        p_pre_v = round(float(pred_prematch.get('prob_visitante', 0)), 1)
        msg += (
            f"\n⚪ <b>Referencia Pre-match Inicial:</b>\n"
            f"1: <code>{p_pre_l}%</code> | X: <code>{p_pre_x}%</code> | 2: <code>{p_pre_v}%</code>"
        )

    return msg


def format_live_matches_summary(partidos_live: List[Dict[str, Any]]) -> str:
    """Formatea la lista de partidos que se están jugando actualmente."""
    if not partidos_live:
        return (
            "⚽ <b>Partidos en Vivo</b>\n\n"
            "😴 <i>No hay partidos en juego en este momento en las ligas monitoreadas.</i>\n\n"
            "Usa /proximos para ver los partidos programados de hoy."
        )

    msg = f"⚡ <b>PARTIDOS EN VIVO ({len(partidos_live)})</b>\n\n"
    for p in partidos_live:
        home = html.escape(str(p.get('homeTeam', {}).get('name') or p.get('home', 'Local')))
        away = html.escape(str(p.get('awayTeam', {}).get('name') or p.get('away', 'Visitante')))
        score = html.escape(str(p.get('score', '0-0')))
        minute = html.escape(str(p.get('minute', "LIVE")))
        comp = html.escape(str(p.get('competition', {}).get('name', 'Liga')))
        
        pred_live = p.get('prediccion_live')
        
        msg += f"🏆 <b>{comp}</b> | ⏱️ <code>{minute}'</code>\n"
        msg += f"⚽ <b>{home} {score} {away}</b>\n"
        
        if pred_live:
            p_loc = round(float(pred_live.get('prob_local', 0)), 1)
            p_emp = round(float(pred_live.get('prob_empate', 0)), 1)
            p_vis = round(float(pred_live.get('prob_visitante', 0)), 1)
            estado_esc = html.escape(str(pred_live.get('estado_tactico', '')))
            msg += f"📊 <b>IA Live:</b> 1: <code>{p_loc}%</code> | X: <code>{p_emp}%</code> | 2: <code>{p_vis}%</code>\n"
            msg += f"🏷️ <i>{estado_esc}</i>\n"
        
        msg += "───────────────────\n"

    msg += "\n💡 <i>Para análisis In-Play detallado, escribe /inplay o pulsa un botón.</i>"
    return msg


def format_upcoming_fixtures(partidos: List[Dict[str, Any]], liga_nombre: str = "Todas las Ligas") -> str:
    """Formatea la lista de próximos partidos con sus probabilidades."""
    liga_esc = html.escape(str(liga_nombre))
    if not partidos:
        return f"📅 <b>Próximos Partidos ({liga_esc})</b>\n\n<i>No hay partidos programados para las próximas 24 horas.</i>"

    msg = f"📅 <b>PRÓXIMOS PARTIDOS ({liga_esc})</b>\n\n"
    for p in partidos[:15]:
        home = html.escape(str(p.get('homeTeam', {}).get('name') or p.get('home', 'Local')))
        away = html.escape(str(p.get('awayTeam', {}).get('name') or p.get('away', 'Visitante')))
        hora = html.escape(str(p.get('utcDate', '')[11:16] if p.get('utcDate') else "Hoy"))
        
        pred = p.get('prediccion_timba') or p.get('prediccion_prematch')
        
        msg += f"⏰ <code>{hora}</code> | <b>{home}</b> vs <b>{away}</b>\n"
        if pred:
            p_loc = int(round(float(pred.get('prob_local', 0))))
            p_emp = int(round(float(pred.get('prob_empate', 0))))
            p_vis = int(round(float(pred.get('prob_visitante', 0))))
            msg += f"   📊 <b>IA:</b> 1: <code>{p_loc}%</code> | X: <code>{p_emp}%</code> | 2: <code>{p_vis}%</code>\n"
        msg += "\n"

    return msg


def format_value_bets_summary(value_bets: List[Dict[str, Any]]) -> str:
    """Formatea el reporte de apuestas de valor y Kelly Criterion."""
    if not value_bets:
        return (
            "💎 <b>Apuestas de Valor (Value Bets)</b>\n\n"
            "🔍 <i>No se detectaron apuestas con Valor Esperado (EV) positivo en las cuotas actuales.</i>"
        )

    msg = f"💎 <b>APUESTAS CON VALOR POSITIVO (+EV)</b>\n\n"
    for vb in value_bets[:8]:
        partido = html.escape(str(vb.get('partido', 'Partido')))
        mercado = html.escape(str(vb.get('mercado', 'Mercado')))
        cuota = vb.get('cuota', 1.0)
        prob_ia = round(float(vb.get('prob_modelo', 0)) * 100, 1)
        ev = round(float(vb.get('valor_esperado', 0)) * 100, 1)
        kelly = round(float(vb.get('stake_kelly', 0)) * 100, 2)
        
        msg += (
            f"⚽ <b>{partido}</b>\n"
            f"• <b>Selección:</b> <code>{mercado}</code> @ <b>{cuota}</b>\n"
            f"• <b>Probabilidad IA:</b> <code>{prob_ia}%</code>\n"
            f"• <b>Valor Esperado (+EV):</b> <code>+{ev}%</code>\n"
            f"• <b>Stake Sugerido (Kelly):</b> <code>{kelly}%</code> del bank\n"
            f"───────────────────\n"
        )

    return msg
