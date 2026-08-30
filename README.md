# 🎯 Timba Predictor v2.2

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-19%20Passing-success?style=flat-square&logo=pytest&logoColor=white)
![Season](https://img.shields.io/badge/Season-2026%2F2027-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Sistema de predicción de resultados de fútbol de alto rendimiento** basado en Distribución de Poisson vectorizada, normalización de equipos por liga, live scores concurrentes y caché inter-procesos persistente.

> 🔮 *"No es magia, son matemáticas vectorizadas."*

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Ligas Soportadas (Temporada 26/27)](#-ligas-soportadas)
- [Estructura Modular del Proyecto](#-estructura-del-proyecto)
- [Instalación](#-instalación)
- [Ejecución](#-ejecución)
- [Suite de Tests Automatizados](#-suite-de-tests-automatizados)
- [Live Scores y Concurrencia SQLite](#-live-scores-y-concurrencia-sqlite)
- [Background Updater y FileSystemCache](#-background-updater-y-filesystemcache)
- [Mantenimiento (CLI)](#-mantenimiento-cli)
- [Metodología de Predicción y Mercados](#-metodología-de-predicción-y-mercados)
- [Optimizaciones de Rendimiento](#-optimizaciones-de-rendimiento)
- [Créditos y Licencia](#-créditos)

---

## 🚀 Características

| Funcionalidad | Descripción |
|---------------|-------------|
| **⚽ Poisson Vectorizado (NumPy)** | Cálculo de xG y matriz de probabilidades 11x11 con `np.outer()`, calculando **>25,000 predicciones/segundo**. |
| **🏎️ Fuerzas Vectorizadas (GroupBy)** | Cálculo de ataque/defensa por liga en **7.6 ms** mediante agrupaciones vectoriales de Pandas. |
| **🇦🇷 Liga Profesional Argentina** | Integración nativa con **Promiedos.com.ar** y feeds para el calendario 2026. |
| **🏆 UEFA Champions League** | Predicción entre ligas combinando fuerzas domésticas y ponderación de promedios de gol. |
| **💾 SQLite Concurrente (Modo WAL)** | Conexión centralizada con `PRAGMA journal_mode=WAL;` y `busy_timeout=5000` sin bloqueos de lectura/escritura. |
| **🗂️ FileSystemCache Inter-Proceso** | Caché compartido en disco (`data/flask_cache/`) entre Gunicorn, Flask y Background Updater. |
| **🎯 Centralización de Mercados** | Módulo canónico `src/utils/markets.py` unificando 1X2, Doble Oportunidad, Over/Under, Córners, Tarjetas y Semáforo. |
| **🧩 Arquitectura Desacoplada** | Separación limpia de responsabilidades en `src/core/`, `src/scrapers/`, `src/utils/` y fachada `src/timba_core.py`. |
| **🧪 Suite Integral de Tests** | 19 tests automatizados con `pytest` cubriendo ETL, base de datos, algoritmos y endpoints web. |
| **📺 Live Scores en Vivo** | Polling en tiempo real y lectura no bloqueante desde base de datos local. |
| **🚀 HTMX Boosting & UI Dark** | Navegación instantánea (~50ms) con estilo oscuro inspirado en Promiedos. |

---

## 📊 Ligas Soportadas

Sincronizadas al calendario oficial de la **Temporada 2026/2027** (`2627` / `2026`):

| Código | Liga | País | Temporada Actual | Fuente Fixture |
|--------|------|------|------------------|----------------|
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
timba-predictor/
├── app.py                          # 🌐 Servidor Flask con FileSystemCache y rutas HTMX
├── background_updater.py           # 🔄 Actualizador en segundo plano y auditoría
├── run_live.py                     # 📺 Servicio de Live Scores independiente
├── requirements.txt                # 📦 Dependencias del proyecto
├── setup.py                        # ⚙️  Compilación Cython opcional (timba_fast)
├── .env                            # 🔑 Variables de entorno
│
├── src/
│   ├── timba_core.py               # 🏛️  Fachada pública unificada (retrocompatibilidad)
│   ├── db_data_provider.py         # 📊 Proveedor de datos SQLite de alta velocidad
│   ├── etl_football_data.py        # ⬇️  Pipeline ETL automatizado (8 ligas)
│   ├── live_scores.py              # 📺 Motor de eventos y snapshots en vivo
│   ├── team_normalization.py       # 🔗 Normalizador de equipos con filtrado por liga
│   ├── team_normalization_cli.py   # 🛠️  Herramienta CLI de gestión de aliases
│   │
│   ├── core/                       # 🧮 Dominio y Algoritmos Core
│   │   ├── __init__.py
│   │   ├── models.py               #    └─ Dataclasses (MatchPrediction, MatchFixture, MLFeatures)
│   │   └── prediction.py           #    └─ Poisson vectorizado, H2H y predicción Champions
│   │
│   ├── scrapers/                   # 🕷️ Web Scraping y Calendarios
│   │   ├── __init__.py
│   │   └── fixtures_scraper.py     #    └─ Scraper Promiedos (Next.js) y FixtureDownload
│   │
│   └── utils/                      # ⚙️  Utilidades Compartidas
│       ├── __init__.py
│       ├── markets.py              #    └─ Reglas 1X2, Doble Oportunidad, Semáforo y Mercados
│       └── shared.py               #    └─ Conexión SQLite WAL, aliases, constantes y rutas
│
├── tests/                          # 🧪 Suite de Tests Automatizados (Pytest)
│   ├── test_api_endpoints.py       #    └─ Tests de integración de rutas Flask
│   ├── test_db_provider.py         #    └─ Tests de concurrencia y PRAGMAs WAL
│   ├── test_etl_football_data.py   #    └─ Tests de limpieza y esquema league_code
│   ├── test_live_scores.py         #    └─ Tests de snapshots y eventos
│   ├── test_markets.py             #    └─ Tests de semáforo y reglas de mercados
│   └── test_prediction_vectorization.py # └─ Tests matemáticos de Poisson vectorizado
│
├── data/
│   ├── databases/                  # 💾 Bases de datos SQLite centralizadas
│   │   ├── football_data.db        #    └─ Partidos históricos indexados con league_code
│   │   ├── team_normalizer.db      #    └─ Diccionario y aliases de equipos
│   │   └── live_scores.db          #    └─ Partidos en vivo
│   ├── flask_cache/                # 🗂️ Caché persistente multi-proceso (FileSystemCache)
│   └── dashboard_cache.json        # ⚡ JSON precalculado para carga ultra-rápida
│
├── templates/                      # 🎨 Plantillas Jinja2 (Dark Theme Promiedos)
├── static/                         # 🎨 CSS, fuentes e íconos
└── logs/                           # 📝 Logs estructurados con rotación
```

---

## ⚙️ Instalación

### 1. Clonar y Configurar Entorno Virtual

```bash
git clone https://github.com/1nachu/timba-predicciones.git
cd timba-predicciones

# Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Crea tu archivo `.env` en la raíz:

```env
SECRET_KEY=clave_secreta_timba_2026_produccion
FOOTBALL_DATA_API_KEY=tu_api_key_aqui
```

### 3. Compilación Opcional de Acelerador Cython

```bash
python setup.py build_ext --inplace
```

---

## 🚀 Ejecución

### Paso 1: Sincronización Inicial de Datos (ETL)

Descarga y procesa las ligas para la temporada actual:

```bash
python src/etl_football_data.py
```

*Para descargar el histórico completo (hasta 11 temporadas por liga):*
```bash
python src/etl_football_data.py --historico
```

### Paso 2: Precalcular Caché del Dashboard

```bash
python background_updater.py
```

### Paso 3: Iniciar el Servidor Web

```bash
python app.py
```

Accede a tu navegador en: **http://localhost:5000**

---

## 🧪 Suite de Tests Automatizados

El proyecto incluye 19 tests unitarios y de integración para garantizar estabilidad matemática, concurrencia y funcionamiento de endpoints:

```bash
# Ejecutar toda la suite
pytest -v tests/
```

**Módulos evaluados:**
- `test_prediction_vectorization.py`: Exactitud de la matriz Poisson $11 \times 11$, probabilidades que suman 1.0, consistencia de Doble Oportunidad.
- `test_db_provider.py`: Verificación de modo WAL, `busy_timeout` $\ge 5000$ y lectura multihilo concurrente sin bloqueos.
- `test_etl_football_data.py`: Validación de tipos, filtrado FTR e integridad de la columna `league_code`.
- `test_markets.py`: Lógica unificada de recomendaciones, umbrales de semáforo (`ALTO`, `MEDIO`, `BAJO`) y tarjetas rojas.
- `test_api_endpoints.py`: Verificación de respuestas HTTP 200 en rutas `/`, `/predict`, `/fixtures`, `/live` y `/history`.

---

## 📺 Live Scores y Concurrencia SQLite

Para evitar cuellos de botella y errores `database is locked`:
1. **Modo WAL (`Write-Ahead Logging`)**:
   - Los lectores leen instantáneamente snapshots sin bloquear a los escritores.
   - Configurado en `src/utils/shared.py` con `PRAGMA busy_timeout = 5000;`.
2. **Servicio Live Scores**:
   ```bash
   python run_live.py
   ```
   Consulta la API respetando rate limits y persiste en `data/databases/live_scores.db`.

---

## 🔄 Background Updater y FileSystemCache

- **`background_updater.py`**:
  Ejecuta scraping, cálculo de fuerzas y genera `data/dashboard_cache.json` en segundo plano en menos de **2 segundos**.
  ```bash
  python background_updater.py --loop 300  # Ejecución periódica cada 5 minutos
  ```
- **`FileSystemCache`**:
  Configurado en `data/flask_cache/`. Permite que múltiples instancias o procesos compartan resultados memoizados de funciones pesadas (`cargar_datos_liga_cached`, `obtener_fixtures_cached`) sin requerir un servidor Redis externo.

---

## 🧮 Metodología de Predicción y Mercados

### 1. Cálculo de Goles Esperados (xG)
$$\lambda_{\text{Local}} = \text{Ataque}_{\text{Local}} \times \text{Defensa}_{\text{Visitante}} \times \text{MediaGoles}_{\text{Local}}$$
$$\lambda_{\text{Visitante}} = \text{Ataque}_{\text{Visitante}} \times \text{Defensa}_{\text{Local}} \times \text{MediaGoles}_{\text{Visitante}}$$

*Ponderación temporal:* 60% forma reciente (últimos 5 partidos) + 40% temporada completa.

### 2. Matriz de Probabilidades Poisson
$$P(L=i, V=j) = \frac{\lambda_L^i e^{-\lambda_L}}{i!} \times \frac{\lambda_V^j e^{-\lambda_V}}{j!}$$

Calculado vectorialmente mediante producto exterior NumPy `np.outer(prob_l, prob_v)`:
- **Victoria Local ($P(1)$)**: $\sum_{i > j} P(i,j)$ (triángulo inferior)
- **Empate ($P(X)$)**: $\sum_{i = j} P(i,j)$ (traza diagonal)
- **Victoria Visitante ($P(2)$)**: $\sum_{i < j} P(i,j)$ (triángulo superior)

### 3. Mercados Adicionales
- **Over/Under Goles**: $1.5$, $2.5$, $3.5$ mediante Poisson CDF acumulada.
- **Doble Oportunidad**: $1X$, $X2$, $12$.
- **Córners Esperados**: Over/Under $8.5$, $9.5$, $10.5$ y ganador de córners.
- **Tarjetas**: Over/Under $2.5$, $3.5$, $4.5$ y probabilidad de tarjeta roja.

---

## ⚡ Optimizaciones de Rendimiento

| Métrica | Versión Anterior | Versión 2.2 (Actual) | Mejora |
|---------|------------------|----------------------|--------|
| **Cálculo de Fuerzas por Liga** | ~320 ms | **7.6 ms** | **42x más rápido** |
| **Motor de Predicción Poisson** | ~1,200 pred/s | **>25,000 pred/s** | **20x más rápido** |
| **Navegación Web (HTMX + Cache)** | 2.5 s | **< 50 ms** | **50x más rápido** |
| **Carga de Datos Dashboard** | 3.5 s | **1.8 s** | **2x más rápido** |
| **Concurrencia SQLite** | Bloqueos en GET | **Cero bloqueos (WAL)** | **100% estable** |

---

## 🙏 Créditos

- **Datos Históricos y Resultados:** [football-data.co.uk](https://www.football-data.co.uk)
- **Fixtures y Calendarios:** [promiedos.com.ar](https://www.promiedos.com.ar) y [fixturedownload.com](https://fixturedownload.com)
- **API Live Scores:** [football-data.org](https://www.football-data.org)
- **Desarrollo y Arquitectura:** Timba Core Team

---

<div align="center">
  <sub>Hecho con ❤️ y matemáticas vectorizadas por el Timba Team</sub><br>
  <img src="https://img.shields.io/badge/Release-Agosto%202026-blue?style=flat-square">
  <img src="https://img.shields.io/badge/Status-Optimized%20v2.2-green?style=flat-square">
</div>
