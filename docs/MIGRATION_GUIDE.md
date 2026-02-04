# Guía de Migración - Timba Predictor v2.1

> **Última actualización:** 3 de Febrero 2026

## Resumen de Cambios

Esta versión incluye dos mejoras arquitectónicas importantes:

1. **Centralización de rutas de BD** - Todos los archivos `.db` ahora deben estar en `data/databases/`
2. **Normalización filtrada por liga** - El TeamNormalizer ahora soporta filtrado por `league_code` para evitar cross-league pollution

---

## 1. Migración de Bases de Datos

### Problema Anterior
Los archivos `.db` estaban dispersos en la raíz del proyecto y otras carpetas.

### Solución
Todas las BDs ahora deben estar en `data/databases/`:

```
data/
└── databases/
    ├── football_data.db      # Datos históricos ETL
    ├── team_normalizer.db    # BD de normalización
    ├── api_football_cache.db # Cache de API
    └── live_scores.db        # Scores en vivo
```

### Pasos de Migración

```bash
# 1. Crear directorio destino
mkdir -p data/databases

# 2. Mover archivo de datos principales (si existe en la raíz)
mv football_data.db data/databases/

# 3. Verificar que no hay otros .db dispersos
find . -name "*.db" -not -path "./data/databases/*" -not -path "./.venv/*"

# 4. Eliminar archivos antiguos (OPCIONAL - solo si confirmaste backup)
# rm -f ./football_data.db
```

### Verificación

```python
from src.utils.shared import DB_PATH, TEAM_NORMALIZER_DB_PATH, LIVE_SCORES_DB_PATH

print(f"DB_PATH: {DB_PATH}")
# Output esperado: /home/.../proyecto timba ver 2/data/databases/football_data.db
```

---

## 2. Actualización del Esquema de TeamNormalizer

### Problema Anterior
El TeamNormalizer buscaba equipos en toda la BD sin filtrar por liga, causando falsos positivos (ej: Paris FC vs PSG, clubes de Argentina vs Francia).

### Solución
Se añadió columna `league_code` a la tabla `master_teams` y filtrado en `normalize_team()`.

### Migración Automática
El sistema aplica la migración automáticamente al inicializar:

```python
# El TeamNormalizer ejecuta esto automáticamente:
ALTER TABLE master_teams ADD COLUMN league_code TEXT
```

### Re-poblar la BD con league_code

Para asociar equipos existentes con su liga, **re-ejecutar el ETL**:

```bash
# Opción 1: Regenerar TODO (recomendado si la BD es corrupta)
python -m src.etl_football_data --ligas E0,SP1,D1,I1,F1

# Opción 2: Solo actualizar normalización (manual)
python -c "
from src.team_normalization import TeamNormalizer
from src.etl_football_data import LIGAS_CONFIG

normalizer = TeamNormalizer()

# Mapeo de países
COUNTRIES = {
    'E0': 'England',
    'SP1': 'Spain',
    'D1': 'Germany',
    'I1': 'Italy',
    'F1': 'France',
}

# Actualizar equipos existentes con league_code
import sqlite3
conn = sqlite3.connect(str(normalizer.db_path))
cursor = conn.cursor()

# Por ejemplo, asociar equipos ingleses con E0
cursor.execute('''
    UPDATE master_teams 
    SET league_code = 'E0' 
    WHERE country = 'England' AND league_code IS NULL
''')
cursor.execute('''
    UPDATE master_teams 
    SET league_code = 'SP1' 
    WHERE country = 'Spain' AND league_code IS NULL
''')
# ... repetir para cada liga

conn.commit()
conn.close()
print('Actualización completada')
"
```

---

## 3. Uso del Nuevo API

### Antes (sin filtro de liga)
```python
normalizer.normalize_team("Paris FC")
# Podía matchear con PSG (Paris Saint-Germain) erróneamente
```

### Después (con filtro de liga)
```python
# Filtrado por liga - evita cross-league pollution
normalizer.normalize_team("Paris FC", league_id="F1")
# Solo busca en equipos de Ligue 1

normalizer.normalize_team("Paris Saint-Germain", league_id="F1")
# Busca específicamente en Ligue 1
```

### En app.py (live predictions)
```python
# El código ya está actualizado para pasar league_code:
league_code = API_TO_LEAGUE_CODE.get(api_code)  # 'E0', 'SP1', etc.
local_normalizado, metodo, conf = _normalizar_nombre_equipo(
    nombre_local, 
    equipos_validos, 
    league_id=league_code  # NUEVO
)
```

---

## 4. Nuevas Constantes en shared.py

```python
from src.utils.shared import (
    # Rutas de directorios
    PROJECT_ROOT,
    DATA_DIR,
    DATABASES_DIR,  # data/databases/
    CACHE_DIR,      # data/live_scores_cache/
    LOGS_DIR,
    
    # Rutas de archivos de BD (Path objects)
    DB_PATH,
    API_CACHE_DB_PATH,
    TEAM_NORMALIZER_DB_PATH,
    LIVE_SCORES_DB_PATH,  # NUEVO
    
    # Rutas como strings (para módulos que no aceptan Path)
    DB_PATH_STR,
    TEAM_NORMALIZER_DB_PATH_STR,
    LIVE_SCORES_DB_PATH_STR,  # NUEVO
    
    # Conexión
    SQLITE_CONNECTION_STRING,
)
```

---

## 5. Verificación Post-Migración

```bash
# 1. Verificar que app.py arranca sin errores
python app.py

# 2. Verificar estadísticas del normalizador
python -c "
from src.team_normalization import TeamNormalizer
n = TeamNormalizer()
stats = n.get_stats()
print(f'Equipos: {stats[\"total_teams\"]}')
print(f'Aliases: {stats[\"total_aliases\"]}')

# Ver equipos por liga
for league in ['E0', 'SP1', 'D1', 'I1', 'F1']:
    teams = n.get_all_teams(league_code=league)
    print(f'{league}: {len(teams)} equipos')
"

# 3. Probar normalización filtrada
python -c "
from src.team_normalization import TeamNormalizer
n = TeamNormalizer()

# Debería encontrar en Premier League
result = n.normalize_team('Manchester United', league_id='E0')
print(f'Man Utd (E0): {result}')

# Debería encontrar en La Liga
result = n.normalize_team('Real Madrid', league_id='SP1')
print(f'Real Madrid (SP1): {result}')
"
```

---

## 6. Troubleshooting

### "No mapping found for team X"
El equipo no existe en la BD para esa liga. Ejecutar:
```bash
python -m src.team_normalization_cli add-team "Nombre Equipo" --country England --league-code E0
```

### "TEAM_NORMALIZER not available"
Verificar que `thefuzz` está instalado:
```bash
pip install thefuzz python-Levenshtein
```

### Base de datos antigua en raíz
Mover manualmente y re-ejecutar ETL:
```bash
mv football_data.db data/databases/
python -m src.etl_football_data
```

---

## Changelog v2.1

- ✅ `src/utils/shared.py`: Añadidas constantes `LIVE_SCORES_DB_PATH`, `*_STR` variants
- ✅ `src/team_normalization.py`: Columna `league_code`, método `normalize_team(league_id=)`
- ✅ `src/app.py`: Pasar `league_id` al normalizador en `/live`
- ✅ `src/etl_football_data.py`: Registrar equipos con `league_code` durante ETL
- ✅ `src/live_scores.py`: Usar rutas centralizadas
- ✅ `src/db_data_provider.py`: Usar rutas centralizadas
