"""
ETL SCRIPT - Football Historical Data Pipeline
===============================================

Extrae datos históricos de Football-Data.co.uk, transforma y carga en base de datos.

Características:
- Descarga 11 temporadas de 7 ligas europeas + Liga Argentina
- Normaliza fechas a ISO 8601
- Mantiene columnas críticas: FTR, HS/AS, HST/AST, cuotas B365
- Soporta SQLite y PostgreSQL
- Manejo robusto de errores con retry
- Logging detallado

Autor: Timba Team
Última actualización: Febrero 2026
"""

# ========== IMPORTS ESTÁNDAR ==========
import sys
import logging
import io
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Literal

# Agregar directorio src al path para imports locales
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ========== IMPORTS DE TERCEROS ==========
import numpy as np
import pandas as pd
import requests

try:
    import sqlalchemy
except ImportError:
    sqlalchemy = None

# ========== IMPORTS LOCALES ==========
try:
    from utils.shared import (
        FOOTBALL_DATA_BASE_URL,
        DB_PATH,
        LOGS_DIR,
        SQLITE_CONNECTION_STRING,
        TEAM_NORMALIZER_DB_PATH_STR,
    )
except ImportError:
    # Fallback si se ejecuta directamente
    FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk"
    DB_PATH = Path("data/databases/football_data.db")
    LOGS_DIR = Path("logs")
    SQLITE_CONNECTION_STRING = f"sqlite:///{DB_PATH}"
    TEAM_NORMALIZER_DB_PATH_STR = "data/databases/team_normalizer.db"

# Intentar importar TeamNormalizer para registrar equipos
try:
    from team_normalization import TeamNormalizer
    TEAM_NORMALIZER_AVAILABLE = True
except ImportError:
    TEAM_NORMALIZER_AVAILABLE = False
    TeamNormalizer = None

# ========== CONFIGURACIÓN DE LOGGING ==========
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'etl_football_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ========== CONFIGURACIÓN DE LIGAS Y TEMPORADAS ==========
# 7 ligas europeas + Argentina con datos de football-data.co.uk

LIGAS_CONFIG = {
    'E0': {
        'nombre': 'Premier League',
        'pais': 'Inglaterra',
        'codigo': 'E0',
        'temporadas': ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'SP1': {
        'nombre': 'La Liga',
        'pais': 'España',
        'codigo': 'SP1',
        'temporadas': ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'D1': {
        'nombre': 'Bundesliga',
        'pais': 'Alemania',
        'codigo': 'D1',
        'temporadas': ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'I1': {
        'nombre': 'Serie A',
        'pais': 'Italia',
        'codigo': 'I1',
        'temporadas': ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'F1': {
        'nombre': 'Ligue 1',
        'pais': 'Francia',
        'codigo': 'F1',
        'temporadas': ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'P1': {
        'nombre': 'Primeira Liga',
        'pais': 'Portugal',
        'codigo': 'P1',
        'temporadas': ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'N1': {
        'nombre': 'Eredivisie',
        'pais': 'Netherlands',
        'codigo': 'N1',
        'temporadas': ['2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    # ========== LIGAS EXTRA (URL directa, no usan patrón mmz4281) ==========
    'ARG': {
        'nombre': 'Liga Profesional',
        'pais': 'Argentina',
        'codigo': 'ARG',
        'temporadas': ['2025'],  # Temporada actual
        'url_directa': 'https://www.football-data.co.uk/new/ARG.csv',  # URL fija
        'es_extra': True
    },
}

# Columnas críticas a mantener después de la transformación
COLUMNAS_CRITICAS = [
    'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',  # Fecha, equipos, goles, resultado
    'HS', 'AS', 'HST', 'AST',                               # Tiros y tiros al arco
    'HC', 'AC',                                             # Corners (Home/Away)
    'B365H', 'B365D', 'B365A',                             # Cuotas Bet365
    'HF', 'AF', 'HR', 'AR'                                 # Faltas y tarjetas rojas
]

# Columnas de tarjetas (varían según temporada)
COLUMNAS_TARJETAS = ['HY', 'AY', 'HR', 'AR']


class FootballDataExtractor:
    """
    Clase responsable de extraer datos desde Football-Data.co.uk
    """
    
    def __init__(self, timeout: int = 30, retry_attempts: int = 3):
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Timba Predictor ETL/1.0)'
        })
    
    def descargar_csv(self, liga_codigo: str, temporada: str) -> Optional[pd.DataFrame]:
        """
        Descarga archivo CSV de una liga y temporada específica.
        
        Args:
            liga_codigo: Código de liga (E0, SP1, D1, ARG, etc)
            temporada: Formato AABB (ej: 2425 para 2024-25) o 'YYYY' para ligas extra
        
        Returns:
            DataFrame con los datos o None si hay error
        """
        liga_info = LIGAS_CONFIG.get(liga_codigo, {})
        
        # Determinar URL según tipo de liga
        if liga_info.get('url_directa'):
            # Liga extra: usar URL directa (ej: Argentina)
            url = liga_info['url_directa']
            logger.info(f"Descargando (URL directa): {liga_info['nombre']}")
        else:
            # Liga estándar: construir URL con temporada
            url = f"{FOOTBALL_DATA_BASE_URL}/mmz4281/{temporada}/{liga_codigo}.csv"
            logger.info(f"Descargando: {liga_info.get('nombre', liga_codigo)} ({temporada})")
        
        for intento in range(self.retry_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                df = pd.read_csv(io.StringIO(response.text))
                logger.info(f"✓ Descargados {len(df)} registros de {liga_codigo}/{temporada}")
                return df
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en intento {intento + 1}/{self.retry_attempts} - {liga_codigo}/{temporada}")
                time.sleep(2 ** intento)  # Backoff exponencial
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    logger.warning(f"✗ Archivo no encontrado: {liga_codigo}/{temporada}")
                    return None
                logger.error(f"Error HTTP {response.status_code}: {liga_codigo}/{temporada}")
                return None
                
            except Exception as e:
                logger.error(f"Error descargando {liga_codigo}/{temporada}: {str(e)}")
                time.sleep(2)
        
        return None
    
    def descargar_multiples_ligas(self, liga_codigos: Optional[List[str]] = None, solo_actual: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Descarga datos de múltiples ligas y temporadas.
        
        Args:
            liga_codigos: Lista de códigos de liga a descargar
            solo_actual: Si True, descarga SOLO la temporada actual (primera de la lista).
                         Si False, descarga TODAS las temporadas (modo histórico).
        
        Returns:
            Diccionario con DataFrames por liga
        """
        if liga_codigos is None:
            liga_codigos = list(LIGAS_CONFIG.keys())
        
        # Determinar modo de ejecución
        modo = "🚀 MODO RÁPIDO (solo temporada actual)" if solo_actual else "📚 MODO HISTÓRICO (todas las temporadas)"
        logger.info(f"\n{'='*60}")
        logger.info(modo)
        logger.info(f"{'='*60}\n")
        
        resultados = {}
        
        for liga_codigo in liga_codigos:
            if liga_codigo not in LIGAS_CONFIG:
                logger.warning(f"Código de liga desconocido: {liga_codigo}")
                continue
            
            liga_info = LIGAS_CONFIG[liga_codigo]
            logger.info(f"\n{'='*60}")
            logger.info(f"Procesando: {liga_info['nombre']} ({liga_info['pais']})")
            logger.info(f"{'='*60}")
            
            dfs_liga = []
            
            # Para ligas con URL directa (ej: Argentina), solo descargar una vez
            if liga_info.get('url_directa'):
                logger.info(f"  📅 Liga extra con URL directa (CSV multi-temporada)")
                df = self.descargar_csv(liga_codigo, 'all')
                if df is not None:
                    df = df.copy()
                    if 'Season' in df.columns:
                        df['Temporada'] = df['Season'].astype(str)
                    elif 'Temporada' in df.columns:
                        df['Temporada'] = df['Temporada'].astype(str)
                    else:
                        df['Temporada'] = str(liga_info['temporadas'][0])
                    
                    if solo_actual and 'Temporada' in df.columns:
                        temporadas_disp = sorted(df['Temporada'].unique())
                        temporadas_filtro = temporadas_disp[-2:] if len(temporadas_disp) >= 2 else temporadas_disp
                        logger.info(f"  📅 Modo rápido: seleccionando temporadas recientes {temporadas_filtro}")
                        df = df[df['Temporada'].isin(temporadas_filtro)].copy()
                    
                    df['league_code'] = liga_codigo
                    dfs_liga.append(df)
            else:
                # Seleccionar temporadas según modo (ligas estándar)
                if solo_actual:
                    temporadas = [liga_info['temporadas'][0]]  # Solo la primera (más reciente)
                else:
                    temporadas = liga_info['temporadas']  # Todas
                
                logger.info(f"  📅 Temporadas a descargar: {', '.join(temporadas)}")
                
                for temporada in temporadas:
                    df = self.descargar_csv(liga_codigo, temporada)
                    if df is not None:
                        df = df.copy()  # Consolidar memoria para evitar PerformanceWarning
                        df['Temporada'] = temporada
                        df['league_code'] = liga_codigo
                        dfs_liga.append(df)
                    time.sleep(1)  # Respetar rate limits
            
            if dfs_liga:
                resultados[liga_codigo] = pd.concat(dfs_liga, ignore_index=True)
                logger.info(f"✓ Total: {len(resultados[liga_codigo])} registros para {liga_info['nombre']}")
            else:
                logger.warning(f"✗ No se descargó data para {liga_info['nombre']}")
        
        return resultados


class FootballDataTransformer:
    """
    Clase responsable de transformar y normalizar datos
    """
    
    @staticmethod
    def normalizar_nombres_columnas(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nombres de columnas para ligas con formato diferente.
        Principalmente para ligas extra (Argentina, Brasil, etc.) que usan
        formato diferente al europeo estándar.
        
        Mapeo de columnas:
        - Home → HomeTeam
        - Away → AwayTeam
        - HG → FTHG (Home Goals)
        - AG → FTAG (Away Goals)
        - Res → FTR (Full Time Result)
        - Season → Temporada
        - B365CH/B365CD/B365CA → B365H/B365D/B365A (Closing odds → standard)
        """
        df = df.copy()
        
        # Mapeo de columnas: formato_extra → formato_estandar
        mapeo_columnas = {
            'Home': 'HomeTeam',
            'Away': 'AwayTeam',
            'HG': 'FTHG',
            'AG': 'FTAG',
            'Res': 'FTR',
            'Season': 'Temporada',
            # Odds de cierre → Odds estándar
            'B365CH': 'B365H',
            'B365CD': 'B365D',
            'B365CA': 'B365A',
            # Pinnacle closing odds
            'PSCH': 'PSH',
            'PSCD': 'PSD',
            'PSCA': 'PSA',
            # Max closing odds
            'MaxCH': 'MaxH',
            'MaxCD': 'MaxD',
            'MaxCA': 'MaxA',
            # Average closing odds
            'AvgCH': 'AvgH',
            'AvgCD': 'AvgD',
            'AvgCA': 'AvgA',
        }
        
        # Aplicar renombrado solo para columnas que existen
        columnas_renombradas = {}
        for col_vieja, col_nueva in mapeo_columnas.items():
            if col_vieja in df.columns and col_nueva not in df.columns:
                columnas_renombradas[col_vieja] = col_nueva
        
        if columnas_renombradas:
            df = df.rename(columns=columnas_renombradas)
            logger.info(f"✓ Columnas normalizadas: {list(columnas_renombradas.keys())} → {list(columnas_renombradas.values())}")
        
        return df
    
    @staticmethod
    def normalizar_fechas(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza columna de fechas a formato ISO 8601.
        
        Soporta múltiples formatos de entrada:
        - DD/MM/YYYY
        - YYYY-MM-DD
        - DD-MM-YYYY
        """
        df = df.copy()
        
        try:
            # Intentar detectar automáticamente el formato
            date_series = pd.to_datetime(df['Date'], format='mixed', dayfirst=True)
            df['Date'] = date_series.dt.strftime('%Y-%m-%d')
            logger.info(f"✓ Fechas normalizadas a ISO 8601")
        except Exception as e:
            logger.error(f"Error normalizando fechas: {str(e)}")
            raise
        
        return df
    
    @staticmethod
    def seleccionar_columnas_criticas(df: pd.DataFrame) -> pd.DataFrame:
        """
        Selecciona solo las columnas críticas para predicción.
        Maneja variaciones según temporada.
        """
        df = df.copy()
        
        # Columnas que definitivamente existen
        columnas_base = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
                         'HS', 'AS', 'HST', 'AST']
        
        # Columnas opcionales (dependen de la temporada)
        columnas_opcionales = ['B365H', 'B365D', 'B365A', 'HF', 'AF', 'HR', 'AR', 'HY', 'AY']
        
        # Construir lista de columnas disponibles
        columnas_disponibles = []
        
        for col in columnas_base:
            if col in df.columns:
                columnas_disponibles.append(col)
            else:
                logger.warning(f"Columna base no encontrada: {col}")
        
        for col in columnas_opcionales:
            if col in df.columns:
                columnas_disponibles.append(col)
        
        # Agregar columna de temporada y league_code si existen
        if 'Temporada' in df.columns:
            columnas_disponibles.append('Temporada')
        if 'league_code' in df.columns:
            columnas_disponibles.append('league_code')
        elif 'League_Code' in df.columns:
            columnas_disponibles.append('League_Code')
        
        df_subset = df[columnas_disponibles].copy()
        logger.info(f"✓ Seleccionadas {len(columnas_disponibles)} columnas críticas")
        
        return df_subset
    
    @staticmethod
    def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia y valida los datos.
        - Elimina duplicados
        - Rellena valores faltantes apropiadamente
        - Valida tipos de datos
        """
        df = df.copy()
        
        registros_antes = len(df)
        
        # Eliminar duplicados basados en fecha, equipos, resultado y liga
        dup_subset = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
        if 'league_code' in df.columns:
            dup_subset.append('league_code')
            
        df_sin_dup = df.drop_duplicates(
            subset=dup_subset,
            keep='first'
        )
        
        duplicados_removidos = registros_antes - len(df_sin_dup)
        if duplicados_removidos > 0:
            logger.info(f"✓ Removidos {duplicados_removidos} registros duplicados")
        
        # Validar que FTR sea válido (H, D, A, 1, X, 2)
        valid_ftr = ['H', 'D', 'A', '1', 'X', '2', 1, 2, 'h', 'd', 'a']
        ftr_mapping = {'1': 'H', 1: 'H', 'X': 'D', '2': 'A', 2: 'A', 'h': 'H', 'd': 'D', 'a': 'A'}
        df_validado = df_sin_dup[df_sin_dup['FTR'].isin(valid_ftr)].copy()
        df_validado['FTR'] = df_validado['FTR'].replace(ftr_mapping)
        removidos = len(df_sin_dup) - len(df_validado)
        if removidos > 0:
            logger.info(f"✓ Removidos {removidos} registros sin resultado final o FTR inválido")
        
        # Asegurar tipos de datos correctos
        columnas_numericas = ['FTHG', 'FTAG', 'HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HR', 'AR', 'HY', 'AY']
        for col in columnas_numericas:
            if col in df_validado.columns:
                df_validado[col] = pd.to_numeric(df_validado[col], errors='coerce')
        
        # Cuotas
        columnas_cuotas = ['B365H', 'B365D', 'B365A']
        for col in columnas_cuotas:
            if col in df_validado.columns:
                df_validado[col] = pd.to_numeric(df_validado[col], errors='coerce')
        
        logger.info(f"✓ Validación completada: {len(df_validado)} registros finales")
        
        return df_validado
    
    @staticmethod
    def enriquecer_datos(df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriquece los datos con columnas derivadas útiles para predicción.
        """
        df = df.copy()
        
        # Total de goles
        df['Total_Goles'] = df['FTHG'] + df['FTAG']
        
        # Over/Under 2.5
        df['Over_25'] = (df['Total_Goles'] > 2.5).astype(int)
        
        # Diferencia de tiros
        if 'HS' in df.columns and 'AS' in df.columns:
            df['Diff_Tiros'] = df['HS'] - df['AS']
        
        # Efectividad de tiros (si hay datos disponibles)
        if 'HS' in df.columns and 'HST' in df.columns:
            df['HST'] = pd.to_numeric(df['HST'], errors='coerce')
            df['HS'] = pd.to_numeric(df['HS'], errors='coerce')
            df['Efectividad_Local'] = (df['HST'] / df['HS']).replace([np.inf, -np.inf], np.nan)
        
        logger.info(f"✓ Datos enriquecidos con columnas derivadas")
        
        return df
    
    @classmethod
    def transformar(cls, df_raw: pd.DataFrame, liga_codigo: Optional[str] = None) -> pd.DataFrame:
        """
        Pipeline completo de transformación.
        """
        logger.info(f"Iniciando transformación...")
        
        # Paso 0: Normalizar nombres de columnas (para ligas extra como ARG)
        df = cls.normalizar_nombres_columnas(df_raw)
        
        # Paso 1: Normalizar fechas
        df = cls.normalizar_fechas(df)
        
        # Paso 2: Seleccionar columnas críticas
        df = cls.seleccionar_columnas_criticas(df)
        
        # Paso 3: Limpiar datos
        df = cls.limpiar_datos(df)
        
        # Paso 4: Enriquecer datos
        df = cls.enriquecer_datos(df)
        
        # Paso 5: Ordenar por fecha
        df = df.sort_values('Date').reset_index(drop=True)
        
        logger.info(f"✓ Transformación completada")
        
        return df


class FootballDataLoader:
    """
    Clase responsable de cargar datos en base de datos.
    Soporta SQLite y PostgreSQL.
    """
    
    def __init__(self, db_type: str = 'sqlite', connection_string: Optional[str] = None):
        """
        Inicializa el loader.
        
        Args:
            db_type: 'sqlite' o 'postgresql'
            connection_string: String de conexión (opcional para SQLite)
        """
        self.db_type = db_type.lower()
        
        if self.db_type == 'sqlite':
            # Usar constante centralizada de shared.py
            self.connection_string = connection_string or SQLITE_CONNECTION_STRING
            self.engine = self._crear_engine_sqlite()
        elif self.db_type == 'postgresql':
            if not connection_string:
                raise ValueError("Se requiere connection_string para PostgreSQL")
            self.connection_string = connection_string
            self.engine = self._crear_engine_postgresql()
        else:
            raise ValueError(f"Tipo de BD no soportado: {db_type}")
        
        logger.info(f"✓ Motor de BD inicializado: {self.db_type}")
    
    def _crear_engine_sqlite(self):
        """Crea engine de SQLite"""
        try:
            if sqlalchemy is None:
                raise ImportError("sqlalchemy no está instalado")
            return sqlalchemy.create_engine(self.connection_string)
        except Exception as e:
            logger.error(f"Error creando engine SQLite: {str(e)}")
            raise
    
    def _crear_engine_postgresql(self):
        """Crea engine de PostgreSQL"""
        try:
            if sqlalchemy is None:
                raise ImportError("sqlalchemy no está instalado")
            return sqlalchemy.create_engine(self.connection_string)
        except Exception as e:
            logger.error(f"Error creando engine PostgreSQL: {str(e)}")
            raise
    
    def crear_tablas(self):
        """
        Crea las tablas necesarias si no existen.
        """
        logger.info("Creando esquema de base de datos...")
        
        try:
            with self.engine.connect() as conn:
                # Tabla principal de partidos
                crear_tabla_sql = f"""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    league_code VARCHAR(10) NOT NULL,
                    date DATE NOT NULL,
                    home_team VARCHAR(100) NOT NULL,
                    away_team VARCHAR(100) NOT NULL,
                    fthg INTEGER,
                    ftag INTEGER,
                    ftr VARCHAR(1),
                    hs INTEGER,
                    as_shots INTEGER,
                    hst INTEGER,
                    ast INTEGER,
                    hc INTEGER,
                    ac INTEGER,
                    hf INTEGER,
                    af INTEGER,
                    hr INTEGER,
                    ar INTEGER,
                    hy INTEGER,
                    ay INTEGER,
                    b365h DECIMAL(5,2),
                    b365d DECIMAL(5,2),
                    b365a DECIMAL(5,2),
                    total_goles INTEGER,
                    over_25 INTEGER,
                    diff_tiros INTEGER,
                    efectividad_local DECIMAL(5,2),
                    temporada VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, home_team, away_team, league_code)
                );
                """
                
                if self.db_type == 'sqlite':
                    from sqlalchemy import text
                    conn.execute(text("DROP TABLE IF EXISTS matches"))  # Para limpieza
                    conn.execute(text(crear_tabla_sql))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_date ON matches(date)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_teams ON matches(home_team, away_team)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_temporada ON matches(temporada)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_league_temporada ON matches(league_code, temporada)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_league_teams ON matches(league_code, home_team, away_team)"))
                
                conn.commit()
                logger.info("✓ Tablas creadas exitosamente")
                
        except Exception as e:
            logger.error(f"Error creando tablas: {str(e)}")
            raise
    
    def cargar_datos(self, df: pd.DataFrame, tabla: str = 'matches', 
                    if_exists: Literal['fail', 'replace', 'append'] = 'append', chunksize: int = 1000):
        """
        Carga DataFrame a la base de datos de forma masiva.
        
        Args:
            df: DataFrame a cargar
            tabla: Nombre de la tabla destino
            if_exists: 'fail', 'replace', 'append'
            chunksize: Tamaño de chunks para inserción
        """
        logger.info(f"Cargando {len(df)} registros en tabla '{tabla}'...")
        
        try:
            # Normalizar nombres de columnas
            df_normalizado = self._normalizar_columnas_bd(df)
            
            # Cargar en chunks
            registros_insertados = 0
            for i in range(0, len(df_normalizado), chunksize):
                chunk = df_normalizado.iloc[i:i+chunksize]
                chunk.to_sql(tabla, self.engine, if_exists=if_exists, 
                            index=False, method='multi')
                registros_insertados += len(chunk)
                if (i // chunksize + 1) % 10 == 0:
                    logger.info(f"  Progreso: {registros_insertados}/{len(df_normalizado)} registros")
            
            logger.info(f"✓ Cargados {registros_insertados} registros exitosamente")
            
        except Exception as e:
            logger.error(f"Error cargando datos: {str(e)}")
            raise
    
    def _normalizar_columnas_bd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nombres de columnas para la base de datos (snake_case).
        """
        df = df.copy()
        
        mapeo = {
            'Date': 'date',
            'HomeTeam': 'home_team',
            'AwayTeam': 'away_team',
            'FTHG': 'fthg',
            'FTAG': 'ftag',
            'FTR': 'ftr',
            'HS': 'hs',
            'AS': 'as_shots',
            'HST': 'hst',
            'AST': 'ast',
            'HC': 'hc',
            'AC': 'ac',
            'HF': 'hf',
            'AF': 'af',
            'HR': 'hr',
            'AR': 'ar',
            'HY': 'hy',
            'AY': 'ay',
            'B365H': 'b365h',
            'B365D': 'b365d',
            'B365A': 'b365a',
            'Total_Goles': 'total_goles',
            'Over_25': 'over_25',
            'Diff_Tiros': 'diff_tiros',
            'Efectividad_Local': 'efectividad_local',
            'Temporada': 'temporada',
            'league_code': 'league_code',
            'League_Code': 'league_code'
        }
        
        df = df.rename(columns=mapeo)
        return df
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas del dataset cargado.
        """
        try:
            with self.engine.connect() as conn:
                # Total de registros
                total = pd.read_sql(
                    "SELECT COUNT(*) as total FROM matches",
                    conn
                )
                
                # Registros por liga
                por_liga = pd.read_sql(
                    "SELECT league_code, COUNT(*) as registros FROM matches GROUP BY league_code ORDER BY registros DESC",
                    conn
                )

                # Registros por temporada
                por_temporada = pd.read_sql(
                    "SELECT temporada, COUNT(*) as registros FROM matches GROUP BY temporada ORDER BY temporada DESC",
                    conn
                )
                
                # Rango de fechas
                fechas = pd.read_sql(
                    "SELECT MIN(date) as fecha_inicio, MAX(date) as fecha_fin FROM matches",
                    conn
                )
                
                # Equipos únicos
                equipos = pd.read_sql(
                    "SELECT COUNT(DISTINCT home_team) as total_equipos FROM matches",
                    conn
                )
                
                stats = {
                    'total_registros': total['total'].values[0],
                    'ligas': por_liga.to_dict(orient='list'),
                    'temporadas': por_temporada.to_dict(orient='list'),
                    'fecha_inicio': fechas['fecha_inicio'].values[0],
                    'fecha_fin': fechas['fecha_fin'].values[0],
                    'total_equipos': equipos['total_equipos'].values[0]
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {}


class FootballETLPipeline:
    """
    Orquestador principal del pipeline ETL.
    Coordina extracción, transformación y carga.
    """
    
    def __init__(self, db_type: str = 'sqlite', connection_string: Optional[str] = None):
        self.extractor = FootballDataExtractor()
        self.transformer = FootballDataTransformer()
        self.loader = FootballDataLoader(db_type, connection_string)
    
    def ejecutar(self, ligas: Optional[List[str]] = None, crear_tablas: bool = True, solo_actual: bool = True):
        """
        Ejecuta el pipeline completo.
        
        Args:
            ligas: Lista de códigos de liga a procesar
            crear_tablas: Si debe crear tablas en BD
            solo_actual: Si True, descarga solo temporada actual (rápido).
                         Si False, descarga historial completo.
        """
        try:
            logger.info("\n" + "="*70)
            logger.info("INICIANDO PIPELINE ETL - FOOTBALL DATA")
            logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*70 + "\n")
            
            # Paso 1: Crear tablas
            if crear_tablas:
                self.loader.crear_tablas()
            
            # Paso 2: Extraer datos
            logger.info("\n[FASE 1: EXTRACCIÓN]")
            datos_crudos = self.extractor.descargar_multiples_ligas(ligas, solo_actual=solo_actual)
            
            if not datos_crudos:
                logger.error("✗ No se descargó data de ninguna liga")
                return False
            
            # Paso 3: Transformar y cargar
            logger.info("\n[FASE 2: TRANSFORMACIÓN Y CARGA]")
            equipos_por_liga = {}  # Para registrar en el normalizador
            
            for liga_codigo, df_raw in datos_crudos.items():
                logger.info(f"\nProcesando: {LIGAS_CONFIG[liga_codigo]['nombre']}")
                
                # Transformar
                df_transformado = self.transformer.transformar(df_raw, liga_codigo)
                
                # Cargar
                self.loader.cargar_datos(df_transformado)
                
                # Recopilar equipos únicos para esta liga
                if 'HomeTeam' in df_raw.columns:
                    equipos_home = set(df_raw['HomeTeam'].dropna().unique())
                    equipos_away = set(df_raw['AwayTeam'].dropna().unique())
                    equipos_por_liga[liga_codigo] = equipos_home.union(equipos_away)
                
                logger.info(f"✓ {LIGAS_CONFIG[liga_codigo]['nombre']} completada\n")
            
            # Paso 4: Registrar equipos en TeamNormalizer (NUEVO)
            logger.info("\n[FASE 3: REGISTRO DE EQUIPOS EN NORMALIZADOR]")
            self._registrar_equipos_en_normalizador(equipos_por_liga)
            
            # Paso 5: Estadísticas finales
            logger.info("\n[FASE 4: VALIDACIÓN]")
            stats = self.loader.obtener_estadisticas()
            
            logger.info("\n" + "="*70)
            logger.info("ESTADÍSTICAS FINALES")
            logger.info("="*70)
            logger.info(f"Total de registros: {stats.get('total_registros', 0)}")
            logger.info(f"Total de equipos: {stats.get('total_equipos', 0)}")
            logger.info(f"Período: {stats.get('fecha_inicio', 'N/A')} a {stats.get('fecha_fin', 'N/A')}")
            logger.info(f"Temporadas: {len(stats.get('temporadas', {}).get('temporada', []))} cargadas")
            
            logger.info("\n✓ PIPELINE COMPLETADO EXITOSAMENTE\n")
            logger.info("="*70 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\n✗ ERROR EN PIPELINE: {str(e)}")
            return False
    
    def _registrar_equipos_en_normalizador(self, equipos_por_liga: Dict[str, set]):
        """
        Registra equipos en la BD del TeamNormalizer con su league_code.
        
        Esto permite filtrar por liga durante la normalización y evita
        cross-league pollution (ej: Paris FC vs PSG).
        
        Args:
            equipos_por_liga: Dict {league_code: set(equipos)}
        """
        if not TEAM_NORMALIZER_AVAILABLE or TeamNormalizer is None:
            logger.warning("⚠️ TeamNormalizer no disponible, saltando registro de equipos")
            return
        
        try:
            normalizer = TeamNormalizer()
            total_registrados = 0
            total_existentes = 0
            
            # Mapeo de códigos a nombres de liga
            LEAGUE_NAMES = {
                'E0': 'Premier League',
                'SP1': 'La Liga',
                'D1': 'Bundesliga',
                'I1': 'Serie A',
                'F1': 'Ligue 1',
                'P1': 'Primeira Liga',
                'N1': 'Eredivisie',
            }
            
            # Mapeo de códigos a países
            LEAGUE_COUNTRIES = {
                'E0': 'England',
                'SP1': 'Spain',
                'D1': 'Germany',
                'I1': 'Italy',
                'F1': 'France',
                'P1': 'Portugal',
                'N1': 'Netherlands',
            }
            
            for league_code, equipos in equipos_por_liga.items():
                league_name = LEAGUE_NAMES.get(league_code, league_code)
                country = LEAGUE_COUNTRIES.get(league_code, 'Unknown')
                
                logger.info(f"Registrando {len(equipos)} equipos para {league_name} ({league_code})...")
                
                for equipo in equipos:
                    if not equipo or not isinstance(equipo, str):
                        continue
                    
                    equipo = equipo.strip()
                    if not equipo:
                        continue
                    
                    try:
                        # Intentar buscar primero si ya existe
                        uuid, similarity = normalizer.normalize_team(
                            team_name=equipo,
                            league_id=league_code,
                            create_if_missing=False
                        )
                        
                        if uuid and similarity >= 90:
                            # Ya existe
                            total_existentes += 1
                        else:
                            # Crear nuevo equipo
                            normalizer.add_team(
                                official_name=equipo,
                                country=country,
                                league=league_name,
                                league_code=league_code
                            )
                            total_registrados += 1
                            
                    except Exception as e:
                        # Puede ser IntegrityError si ya existe
                        total_existentes += 1
            
            logger.info(f"✓ Equipos registrados: {total_registrados} nuevos, {total_existentes} existentes")
            
            # Mostrar estadísticas del normalizador
            stats = normalizer.get_stats()
            logger.info(f"  Total en BD: {stats.get('total_teams', 0)} equipos")
            
        except Exception as e:
            logger.error(f"Error registrando equipos en normalizador: {e}")


# ========== UTILITARIOS ==========
def obtener_resumen_bd(db_type: str = 'sqlite', connection_string: Optional[str] = None) -> pd.DataFrame:
    """
    Obtiene resumen de datos cargados en BD.
    Útil para análisis exploratorio.
    """
    try:
        loader = FootballDataLoader(db_type, connection_string)
        
        with loader.engine.connect() as conn:
            df = pd.read_sql(
                """
                SELECT 
                    temporada,
                    COUNT(*) as total_matches,
                    COUNT(DISTINCT home_team) as unique_teams,
                    ROUND(AVG(fthg + ftag), 2) as avg_goles,
                    ROUND(AVG(total_goles > 2.5), 2) as pct_over_25
                FROM matches
                GROUP BY temporada
                ORDER BY temporada DESC
                """,
                conn
            )
            
            return df
            
    except Exception as e:
        logger.error(f"Error obteniendo resumen: {str(e)}")
        return pd.DataFrame()


# ========== PUNTO DE ENTRADA ==========
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ETL Pipeline para descarga de datos de football-data.co.uk'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'postgresql'],
        default='sqlite',
        help='Tipo de base de datos (default: sqlite)'
    )
    parser.add_argument(
        '--connection',
        type=str,
        default=SQLITE_CONNECTION_STRING,
        help=f'String de conexión a BD (default: {SQLITE_CONNECTION_STRING})'
    )
    parser.add_argument(
        '--ligas',
        type=str,
        default='E0,SP1,D1,I1,F1,P1,N1,ARG',
        help='Códigos de ligas separados por coma (default: E0,SP1,D1,I1,F1,P1,N1,ARG)'
    )
    parser.add_argument(
        '--skip-create-tables',
        action='store_true',
        help='No crear tablas'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Solo mostrar estadísticas (no ejecutar ETL)'
    )
    parser.add_argument(
        '--historico', '--full',
        action='store_true',
        dest='historico',
        help='Descarga TODAS las temporadas (por defecto solo la actual 25/26)'
    )
    
    args = parser.parse_args()
    
    if args.stats_only:
        logger.info("Obteniendo estadísticas...")
        df_stats = obtener_resumen_bd(args.db_type, args.connection)
        print("\n" + df_stats.to_string())
    else:
        ligas_lista = args.ligas.split(',')
        
        # solo_actual = True (por defecto, rápido)
        # solo_actual = False (si --historico, descarga todo)
        solo_actual = not args.historico
        
        if solo_actual:
            logger.info("🚀 Modo RÁPIDO: Solo temporada actual (25/26)")
            logger.info("   Usa --historico para descargar todas las temporadas\n")
        else:
            logger.info("📚 Modo HISTÓRICO: Descargando TODAS las temporadas (~11 por liga)")
            logger.info("   ⏱️  Esto puede tomar varios minutos...\n")
        
        pipeline = FootballETLPipeline(args.db_type, args.connection)
        exitoso = pipeline.ejecutar(
            ligas_lista, 
            crear_tablas=not args.skip_create_tables,
            solo_actual=solo_actual
        )
        
        sys.exit(0 if exitoso else 1)
