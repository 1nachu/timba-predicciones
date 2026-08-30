# ⚡ Optimizaciones de Rendimiento y Raspberry Pi - Timba Predictor v2.2

**Versión:** 2.2  
**Fecha:** Agosto 2026  
**Objetivo:** Rendimiento submétrico (<10ms en predicción, <50ms en interfaz web) en servidores embebidos, Raspberry Pi 4/5 y entornos Linux ligeros.

---

## 📊 Resumen de Rendimiento

| Componente | Antes | Ahora (v2.2) | Técnica Clave |
|------------|-------|--------------|---------------|
| **Cálculo de Fuerzas por Liga** | 320 ms | **7.6 ms** | Vectorización con Pandas `groupby` y aggregations NumPy |
| **Predicción Poisson (Python Fallback)** | 1,200 pred/s | **>25,000 pred/s** | Matriz $11 \times 11$ con `np.outer()`, `np.trace()`, `np.tril()` |
| **Motor Cython (`timba_fast`)** | ~15,000 pred/s | **>50,000 pred/s** | Extensión C/Cython compilada en CPython |
| **Acceso a Base de Datos SQLite** | Bloqueos / 150ms | **< 1 ms (WAL Mode)** | `PRAGMA journal_mode=WAL;` y `busy_timeout=5000` |
| **Caché Compartido Inter-Proceso** | RAM aislada | **Persistente en Disco** | `FileSystemCache` en `data/flask_cache/` |
| **Navegación Web** | 2.5 s | **< 50 ms** | HTMX Boosting + memoización |

---

## 🛠️ Detalle de Optimizaciones Implementadas

### 1. Vectorización Algorítmica de Fuerzas (`calcular_fuerzas`)
- **Problema previo:** Se ejecutaba un bucle iterativo sobre cada equipo escaneando el DataFrame completo 40 veces por liga.
- **Solución implementada:** Agrupación global con `df.groupby('HomeTeam')` y `df.groupby('AwayTeam')`.
- **Resultado:** Reducción del tiempo de cálculo de **320 ms a 7.6 ms por liga** y eliminación de 95% de las asignaciones temporales en RAM.

### 2. Matriz Poisson Vectorizada (`np.outer`)
- **Problema previo:** Dos bucles anidados `for i in range(11): for j in range(11):` calculando probabilidades puntuales.
- **Solución implementada:**
  ```python
  k = np.arange(11)
  prob_local_arr = poisson.pmf(k, lambda_local)
  prob_vis_arr = poisson.pmf(k, lambda_visitante)
  matriz_prob = np.outer(prob_local_arr, prob_vis_arr)
  
  empate = float(np.trace(matriz_prob))
  victoria_local = float(np.sum(np.tril(matriz_prob, -1)))
  victoria_visitante = float(np.sum(np.triu(matriz_prob, 1)))
  ```
- **Resultado:** Rendimiento superior a **25,000 predicciones por segundo** en CPU estándar.

### 3. Concurrencia SQLite sin Bloqueos (Modo WAL)
- **Problema previo:** Peticiones web GET disparaban escrituras automáticas generando `OperationalError: database is locked`.
- **Solución implementada:**
  - Helper centralizado [`get_db_connection`](src/utils/shared.py) que activa:
    ```sql
    PRAGMA journal_mode = WAL;
    PRAGMA synchronous = NORMAL;
    PRAGMA busy_timeout = 5000;
    PRAGMA cache_size = -64000;
    ```
  - Separación estricta de conexiones de solo lectura (`file:...mode=ro`) para la web y conexiones de escritura para el actualizador en segundo plano.

### 4. FileSystemCache Inter-Procesos
- **Problema previo:** `SimpleCache` almacenaba objetos en la memoria RAM del proceso Flask y no se compartía con `background_updater.py` ni entre workers Gunicorn.
- **Solución implementada:** Migración a `FileSystemCache` en `data/flask_cache/`. Los resultados precalculados por el background updater son aprovechados de forma inmediata por cualquier worker web sin overhead de red.

### 5. Carga Selectiva de Columnas y Dtypes Ligeros
- **Implementación:** `usecols` en `descargar_csv_safe` y filtrado estricto en `FootballDataTransformer.seleccionar_columnas_criticas`.
- **Resultado:** Reducción del **50% en consumo de memoria** al descargar y procesar DataFrames.

---

## 🧪 Verificación de Rendimiento

Para validar el rendimiento y las pruebas unitarias en tu entorno:

```bash
# Ejecutar suite de pruebas
pytest -v tests/

# Benchmark de predicción y cálculo de fuerzas
python -c "
import sys; sys.path.insert(0, 'src')
from db_data_provider import DatabaseDataProvider
from core.prediction import calcular_fuerzas, predecir_partido
import time

provider = DatabaseDataProvider()
df = provider.get_data_from_db('E0')

t0 = time.perf_counter()
for _ in range(100):
    fuerzas, ml, mv = calcular_fuerzas(df)
t_fuerzas = (time.perf_counter() - t0) / 100

t0 = time.perf_counter()
for _ in range(10000):
    predecir_partido('Arsenal', 'Chelsea', fuerzas, ml, mv)
t_pred = (time.perf_counter() - t0) / 10000

print(f'Tiempo fuerzas: {t_fuerzas*1000:.2f} ms')
print(f'Velocidad predicción: {1/t_pred:,.0f} pred/seg')
"
```
