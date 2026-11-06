# 🎯 Timba Predictor v2.2

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-60%20Passing-success?style=flat-square&logo=pytest&logoColor=white)
![Season](https://img.shields.io/badge/Season-2026%2F2027-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Sistema de predicción de fútbol y apuestas de valor (Value Betting)** basado en Distribución de Poisson con ajuste **Dixon-Coles (1997)**, Criterio de Kelly, normalización inteligente de equipos por liga, predicciones dinámicas **In-Play**, API REST JSON v1, motor de **Backtesting Cuantitativo**, Bot de Telegram interactivo y despliegue contenerizado con Docker.

> 🔮 *"No es magia, son matemáticas vectorizadas y valor esperado."*

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Ligas Soportadas (Temporada 26/27)](#-ligas-soportadas)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Variables de Entorno](#-variables-de-entorno)
- [Ejecución y Despliegue](#-ejecución-y-despliegue)
- [API REST JSON v1](#-api-rest-json-v1)
- [Motor de Backtesting Cuantitativo](#-motor-de-backtesting-cuantitativo)
- [Bot de Telegram Interactivo](#-bot-de-telegram-interactivo)
- [Suite de Tests Automatizados](#-suite-de-tests-automatizados)
- [Documentación Adicional](#-documentación-adicional)
- [Créditos y Licencia](#-créditos-y-licencia)

---

## 🚀 Características

| Funcionalidad | Descripción |
|---|---|
| **⚽ Poisson + Dixon-Coles (1997)** | Matriz de probabilidades $11 \times 11$ ajustada con factor de correlación $\tau(x, y, \rho)$ para corregir la subdispersión en empates de pocos goles. |
| **💡 Value Betting & Kelly Criterion** | Cálculo automático de Valor Esperado ($\text{EV} = P \times \text{Cuota} - 1$) y sugerencia de tamaño de apuesta con el Criterio de Kelly fraccional. |
| **📈 Backtesting Cuantitativo (Walk-Forward)** | Simulación histórica de apuestas calculando Brier Score, Yield / ROI %, Max Drawdown y evolución de bankroll. |
| **🌐 API REST v1 JSON** | Endpoints para consumo externo de predicciones pre-partido e In-Play, value bets, fixtures, marcadores en vivo y auditoría. |
| **🏗️ Arquitectura Modular (Blueprints & Services)** | Desacoplamiento entre capa web (`src/web/blueprints/`), capa de servicios (`src/services/`), ETL (`src/etl/`) y dominio (`src/core/`). |
| **🏎️ Fuerzas Vectorizadas (GroupBy)** | Cálculo de ataque/defensa por liga en **<10 ms** mediante agrupaciones vectoriales de Pandas/NumPy y módulo Cython opcional (`timba_fast`). |
| **🇦🇷 Liga Profesional Argentina** | Integración nativa con **Promiedos.com.ar** y normalización automática del CSV histórico de Football-Data (`ARG.csv`). |
| **🏆 Champions League Inter-Liga** | Normalización de fuerzas domésticas calibradas con coeficientes de nivel competitivo por liga (`COEFICIENTES_LIGAS`). |
| **💾 SQLite Concurrente (WAL Mode)** | Conexión con `PRAGMA journal_mode=WAL;` y `busy_timeout=5000` sin bloqueos de lectura/escritura. |
| **🗂️ FileSystemCache Inter-Proceso** | Caché compartido en disco (`data/flask_cache/`) entre Gunicorn, Flask y `background_updater.py`. |
| **📺 Live Scores & Predicción In-Play** | Auto-refresco en vivo vía HTMX y recálculo de probabilidades en tiempo real según minuto, marcador y tarjetas rojas. |
| **🐳 Docker & Docker Compose** | Imagen multi-etapa con servicios para Web, Background Updater, Live Scores y Bot de Telegram. |

---

## 📊 Ligas Soportadas

Sincronizadas al calendario oficial de la **Temporada 2026/2027** (`2627` / `2026`):

| ID | Código | Liga | País | Temporada | Fuente Fixture |
|---|---|---|---|---|---|
| `10` | `ARG` | **Liga Profesional** | 🇦🇷 Argentina | 2026 | Promiedos / Football-Data (`new/ARG.csv`) |
| `1` | `E0` | **Premier League** | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 26/27 | FixtureDownload (`epl-2026`) |
| `2` | `SP1` | **La Liga** | 🇪🇸 España | 26/27 | FixtureDownload (`la-liga-2026`) |
| `3` | `I1` | **Serie A** | 🇮🇹 Italia | 26/27 | FixtureDownload (`serie-a-2026`) |
| `4` | `D1` | **Bundesliga** | 🇩🇪 Alemania | 26/27 | FixtureDownload (`bundesliga-2026`) |
| `5` | `F1` | **Ligue 1** | 🇫🇷 Francia | 26/27 | FixtureDownload (`ligue-1-2026`) |
| `6` | `P1` | **Primeira Liga** | 🇵🇹 Portugal | 26/27 | FixtureDownload (`primeira-liga-2026`) |
| `7` | `N1` | **Eredivisie** | 🇳🇱 Países Bajos | 26/27 | FixtureDownload (`eredivisie-2026`) |
| `8` | `CL` | **UEFA Champions League** | 🇪🇺 Europa | 26/27 | FixtureDownload (`champions-league-2026`) |

---

## 📁 Estructura del Proyecto

```text
timba-predicciones/
├── app.py                          # 🌐 Servidor Flask (Application Factory & Blueprints)
├── background_updater.py           # 🔄 Worker de actualización de caché y auditoría
├── run_live.py                     # 📺 Demonio de actualización de marcadores en vivo
├── bot.py                          # 🤖 Punto de entrada del Bot de Telegram
├── setup.py                        # ⚙️ Build script para extensión Cython (timba_fast)
├── requirements.txt                # 📦 Dependencias de producción
├── requirements-dev.txt            # 🧪 Dependencias de desarrollo y testing (pytest)
├── Dockerfile                      # 🐳 Dockerfile multi-etapa optimizado
├── docker-compose.yml              # 🐳 Orquestación (web, updater, live, bot)
├── .github/workflows/ci.yml        # 🤖 Pipeline de Integración Continua (GitHub Actions)
├── .env.example                    # 🔑 Plantilla de variables de entorno
├── CHANGELOG.md                    # 📝 Historial de versiones
│
├── docs/
│   ├── ARCHITECTURE.md             # 🏗️ Diseño arquitectónico, flujo de datos y esquemas SQLite
│   └── OPTIMIZATIONS.md            # ⚡ Detalle de optimizaciones vectorizadas y Raspberry Pi
│
├── scripts/
│   ├── run_backtest.py             # 📈 CLI de Backtesting histórico cuantitativo
│   └── migrate_legacy_aliases.py   # 🔗 Utilidad de migración de alias a SQLite
│
├── src/
│   ├── timba_core.py               # 🏛️ Fachada central y caché LRU de datos históricos
│   ├── timba_fast.pyx              # ⚡ Motor Poisson en Cython (opcional)
│   ├── db_data_provider.py         # 📊 Proveedor de datos SQLite con fallback a CSV online
│   ├── etl_football_data.py        # ⬇️ CLI del pipeline ETL histórico
│   ├── live_scores.py              # 📺 Gestor de partidos y marcadores en vivo
│   ├── football_api_client.py      # 🌐 Cliente HTTP para Football-Data.org API v4
│   ├── team_normalization.py       # 🔗 Normalizador de equipos en SQLite filtrado por liga
│   ├── team_normalization_cli.py   # 🛠️ CLI de administración de equipos normalizados
│   │
│   ├── config/
│   │   └── leagues.py              # ⚙️ Configuración canónica de ligas y URLs
│   ├── core/
│   │   ├── models.py               # 📐 Dataclasses y Enums de dominio
│   │   └── prediction.py           # 🧮 Poisson + Dixon-Coles, fuerzas, Champions e In-Play
│   ├── analytics/
│   │   └── backtester.py           # 📈 Motor Walk-Forward, Brier Score y Kelly
│   ├── etl/
│   │   ├── config.py               # ⚙️ Ligas y columnas del ETL
│   │   ├── extractor.py            # ⬇️ Descarga de CSVs históricos por temporada
│   │   ├── transformer.py          # 🔄 Limpieza y tipado de DataFrames
│   │   ├── loader.py               # 💾 Carga transaccional en SQLite (tabla matches)
│   │   └── pipeline.py             # 🔗 Orquestador ETL
│   ├── services/
│   │   ├── audit_service.py        # ✅ Evaluación y sincronización de aciertos históricos
│   │   ├── fixtures_service.py     # 📅 Enriquecimiento y cruce de fixtures
│   │   └── prediction_service.py   # ⚡ Servicio de caché y predicciones para la capa web
│   ├── scrapers/
│   │   └── fixtures_scraper.py     # 🕷️ Scraper de Promiedos y feeds JSON
│   ├── bot/
│   │   ├── bot_app.py              # 🤖 Inicialización del bot de Telegram
│   │   ├── handlers.py             # 💬 Comandos y callbacks inline
│   │   └── formatters.py           # 🎨 Formateo de mensajes Markdown/HTML
│   ├── utils/
│   │   ├── markets.py              # 💰 Mercados derivados, Value Bets, EV y Kelly
│   │   └── shared.py               # 🛠️ Conexión SQLite WAL, normalizar_csv y ALIAS_TEAMS
│   └── web/
│       ├── cache.py                # 🗂️ Instancia compartida de FileSystemCache
│       └── blueprints/             # 🌐 Rutas modulares (dashboard, predict, fixtures, live, history, seo, api)
│
├── tests/                          # 🧪 Suite de 60 tests automatizados (12 archivos)
├── templates/                      # 🎨 Plantillas Jinja2 + HTMX
└── static/                         # 🎨 Assets estáticos, CSS e íconos locales
```

---

## ⚙️ Instalación y Configuración

### 1. Clonar y crear entorno virtual

**En Linux / macOS:**
```bash
git clone https://github.com/1nachu/timba-predicciones.git
cd timba-predicciones

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
# Para desarrollo y correr tests:
pip install -r requirements-dev.txt

cp .env.example .env
```

**En Windows (PowerShell):**
```powershell
git clone https://github.com/1nachu/timba-predicciones.git
cd timba-predicciones

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
# Para desarrollo y correr tests:
pip install -r requirements-dev.txt

copy .env.example .env
```

### 2. Poblar la base de datos histórica local (Recomendado)

Para crear la tabla `matches` en `data/databases/football_data.db` con las últimas temporadas de todas las ligas y evitar descargar CSVs en cada arranque:

```bash
python -m src.etl_football_data
```

> 💡 **Nota:** Si omitís este paso, el sistema sigue funcionando automáticamente descargando y normalizando los CSVs online bajo demanda.

### 3. Compilar aceleración Cython (Opcional)

Para dispositivos embebidos (Raspberry Pi / mini PCs) o máximo throughput:

```bash
python setup.py build_ext --inplace
```

---

## 🔑 Variables de Entorno

Configurá el archivo `.env` en la raíz del proyecto (ver [`.env.example`](.env.example)):

| Variable | Obligatoria | Descripción |
|---|---|---|
| `SECRET_KEY` | Sí (en prod) | Clave secreta de sesiones Flask. Generar con `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `FOOTBALL_DATA_API_KEY` | Opcional | API key gratuita de [football-data.org](https://www.football-data.org/) para marcadores en vivo (`run_live.py`). |
| `TELEGRAM_BOT_TOKEN` | Opcional | Token provisto por [@BotFather](https://t.me/BotFather) para ejecutar `bot.py`. |

---

## 🚀 Ejecución y Despliegue

### Opción A: Docker Compose (Recomendado)

```bash
# Levantar servidor web, background updater y servicio de live scores
docker compose up -d --build

# (Opcional) Levantar también el Bot de Telegram
docker compose --profile bot up -d --build

# Ver logs en tiempo real
docker compose logs -f
```
El servidor web quedará disponible en `http://localhost:5000`.

### Opción B: Ejecución Local

| Servicio | Comando | Descripción |
|---|---|---|
| **Web + API REST** | `python app.py` | Levanta el servidor Flask en `http://localhost:5000`. |
| **Background Updater** | `python background_updater.py` | Actualiza `data/dashboard_cache.json` y audita predicciones (agregar `--loop 300` para correr cada 5 min). |
| **Live Scores** | `python run_live.py` | Sincroniza marcadores en tiempo real en `data/databases/live_scores.db`. |
| **Telegram Bot** | `python bot.py` | Inicia el bot interactivo (requiere `TELEGRAM_BOT_TOKEN`). |

---

## 📡 API REST JSON v1

Todos los endpoints bajo `/api/v1` retornan `application/json`:

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/health` | Estado del servicio y versión. |
| `GET` | `/api/v1/leagues` | Catálogo de ligas soportadas. |
| `GET` | `/api/v1/predict` | Predicción pre-partido o In-Play (`liga_id`, `local`, `visitante`, cuotas opcionales `odds_home`, `odds_draw`, `odds_away`, y parámetros en vivo `live=true`, `minute`, `home_score`, `away_score`). |
| `GET` | `/api/v1/value-bets` | Escaneo de apuestas con valor esperado positivo (`min_ev=0.05`). |
| `GET` | `/api/v1/fixtures` | Próximos partidos con probabilidades calculadas (`liga_id`). |
| `GET` | `/api/v1/live` | Partidos en juego con probabilidades dinámicas In-Play. |
| `GET` | `/api/v1/audit` | Historial de aciertos verificados y precisión del modelo (`liga_id`, `days`). |

### Ejemplo: Predicción con Value Betting y Kelly
```http
GET /api/v1/predict?liga_id=1&local=Arsenal&visitante=Chelsea&odds_home=2.10&odds_draw=3.40&odds_away=3.80
```
```json
{
  "local": "Arsenal",
  "visitante": "Chelsea",
  "liga_id": 1,
  "probabilidades": {
    "local": 54.2,
    "empate": 24.8,
    "visitante": 21.0,
    "doble_oportunidad": {
      "1X": 79.0,
      "X2": 45.8,
      "12": 75.2
    }
  },
  "goles_esperados": {
    "local": 1.72,
    "visitante": 0.98,
    "total": 2.70
  },
  "value_bets": [
    {
      "mercado": "Victoria Local (1)",
      "cuota": 2.10,
      "prob_modelo": 54.2,
      "prob_implicita": 47.6,
      "edge_pct": 6.6,
      "ev_pct": 13.8,
      "kelly_stake_pct": 3.13,
      "badge": "🔥 VALUE BET"
    }
  ]
}
```

---

## 📈 Motor de Backtesting Cuantitativo

Ejecuta simulaciones walk-forward sobre temporadas pasadas para medir calibración probabilística y rentabilidad:

```bash
# Backtest con stake fijo de $10 en Premier League
python scripts/run_backtest.py --league E0 --seasons 3 --min-ev 0.04

# Backtest con Criterio de Kelly (fracción 0.25) en La Liga
python scripts/run_backtest.py --league SP1 --seasons 3 --stake-mode kelly --kelly-fraction 0.25
```

- **Brier Score (1X2)**: precisión probabilística cuadrática ($0.0 = \text{perfección}$).
- **Yield / ROI (%)**: beneficio neto sobre el capital total arriesgado.
- **Max Drawdown (%)**: caída máxima desde el pico de bankroll.
- **Hit Rate (%)**: porcentaje de apuestas acertadas.

---

## 🤖 Bot de Telegram Interactivo

Comandos disponibles en `bot.py`:
- `/start` — Menú principal con botonera inline.
- `/live` — Marcadores en tiempo real y proyecciones In-Play.
- `/proximos [liga_id]` — Próximos partidos con probabilidades 1X2.
- `/predecir <Local> vs <Visitante>` — Análisis pre-partido completo (xG, 1X2, Over/Under, BTTS, marcadores exactos).
- `/inplay <Local> vs <Vis> <score> min <minuto> [rojas L-V]` — Simulación en vivo (ej: `/inplay Real Madrid vs Barcelona 2-1 min 70 rojas 0-1`).
- `/valuebets` — Oportunidades del día con valor esperado positivo (+EV).
- `/ligas` — Listado de competiciones soportadas.

---

## 🧪 Suite de Tests Automatizados

Con las dependencias de desarrollo instaladas (`pip install -r requirements-dev.txt`):

```bash
pytest -v
```

> 💡 Los tests `test_db_provider.py` y `test_etl_football_data.py` verifican también consultas sobre la tabla `matches` si el ETL (`python -m src.etl_football_data`) fue ejecutado previamente.

---

## 📚 Documentación Adicional

- [🏗️ Arquitectura del Sistema y Esquema de Datos](docs/ARCHITECTURE.md)
- [⚡ Optimizaciones de Rendimiento y Raspberry Pi](docs/OPTIMIZATIONS.md)
- [📝 Changelog](CHANGELOG.md)

---

## 📄 Créditos y Licencia

Desarrollado por el **Timba Team**.  
Distribuido bajo la Licencia **MIT**. Consulta el archivo [`LICENSE`](LICENSE) para más información.
