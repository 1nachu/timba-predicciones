"""
ETL Pipeline Orchestrator
=========================
Coordinador integral del pipeline ETL: extracción, transformación, carga y registro de equipos.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .config import LIGAS_CONFIG
from .extractor import FootballDataExtractor
from .transformer import FootballDataTransformer
from .loader import FootballDataLoader

try:
    from team_normalization import TeamNormalizer
    TEAM_NORMALIZER_AVAILABLE = True
except ImportError:
    TEAM_NORMALIZER_AVAILABLE = False
    TeamNormalizer = None

logger = logging.getLogger(__name__)


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
            
            # Paso 4: Registrar equipos en TeamNormalizer
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
