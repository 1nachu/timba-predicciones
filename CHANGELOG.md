# Changelog

Todos los cambios relevantes de **Timba Predictor** se documentan en este archivo.

---

## [2.2.1] - 2026-11-06

### Fixed
- **Normalización CSV de Liga Profesional Argentina (`ARG`)**: `DatabaseDataProvider.get_data_from_csv()` y `calcular_fuerzas()` ahora normalizan siempre las columnas con `normalizar_csv()`, resolviendo el error `KeyError: 'FTHG'` con el formato `Home`/`Away`/`HG`/`AG` de `ARG.csv`.
- **Verificación de tabla `matches` en SQLite**: `DatabaseDataProvider` comprueba la existencia de la tabla `matches` antes de ejecutar consultas SQL y resuelve automáticamente la URL CSV por código de liga cuando hace fallback.
- **Esquema y migración automática de `predictions_audit`**: añadidas las columnas `guardado_at` y `resultado_registrado_at` en `CREATE TABLE` y migración automática con `PRAGMA table_info` + `ALTER TABLE` en `background_updater.py` y `src/services/audit_service.py`.
- **Manejo de torneos inter-liga en `background_updater.py`**: `cargar_fuerzas_liga()` detecta competiciones con `es_torneo: True` (UEFA Champions League) sin lanzar errores de fuente faltante, y reutiliza `cache_fixtures` para no descargar dos veces seguidas los mismos calendarios.
- **Infraestructura Docker y CI**:
  - `Dockerfile` instala paquetes en `/usr/local` (accesible para `timbauser`), compila Cython en la etapa `builder` y limpia el `PATH`.
  - `docker-compose.yml` usa `env_file: .env`, elimina el `SECRET_KEY` hardcodeado y añade el servicio opcional `bot` (`--profile bot`).
  - Añadido `requirements-dev.txt` con `pytest` y `pytest-mock`.

### Removed
- Eliminadas ~600 líneas de clases legacy sin uso y rotas (`APIFootballCache`, `APIFootballClient`, `BatchFetcher`, `PredictionFetcher`, `MLFeatureExtractor`, `TimbaCoreAPI`) en `src/timba_core.py`.
- Eliminada función muerta `registrar_resultados_desde_csv()` en `background_updater.py` y script obsoleto `scripts/benchmark_optimizations.py`.

---

## [2.2.0] - 2026-08-31

### Added
- **Ajuste Dixon-Coles (1997)**: corrección probabilística de correlación $\tau(x, y, \rho)$ para marcadores bajos (`0-0`, `1-0`, `0-1`, `1-1`).
- **Value Betting & Criterio de Kelly**: cálculo de Valor Esperado ($\text{EV}$) y tamaño de apuesta sugerido contra cuotas de mercado.
- **Motor de Backtesting Cuantitativo**: simulación histórica walk-forward (`src/analytics/backtester.py` y CLI `scripts/run_backtest.py`) con métricas de Brier Score, Yield/ROI y Max Drawdown.
- **API REST JSON v1**: endpoints `/api/v1/health`, `/api/v1/leagues`, `/api/v1/predict`, `/api/v1/value-bets`, `/api/v1/fixtures`, `/api/v1/live` y `/api/v1/audit`.
- **Predicciones Dinámicas In-Play**: `predecir_partido_en_vivo()` ajustado por minuto de juego, marcador actual y tarjetas rojas.
- **Bot de Telegram Interactivo (`bot.py`)**: comandos `/start`, `/live`, `/proximos`, `/predecir`, `/inplay`, `/valuebets` y `/ligas`.
- **Sincronización multi-fuente de auditoría**: `sincronizar_resultados_audit()` cruza resultados desde feeds JSON de FixtureDownload y la tabla local `matches`.

### Changed
- **Arquitectura Modular**: desacoplamiento de `app.py` en Flask Blueprints (`src/web/blueprints/`) y capa de servicios (`src/services/`).
- **Configuración Centralizada de Ligas**: unificada en `src/config/leagues.py` para la temporada `2026/2027`.
- **Caché Compartido**: migración de `SimpleCache` a `FileSystemCache` en `data/flask_cache/`.

---

## [2.1.0] - 2026-02-03

### Added
- **Centralización de bases de datos SQLite**: todas las BDs residen en `data/databases/` (`football_data.db`, `team_normalizer.db`, `live_scores.db`, `api_football_cache.db`) con modo `WAL` y `busy_timeout = 5000`.
- **Normalización de equipos filtrada por liga**: `TeamNormalizer` filtra por `league_code` para evitar falsos positivos entre equipos de distintas ligas.
- **Vectorización con Pandas/NumPy**: reducción del cálculo de fuerzas por liga de ~320 ms a ~7.6 ms.
