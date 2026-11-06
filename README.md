# Timba Predictor v2.2

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-60%20Passing-success?style=flat-square&logo=pytest&logoColor=white)
![Season](https://img.shields.io/badge/Season-2026%2F2027-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

Sistema de modelado estadístico para predicción de partidos de fútbol y detección de apuestas con valor esperado positivo (*Value Betting*). Implementa la distribución de Poisson bivariada con ajuste de correlación de **Dixon-Coles (1997)**, dimensionamiento de capital mediante el **Criterio de Kelly**, predicciones dinámicas en tiempo real (*In-Play*), motor de *backtesting* cuantitativo, API REST JSON v1 y despliegue contenerizado con Docker.

---

## Tabla de Contenidos

- [Características Técnicas](#características-técnicas)
- [Competiciones Soportadas](#competiciones-soportadas)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Instalación y Configuración](#instalación-y-configuración)
- [Variables de Entorno](#variables-de-entorno)
- [Ejecución y Despliegue](#ejecución-y-despliegue)
- [API REST v1](#api-rest-v1)
- [Backtesting Cuantitativo](#backtesting-cuantitativo)
- [Bot de Telegram](#bot-de-telegram)
- [Pruebas Automatizadas](#pruebas-automatizadas)
- [Documentación Adicional](#documentación-adicional)
- [Licencia](#licencia)

---

## Características Técnicas

| Módulo | Descripción |
|---|---|
| **Modelo Poisson + Dixon-Coles (1997)** | Matriz de probabilidades $11 \times 11$ ajustada con el factor de dependencia $\tau(x, y, \rho)$ para corregir la subestimación de empates de bajo marcador (`0-0`, `1-0`, `0-1`, `1-1`). |
| **Value Betting y Criterio de Kelly** | Cálculo de Valor Esperado ($\text{EV} = P \times \text{Cuota} - 1$) y asignación óptima de banca mediante el Criterio de Kelly fraccional. |
| **Backtesting Walk-Forward** | Simulación histórica sin *look-ahead bias* con reporte de Brier Score, Yield / ROI %, Max Drawdown y evolución de capital. |
| **Predicción Dinámica In-Play** | Recálculo en tiempo real de tasas de gol esperado ($\lambda$) en función del minuto de juego, marcador actual y sanciones disciplinarias (tarjetas rojas). |
| **Normalización Inter-Liga (Champions League)** | Ponderación de fuerzas ofensivas y defensivas domésticas ajustadas por coeficientes competitivos de cada liga (`COEFICIENTES_LIGAS`). |
| **Vectorización y Extensión Cython** | Cálculo de fuerzas por liga en `<10 ms` con operaciones vectoriales de Pandas/NumPy y módulo opcional compilado en C (`timba_fast`). |
| **Persistencia SQLite en Modo WAL** | Conexiones concurrentes con `PRAGMA journal_mode=WAL;` y `busy_timeout=5000`, con *fallback* transparente a fuentes CSV online si la base local aún no fue inicializada. |
| **Arquitectura Modular** | Separación entre capa de presentación (`src/web/blueprints/`), capa de servicios (`src/services/`), pipeline ETL (`src/etl/`) y núcleo matemático (`src/core/`). |

---

## Competiciones Soportadas

Configuradas para el calendario oficial de la **Temporada 2026/2027** (`2627` / `2026`):

| ID | Código | Competición | País / Región | Temporada | Fuente de Calendario |
|---|---|---|---|---|---|
| `10` | `ARG` | Liga Profesional | Argentina | 2026 | Promiedos / Football-Data (`new/ARG.csv`) |
| `1` | `E0` | Premier League | Inglaterra | 26/27 | FixtureDownload (`epl-2026`) |
| `2` | `SP1` | La Liga | España | 26/27 | FixtureDownload (`la-liga-2026`) |
| `3` | `I1` | Serie A | Italia | 26/27 | FixtureDownload (`serie-a-2026`) |
| `4` | `D1` | Bundesliga | Alemania | 26/27 | FixtureDownload (`bundesliga-2026`) |
| `5` | `F1` | Ligue 1 | Francia | 26/27 | FixtureDownload (`ligue-1-2026`) |
| `6` | `P1` | Primeira Liga | Portugal | 26/27 | FixtureDownload (`primeira-liga-2026`) |
| `7` | `N1` | Eredivisie | Países Bajos | 26/27 | FixtureDownload (`eredivisie-2026`) |
| `8` | `CL` | UEFA Champions League | Europa | 26/27 | FixtureDownload (`champions-league-2026`) |

---

## Estructura del Proyecto

```text
timba-predicciones/
├── app.py                          # Servidor Flask y registro de Blueprints
├── background_updater.py           # Proceso de actualización de caché, ETL automático y auditoría
├── run_live.py                     # Servicio de sincronización de marcadores en vivo
├── bot.py                          # Punto de entrada del Bot de Telegram
├── setup.py                        # Script de compilación para la extensión Cython (timba_fast)
├── requirements.txt                # Dependencias de producción
├── requirements-dev.txt            # Dependencias de desarrollo y testing (pytest)
├── Dockerfile                      # Imagen Docker multi-etapa
├── docker-compose.yml              # Orquestación de servicios (web, updater, live, bot)
├── .github/workflows/ci.yml        # Pipeline de Integración Continua (GitHub Actions)
├── .env.example                    # Plantilla de variables de entorno
├── CHANGELOG.md                    # Registro de cambios por versión
│
├── docs/
│   ├── ARCHITECTURE.md             # Diseño de arquitectura, flujo de datos y esquemas SQLite
│   └── OPTIMIZATIONS.md            # Documentación de rendimiento y ejecución en hardware embebido
│
├── scripts/
│   ├── run_backtest.py             # CLI de backtesting histórico cuantitativo
│   └── migrate_legacy_aliases.py   # Script de migración de alias de equipos a SQLite
│
├── src/
│   ├── timba_core.py               # Fachada de compatibilidad y caché LRU de datos históricos
│   ├── timba_fast.pyx              # Implementación Cython del motor Poisson (opcional)
│   ├── db_data_provider.py         # Proveedor de datos SQLite con fallback a CSV online
│   ├── etl_football_data.py        # CLI del pipeline ETL histórico
│   ├── live_scores.py              # Gestión de estado y eventos de partidos en vivo
│   ├── football_api_client.py      # Cliente HTTP para Football-Data.org API v4
│   ├── team_normalization.py       # Normalizador de nombres de equipos filtrado por liga
│   ├── team_normalization_cli.py   # CLI de administración de equipos normalizados
│   │
│   ├── config/
│   │   └── leagues.py              # Definición canónica de ligas, códigos y URLs
│   ├── core/
│   │   ├── models.py               # Modelos de datos (MatchPrediction, MatchFixture, MLFeatures)
│   │   └── prediction.py           # Algoritmos Poisson, Dixon-Coles, fuerzas, Champions e In-Play
│   ├── analytics/
│   │   └── backtester.py           # Motor Walk-Forward, Brier Score y Kelly
│   ├── etl/
│   │   ├── config.py               # Configuración de ligas y columnas del ETL
│   │   ├── extractor.py            # Descarga de archivos CSV históricos por temporada
│   │   ├── transformer.py          # Normalización, limpieza y tipado de DataFrames
│   │   ├── loader.py               # Carga en SQLite / PostgreSQL (tabla matches)
│   │   └── pipeline.py             # Orquestador del flujo ETL
│   ├── services/
│   │   ├── audit_service.py        # Evaluación y sincronización de predicciones vs resultados reales
│   │   ├── fixtures_service.py     # Obtención y enriquecimiento de próximos partidos
│   │   └── prediction_service.py   # Servicio de caché y cálculo de predicciones
│   ├── scrapers/
│   │   └── fixtures_scraper.py     # Extracción de calendarios desde Promiedos y FixtureDownload
│   ├── bot/
│   │   ├── bot_app.py              # Inicialización de la aplicación de Telegram
│   │   ├── handlers.py             # Manejadores de comandos y callbacks
│   │   └── formatters.py           # Formateo de respuestas
│   ├── utils/
│   │   ├── markets.py              # Mercados derivados, Value Bets, EV y Criterio de Kelly
│   │   └── shared.py               # Conexiones SQLite WAL, normalización CSV y constantes
│   └── web/
│       ├── cache.py                # Configuración de FileSystemCache
│       └── blueprints/             # Rutas modulares (dashboard, predict, fixtures, live, history, seo, api)
│
├── tests/                          # Suite de 60 pruebas automatizadas (12 módulos)
├── templates/                      # Plantillas Jinja2 + HTMX
└── static/                         # Hojas de estilo, fuentes e íconos locales
```

---

## Instalación y Configuración

### 1. Clonar el repositorio y crear el entorno virtual

**Linux / macOS:**
```bash
git clone https://github.com/1nachu/timba-predicciones.git
cd timba-predicciones

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
# Para desarrollo y ejecución de tests:
pip install -r requirements-dev.txt

cp .env.example .env
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/1nachu/timba-predicciones.git
cd timba-predicciones

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
# Para desarrollo y ejecución de tests:
pip install -r requirements-dev.txt

copy .env.example .env
```

### 2. Inicializar la base de datos histórica local

El pipeline ETL descarga y normaliza las últimas 3 temporadas de las 8 ligas dentro de `data/databases/football_data.db` (tabla `matches`):

```bash
python -m src.etl_football_data
```

> Nota: Si se ejecuta `background_updater.py` sin haber corrido este comando previamente, el actualizador detecta la ausencia de la tabla `matches` y dispara el ETL de forma automática en su primer ciclo.

### 3. Compilar la extensión Cython (Opcional)

Para maximizar el rendimiento de cálculo en servidores de bajos recursos (Raspberry Pi o mini PCs):

```bash
python setup.py build_ext --inplace
```

---

## Variables de Entorno

Definidas en el archivo `.env` en la raíz del proyecto (ver plantilla en [`.env.example`](.env.example)):

| Variable | Requerida | Descripción |
|---|---|---|
| `SECRET_KEY` | Sí (producción) | Clave de firma de sesiones Flask. Generar con `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `FOOTBALL_DATA_API_KEY` | Opcional | Clave de API de [football-data.org](https://www.football-data.org/) para el servicio de marcadores en vivo (`run_live.py`). |
| `TELEGRAM_BOT_TOKEN` | Opcional | Token generado con [@BotFather](https://t.me/BotFather) para ejecutar el bot de Telegram (`bot.py`). |

---

## Ejecución y Despliegue

### Opción A: Docker Compose (Recomendado para Producción / Home Server)

```bash
# Construir e iniciar servidor web, actualizador en segundo plano y servicio de marcadores en vivo
docker compose up -d --build

# (Opcional) Incluir también el contenedor del Bot de Telegram
docker compose --profile bot up -d --build

# Consultar logs de los servicios
docker compose logs -f
```
La aplicación web y la API estarán disponibles en `http://localhost:5000`.

### Opción B: Ejecución Local Manual

| Servicio | Comando | Función |
|---|---|---|
| **Servidor Web y API** | `python app.py` | Inicia el servidor Flask en `http://localhost:5000`. |
| **Background Updater** | `python background_updater.py --loop 300` | Actualiza `data/dashboard_cache.json` y sincroniza la auditoría cada 5 minutos. |
| **Live Scores** | `python run_live.py` | Actualiza los marcadores en tiempo real en `data/databases/live_scores.db`. |
| **Bot de Telegram** | `python bot.py` | Inicia el bot interactivo (requiere `TELEGRAM_BOT_TOKEN`). |

---

## API REST v1

Todos los endpoints bajo `/api/v1` devuelven respuestas en formato `application/json`:

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/health` | Estado operativo del servicio y versión actual. |
| `GET` | `/api/v1/leagues` | Listado de competiciones configuradas. |
| `GET` | `/api/v1/predict` | Predicción pre-partido o In-Play. Parámetros: `liga_id`, `local`, `visitante`, cuotas opcionales (`odds_home`, `odds_draw`, `odds_away`) y estado en vivo (`live=true`, `minute`, `home_score`, `away_score`, `red_cards_home`, `red_cards_away`). |
| `GET` | `/api/v1/value-bets` | Detección de apuestas con valor esperado positivo en la jornada (`min_ev=0.05`). |
| `GET` | `/api/v1/fixtures` | Calendario de próximos partidos con probabilidades proyectadas (`liga_id`). |
| `GET` | `/api/v1/live` | Partidos en curso con probabilidades dinámicas In-Play. |
| `GET` | `/api/v1/history` | Historial auditado de predicciones frente a resultados reales (`liga_id`, `days`). |

### Ejemplo de respuesta: `/api/v1/predict`

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
      "badge": "VALUE BET"
    }
  ]
}
```

---

## Backtesting Cuantitativo

El script `scripts/run_backtest.py` ejecuta simulaciones *walk-forward* sobre datos históricos para evaluar la calibración probabilística y el retorno del modelo:

```bash
# Backtest con stake plano en Premier League (últimas 3 temporadas)
python scripts/run_backtest.py --league E0 --seasons 3 --min-ev 0.04

# Backtest con Criterio de Kelly fraccional (0.25) en La Liga
python scripts/run_backtest.py --league SP1 --seasons 3 --stake-mode kelly --kelly-fraction 0.25
```

**Indicadores reportados:**
- **Brier Score (1X2):** Error cuadrático medio de las probabilidades predichas ($0.0 = \text{calibración perfecta}$).
- **Yield / ROI (%):** Beneficio neto porcentual sobre el volumen total apostado.
- **Max Drawdown (%):** Caída máxima registrada desde un pico previo de capital.
- **Hit Rate (%):** Proporción de apuestas acertadas sobre el total ejecutado.

---

## Bot de Telegram

Comandos soportados por `bot.py`:
- `/start` — Menú principal de navegación.
- `/live` — Marcadores en directo y proyecciones In-Play.
- `/proximos [liga_id]` — Calendario próximo con probabilidades 1X2.
- `/predecir <Local> vs <Visitante>` — Reporte pre-partido (xG, 1X2, Over/Under, BTTS y marcadores más probables).
- `/inplay <Local> vs <Vis> <score> min <minuto> [rojas L-V]` — Cálculo en tiempo real (ejemplo: `/inplay Real Madrid vs Barcelona 2-1 min 70 rojas 0-1`).
- `/valuebets` — Oportunidades del día con valor esperado positivo (+EV).
- `/ligas` — Listado de competiciones e identificadores disponibles.

---

## Pruebas Automatizadas

Con las dependencias de desarrollo instaladas (`pip install -r requirements-dev.txt`):

```bash
pytest -v
```

---

## Documentación Adicional

- [Arquitectura del Sistema y Esquema de Base de Datos](docs/ARCHITECTURE.md)
- [Optimizaciones de Rendimiento y Hardware Embebido](docs/OPTIMIZATIONS.md)
- [Historial de Cambios (Changelog)](CHANGELOG.md)

---

## Licencia

Desarrollado por **Timba Team**. Distribuido bajo la licencia **MIT**. Consulte el archivo [`LICENSE`](LICENSE) para más detalles.
