"""
ETL Transformer
===============
Normalización, limpieza, validación y enriquecimiento de datos de partidos.
"""

import logging
from typing import Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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
