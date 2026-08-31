"""
ETL Loader
==========
Carga masiva a base de datos (SQLite / PostgreSQL) y estadísticas del dataset.
"""

import logging
from typing import Dict, Optional, Literal
import pandas as pd

try:
    import sqlalchemy
except ImportError:
    sqlalchemy = None

try:
    from utils.shared import SQLITE_CONNECTION_STRING
except ImportError:
    SQLITE_CONNECTION_STRING = "sqlite:///data/databases/football_data.db"

logger = logging.getLogger(__name__)


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
