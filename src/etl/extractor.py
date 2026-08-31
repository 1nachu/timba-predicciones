"""
ETL Extractor
=============
Descarga y extracción de datos históricos y recientes desde Football-Data.co.uk.
"""

import io
import time
import logging
from typing import List, Dict, Optional
import pandas as pd
import requests

from .config import LIGAS_CONFIG

try:
    from utils.shared import FOOTBALL_DATA_BASE_URL
except ImportError:
    FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk"

logger = logging.getLogger(__name__)


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
                    temporadas = liga_info['temporadas'][:3]  # Las 3 temporadas más recientes (ej: 2627, 2526, 2425)
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
