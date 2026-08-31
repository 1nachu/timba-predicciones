"""
Telegram Bot Application Setup
===============================
Inicializa y ejecuta el bot de Telegram con todos sus comandos, manejadores y error handler global.
"""

import os
import logging
import traceback
from typing import Optional
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from bot.handlers import (
    cmd_start,
    cmd_help,
    cmd_ligas,
    cmd_live,
    cmd_proximos,
    cmd_predecir,
    cmd_inplay,
    cmd_valuebets,
    handle_callback_query
)

logger = logging.getLogger(__name__)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador global de errores para capturar y registrar excepciones sin tirar el bot."""
    logger.error(f"Excepción no controlada procesando actualización {update}: {context.error}")
    
    # Notificar al usuario si la actualización fue un mensaje
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ <b>Ocurrió un error inesperado al procesar tu solicitud.</b>\n"
                "Por favor intenta nuevamente o usa /help.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


def create_bot_application(token: str) -> Application:
    """Construye y configura la aplicación del bot de Telegram."""
    if not token or len(token) < 10:
        raise ValueError("Token de Telegram inválido. Configura TELEGRAM_BOT_TOKEN en .env")

    app = ApplicationBuilder().token(token).build()

    # Comandos principales
    app.add_handler(CommandHandler(["start", "inicio"], cmd_start))
    app.add_handler(CommandHandler(["help", "ayuda"], cmd_help))
    app.add_handler(CommandHandler(["ligas", "leagues"], cmd_ligas))
    app.add_handler(CommandHandler(["live", "envivo", "vivo"], cmd_live))
    app.add_handler(CommandHandler(["proximos", "fixtures", "partidos"], cmd_proximos))
    app.add_handler(CommandHandler(["predecir", "predict", "pronostico"], cmd_predecir))
    app.add_handler(CommandHandler(["inplay", "livepredict"], cmd_inplay))
    app.add_handler(CommandHandler(["valuebets", "valor", "apuestas"], cmd_valuebets))

    # Botones interactivos (Callback Queries)
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Mensajes de texto directos (ej: si escribe "Arsenal vs Chelsea" directamente)
    async def text_direct_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip() if update.message and update.message.text else ""
        if not text:
            return
        if " vs " in text.lower() or " - " in text:
            context.args = text.split()
            await cmd_predecir(update, context)
        else:
            await update.message.reply_text(
                "💡 <i>¿Deseas predecir un partido?</i> Escribe: <code>Arsenal vs Chelsea</code> o usa /help",
                parse_mode=ParseMode.HTML
            )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_direct_prediction))

    # Error Handler Global
    app.add_error_handler(global_error_handler)

    return app


def run_telegram_bot(token: Optional[str] = None):
    """Ejecuta el bot de Telegram en modo Polling continuo."""
    load_dotenv()
    bot_token = token or os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token or bot_token == "TU_TOKEN_DE_TELEGRAM_AQUI":
        print("\n" + "=" * 60)
        print("⚠️  TELEGRAM_BOT_TOKEN NO CONFIGURADO")
        print("=" * 60)
        print("Para activar el Bot de Telegram:")
        print("1. Habla con @BotFather en Telegram y crea un nuevo bot.")
        print("2. Copia el token proporcionado.")
        print("3. Agrégalo a tu archivo .env:")
        print("   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz")
        print("4. Ejecuta: python bot.py")
        print("=" * 60 + "\n")
        return

    print("=" * 60)
    print("🤖 TIMBA PREDICTOR - TELEGRAM BOT INICIADO")
    print("=" * 60)
    print("📡 Modo: Polling interactivo")
    print("⚡ Presiona Ctrl+C para detener")
    print("=" * 60)

    app = create_bot_application(bot_token)
    app.run_polling(drop_pending_updates=True)
