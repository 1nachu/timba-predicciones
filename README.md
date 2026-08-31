# 🎯 Timba Predictor v2.2

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-53%20Passing-success?style=flat-square&logo=pytest&logoColor=white)
![Season](https://img.shields.io/badge/Season-2026%2F2027-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Sistema profesional de predicción de fútbol y apuestas de valor (Value Betting)** basado en Distribución de Poisson con ajuste **Dixon-Coles (1997)**, Criterio de Kelly, normalización inteligente de equipos por liga, API REST JSON v1, motor de **Backtesting Cuantitativo**, arquitectura modular en Blueprints y despliegue contenerizado con Docker.

> 🔮 *"No es magia, son matemáticas vectorizadas y valor esperado."*

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Novedades en v2.2](#-novedades-en-v22)
- [Ligas Soportadas (Temporada 26/27)](#-ligas-soportadas)
- [Estructura Modular del Proyecto](#-estructura-del-proyecto)
- [Instalación Rápida](#-instalación-rápida)
- [Ejecución y Despliegue (Docker / Local)](#-ejecución-y-despliegue)
- [API REST JSON v1](#-api-rest-json-v1)
- [Motor de Backtesting Cuantitativo](#-motor-de-backtesting-cuantitativo)
- [Metodología de Predicción y Value Betting](#-metodología-de-predicción-y-value-betting)
- [Suite de Tests Automatizados](#-suite-de-tests-automatizados)
- [Créditos y Licencia](#-créditos-y-licencia)

---

## 🚀 Características

| Funcionalidad | Descripción |
|---|---|
| **⚽ Poisson + Dixon-Coles (1997)** | Matriz de probabilidades 11x11 ajustada con factor de correlación $\tau(x, y, \rho)$ para corregir subdispersión en empates de pocos goles. |
| **💡 Value Betting & Kelly Criterion** | Cálculo automático de Valor Esperado ($\text{EV} = P \times \text{Cuota} - 1$) y sugerencia de tamaño de apuesta con el Criterio de Kelly fraccional. |
| **📈 Backtesting Cuantitativo (Walk-Forward)** | Simulación histórica de apuestas sobre +11 temporadas reales calculando Brier Score, Yield / ROI %, Max Drawdown y evolución de bankroll. |
| **🌐 API REST v1 JSON** | Endpoints para consumo headless de predicciones, value bets, fixtures y marcadores en vivo. |
| **🏗️ Arquitectura Modular (Blueprints & Services)** | Desacoplamiento total entre capa web (`src/web/blueprints/`) y capa de servicios (`src/services/`). |
| **🏎️ Fuerzas Vectorizadas (GroupBy)** | Cálculo de ataque/defensa por liga en **<10 ms** mediante agrupaciones vectoriales de Pandas/NumPy. |
| **🇦🇷 Liga Profesional Argentina** | Integración nativa con **Promiedos.com.ar** y feeds para el calendario 2026/2027. |
| **🏆 Champions League Inter-Liga** | Normalización de fuerzas domésticas calibradas con coeficientes de nivel competitivo por liga. |
| **💾 SQLite Concurrente (WAL Mode)** | Conexión con `PRAGMA journal_mode=WAL;` y `busy_timeout=5000` sin bloqueos de lectura/escritura. |
| **🗂️ FileSystemCache Inter-Proceso** | Caché compartido en disco (`data/flask_cache/`) entre Gunicorn, Flask y Background Updater. |
| **📺 Live Scores en Tiempo Real** | Auto-refresco en vivo vía HTMX con polling fluido de 15 segundos sin recargar la página. |
| **🐳 Docker & Docker Compose** | Entorno contenerizado multi-etapa listo para producción. |

---

## ✨ Novedades en v2.2

1. **Ajuste Dixon-Coles**: Corrección probabilística para marcadores 0-0, 1-0, 0-1 y 1-1.
2. **Value Betting & Kelly**: Identificación de apuestas con valor positivo contra cuotas de mercado (Bet365 / Bookmakers).
3. **Refactorización Modular**: `app.py` modularizado en Flask Blueprints (`dashboard`, `predict`, `fixtures`, `live`, `history`, `seo`, `api`) y Service Layer (`services/`).
4. **API REST v1**: Endpoints JSON documentados para integración móvil, Discord/Telegram bots y servicios externos.
5. **Backtesting Cuantitativo**: CLI `scripts/run_backtest.py` para evaluar ROI y Brier Score histórico.
6. **Docker & CI/CD**: Manifiestos `Dockerfile`, `docker-compose.yml` y pipeline en `.github/workflows/ci.yml`.

---

## 📊 Ligas Soportadas

Sincronizadas al calendario oficial de la **Temporada 2026/2027** (`2627` / `2026`):

| Código | Liga | País | Temporada Actual | Fuente Fixture |
|---|---|---|---|---|
| `ARG` | **Liga Profesional** | 🇦🇷 Argentina | 2026 | Promiedos / Football-Data |
| `E0` | **Premier League** | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 26/27 | FixtureDownload (epl-2026) |
| `SP1` | **La Liga** | 🇪🇸 España | 26/27 | FixtureDownload (la-liga-2026) |
| `D1` | **Bundesliga** | 🇩🇪 Alemania | 26/27 | FixtureDownload (bundesliga-2026) |
| `I1` | **Serie A** | 🇮🇹 Italia | 26/27 | FixtureDownload (serie-a-2026) |
| `F1` | **Ligue 1** | 🇫🇷 Francia | 26/27 | FixtureDownload (ligue-1-2026) |
| `P1` | **Primeira Liga** | 🇵🇹 Portugal | 26/27 | FixtureDownload (primeira-liga-2026) |
| `N1` | **Eredivisie** | 🇳🇱 Países Bajos | 26/27 | FixtureDownload (eredivisie-2026) |
| `CL` | **UEFA Champions League** | 🇪🇺 Europa | 26/27 | FixtureDownload (champions-league-2026) |

---

## 📁 Estructura del Proyecto

```
timba-predicciones/
├── app.py                          # 🌐 Servidor Flask (Modular & Factory)
├── background_updater.py           # 🔄 Worker en segundo plano y auditoría
├── run_live.py                     # 📺 Servicio de Live Scores independiente
├── requirements.txt                # 📦 Dependencias de producción y testing
├── setup.py                        # ⚙️ Compilación Cython opcional (timba_fast)
├── Dockerfile                      # 🐳 Dockerfile multi-etapa
├── docker-compose.yml              # 🐳 Orquestación de Web + Background Updater
├── .github/workflows/ci.yml        # 🤖 Pipeline de Integración Continua (CI)
├── .env.example                    # 🔑 Variables de entorno de ejemplo
│
├── scripts/
│   └── run_backtest.py             # 📈 CLI de Backtesting histórico cuantitativo
│
├── src/
│   ├── timba_core.py               # 🏛️ Fachada central y configuración de ligas
│   ├── db_data_provider.py         # 📊 Proveedor de datos SQLite de alta velocidad
│   ├── etl_football_data.py        # ⬇️ Pipeline ETL automatizado (8 ligas)
│   ├── live_scores.py              # 📺 Motor de eventos y snapshots en vivo
│   ├── team_normalization.py       # 🔗 Normalizador de equipos con filtrado por liga
│   │
│   ├── core/                       # 🧮 Dominio y Modelado Matemático
│   │   ├── models.py               #    └─ Dataclasses (MatchPrediction, MatchFixture)
│   │   └── prediction.py           #    └─ Poisson + Dixon-Coles, Fuerzas y Coeficientes
│   │
│   ├── analytics/                  # 📈 Análisis Cuantitativo y Finanzas
│   │   ├── __init__.py
│   │   └── backtester.py           #    └─ Motor de Backtesting, Brier Score y Kelly
│   │
│   ├── services/                   # ⚙️ Capa de Servicios Desacoplada
│   │   ├── audit_service.py        #    └─ Validación de aciertos e historial
│   │   ├── fixtures_service.py     #    └─ Normalización, fixtures y marcadores
│   │   └── prediction_service.py   #    └─ Caché de dashboard y predicciones
│   │
│   ├── web/                        # 🌐 Capa Web (Flask Blueprints)
│   │   └── blueprints/
│   │       ├── dashboard.py        #    └─ Dashboard principal (/)
│   │       ├── predict.py          #    └─ Predicciones manuales (/predict)
│   │       ├── fixtures.py         #    └─ Fixtures y calendario (/fixtures)
│   │       ├── live.py             #    └─ Partidos en vivo (/live)
│   │       ├── history.py          #    └─ Historial de aciertos (/history)
│   │       ├── seo.py              #    └─ robots.txt y sitemap.xml
│   │       └── api.py              #    └─ REST API JSON (/api/v1/...)
│   │
│   ├── scrapers/                   # 🕷️ Web Scraping
│   │   └── fixtures_scraper.py     #    └─ Scraper Promiedos (Next.js) y FixtureDownload
│   │
│   └── utils/                      # 🛠️ Utilidades Compartidas
│       ├── markets.py              #    └─ Mercados, EV, Kelly, Semáforos y Reglas
│       └── shared.py               #    └─ Conexión SQLite WAL, aliases y rutas
│
├── tests/                          # 🧪 Suite de Tests Automatizados (Pytest - 43 tests)
│   ├── test_api_endpoints.py       #    └─ Tests de integración web Flask
│   ├── test_api_v1.py              #    └─ Tests de la API REST v1
│   ├── test_backtester.py          #    └─ Tests del motor de backtesting
│   ├── test_db_provider.py         #    └─ Tests de base de datos y WAL
│   ├── test_etl_football_data.py   #    └─ Tests del pipeline ETL
│   ├── test_frontend.py            #    └─ Tests de renderizado de plantillas
│   ├── test_live_scores.py         #    └─ Tests de marcadores en vivo
│   ├── test_markets.py             #    └─ Tests de mercados, EV y Kelly
│   └── test_prediction_vectorization.py # └─ Tests matemáticos y Dixon-Coles
│
├── data/                           # 💾 Bases de datos SQLite y caché en disco
├── templates/                      # 🎨 Plantillas Jinja2 (Cyber Pitch Dark UI)
└── static/                         # 🎨 CSS, fuentes e íconos locales
```

---

## ⚙️ Instalación Rápida

### Entorno Local (Python)

```bash
# 1. Clonar repositorio
git clone https://github.com/1nachu/timba-predicciones.git
cd timba-predicciones

# 2. Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
```

---

## 🚀 Ejecución y Despliegue

### Opción A: Despliegue con Docker Compose (Recomendado)

```bash
# Construir y levantar contenedores en segundo plano
docker compose up -d --build

# Ver logs en tiempo real
docker compose logs -f
```
El servidor web quedará disponible en `http://localhost:5000`.

### Opción B: Ejecución Local

```bash
# Terminal 1: Servidor Web Flask
python app.py

# Terminal 2: Worker de fondo (actualiza caché cada 5 min)
python background_updater.py --loop 300
```

---

## 📡 API REST JSON v1

Todos los endpoints retornan respuestas en formato `application/json`:

### 1. Health Check
```http
GET /api/v1/health
```
```json
{
  "status": "ok",
  "version": "2.2",
  "service": "Timba Predictor API",
  "timestamp": "2026-08-31T15:30:00Z"
}
```

### 2. Ligas Soportadas
```http
GET /api/v1/leagues
```

### 3. Predicción con Value Betting y Kelly
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

### 4. Escaneo de Value Bets del Día
```http
GET /api/v1/value-bets?min_ev=0.05
```

---

## 📈 Motor de Backtesting Cuantitativo

Ejecuta simulaciones walk-forward sobre temporadas pasadas para medir calibración y rentabilidad matemática:

```bash
# Backtest estándar con stake fijo de $10 en Premier League
python scripts/run_backtest.py --league E0 --seasons 3 --min-ev 0.04

# Backtest con Criterio de Kelly (fracción 0.25) en La Liga
python scripts/run_backtest.py --league SP1 --seasons 3 --stake-mode kelly --kelly-fraction 0.25
```

**Métricas evaluadas:**
- **Brier Score (1X2)**: Medida cuadrática de precisión probabilística ($0.0 = \text{perfección}$).
- **Yield / ROI (%)**: Rendimiento neto sobre el capital total arriesgado.
- **Max Drawdown (%)**: Máxima caída de bankroll desde el punto máximo histórico.
- **Hit Rate (%)**: Porcentaje de apuestas ganadoras.

---

## 🤖 Bot de Telegram Interactivo (`bot.py`)

Timba Predictor incluye un Bot de Telegram con interfaz interactiva completa basada en botones inline y comandos directos:

### Configuración Rápida
1. Crea un bot con [@BotFather](https://t.me/BotFather) en Telegram y copia el token.
2. Agrega el token en tu archivo `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
   ```
3. Inicia el bot:
   ```bash
   python bot.py
   ```

### Comandos del Bot
- `/start` - Menú interactivo con botones inline para navegación rápida.
- `/live` - Marcadores en tiempo real y predicciones dinámicas In-Play.
- `/proximos [liga_id]` - Fixture del día con probabilidades 1X2 del modelo.
- `/predecir <Local> vs <Visitante>` - Análisis completo pre-match (xG, 1X2, Over/Under, BTTS, marcadores probables).
- `/inplay <Local> vs <Vis> <score> min <minuto> [rojas L-V]` - Simulación In-Play en vivo con minuto, marcador y expulsiones.
  *(Ej: `/inplay Real Madrid vs Barcelona 2-1 min 70 rojas 0-1`)*
- `/valuebets` - Oportunidades de apuestas de valor (+EV) y sizing de Kelly.
- `/ligas` - Listado interactivo de competiciones soportadas.

---

## 🧪 Suite de Tests Automatizados

La suite integral de tests cubre matemáticas, modelos Poisson/Dixon-Coles, endpoints web, API REST, In-Play en vivo, Bot de Telegram y backtesting:

```bash
pytest -v
```

```
============================= 53 passed in 13.96s ==============================
```

---

## 📄 Créditos y Licencia

Desarrollado con dedicación por el **Timba Team**.  
Distribuido bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más información.
