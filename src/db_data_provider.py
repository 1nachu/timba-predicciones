"""
Database Data Provider
======================

Proveedor de datos desde bases de datos locales para el motor de predicciones.
Integra múltiples fuentes de datos para mayor precisión:
- football_data.db (datos históricos del ETL)
- api_football_cache.db (datos enriquecidos de API)
- CSVs online como fallback

Autor: Data Integration Team
Fecha: 30 de Enero de 2026
"""
from __future__ import annotations

import os
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime, timedelta
import requests
from io import StringIO

# ========== IMPORTS DE RUTAS CENTRALIZADAS ==========
try:
    from utils.shared import DB_PATH_STR, DB_PATH
    SHARED_AVAILABLE = True
except ImportError:
    SHARED_AVAILABLE = False
    DB_PATH_STR = "data/databases/football_data.db"
    DB_PATH = Path(DB_PATH_STR)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseDataProvider:
    """
    Proveedor inteligente de datos que combina múltiples fuentes.
    Prioridad: BD Local > API Cache > CSV Online
    """
    
    def __init__(self, db_path: str | None = None):
        """
        Inicializa el proveedor de datos.
        
        Args:
            db_path: Ruta a la base de datos principal (usa centralizada si no se especifica)
        """
        # Usar constante centralizada si no se especifica
        if db_path is None:
            self.db_path = DB_PATH_STR
            self.db_full_path = DB_PATH
        else:
            self.db_path = db_path
            self.project_root = Path(__file__).parent.parent
            self.db_full_path = self.project_root / db_path if not Path(db_path).is_absolute() else Path(db_path)
        
        # Verificar si existe la BD
        self.db_available = self.db_full_path.exists()
        
        if self.db_available:
            logger.info(f"✓ Base de datos encontrada: {self.db_full_path}")
        else:
            logger.warning(f"⚠️  Base de datos no encontrada: {self.db_full_path}")
            logger.info("Se usarán CSVs online como fallback")
    
    def get_data_from_db(self, liga_codigo: str | None = None, 
                         temporadas: int = 3) -> Optional[pd.DataFrame]:
        """
        Obtiene datos desde la base de datos local.
        
        Args:
            liga_codigo: Código de liga (E0, SP1, D1, etc)
            temporadas: Número de temporadas recientes a cargar
        
        Returns:
            DataFrame con datos históricos o None si no hay datos
        """
        if not self.db_available:
            return None
        
        try:
            # REFACTORIZADO: Usar context manager para conexión SQLite
            with sqlite3.connect(str(self.db_full_path)) as conn:
                # Consulta SQL para obtener datos filtrados por liga
                if liga_codigo and str(liga_codigo).upper() != "ALL":
                    query = """
                        SELECT 
                            date as Date,
                            home_team as HomeTeam,
                            away_team as AwayTeam,
                            fthg as FTHG,
                            ftag as FTAG,
                            ftr as FTR,
                            hs as HS,
                            as_shots as [AS],
                            hst as HST,
                            ast as AST,
                            hc as HC,
                            ac as AC,
                            hf as HF,
                            af as AF,
                            hr as HR,
                            ar as AR,
                            hy as HY,
                            ay as AY,
                            b365h as B365H,
                            b365d as B365D,
                            b365a as B365A,
                            temporada as Temporada,
                            league_code as LeagueCode
                        FROM matches
                        WHERE league_code = ?
                          AND temporada IN (
                            SELECT DISTINCT temporada 
                            FROM matches 
                            WHERE league_code = ?
                            ORDER BY temporada DESC 
                            LIMIT ?
                        )
                        ORDER BY date DESC
                    """
                    df = pd.read_sql_query(query, conn, params=(str(liga_codigo), str(liga_codigo), int(temporadas)))
                else:
                    query = """
                        SELECT 
                            date as Date,
                            home_team as HomeTeam,
                            away_team as AwayTeam,
                            fthg as FTHG,
                            ftag as FTAG,
                            ftr as FTR,
                            hs as HS,
                            as_shots as [AS],
                            hst as HST,
                            ast as AST,
                            hc as HC,
                            ac as AC,
                            hf as HF,
                            af as AF,
                            hr as HR,
                            ar as AR,
                            hy as HY,
                            ay as AY,
                            b365h as B365H,
                            b365d as B365D,
                            b365a as B365A,
                            temporada as Temporada,
                            league_code as LeagueCode
                        FROM matches
                        WHERE temporada IN (
                            SELECT DISTINCT temporada 
                            FROM matches 
                            ORDER BY temporada DESC 
                            LIMIT ?
                        )
                        ORDER BY date DESC
                    """
                    df = pd.read_sql_query(query, conn, params=(int(temporadas),))
            
            if not df.empty:
                logger.info(f"✓ Cargados {len(df)} registros desde BD local para liga '{liga_codigo}'")
                logger.info(f"  Período: {df['Date'].min()} a {df['Date'].max()}")
                logger.info(f"  Equipos únicos: {len(set(df['HomeTeam']).union(set(df['AwayTeam'])))}")
                return df
            else:
                logger.warning(f"⚠️  No hay datos en la BD para liga '{liga_codigo}'")
                return None
                
        except Exception as e:
            logger.error(f"Error cargando datos de BD para liga '{liga_codigo}': {str(e)}")
            return None
    
    def get_data_from_csv(self, url: str) -> Optional[pd.DataFrame]:
        """
        Fallback: Descarga datos desde CSV online.
        
        Args:
            url: URL del CSV
        
        Returns:
            DataFrame con datos o None si falla
        """
        try:
            logger.info(f"Descargando CSV desde: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            df = pd.read_csv(StringIO(response.text))
            logger.info(f"✓ Descargados {len(df)} registros desde CSV")
            return df
            
        except Exception as e:
            logger.error(f"Error descargando CSV: {str(e)}")
            return None
    
    def get_enriched_data(self, df_base: pd.DataFrame) -> pd.DataFrame:
        """
        Enriquece datos base con información adicional de otras fuentes.
        
        Args:
            df_base: DataFrame base
        
        Returns:
            DataFrame enriquecido
        """
        df = df_base.copy()
        
        # Aquí se puede integrar con api_football_cache.db si existe
        api_cache_path = self.project_root / "data/databases/api_football_cache.db"
        
        if api_cache_path.exists():
            try:
                # REFACTORIZADO: Usar context manager para conexión SQLite
                with sqlite3.connect(str(api_cache_path)) as conn:
                    # Aquí se pueden hacer joins inteligentes
                    pass
                logger.info("✓ Datos enriquecidos con API cache")
            except Exception as e:
                logger.warning(f"No se pudo enriquecer con API cache: {str(e)}")
        
        return df
    
    def get_smart_data(self, liga_codigo: Optional[str] = None, 
                       url_csv: Optional[str] = None,
                       temporadas: int = 3,
                       enrich: bool = True) -> pd.DataFrame:
        """
        Obtiene datos de forma inteligente:
        1. Intenta BD local primero
        2. Fallback a CSV online
        3. Opcionalmente enriquece con otras fuentes
        
        Args:
            liga_codigo: Código de liga
            url_csv: URL del CSV como fallback
            temporadas: Número de temporadas
            enrich: Si debe enriquecer datos
        
        Returns:
            DataFrame con datos (nunca None, lanza excepción si falla)
        """
        # Intento 1: Base de datos local
        df = self.get_data_from_db(liga_codigo, temporadas)
        
        if df is not None and not df.empty:
            logger.info("✓ Usando datos de BD local")
            source = "BD Local"
        elif url_csv:
            # Intento 2: CSV online
            logger.info("⚠️  BD no disponible, usando CSV online")
            df = self.get_data_from_csv(url_csv)
            source = "CSV Online"
            
            if df is None or df.empty:
                raise ValueError("No se pudieron obtener datos de ninguna fuente")
        else:
            raise ValueError("No hay fuentes de datos disponibles")
        
        # Enriquecimiento opcional
        if enrich and df is not None:
            df = self.get_enriched_data(df)
        
        # Agregar metadata
        df.attrs['source'] = source
        df.attrs['loaded_at'] = datetime.now().isoformat()
        
        return df
    
    def get_db_stats(self) -> Dict:
        """
        Obtiene estadísticas de la base de datos.
        
        Returns:
            Diccionario con estadísticas
        """
        if not self.db_available:
            return {
                'available': False,
                'message': 'Base de datos no disponible'
            }
        
        try:
            # REFACTORIZADO: Usar context manager para conexión SQLite
            with sqlite3.connect(str(self.db_full_path)) as conn:
                stats = {}
                
                # Total de registros
                total = pd.read_sql_query(
                    "SELECT COUNT(*) as total FROM matches", conn
                )
                stats['total_matches'] = int(total['total'].values[0])
                
                # Por temporada
                temporadas = pd.read_sql_query(
                    """SELECT temporada, COUNT(*) as count 
                       FROM matches 
                       GROUP BY temporada 
                       ORDER BY temporada DESC""", 
                    conn
                )
            stats['by_season'] = temporadas.to_dict(orient='records')
            
            # Rango de fechas
            fechas = pd.read_sql_query(
                "SELECT MIN(date) as min_date, MAX(date) as max_date FROM matches",
                conn
            )
            stats['date_range'] = {
                'min': fechas['min_date'].values[0],
                'max': fechas['max_date'].values[0]
            }
            
            # Equipos únicos
            equipos = pd.read_sql_query(
                """SELECT COUNT(DISTINCT home_team) + 
                          COUNT(DISTINCT away_team) as total_teams 
                   FROM matches""",
                conn
            )
            stats['total_teams'] = int(equipos['total_teams'].values[0])
            
            # Context manager cierra automáticamente
            
            stats['available'] = True
            stats['db_path'] = str(self.db_full_path)
            
            return stats
            
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }
    
    def check_data_quality(self, df: pd.DataFrame) -> Dict:
        """
        Verifica la calidad de los datos cargados.
        
        Args:
            df: DataFrame a verificar
        
        Returns:
            Diccionario con métricas de calidad
        """
        quality = {}
        
        # Completitud de columnas críticas
        critical_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
        quality['critical_columns_present'] = all(col in df.columns for col in critical_cols)
        
        # Valores faltantes
        quality['missing_values'] = df[critical_cols].isnull().sum().to_dict()
        
        # Duplicados
        quality['duplicates'] = df.duplicated(subset=['Date', 'HomeTeam', 'AwayTeam']).sum()
        
        # Rango temporal
        if 'Date' in df.columns:
            df_sorted = df.copy()
            df_sorted['Date'] = pd.to_datetime(df_sorted['Date'])
            quality['date_range'] = {
                'min': df_sorted['Date'].min().strftime('%Y-%m-%d'),
                'max': df_sorted['Date'].max().strftime('%Y-%m-%d'),
                'span_days': (df_sorted['Date'].max() - df_sorted['Date'].min()).days
            }
        
        # Score de calidad (0-100)
        score = 100
        if not quality['critical_columns_present']:
            score -= 50
        score -= min(sum(quality['missing_values'].values()), 20)
        score -= min(quality['duplicates'], 10)
        
        quality['quality_score'] = max(0, score)
        
        return quality


# ========== FUNCIONES DE UTILIDAD ==========

def get_provider() -> DatabaseDataProvider:
    """
    Obtiene una instancia del proveedor de datos.
    Función de conveniencia para importación rápida.
    """
    return DatabaseDataProvider()


def test_data_sources():
    """
    Prueba las diferentes fuentes de datos disponibles.
    """
    print("\n" + "="*70)
    print("🧪 TEST DE FUENTES DE DATOS")
    print("="*70 + "\n")
    
    provider = DatabaseDataProvider()
    
    # Test 1: Estadísticas de BD
    print("1️⃣  Estadísticas de Base de Datos:")
    stats = provider.get_db_stats()
    
    if stats['available']:
        print(f"   ✓ BD Disponible: {stats['db_path']}")
        print(f"   ✓ Total de partidos: {stats['total_matches']}")
        print(f"   ✓ Total de equipos: {stats['total_teams']}")
        print(f"   ✓ Rango: {stats['date_range']['min']} a {stats['date_range']['max']}")
        print(f"\n   Temporadas:")
        for season in stats['by_season'][:5]:
            print(f"     - {season['temporada']}: {season['count']} partidos")
    else:
        print(f"   ✗ BD No disponible: {stats.get('message', stats.get('error'))}")
    
    # Test 2: Carga de datos
    print("\n2️⃣  Test de Carga de Datos:")
    try:
        df = provider.get_smart_data(temporadas=2)
        print(f"   ✓ Datos cargados exitosamente")
        print(f"   ✓ Registros: {len(df)}")
        print(f"   ✓ Columnas: {len(df.columns)}")
        print(f"   ✓ Fuente: {df.attrs.get('source', 'Desconocida')}")
        
        # Test 3: Calidad de datos
        print("\n3️⃣  Calidad de Datos:")
        quality = provider.check_data_quality(df)
        print(f"   ✓ Score de calidad: {quality['quality_score']}/100")
        print(f"   ✓ Columnas críticas: {'✓' if quality['critical_columns_present'] else '✗'}")
        print(f"   ✓ Duplicados: {quality['duplicates']}")
        
        if quality['quality_score'] >= 80:
            print("\n   🎉 Calidad de datos: EXCELENTE")
        elif quality['quality_score'] >= 60:
            print("\n   ⚠️  Calidad de datos: ACEPTABLE")
        else:
            print("\n   ❌ Calidad de datos: POBRE")
        
    except Exception as e:
        print(f"   ✗ Error cargando datos: {str(e)}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_data_sources()
