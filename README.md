# 🎯 Timba Predictor v2.1

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![Maintenance](https://img.shields.io/badge/Maintained-Yes-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**Sistema de predicción de resultados de fútbol** basado en Distribución de Poisson y datos históricos de xG, con normalización inteligente de nombres de equipos por liga y live scores en tiempo real.

> 🔮 *"No es magia, son matemáticas."*

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Ligas Soportadas](#-ligas-soportadas)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación](#-instalación)
- [Ejecución](#-ejecución)
- [Live Scores](#-live-scores)
- [Background Updater](#-background-updater)
- [Mantenimiento (CLI)](#-mantenimiento-cli)
- [Metodología de Predicción](#-metodología-de-predicción)
- [Tecnologías](#-tecnologías)
- [Optimizaciones de Rendimiento](#-optimizaciones-de-rendimiento)
- [Créditos](#-créditos)

---

## 🚀 Características

| Funcionalidad | Descripción |
|---------------|-------------|
| **⚽ Predicción Poisson** | Cálculo de xG (Expected Goals) con probabilidades 1X2, Over/Under y BTTS |
| **🇦🇷 Liga Argentina** | Integración completa con **Promiedos.com.ar** para fixtures en tiempo real |
| **📺 Live Scores** | Resultados en tiempo real desde **DB local** (sin límites de API) |
| **🔄 Background Updater** | Script independiente para actualizar datos en segundo plano |
| **📅 Partidos de Hoy** | Dashboard con predicciones automáticas y horario Argentina (UTC-3) |
| **🔗 Normalización por Liga** | Fuzzy matching de nombres de equipos **filtrado por `league_code`** |
| **📅 Fixtures** | Calendario de próximos partidos con barras de predicción |
| **📊 Doble Oportunidad** | Predicciones 1X, X2, 12 cuando ningún resultado supera el 50% |
| **🚩 Mercados Extras** | Córners (Over 8.5/9.5) y Tarjetas (Over 2.5/3.5/4.5) |
| **⚡ Memoización Granular** | Predicciones individuales cacheadas 1 hora (reduce CPU) |
| **⚡ Flask-Caching** | Caché en RAM con memoize para datos pesados (CSV, fixtures) |
| **🚀 HTMX Boosting** | Navegación instantánea sin recarga de página (SPA-feel) |
| **🔧 Optimizado para RPi** | Carga selectiva de columnas, GC forzado, operaciones vectorizadas |
| **🎭 UI Promiedos** | Interfaz dark inspirada en promiedos.com.ar |

---

## 📊 Ligas Soportadas

| Código | Liga | País | Temporadas | Fuente Fixture |
|--------|------|------|------------|----------------|
| `ARG` | **Liga Profesional** | 🇦🇷 Argentina | 2024-2026 | Promiedos |
| `E0` | Premier League | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 2015-2026 | FixtureDownload |
| `SP1` | La Liga | 🇪🇸 España | 2015-2026 | FixtureDownload |
| `D1` | Bundesliga | 🇩🇪 Alemania | 2015-2026 | FixtureDownload |
| `I1` | Serie A | 🇮🇹 Italia | 2015-2026 | FixtureDownload |
| `F1` | Ligue 1 | 🇫🇷 Francia | 2015-2026 | FixtureDownload |
| `P1` | Primeira Liga | 🇵🇹 Portugal | 2015-2026 | FixtureDownload |
| `N1` | Eredivisie | 🇳🇱 Países Bajos | 2015-2026 | FixtureDownload |

---

## 📁 Estructura del Proyecto

```
timba-predictor/
├── app.py                          # 🌐 Aplicación Flask principal
├── background_updater.py           # 🔄 Script de actualización en segundo plano
├── run_live.py                     # 📺 Servicio de Live Scores independiente
├── requirements.txt                # 📦 Dependencias Python
├── setup.py                        # ⚙️  Compilación de módulo Cython (opcional)
├── test_optimizations.py           # 🧪 Tests de rendimiento
├── .env                            # 🔑 Variables de entorno (no en git)
│
├── data/
│   ├── databases/                  # 💾 TODAS las bases de datos centralizadas
│   │   ├── football_data.db        #    └─ Datos históricos (partidos)
│   │   ├── team_normalizer.db      #    └─ Equipos normalizados + aliases
│   │   └── live_scores.db          #    └─ Caché de scores en vivo
│   └── live_scores_cache/          # 📁 Caché JSON de live scores
│
├── src/
│   ├── timba_core.py               # 🧮 Motor de predicción (Poisson + Promiedos scraper)
│   ├── timba_fast.pyx              # ⚡ Módulo Cython optimizado (opcional)
│   ├── etl_football_data.py        # ⬇️  Pipeline ETL (incluye Argentina)
│   ├── team_normalization.py       # 🔗 Sistema de normalización por liga
│   ├── team_normalization_cli.py   # 🛠️  CLI de mantenimiento
│   ├── db_data_provider.py         # 📊 Proveedor de datos BD
│   ├── live_scores.py              # 📺 Gestor de live scores con polling
│   ├── football_api_client.py      # 🌍 Cliente API Football-Data.org (rate limiting)
│   ├── etl_team_integration.py     # 🔗 Integración ETL + normalización
│   └── utils/
│       ├── __init__.py
│       └── shared.py               # ⚙️  Constantes, rutas, aliases de equipos
│
├── templates/                      # 🎨 Templates Jinja2 (estilo Promiedos)
│   ├── base.html                   #    └─ Layout con sidebar + navbar
│   ├── index.html                  #    └─ Partidos de hoy con predicciones
│   ├── predict.html                #    └─ Predicción detallada
│   ├── fixtures.html               #    └─ Calendario con barras de predicción
│   ├── live.html                   #    └─ Scores en vivo
│   └── results.html                #    └─ Historial de predicciones
│
├── static/
│   └── style.css                   # 🎨 Estilos dark theme (Promiedos-style)
│
├── scripts/
│   └── migrate_legacy_aliases.py   # 🔧 Script de migración de aliases
│
├── docs/
│   └── MIGRATION_GUIDE.md          # 📖 Guía de migración v2.0 → v2.1
│
└── logs/                           # 📝 Archivos de log
```

> 💡 **Nota:** Todas las rutas de bases de datos están centralizadas en `src/utils/shared.py`.

---

## ⚙️ Instalación

### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/1nachu/timba-predicciones.git
cd timba-predicciones
```

### Paso 2: Crear Entorno Virtual

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Clave secreta para Flask (genera una única)
SECRET_KEY=tu_clave_secreta_muy_larga_aqui

# API Key de Football-Data.org (REQUERIDO para live scores)
FOOTBALL_DATA_API_KEY=tu_api_key_aqui
```

> 📝 Obtén tu API Key gratis en [football-data.org/client/register](https://www.football-data.org/client/register)

---

## 🚀 Ejecución

### ⚠️ IMPORTANTE: Orden de Ejecución

La aplicación requiere datos históricos para funcionar. **Debes ejecutar el ETL antes de iniciar la web.**

---

### Paso 1: Ejecutar el ETL (Obligatorio la primera vez)

El ETL tiene **dos modos de ejecución**:

#### 🚀 Modo Rápido (Por defecto) - Solo temporada actual

```bash
python src/etl_football_data.py
```

**Salida esperada:**
```
🚀 Modo RÁPIDO: Solo temporada actual (25/26)
   Usa --historico para descargar todas las temporadas

============================================================
🚀 MODO RÁPIDO (solo temporada actual)
============================================================
[INFO] Descargando E0 (Premier League) - Temporadas: 2526
[INFO] Descargando SP1 (La Liga) - Temporadas: 2526
...
[INFO] ✓ ETL completado: 7 ligas, 1 temporada cada una
```

#### 📚 Modo Histórico - Todas las temporadas (11 por liga)

```bash
python src/etl_football_data.py --historico
```

**Salida esperada:**
```
📚 Modo HISTÓRICO: Descargando TODAS las temporadas (~11 por liga)
   ⏱️ Esto puede tomar varios minutos...

============================================================
📚 MODO HISTÓRICO (todas las temporadas)
============================================================
[INFO] Descargando E0 - Temporadas: 2526, 2425, 2324...
...
[INFO] ✓ ETL completado: 7 ligas, 11 temporadas, ~25,000 partidos
```

---

**Opciones del ETL:**

| Comando | Descripción |
|---------|-------------|
| `python src/etl_football_data.py` | 🚀 **Rápido** - Solo temporada 25/26 |
| `python src/etl_football_data.py --historico` | 📚 Histórico - Todas las temporadas |
| `python src/etl_football_data.py --ligas E0,SP1` | Solo descargar Premier y La Liga |
| `python src/etl_football_data.py --stats-only` | Ver estadísticas sin descargar |
| `python src/etl_football_data.py --historico --ligas D1` | Histórico solo Bundesliga |

---

### Paso 2: Iniciar la Aplicación Web

```bash
python app.py
```

Abre tu navegador en: **http://localhost:5000**

---

## 📺 Live Scores

El sistema incluye un servicio de Live Scores que obtiene resultados en tiempo real desde **Football-Data.org** y los almacena en base de datos local.

### Ejecutar el Servicio de Live Scores

```bash
python run_live.py
```

**Características:**
- Polling automático cada 30 segundos (configurable)
- Almacenamiento en SQLite (`data/databases/live_scores.db`)
- Rate limiting integrado para respetar límites de API
- Callbacks para eventos (goles, inicio, fin de partido)

### Integración con Dashboard

El dashboard `/live` lee directamente de la BD local, evitando límites de API y mejorando rendimiento:

| Fuente | Latencia | Límites |
|--------|----------|---------|
| API directa | ~2s | 10 req/min |
| **BD Local** | **~10ms** | **Ilimitado** |

---

## 🔄 Background Updater

Script independiente para pre-calcular datos del dashboard sin bloquear la aplicación web.

### Ejecución Única

```bash
python background_updater.py
```

### Modo Loop (Actualización Continua)

```bash
python background_updater.py --loop 300  # Cada 5 minutos
```

**Salida:** `data/dashboard_cache.json`

**Uso recomendado:**
- Ejecutar en un **screen** o **tmux** en servidor
- Ideal para Raspberry Pi: reduce carga durante requests HTTP
- La app Flask lee el JSON pre-calculado si existe

---

## 🛠️ Mantenimiento (CLI)

El sistema incluye una herramienta CLI para gestionar la normalización de equipos. 

> 🔑 **Los comandos ahora requieren códigos de liga** para evitar confusiones entre equipos de diferentes países.

### Ver Estado del Sistema

```bash
python -m src.team_normalization_cli stats
```

**Salida:**
```
======================================================================
📊 ESTADÍSTICAS DEL SISTEMA DE NORMALIZACIÓN
======================================================================

📁 Base de datos: data/databases/team_normalizer.db

RESUMEN GENERAL
────────────────────────────────────────
  Total equipos registrados:     162
  Equipos sin liga asignada:       0

EQUIPOS POR LIGA
────────────────────────────────────────
| Código | Liga                        | Equipos |
|--------|-----------------------------+---------|
| E0     | Premier League (Inglaterra) |      34 |
| SP1    | La Liga (España)            |      31 |
| D1     | Bundesliga (Alemania)       |      30 |
| I1     | Serie A (Italia)            |      35 |
| F1     | Ligue 1 (Francia)           |      32 |
```

---

### Probar Normalización de un Nombre

Útil para verificar si un nombre de equipo se resuelve correctamente:

```bash
python -m src.team_normalization_cli normalize "Chelsea FC" --league E0
```

**Salida:**
```
🔍 RESULTADO DE NORMALIZACIÓN
══════════════════════════════════════════════════════════════
  Input:         Chelsea FC
  Liga filtro:   E0 (Premier League)
──────────────────────────────────────────────────────────────

  ✓ MATCH ENCONTRADO

  UUID:          a1b2c3d4-5678-90ab-cdef-1234567890ab
  Nombre Oficial: Chelsea
  Confianza:     95.0% (🟢 Alta)
```

---

### Agregar un Alias (Corregir nombre de la API)

Cuando la API de Live Scores devuelve un nombre que no coincide con los datos históricos:

```bash
python -m src.team_normalization_cli add-alias "Nombre Raro API" "Nombre Oficial CSV"
```

**Ejemplo real:**
```bash
python -m src.team_normalization_cli add-alias "Wolverhampton Wanderers FC" "Wolves"
```

---

### Agregar un Equipo Nuevo

```bash
python -m src.team_normalization_cli add-team "Nuevo Equipo" --league-code E0
```

> El país se infiere automáticamente del código de liga.

---

### Buscar Equipos

```bash
# Buscar por nombre parcial
python -m src.team_normalization_cli search "Madrid"

# Filtrar por liga
python -m src.team_normalization_cli search "United" --league E0
```

---

### Listar Todos los Equipos

```bash
# Todos los equipos
python -m src.team_normalization_cli list-teams

# Solo Premier League
python -m src.team_normalization_cli list-teams --league E0
```

---

### Exportar Datos

```bash
# Exportar a JSON
python -m src.team_normalization_cli export --output equipos.json

# Exportar solo una liga a CSV
python -m src.team_normalization_cli export --league SP1 --format csv --output laliga.csv
```

---

### Resumen de Comandos CLI

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `stats` | Ver estadísticas por liga | `stats` |
| `normalize` | Probar normalización | `normalize "Man Utd" --league E0` |
| `add-alias` | Vincular alias a nombre oficial | `add-alias "Alias" "Nombre Oficial"` |
| `add-team` | Agregar equipo nuevo | `add-team "Equipo" --league-code D1` |
| `search` | Buscar equipos | `search "Arsenal" --league E0` |
| `list-teams` | Listar equipos | `list-teams --league I1` |
| `export` | Exportar a JSON/CSV | `export --output teams.json` |

---

## 🧮 Metodología de Predicción

### Distribución de Poisson

El sistema calcula **Expected Goals (xG)** con la fórmula:

```
λ_local     = Ataque_Local × Defensa_Visitante × Media_Liga_Local
λ_visitante = Ataque_Visitante × Defensa_Local × Media_Liga_Visitante
```

**Ponderación:** 60% últimos 5 partidos + 40% temporada completa.

### Probabilidades Calculadas

| Mercado | Descripción |
|---------|-------------|
| **1X2** | Victoria local, empate, victoria visitante |
| **Over/Under 2.5** | Más o menos de 2.5 goles totales |
| **BTTS** | Ambos equipos anotan |
| **Doble Oportunidad** | 1X, X2, 12 cuando ninguna prob. > 50% |

### Sistema de Predicción IA

El sistema selecciona la predicción más confiable:

1. **Si alguna probabilidad ≥ 50%**: Se recomienda 1, X o 2 directo
2. **Si ninguna ≥ 50%**: Se calcula Doble Oportunidad:
   - **1X** (Local o Empate): P(1) + P(X)
   - **X2** (Empate o Visitante): P(X) + P(2)  
   - **12** (Local o Visitante): P(1) + P(2)

> Las probabilidades siempre suman **exactamente 100%** gracias a la normalización post-Poisson.

---

## 🔧 Tecnologías

| Tecnología | Uso |
|------------|-----|
| **Python 3.10+** | Lenguaje principal |
| **Flask 3.0** | Framework web |
| **Flask-Caching** | Caché en RAM (SimpleCache) para rendimiento óptimo |
| **HTMX 1.9** | Navegación instantánea sin JavaScript complejo |
| **SQLite** | Base de datos (centralizada en `data/databases/`) |
| **SQLAlchemy 2.0** | ORM para operaciones ETL |
| **Pandas 2.0+** | Procesamiento y análisis de datos |
| **NumPy** | Operaciones numéricas vectorizadas |
| **SciPy** | Distribución de Poisson para predicciones |
| **BeautifulSoup4** | Web scraping (Promiedos Argentina) |
| **TheFuzz** | Fuzzy matching para normalización de nombres |
| **python-Levenshtein** | Aceleración de fuzzy matching |
| **Requests** | Cliente HTTP con retry y backoff |
| **Bootstrap 5** | UI/Frontend con tema dark |
| **Cython** | Optimización opcional para Raspberry Pi |

---

## ⚡ Optimizaciones de Rendimiento

### Flask-Caching (Backend)

El sistema utiliza **caché en memoria RAM** para evitar operaciones lentas repetidas:

| Función | Timeout | Descripción |
|---------|---------|-------------|
| `cargar_datos_liga_cached()` | **1 hora** | Descarga CSV y calcula fuerzas de equipos |
| `obtener_fixtures_cached()` | **30 min** | Scraping de próximos partidos |
| Rutas `/`, `/predict`, `/fixtures` | **5 min** | Respuestas HTML cacheadas |
| Ruta `/live` | **15 seg** | Live scores desde DB local |

### HTMX Boosting (Frontend)

Navegación instantánea entre páginas **sin recarga completa**:

```html
<body hx-boost="true" hx-indicator="#page-loader">
```

- **`hx-boost="true"`**: Intercepta clicks en enlaces y carga solo el contenido
- **`hx-indicator`**: Muestra barra de progreso roja mientras carga
- **Resultado**: Navegación ~50ms en lugar de 2-3 segundos

### Rendimiento en Raspberry Pi

| Página | Sin Caché | Con Caché |
|--------|----------|----------|
| Dashboard | ~2-3s | **~50ms** |
| Predicción | ~3-5s | **~50ms** |
| Fixtures | ~4-6s | **~50ms** |
| Live Scores | ~2s (API) | **~10ms** (DB local) |

---

## 🙏 Créditos

- **Datos históricos:** [football-data.co.uk](https://www.football-data.co.uk)
- **Fixtures Argentina:** [promiedos.com.ar](https://www.promiedos.com.ar)
- **API Live Scores:** [football-data.org](https://www.football-data.org)
- **Framework:** [Flask](https://flask.palletsprojects.com)
- **Modelo estadístico:** Distribución de Poisson
- **UI inspirada en:** [promiedos.com.ar](https://www.promiedos.com.ar)

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

<div align="center">
  <br>
  <sub>Hecho con ❤️ y matemáticas por el Timba Team</sub>
  <br><br>
  <img src="https://img.shields.io/badge/Last%20Update-Febrero%202026-blue?style=flat-square" alt="Last Update">
  <img src="https://img.shields.io/badge/Version-2.1-green?style=flat-square" alt="Version">
</div>
