"""
Telegram Bot Handlers
=====================
Manejadores de comandos, mensajes interactivos y callback queries con manejo robusto de errores.
"""

import logging
import re
import html
from typing import Optional, Tuple, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from timba_core import (
    LIGAS,
    predecir_partido,
    predecir_partido_champions,
    predecir_partido_en_vivo,
    calcular_fuerzas,
    descargar_csv_safe,
    emparejar_equipo
)
from utils.markets import evaluar_value_bets, generar_recomendaciones
from services.prediction_service import cargar_datos_liga_cached, predecir_partido_cached
from services.fixtures_service import (
    obtener_partidos_locales,
    enriquecer_partidos_con_prediccion,
    API_TO_LIGA_ID
)
from bot.formatters import (
    format_welcome_message,
    format_leagues_list,
    format_prediction_card,
    format_live_prediction_card,
    format_live_matches_summary,
    format_upcoming_fixtures,
    format_value_bets_summary
)

logger = logging.getLogger(__name__)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado principal interactivo."""
    keyboard = [
        [
            InlineKeyboardButton("⚡ En Vivo (In-Play)", callback_data="menu_live"),
            InlineKeyboardButton("📅 Próximos Hoy", callback_data="menu_fixtures")
        ],
        [
            InlineKeyboardButton("💎 Value Bets (+EV)", callback_data="menu_valuebets"),
            InlineKeyboardButton("🏆 Ligas Soportadas", callback_data="menu_leagues")
        ],
        [
            InlineKeyboardButton("🔮 Predecir Partido", callback_data="menu_predict_select")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def safe_edit_message(query, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None):
    """Edita el mensaje evitando excepciones si el contenido no ha cambiado."""
    try:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            logger.warning(f"Error editando mensaje: {e}")
    except Exception as e:
        logger.error(f"Error inesperado editando mensaje: {e}")


def filtrar_partidos_por_liga(partidos: List[Dict[str, Any]], liga_id: Optional[int]) -> List[Dict[str, Any]]:
    """Filtra la lista de partidos por el ID de liga interna."""
    if not liga_id or liga_id not in LIGAS:
        return partidos

    resultado = []
    for p in partidos:
        comp = p.get('competition', {})
        code = comp.get('code', '') if isinstance(comp, dict) else ''
        p_liga_id = API_TO_LIGA_ID.get(code)
        
        # Coincidencia por código de API o por nombre
        if p_liga_id == liga_id:
            resultado.append(p)
        elif str(liga_id) in str(p.get('liga_id', '')):
            resultado.append(p)
            
    return resultado


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /start."""
    text = format_welcome_message()
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard()
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /help."""
    text = (
        "ℹ️ <b>Guía de Uso - Timba Predictor Bot</b>\n\n"
        "⚽ <b>Comandos Disponibles:</b>\n"
        "• <code>/live</code> - Consulta partidos en juego con probabilidades In-Play en tiempo real.\n"
        "• <code>/proximos [liga_id]</code> - Lista los próximos encuentros (ej: <code>/proximos 1</code>).\n"
        "• <code>/predecir &lt;Local&gt; vs &lt;Visitante&gt;</code> - Predicción pre-partido completa con probabilidades 1X2, xG, Over/Under y BTTS.\n"
        "• <code>/inplay &lt;Local&gt; vs &lt;Vis&gt; 2-1 min 70 [rojas 0-1]</code> - Simula un escenario en vivo con minuto, marcador y expulsiones.\n"
        "• <code>/valuebets</code> - Muestra oportunidades de apuestas con Valor Esperado positivo (+EV).\n"
        "• <code>/ligas</code> - Muestra las ligas soportadas y sus IDs.\n\n"
        "💡 <i>Ejemplos rápidos:</i>\n"
        "<code>/predecir Arsenal vs Chelsea</code>\n"
        "<code>/inplay Real Madrid vs Barcelona 1-0 min 65</code>\n"
        "<code>/inplay Liverpool vs Man City 2-2 min 82 rojas 1-0</code>"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard()
    )


async def cmd_ligas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /ligas."""
    text = format_leagues_list(LIGAS)
    keyboard = []
    row = []
    for lid, linfo in LIGAS.items():
        flag = linfo.get('flag', '⚽')
        btn = InlineKeyboardButton(f"{flag} {linfo.get('nombre', f'L{lid}')[:12]}", callback_data=f"fixtures_league:{lid}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")])

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /live."""
    try:
        partidos = obtener_partidos_locales()
        partidos_enriquecidos = enriquecer_partidos_con_prediccion(partidos)
        partidos_live = [p for p in partidos_enriquecidos if p.get('seccion') == 'live' or p.get('status') in ['LIVE', 'EN VIVO', 'IN_PLAY', 'PAUSED']]
        
        text = format_live_matches_summary(partidos_live)
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar En Vivo", callback_data="menu_live")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error en cmd_live: {e}")
        await update.message.reply_text("⚠️ Ocurrió un error al obtener partidos en vivo.", parse_mode=ParseMode.HTML)


async def cmd_proximos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /proximos [liga_id]."""
    try:
        liga_id = None
        if context.args and len(context.args) > 0:
            try:
                liga_id = int(context.args[0])
            except ValueError:
                pass

        partidos = obtener_partidos_locales()
        partidos_enriquecidos = enriquecer_partidos_con_prediccion(partidos)
        proximos = [p for p in partidos_enriquecidos if p.get('seccion') != 'live' and p.get('status') not in ['LIVE', 'EN VIVO']]

        if liga_id and liga_id in LIGAS:
            liga_nombre = LIGAS[liga_id].get('nombre', f"Liga {liga_id}")
            proximos = filtrar_partidos_por_liga(proximos, liga_id)
        else:
            liga_nombre = "Todas las Ligas"

        text = format_upcoming_fixtures(proximos, liga_nombre)
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="menu_fixtures")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error en cmd_proximos: {e}")
        await update.message.reply_text("⚠️ Ocurrió un error al obtener los próximos partidos.", parse_mode=ParseMode.HTML)


async def cmd_valuebets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /valuebets."""
    try:
        partidos = obtener_partidos_locales()
        partidos_enriquecidos = enriquecer_partidos_con_prediccion(partidos)
        
        value_bets = []
        for p in partidos_enriquecidos:
            pred = p.get('prediccion_prematch')
            cuotas = p.get('cuotas', {})
            if pred and cuotas:
                vb_list = evaluar_value_bets(pred, cuotas)
                value_bets.extend(vb_list)

        text = format_value_bets_summary(value_bets)
        keyboard = [
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error en cmd_valuebets: {e}")
        await update.message.reply_text("⚠️ Ocurrió un error al analizar apuestas de valor.", parse_mode=ParseMode.HTML)


def parse_prediction_args(args_str: str) -> Optional[Tuple[str, str, Optional[int]]]:
    """Parsea cadena tipo 'Arsenal vs Chelsea' o '1 Arsenal Chelsea'."""
    args_str = args_str.strip()
    if not args_str:
        return None

    if " vs " in args_str.lower():
        parts = re.split(r'\s+vs\s+', args_str, flags=re.IGNORECASE)
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip(), None

    if " - " in args_str:
        parts = args_str.split(" - ")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip(), None

    tokens = args_str.split()
    if len(tokens) >= 2:
        if tokens[0].isdigit():
            lid = int(tokens[0])
            mid = len(tokens[1:]) // 2
            if mid > 0:
                loc = " ".join(tokens[1:1+mid])
                vis = " ".join(tokens[1+mid:])
                return loc, vis, lid
        else:
            mid = len(tokens) // 2
            loc = " ".join(tokens[:mid])
            vis = " ".join(tokens[mid:])
            return loc, vis, None

    return None


async def cmd_predecir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /predecir <Local> vs <Visitante>."""
    if not context.args:
        keyboard = []
        row = []
        for lid, linfo in LIGAS.items():
            flag = linfo.get('flag', '⚽')
            btn = InlineKeyboardButton(f"{flag} {linfo.get('nombre', f'L{lid}')[:12]}", callback_data=f"pred_select_league:{lid}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")])

        await update.message.reply_text(
            "🔮 <b>Predicción de Partidos</b>\n\n"
            "Escribe directamente el partido que deseas analizar:\n"
            "👉 <code>/predecir Arsenal vs Chelsea</code>\n"
            "👉 <code>/predecir Real Madrid vs Barcelona</code>\n\n"
            "<i>O selecciona una liga para ver sus equipos:</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    raw_args = " ".join(context.args)
    parsed = parse_prediction_args(raw_args)
    if not parsed:
        await update.message.reply_text(
            "⚠️ <b>Formato incorrecto.</b> Usa:\n<code>/predecir &lt;Local&gt; vs &lt;Visitante&gt;</code>\nEj: <code>/predecir Arsenal vs Chelsea</code>",
            parse_mode=ParseMode.HTML
        )
        return

    local, visitante, specified_liga = parsed

    # Buscar en las ligas: primero domésticas (1, 2, 3, 4, 5, 6, 7, 10) y luego Champions (8)
    pred = None
    encontrado_en_liga = None
    ligas_a_buscar = [specified_liga] if specified_liga and specified_liga in LIGAS else [1, 2, 3, 4, 5, 6, 7, 10, 8]

    for lid in ligas_a_buscar:
        try:
            p = predecir_partido_cached(lid, local, visitante)
            if p:
                pred = p
                encontrado_en_liga = LIGAS.get(lid, {}).get('nombre', f"Liga {lid}")
                break
        except Exception as e:
            logger.debug(f"Error evaluando liga {lid}: {e}")
            continue

    if not pred:
        local_esc = html.escape(str(local))
        vis_esc = html.escape(str(visitante))
        await update.message.reply_text(
            f"❌ <b>No se encontraron datos para:</b>\n⚽ <i>{local_esc} vs {vis_esc}</i>\n\n"
            f"Verifica la ortografía de los nombres o revisa /ligas.",
            parse_mode=ParseMode.HTML
        )
        return

    text = format_prediction_card(local, visitante, pred, encontrado_en_liga)
    keyboard = [
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
    ]
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def parse_inplay_args(text: str) -> Optional[dict]:
    """Parsea comando inplay."""
    text = text.strip()
    match = re.search(r'^(.*?)\s+vs\s+(.*?)\s+(\d+)[-:](\d+)(.*)$', text, re.IGNORECASE)
    if not match:
        return None

    local = match.group(1).strip()
    vis = match.group(2).strip()
    g_loc = int(match.group(3))
    g_vis = int(match.group(4))
    rest = match.group(5).strip()

    minute = 45
    min_match = re.search(r'(?:min|m|minuto)?\s*(\d+)', rest, re.IGNORECASE)
    if min_match:
        minute = int(min_match.group(1))

    r_loc, r_vis = 0, 0
    rojas_match = re.search(r'rojas?\s*(\d+)[-:](\d+)', rest, re.IGNORECASE)
    if rojas_match:
        r_loc = int(rojas_match.group(1))
        r_vis = int(rojas_match.group(2))

    return {
        'local': local,
        'visitante': vis,
        'home_score': g_loc,
        'away_score': g_vis,
        'minute': minute,
        'red_cards_home': r_loc,
        'red_cards_away': r_vis
    }


async def cmd_inplay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de /inplay <local> vs <vis> <score> min <minuto>."""
    if not context.args:
        await update.message.reply_text(
            "⚡ <b>Simulador de Predicciones En Vivo (In-Play)</b>\n\n"
            "Calcula probabilidades en tiempo real ajustadas por marcador, minuto y tarjetas rojas.\n\n"
            "📌 <b>Formato:</b>\n"
            "<code>/inplay &lt;Local&gt; vs &lt;Vis&gt; &lt;GolesL&gt;-&lt;GolesV&gt; min &lt;Minuto&gt; [rojas L-V]</code>\n\n"
            "💡 <b>Ejemplos:</b>\n"
            "• <code>/inplay Arsenal vs Chelsea 2-0 min 75</code>\n"
            "• <code>/inplay Real Madrid vs Barcelona 1-1 min 60 rojas 1-0</code>\n"
            "• <code>/inplay Boca Juniors vs River Plate 0-0 min 80</code>",
            parse_mode=ParseMode.HTML
        )
        return

    raw = " ".join(context.args)
    params = parse_inplay_args(raw)
    if not params:
        await update.message.reply_text(
            "⚠️ <b>Formato no reconocido.</b>\nUsa: <code>/inplay Local vs Visitante 2-1 min 70</code>",
            parse_mode=ParseMode.HTML
        )
        return

    local = params['local']
    visitante = params['visitante']
    
    pred_prematch = None
    for lid in [1, 2, 3, 4, 5, 6, 7, 10, 8]:
        try:
            p = predecir_partido_cached(lid, local, visitante)
            if p:
                pred_prematch = p
                break
        except Exception:
            continue

    pred_live = predecir_partido_en_vivo(
        local, visitante, {}, 0.0, 0.0,
        home_score=params['home_score'],
        away_score=params['away_score'],
        minute=params['minute'],
        red_cards_home=params['red_cards_home'],
        red_cards_away=params['red_cards_away'],
        pred_prematch=pred_prematch
    )

    pred_pre_dict = None
    if pred_prematch:
        pred_pre_dict = {
            'prob_local': round(float(pred_prematch.get('Prob_Local', 0)) * 100, 1),
            'prob_empate': round(float(pred_prematch.get('Prob_Empate', 0)) * 100, 1),
            'prob_visitante': round(float(pred_prematch.get('Prob_Vis', 0)) * 100, 1),
        }

    text = format_live_prediction_card(local, visitante, pred_live, pred_pre_dict)
    keyboard = [
        [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
    ]
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todas las interacciones de botones en línea de forma segura."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "menu_main":
        text = format_welcome_message()
        await safe_edit_message(query, text, get_main_menu_keyboard())

    elif data == "menu_live":
        partidos = obtener_partidos_locales()
        partidos_enriquecidos = enriquecer_partidos_con_prediccion(partidos)
        partidos_live = [p for p in partidos_enriquecidos if p.get('seccion') == 'live' or p.get('status') in ['LIVE', 'EN VIVO', 'IN_PLAY', 'PAUSED']]
        
        text = format_live_matches_summary(partidos_live)
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar En Vivo", callback_data="menu_live")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await safe_edit_message(query, text, InlineKeyboardMarkup(keyboard))

    elif data == "menu_fixtures":
        partidos = obtener_partidos_locales()
        partidos_enriquecidos = enriquecer_partidos_con_prediccion(partidos)
        proximos = [p for p in partidos_enriquecidos if p.get('seccion') != 'live' and p.get('status') not in ['LIVE', 'EN VIVO']]
        
        text = format_upcoming_fixtures(proximos, "Todas las Ligas")
        keyboard = [
            [InlineKeyboardButton("🔄 Actualizar", callback_data="menu_fixtures")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await safe_edit_message(query, text, InlineKeyboardMarkup(keyboard))

    elif data == "menu_valuebets":
        partidos = obtener_partidos_locales()
        partidos_enriquecidos = enriquecer_partidos_con_prediccion(partidos)
        value_bets = []
        for p in partidos_enriquecidos:
            pred = p.get('prediccion_prematch')
            cuotas = p.get('cuotas', {})
            if pred and cuotas:
                vb_list = evaluar_value_bets(pred, cuotas)
                value_bets.extend(vb_list)

        text = format_value_bets_summary(value_bets)
        keyboard = [
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await safe_edit_message(query, text, InlineKeyboardMarkup(keyboard))

    elif data == "menu_leagues":
        text = format_leagues_list(LIGAS)
        keyboard = []
        row = []
        for lid, linfo in LIGAS.items():
            flag = linfo.get('flag', '⚽')
            btn = InlineKeyboardButton(f"{flag} {linfo.get('nombre', f'L{lid}')[:12]}", callback_data=f"fixtures_league:{lid}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")])

        await safe_edit_message(query, text, InlineKeyboardMarkup(keyboard))

    elif data.startswith("fixtures_league:"):
        lid = int(data.split(":")[1])
        liga_nombre = LIGAS.get(lid, {}).get('nombre', f"Liga {lid}")
        partidos = obtener_partidos_locales()
        partidos_enriquecidos = enriquecer_partidos_con_prediccion(partidos)
        proximos = [p for p in partidos_enriquecidos if p.get('seccion') != 'live']
        proximos_filtrados = filtrar_partidos_por_liga(proximos, lid)

        text = format_upcoming_fixtures(proximos_filtrados, liga_nombre)
        keyboard = [
            [InlineKeyboardButton("🔙 Ligas", callback_data="menu_leagues")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await safe_edit_message(query, text, InlineKeyboardMarkup(keyboard))

    elif data == "menu_predict_select":
        keyboard = []
        row = []
        for lid, linfo in LIGAS.items():
            flag = linfo.get('flag', '⚽')
            btn = InlineKeyboardButton(f"{flag} {linfo.get('nombre', f'L{lid}')[:12]}", callback_data=f"pred_league_info:{lid}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")])

        await safe_edit_message(
            query,
            "🔮 <b>Selecciona una liga para predecir:</b>\n\n"
            "O escribe directamente:\n<code>/predecir Arsenal vs Chelsea</code>",
            InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("pred_league_info:"):
        lid = int(data.split(":")[1])
        linfo = LIGAS.get(lid, {})
        nombre = html.escape(str(linfo.get('nombre', f"Liga {lid}")))
        flag = linfo.get('flag', '⚽')
        
        # Cargar equipos de la liga de forma segura (tupla)
        try:
            cache_l = cargar_datos_liga_cached(lid)
            if isinstance(cache_l, tuple) and len(cache_l) == 4:
                _, _, _, equipos = cache_l
            elif isinstance(cache_l, dict):
                equipos = cache_l.get('equipos', [])
            else:
                equipos = []
            equipos_str = html.escape(", ".join(equipos[:10])) + ("..." if len(equipos) > 10 else "")
        except Exception as e:
            logger.error(f"Error cargando equipos para liga {lid}: {e}")
            equipos_str = "Equipos cargados en base de datos"

        text = (
            f"{flag} <b>{nombre}</b>\n\n"
            f"📋 <b>Equipos destacados:</b>\n<i>{equipos_str}</i>\n\n"
            f"💡 Para predecir escribe:\n"
            f"<code>/predecir &lt;Equipo1&gt; vs &lt;Equipo2&gt;</code>"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 Seleccionar Otra Liga", callback_data="menu_predict_select")],
            [InlineKeyboardButton("🔙 Menú Principal", callback_data="menu_main")]
        ]
        await safe_edit_message(query, text, InlineKeyboardMarkup(keyboard))
