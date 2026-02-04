"""
ETL Team Integration
====================

Script de integración que utiliza el normalizador de equipos para reconciliar
datos de múltiples fuentes (Football-Data.org, API-Football, CSVs históricos)
en un único UUID interno.

Funcionalidades:
- Procesamiento de datos de múltiples fuentes
- Normalización automática con similitud >90%
- Mapping de datos históricos
- Validación de integridad
- Reportes de mapeos conflictivos
- Exportación de datos normalizados

Usage:
    from src.etl_team_integration import TeamETLIntegrator
    
    integrator = TeamETLIntegrator()
    
    # Procesar datos de Football-Data
    integrator.process_footballdata_teams(csv_file="data/teams.csv")
    
    # Procesar datos de API-Football
    integrator.process_apifootball_teams(api_response)
    
    # Obtener reporte de mapeos
    report = integrator.get_mapping_report()
"""

import pandas as pd
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Import del normalizador (sin prefijo src. para ejecución correcta)
try:
    from team_normalization import TeamNormalizer
except ImportError:
    # Fallback para cuando se ejecuta desde la raíz del proyecto
    from src.team_normalization import TeamNormalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TeamETLIntegrator:
    """
    Integrador de datos de equipos desde múltiples fuentes ETL.
    
    Procesa datos de:
    - Football-Data.co.uk (CSVs históricos)
    - Football-Data.org (API)
    - API-Football (API v3)
    
    Normaliza todos a UUIDs internos únicos.
    """
    
    def __init__(self, db_path: str = "data/databases/football_data.db"):
        """
        Inicializa el integrador.
        
        Args:
            db_path: Ruta a la base de datos
        """
        self.normalizer = TeamNormalizer(db_path)
        self.db_path = db_path
        self._init_integration_table()
        logger.info("TeamETLIntegrator initialized")
    
    def _init_integration_table(self):
        """Crea tabla para tracking de integraciones."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_integration_log (
                log_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                external_name TEXT NOT NULL,
                team_uuid TEXT,
                similarity_score REAL,
                status TEXT,
                error_message TEXT,
                processed_at TEXT NOT NULL,
                FOREIGN KEY (team_uuid) REFERENCES master_teams(team_uuid)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def process_footballdata_teams(
        self,
        csv_file: str,
        league: str = "Unknown"
    ) -> Tuple[int, int]:
        """
        Procesa datos de equipos desde CSV de Football-Data.co.uk.
        
        Args:
            csv_file: Ruta al archivo CSV
            league: Liga (se usa como fallback si no está en CSV)
        
        Returns:
            (total_procesados, total_nuevos)
        """
        logger.info(f"Processing Football-Data CSV: {csv_file}")
        
        if not Path(csv_file).exists():
            logger.error(f"File not found: {csv_file}")
            return 0, 0
        
        df = pd.read_csv(csv_file)
        
        # Normalizar columnas
        df.columns = df.columns.str.lower().str.strip()
        
        # Buscar columnas de nombre del equipo
        team_cols = [col for col in df.columns if 'team' in col or 'name' in col]
        
        processed = 0
        new_teams = 0
        
        for idx, row in df.iterrows():
            # Extraer nombre del equipo
            team_name = None
            for col in team_cols:
                if pd.notna(row[col]):
                    team_name = str(row[col]).strip()
                    break
            
            if not team_name:
                continue
            
            # Normalizar
            team_uuid, similarity = self.normalizer.normalize_team(
                team_name=team_name,
                source="footballdata",
                external_id=str(idx),
                create_if_missing=True
            )
            
            if similarity == 0.0:
                new_teams += 1
            
            self._log_integration(
                source="footballdata",
                external_id=str(idx),
                external_name=team_name,
                team_uuid=team_uuid,
                similarity_score=similarity,
                status="success"
            )
            
            processed += 1
        
        logger.info(f"Processed {processed} teams ({new_teams} new)")
        return processed, new_teams
    
    def process_apifootball_teams(
        self,
        teams_data: List[Dict],
        season: int = 2026,
        league_id: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Procesa datos de equipos desde API-Football v3.
        
        Args:
            teams_data: Lista de dicts con datos de equipos
            season: Temporada
            league_id: ID de la liga
        
        Returns:
            (total_procesados, total_nuevos)
        """
        logger.info(f"Processing API-Football teams (season={season})")
        
        processed = 0
        new_teams = 0
        
        for team_data in teams_data:
            if not isinstance(team_data, dict):
                continue
            
            # Extraer campos de API-Football
            team_id = team_data.get('id')
            team_name = team_data.get('name')
            country = team_data.get('country', 'Unknown')
            
            if not team_id or not team_name:
                continue
            
            # Normalizar
            team_uuid, similarity = self.normalizer.normalize_team(
                team_name=team_name,
                source="apifootball",
                external_id=str(team_id),
                create_if_missing=True
            )
            
            if similarity == 0.0:
                new_teams += 1
            
            self._log_integration(
                source="apifootball",
                external_id=str(team_id),
                external_name=team_name,
                team_uuid=team_uuid,
                similarity_score=similarity,
                status="success"
            )
            
            processed += 1
        
        logger.info(f"Processed {processed} teams ({new_teams} new)")
        return processed, new_teams
    
    def process_footballdataorg_api(
        self,
        teams_response: Dict
    ) -> Tuple[int, int]:
        """
        Procesa datos de equipos desde Football-Data.org API.
        
        Args:
            teams_response: Response JSON de la API
        
        Returns:
            (total_procesados, total_nuevos)
        """
        logger.info("Processing Football-Data.org API response")
        
        processed = 0
        new_teams = 0
        
        teams = teams_response.get('teams', [])
        
        for team in teams:
            team_id = team.get('id')
            team_name = team.get('name')
            country = team.get('area', {}).get('name', 'Unknown')
            
            if not team_id or not team_name:
                continue
            
            # Normalizar
            team_uuid, similarity = self.normalizer.normalize_team(
                team_name=team_name,
                source="footballdataorg",
                external_id=str(team_id),
                create_if_missing=True
            )
            
            if similarity == 0.0:
                new_teams += 1
            
            self._log_integration(
                source="footballdataorg",
                external_id=str(team_id),
                external_name=team_name,
                team_uuid=team_uuid,
                similarity_score=similarity,
                status="success"
            )
            
            processed += 1
        
        logger.info(f"Processed {processed} teams ({new_teams} new)")
        return processed, new_teams
    
    def _log_integration(
        self,
        source: str,
        external_id: str,
        external_name: str,
        team_uuid: Optional[str],
        similarity_score: float,
        status: str,
        error_message: Optional[str] = None
    ):
        """Registra una integración en la tabla de logs."""
        import uuid as uuid_lib
        
        log_id = str(uuid_lib.uuid4())
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO team_integration_log
            (log_id, source, external_id, external_name, team_uuid, 
             similarity_score, status, error_message, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (log_id, source, external_id, external_name, team_uuid,
              similarity_score, status, error_message, now))
        
        conn.commit()
        conn.close()
    
    def get_mapping_report(self) -> Dict:
        """
        Genera un reporte de mapeos y conflictos.
        
        Returns:
            Dict con estadísticas de mapeos
        """
        conn = sqlite3.connect(self.db_path)
        
        # Estadísticas generales
        stats = self.normalizer.get_stats()
        
        # Mapeos por fuente
        df_mappings = pd.read_sql("""
            SELECT source, COUNT(*) as count,
                   AVG(similarity_score) as avg_similarity,
                   SUM(CASE WHEN is_automatic = 1 THEN 1 ELSE 0 END) as auto_count
            FROM external_team_mappings
            GROUP BY source
        """, conn)
        
        # Equipos sin mapeos completos
        df_unmapped = pd.read_sql("""
            SELECT mt.team_uuid, mt.official_name,
                   COUNT(etm.source) as source_count
            FROM master_teams mt
            LEFT JOIN external_team_mappings etm ON mt.team_uuid = etm.team_uuid
            GROUP BY mt.team_uuid
            HAVING source_count < 2
        """, conn)
        
        # Conflictos (mismo external_id mapeado a diferentes UUIDs)
        df_conflicts = pd.read_sql("""
            SELECT source, external_id,
                   COUNT(DISTINCT team_uuid) as conflicting_uuids,
                   GROUP_CONCAT(team_uuid) as team_uuids
            FROM external_team_mappings
            GROUP BY source, external_id
            HAVING conflicting_uuids > 1
        """, conn)
        
        conn.close()
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': stats,
            'mappings_by_source': df_mappings.to_dict('records') if not df_mappings.empty else [],
            'unmapped_count': len(df_unmapped),
            'unmapped_teams': df_unmapped.to_dict('records') if not df_unmapped.empty else [],
            'conflicts_count': len(df_conflicts),
            'conflicts': df_conflicts.to_dict('records') if not df_conflicts.empty else []
        }
        
        return report
    
    def export_normalized_data(
        self,
        output_file: str = "normalized_teams.csv"
    ) -> str:
        """
        Exporta todos los datos normalizados a CSV.
        
        Args:
            output_file: Ruta del archivo de salida
        
        Returns:
            Ruta del archivo exportado
        """
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql("""
            SELECT 
                mt.team_uuid,
                mt.official_name,
                mt.country,
                mt.league,
                COUNT(DISTINCT etm.source) as source_count,
                GROUP_CONCAT(DISTINCT etm.source) as sources,
                COUNT(ta.alias_id) as alias_count
            FROM master_teams mt
            LEFT JOIN external_team_mappings etm ON mt.team_uuid = etm.team_uuid
            LEFT JOIN team_aliases ta ON mt.team_uuid = ta.team_uuid
            GROUP BY mt.team_uuid
            ORDER BY mt.official_name
        """, conn)
        
        conn.close()
        
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"Normalized data exported to {output_file}")
        
        return output_file
    
    def validate_integrity(self) -> Dict:
        """
        Valida la integridad referencial de los mapeos.
        
        Returns:
            Dict con resultados de validación
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        issues = {
            'orphaned_mappings': 0,
            'orphaned_aliases': 0,
            'duplicate_aliases': 0,
            'details': []
        }
        
        # Mapeos sin team_uuid válido
        cursor.execute("""
            SELECT COUNT(*) FROM external_team_mappings
            WHERE team_uuid NOT IN (SELECT team_uuid FROM master_teams)
        """)
        issues['orphaned_mappings'] = cursor.fetchone()[0]
        
        # Aliases sin team_uuid válido
        cursor.execute("""
            SELECT COUNT(*) FROM team_aliases
            WHERE team_uuid NOT IN (SELECT team_uuid FROM master_teams)
        """)
        issues['orphaned_aliases'] = cursor.fetchone()[0]
        
        # Duplicados de aliases
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT alias_id, COUNT(*) FROM team_aliases
                GROUP BY alias_name HAVING COUNT(*) > 1
            )
        """)
        issues['duplicate_aliases'] = cursor.fetchone()[0]
        
        conn.close()
        
        return issues


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("ETL TEAM INTEGRATION - TEST")
    print("="*80 + "\n")
    
    integrator = TeamETLIntegrator()
    
    # Simular datos de múltiples fuentes
    print("1. Simulando procesamiento de datos de API-Football...")
    apifootball_teams = [
        {'id': 1, 'name': 'Manchester United', 'country': 'England'},
        {'id': 2, 'name': 'Liverpool FC', 'country': 'England'},
        {'id': 3, 'name': 'Real Madrid', 'country': 'Spain'},
    ]
    processed, new = integrator.process_apifootball_teams(apifootball_teams)
    print(f"  ✓ Procesados: {processed}, Nuevos: {new}\n")
    
    print("2. Simulando procesamiento de Football-Data.org API...")
    footballdataorg_teams = {
        'teams': [
            {'id': 123, 'name': 'Man. United', 'area': {'name': 'England'}},
            {'id': 124, 'name': 'Liverpool Football Club', 'area': {'name': 'England'}},
            {'id': 456, 'name': 'Real Madrid Club de Fútbol', 'area': {'name': 'Spain'}},
        ]
    }
    processed, new = integrator.process_footballdataorg_api(footballdataorg_teams)
    print(f"  ✓ Procesados: {processed}, Nuevos: {new}\n")
    
    print("3. Obteniendo reporte de mapeos...")
    report = integrator.get_mapping_report()
    print(f"  Total equipos: {report['summary']['total_teams']}")
    print(f"  Total mapeos: {report['summary']['total_mappings']}")
    print(f"  Auto-mapeados: {report['summary']['auto_mappings']}")
    print(f"  Conflictos: {report['conflicts_count']}\n")
    
    print("4. Validando integridad...")
    validation = integrator.validate_integrity()
    print(f"  Mapeos huérfanos: {validation['orphaned_mappings']}")
    print(f"  Aliases huérfanos: {validation['orphaned_aliases']}\n")
    
    print("5. Exportando datos normalizados...")
    output_file = integrator.export_normalized_data()
    print(f"  ✓ Exportado a {output_file}\n")
    
    print("="*80)
    print("TEST COMPLETADO")
    print("="*80 + "\n")
