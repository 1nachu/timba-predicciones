"""
Team Normalization System
=========================

Sistema de normalización de nombres de equipos usando Levenshtein fuzzy matching
y tabla maestra con UUIDs únicos internos para reconciliar datos de múltiples
fuentes (Football-Data.org, API-Football, CSVs históricos).

Features:
- Tabla maestra de equipos con UUID único interno
- FILTRADO POR LIGA (evita cross-league pollution)
- Mapeo automático de IDs externos a internos
- Similitud configurable (default: >90% para mapeo automático)
- Caché en memoria para optimizar búsquedas
- Logging detallado de mapeos y conflictos
- Soporte para alias de equipos
- Validación de integridad referencial

Usage:
    from src.team_normalization import TeamNormalizer
    
    normalizer = TeamNormalizer()  # Usa ruta centralizada por defecto
    
    # Mapear nombre a UUID interno (FILTRADO POR LIGA)
    team_uuid = normalizer.normalize_team("Manchester United", league_id="E0")
    
    # Agregar nuevo equipo con código de liga
    new_uuid = normalizer.add_team(
        official_name="Manchester United FC",
        country="England",
        league="Premier League",
        league_code="E0",  # Código de liga para filtrado
        source="footballdata",
        external_id="12345"
    )
"""

import sqlite3
import uuid
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from thefuzz import fuzz, process
from pathlib import Path
import json

# ========== IMPORTS DE RUTAS CENTRALIZADAS ==========
try:
    from utils.shared import TEAM_NORMALIZER_DB_PATH_STR
    SHARED_AVAILABLE = True
except ImportError:
    SHARED_AVAILABLE = False
    TEAM_NORMALIZER_DB_PATH_STR = "data/databases/team_normalizer.db"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MasterTeam:
    """Representa un equipo en la tabla maestra."""
    team_uuid: str
    official_name: str
    country: str
    league: Optional[str] = None
    league_code: Optional[str] = None  # E0, SP1, D1, I1, F1 - PARA FILTRADO
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()


@dataclass
class ExternalTeamMapping:
    """Mapeo de ID externo a UUID interno."""
    mapping_id: str
    team_uuid: str
    source: str  # 'footballdata', 'apifootball', 'csv', etc.
    external_id: str
    external_name: str
    similarity_score: float  # 0-100 (similitud con official_name)
    is_automatic: bool  # True si fue mapeado automáticamente
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class TeamAlias:
    """Alias alternativo para un equipo (ej: "Man United" → "Manchester United")."""
    alias_id: str
    team_uuid: str
    alias_name: str
    priority: int = 0  # Orden de prioridad en búsquedas
    source: Optional[str] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


class TeamNormalizer:
    """
    Gestor central de normalización de equipos con tabla maestra.
    
    Proporciona:
    - CRUD para tabla maestra de equipos
    - Mapeo fuzzy de nombres a UUIDs
    - FILTRADO POR LIGA (evita cross-league pollution)
    - Gestión de mappings externos
    - Sistema de aliases
    - Caché en memoria
    """
    
    SIMILARITY_THRESHOLD = 90  # % para mapeo automático
    CACHE_SIZE = 1000
    
    # Mapeo de códigos de liga a países (para inferencia)
    LEAGUE_TO_COUNTRY = {
        'E0': 'England',
        'SP1': 'Spain',
        'D1': 'Germany',
        'I1': 'Italy',
        'F1': 'France',
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa el normalizador.
        
        Args:
            db_path: Ruta a la base de datos SQLite (usa centralizada si None)
        """
        # Usar ruta centralizada si no se especifica
        self.db_path = db_path if db_path else TEAM_NORMALIZER_DB_PATH_STR
        
        self._cache = {}  # {team_name: team_uuid}
        self._external_cache = {}  # {(source, external_id): team_uuid}
        self._league_cache = {}  # {(team_name, league_code): team_uuid} - NUEVO
        self._initialized = False
        
        # Crear directorio si no existe
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        self._load_cache()
        logger.info(f"TeamNormalizer initialized with DB: {self.db_path}")
    
    def _init_db(self):
        """Crea las tablas necesarias si no existen."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla maestra de equipos - INCLUYE league_code PARA FILTRADO
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_teams (
                team_uuid TEXT PRIMARY KEY,
                official_name TEXT NOT NULL,
                country TEXT NOT NULL,
                league TEXT,
                league_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Agregar columna league_code si no existe (migración)
        try:
            cursor.execute("ALTER TABLE master_teams ADD COLUMN league_code TEXT")
            logger.info("Migración: Columna league_code agregada a master_teams")
        except sqlite3.OperationalError:
            pass  # Columna ya existe
        
        # Crear índice único sobre (official_name, league_code) para evitar duplicados
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_team_name_league 
                ON master_teams(official_name, league_code)
            """)
        except sqlite3.OperationalError:
            pass  # Índice ya existe o conflicto
        
        # Tabla de mapeos externos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS external_team_mappings (
                mapping_id TEXT PRIMARY KEY,
                team_uuid TEXT NOT NULL,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                external_name TEXT NOT NULL,
                similarity_score REAL NOT NULL,
                is_automatic INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (team_uuid) REFERENCES master_teams(team_uuid),
                UNIQUE(source, external_id)
            )
        """)
        
        # Tabla de aliases
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_aliases (
                alias_id TEXT PRIMARY KEY,
                team_uuid TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                source TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (team_uuid) REFERENCES master_teams(team_uuid),
                UNIQUE(team_uuid, alias_name)
            )
        """)
        
        # Índices para optimizar búsquedas
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_master_teams_official_name 
            ON master_teams(official_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_master_teams_league_code 
            ON master_teams(league_code)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_external_mappings_source_id 
            ON external_team_mappings(source, external_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_aliases_name 
            ON team_aliases(alias_name)
        """)
        
        conn.commit()
        conn.close()
        self._initialized = True
        logger.info("Database initialized successfully")
    
    def _load_cache(self):
        """Carga la caché desde la BD."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cargar teams (global)
        cursor.execute("SELECT official_name, team_uuid FROM master_teams")
        for name, uuid_val in cursor.fetchall():
            self._cache[name.lower()] = uuid_val
        
        # Cargar teams por liga (NUEVO - evita cross-league pollution)
        cursor.execute("SELECT official_name, league_code, team_uuid FROM master_teams WHERE league_code IS NOT NULL")
        for name, league_code, uuid_val in cursor.fetchall():
            self._league_cache[(name.lower(), league_code)] = uuid_val
        
        # Cargar external mappings
        cursor.execute("""
            SELECT source, external_id, team_uuid 
            FROM external_team_mappings
        """)
        for source, ext_id, uuid_val in cursor.fetchall():
            self._external_cache[(source, ext_id)] = uuid_val
        
        conn.close()
        logger.info(f"Cache loaded: {len(self._cache)} teams, {len(self._league_cache)} league-specific, {len(self._external_cache)} mappings")
    
    def add_team(
        self,
        official_name: str,
        country: str,
        league: Optional[str] = None,
        league_code: Optional[str] = None,
        source: Optional[str] = None,
        external_id: Optional[str] = None,
        external_name: Optional[str] = None
    ) -> str:
        """
        Agrega un nuevo equipo a la tabla maestra.
        
        Args:
            official_name: Nombre oficial del equipo
            country: País
            league: Liga (nombre completo, opcional)
            league_code: Código de liga (E0, SP1, D1, I1, F1) - PARA FILTRADO
            source: Fuente de datos (para mapeo externo)
            external_id: ID externo
            external_name: Nombre en la fuente externa
        
        Returns:
            UUID único del equipo
        """
        team_uuid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Inferir país desde league_code si no se especifica
        if not country or country == "Unknown":
            if league_code:
                country = self.LEAGUE_TO_COUNTRY.get(league_code, country or "Unknown")
            else:
                country = country or "Unknown"
        
        team = MasterTeam(
            team_uuid=team_uuid,
            official_name=official_name,
            country=country,
            league=league,
            league_code=league_code,
            created_at=now,
            updated_at=now
        )
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO master_teams 
                (team_uuid, official_name, country, league, league_code, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (team.team_uuid, team.official_name, team.country, team.league, 
                  team.league_code, team.created_at, team.updated_at))
            
            # Agregar mapeo externo si se proporciona
            if source and external_id:
                similarity = 100.0  # Nombre nuevo, 100% confianza
                self.add_external_mapping(
                    team_uuid=team_uuid,
                    source=source,
                    external_id=external_id,
                    external_name=external_name or official_name,
                    similarity_score=similarity,
                    is_automatic=False
                )
            
            conn.commit()
            conn.close()
            
            # Actualizar cachés
            self._cache[official_name.lower()] = team_uuid
            if league_code:
                self._league_cache[(official_name.lower(), league_code)] = team_uuid
            
            logger.info(f"Team added: {official_name} ({team_uuid}) [league_code={league_code}]")
            return team_uuid
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Error adding team {official_name}: {e}")
            raise
    
    def add_external_mapping(
        self,
        team_uuid: str,
        source: str,
        external_id: str,
        external_name: str,
        similarity_score: float,
        is_automatic: bool = False
    ) -> str:
        """
        Agrega un mapeo de ID externo a UUID interno.
        
        Args:
            team_uuid: UUID interno
            source: Fuente de datos ('footballdata', 'apifootball', etc.)
            external_id: ID en la fuente externa
            external_name: Nombre en la fuente externa
            similarity_score: Similitud (0-100)
            is_automatic: True si fue mapeado automáticamente
        
        Returns:
            ID del mapeo
        """
        mapping_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        mapping = ExternalTeamMapping(
            mapping_id=mapping_id,
            team_uuid=team_uuid,
            source=source,
            external_id=external_id,
            external_name=external_name,
            similarity_score=similarity_score,
            is_automatic=is_automatic,
            created_at=now
        )
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO external_team_mappings
                (mapping_id, team_uuid, source, external_id, external_name, 
                 similarity_score, is_automatic, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (mapping.mapping_id, mapping.team_uuid, mapping.source, 
                  mapping.external_id, mapping.external_name, 
                  mapping.similarity_score, int(mapping.is_automatic), mapping.created_at))
            
            conn.commit()
            conn.close()
            
            # Actualizar caché
            self._external_cache[(source, external_id)] = team_uuid
            
            action = "auto-mapped" if is_automatic else "manually-mapped"
            logger.info(f"External mapping added: {source}/{external_id} → {team_uuid} ({action})")
            return mapping_id
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Error adding mapping {source}/{external_id}: {e}")
            raise
    
    def normalize_team(
        self,
        team_name: str,
        source: Optional[str] = None,
        external_id: Optional[str] = None,
        league_id: Optional[str] = None,
        create_if_missing: bool = True
    ) -> Tuple[Optional[str], float]:
        """
        Normaliza un nombre de equipo a UUID interno usando fuzzy matching.
        
        FILTRADO POR LIGA: Si se especifica league_id, solo busca equipos
        de esa liga, evitando cross-league pollution (ej: Paris FC vs PSG).
        
        Strategy:
        1. Si (source, external_id) existe en mappings → return UUID
        2. Si (nombre, league_id) existe en caché → return UUID (NUEVO)
        3. Si nombre exacto existe → return UUID
        4. Si alias exacto existe → return UUID
        5. Fuzzy match con threshold 90% (FILTRADO POR LIGA) → auto-map y return UUID
        6. Si no encontrado y create_if_missing → crear nuevo equipo
        7. Si no encontrado y no create_if_missing → return None
        
        Args:
            team_name: Nombre del equipo
            source: Fuente de datos (opcional)
            external_id: ID externo (opcional)
            league_id: Código de liga para filtrar (E0, SP1, D1, I1, F1) - NUEVO
            create_if_missing: Crear nuevo equipo si no existe
        
        Returns:
            Tuple (team_uuid, similarity_score)
        """
        
        # 1. Buscar por mapeo externo
        if source and external_id:
            cache_key = (source, external_id)
            if cache_key in self._external_cache:
                uuid_val = self._external_cache[cache_key]
                logger.debug(f"Found in external cache: {source}/{external_id} → {uuid_val}")
                return uuid_val, 100.0
        
        team_name_lower = team_name.lower()
        
        # 2. Buscar por (nombre, liga) en caché específico de liga (NUEVO)
        if league_id:
            league_cache_key = (team_name_lower, league_id)
            if league_cache_key in self._league_cache:
                uuid_val = self._league_cache[league_cache_key]
                logger.debug(f"Found in league cache: {team_name} ({league_id}) → {uuid_val}")
                return uuid_val, 100.0
        
        # 3. Buscar por nombre exacto (global)
        if team_name_lower in self._cache:
            uuid_val = self._cache[team_name_lower]
            logger.debug(f"Found exact match: {team_name} → {uuid_val}")
            return uuid_val, 100.0
        
        # 4. Buscar por alias exacto
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT team_uuid FROM team_aliases 
            WHERE LOWER(alias_name) = ? 
            ORDER BY priority DESC LIMIT 1
        """, (team_name_lower,))
        
        result = cursor.fetchone()
        if result:
            uuid_val = result[0]
            logger.debug(f"Found alias match: {team_name} → {uuid_val}")
            conn.close()
            return uuid_val, 100.0
        
        # 5. Fuzzy match contra tabla maestra (FILTRADO POR LIGA si se especifica)
        if league_id:
            # FILTRAR por liga específica - evita cross-league pollution
            cursor.execute("""
                SELECT official_name, team_uuid FROM master_teams 
                WHERE league_code = ?
            """, (league_id,))
            logger.debug(f"Fuzzy matching filtered by league: {league_id}")
        else:
            # Búsqueda global (fallback)
            cursor.execute("SELECT official_name, team_uuid FROM master_teams")
        
        teams = cursor.fetchall()
        conn.close()
        
        if teams:
            names = [t[0] for t in teams]
            matches = process.extract(team_name, names, scorer=fuzz.token_set_ratio, limit=3)
            
            if matches:
                best_name, similarity = matches[0]
                team_uuid = next(t[1] for t in teams if t[0] == best_name)
                
                logger.info(f"Fuzzy match: {team_name} → {best_name} (similarity: {similarity}%, league_filter={league_id})")
                
                # Auto-mapear si similitud > threshold
                if similarity >= self.SIMILARITY_THRESHOLD:
                    logger.info(f"Auto-mapping: {team_name} → {team_uuid} ({similarity}%)")
                    
                    if source and external_id:
                        self.add_external_mapping(
                            team_uuid=team_uuid,
                            source=source,
                            external_id=external_id,
                            external_name=team_name,
                            similarity_score=float(similarity),
                            is_automatic=True
                        )
                    
                    return team_uuid, float(similarity)
                else:
                    logger.warning(f"Similarity {similarity}% below threshold ({self.SIMILARITY_THRESHOLD}%) for '{team_name}' [league={league_id}]")
        
        # 6. Crear nuevo equipo si es necesario
        if create_if_missing:
            logger.warning(f"Creating new team: {team_name} [league={league_id}]")
            new_uuid = self.add_team(
                official_name=team_name,
                country="Unknown",
                league_code=league_id,
                source=source,
                external_id=external_id,
                external_name=team_name
            )
            return new_uuid, 0.0
        
        logger.error(f"No mapping found for: {team_name} [league={league_id}]")
        return None, 0.0
    
    def add_alias(
        self,
        team_uuid: str,
        alias_name: str,
        priority: int = 0,
        source: Optional[str] = None
    ) -> str:
        """
        Agrega un alias para un equipo.
        
        Args:
            team_uuid: UUID del equipo
            alias_name: Nombre alternativo
            priority: Prioridad en búsquedas (mayor = más prioritario)
            source: Fuente del alias
        
        Returns:
            ID del alias
        """
        alias_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        alias = TeamAlias(
            alias_id=alias_id,
            team_uuid=team_uuid,
            alias_name=alias_name,
            priority=priority,
            source=source,
            created_at=now
        )
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO team_aliases
                (alias_id, team_uuid, alias_name, priority, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (alias.alias_id, alias.team_uuid, alias.alias_name, 
                  alias.priority, alias.source, alias.created_at))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Alias added: {alias_name} → {team_uuid}")
            return alias_id
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Error adding alias {alias_name}: {e}")
            raise
    
    def get_team(self, team_uuid: str) -> Optional[Dict]:
        """Obtiene información completa de un equipo."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT team_uuid, official_name, country, league, league_code, created_at, updated_at
            FROM master_teams WHERE team_uuid = ?
        """, (team_uuid,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        team = {
            'team_uuid': row[0],
            'official_name': row[1],
            'country': row[2],
            'league': row[3],
            'league_code': row[4],
            'created_at': row[5],
            'updated_at': row[6],
            'mappings': [],
            'aliases': []
        }
        
        # Obtener mapeos externos
        cursor.execute("""
            SELECT source, external_id, external_name, similarity_score, is_automatic
            FROM external_team_mappings WHERE team_uuid = ?
            ORDER BY created_at DESC
        """, (team_uuid,))
        
        for source, ext_id, ext_name, sim, is_auto in cursor.fetchall():
            team['mappings'].append({
                'source': source,
                'external_id': ext_id,
                'external_name': ext_name,
                'similarity_score': sim,
                'is_automatic': bool(is_auto)
            })
        
        # Obtener aliases
        cursor.execute("""
            SELECT alias_name, priority, source
            FROM team_aliases WHERE team_uuid = ?
            ORDER BY priority DESC
        """, (team_uuid,))
        
        for alias_name, priority, source in cursor.fetchall():
            team['aliases'].append({
                'alias_name': alias_name,
                'priority': priority,
                'source': source
            })
        
        conn.close()
        return team
    
    def get_all_teams(self, league_code: Optional[str] = None) -> List[Dict]:
        """
        Obtiene todos los equipos de la tabla maestra.
        
        Args:
            league_code: Filtrar por liga (opcional)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if league_code:
            cursor.execute("""
                SELECT team_uuid, official_name, country, league, league_code, created_at, updated_at
                FROM master_teams
                WHERE league_code = ?
                ORDER BY official_name
            """, (league_code,))
        else:
            cursor.execute("""
                SELECT team_uuid, official_name, country, league, league_code, created_at, updated_at
                FROM master_teams
                ORDER BY official_name
            """)
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'team_uuid': row[0],
                'official_name': row[1],
                'country': row[2],
                'league': row[3],
                'league_code': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            })
        
        conn.close()
        return teams
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del normalizador."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM master_teams")
        total_teams = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM external_team_mappings")
        total_mappings = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM team_aliases")
        total_aliases = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT source, COUNT(*) FROM external_team_mappings 
            GROUP BY source
        """)
        mappings_by_source = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT COUNT(*) FROM external_team_mappings 
            WHERE is_automatic = 1
        """)
        auto_mappings = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_teams': total_teams,
            'total_mappings': total_mappings,
            'auto_mappings': auto_mappings,
            'manual_mappings': total_mappings - auto_mappings,
            'total_aliases': total_aliases,
            'mappings_by_source': mappings_by_source,
            'cache_size': len(self._cache)
        }
    
    def export_mappings(self, output_file: str = "team_mappings.json"):
        """Exporta todos los mapeos a JSON para auditoría."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        export = {
            'timestamp': datetime.utcnow().isoformat(),
            'teams': [],
            'mappings': []
        }
        
        # Exportar equipos
        cursor.execute("SELECT * FROM master_teams")
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            export['teams'].append(dict(zip(columns, row)))
        
        # Exportar mapeos
        cursor.execute("SELECT * FROM external_team_mappings")
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            export['mappings'].append(dict(zip(columns, row)))
        
        conn.close()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Mappings exported to {output_file}")
        return output_file


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEAM NORMALIZATION SYSTEM - TEST")
    print("="*80 + "\n")
    
    # Inicializar normalizador
    normalizer = TeamNormalizer(db_path="data/databases/football_data.db")
    
    # Agregar algunos equipos de prueba
    print("1. Agregando equipos de prueba...")
    teams_data = [
        ("Manchester United FC", "England", "Premier League"),
        ("Liverpool Football Club", "England", "Premier League"),
        ("Real Madrid Club de Fútbol", "Spain", "La Liga"),
        ("FC Barcelona", "Spain", "La Liga"),
    ]
    
    team_uuids = {}
    for name, country, league in teams_data:
        uuid_val = normalizer.add_team(name, country, league)
        team_uuids[name] = uuid_val
        print(f"  ✓ {name}: {uuid_val}")
    
    # Agregar aliases
    print("\n2. Agregando aliases...")
    normalizer.add_alias(team_uuids["Manchester United FC"], "Man United", priority=10)
    normalizer.add_alias(team_uuids["Manchester United FC"], "Manchester Utd", priority=9)
    normalizer.add_alias(team_uuids["Liverpool Football Club"], "LFC", priority=10)
    normalizer.add_alias(team_uuids["Real Madrid Club de Fútbol"], "Real Madrid", priority=10)
    print("  ✓ Aliases agregados")
    
    # Agregar mapeos externos
    print("\n3. Agregando mapeos externos...")
    normalizer.add_external_mapping(
        team_uuid=team_uuids["Manchester United FC"],
        source="footballdata",
        external_id="66",
        external_name="Manchester United",
        similarity_score=100.0,
        is_automatic=False
    )
    print("  ✓ Mapeos externos agregados")
    
    # Normalizar nombres variantes
    print("\n4. Normalizando nombres con fuzzy matching...")
    test_names = [
        ("Manchester United", None, None),
        ("Man United", None, None),
        ("Manchester Utd", None, None),
        ("Liverpool", None, None),
        ("Real Madrid", None, None),
        ("Barcelona", None, None),
        ("Manchester City", "footballdata", "65"),  # No existe, debería crear
    ]
    
    for team_name, source, ext_id in test_names:
        uuid_val, similarity = normalizer.normalize_team(
            team_name, 
            source=source, 
            external_id=ext_id
        )
        status = "✓" if uuid_val else "✗"
        print(f"  {status} {team_name} → {uuid_val} (similarity: {similarity:.0f}%)")
    
    # Mostrar estadísticas
    print("\n5. Estadísticas del sistema:")
    stats = normalizer.get_stats()
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    # Mostrar información completa de un equipo
    print("\n6. Información completa de un equipo:")
    team_info = normalizer.get_team(team_uuids["Manchester United FC"])
    if team_info:
        print(f"  Equipo: {team_info['official_name']}")
        print(f"  UUID: {team_info['team_uuid']}")
        print(f"  País: {team_info['country']}")
        print(f"  Mapeos externos: {len(team_info['mappings'])}")
        print(f"  Aliases: {len(team_info['aliases'])}")
        for alias in team_info['aliases']:
            print(f"    - {alias['alias_name']} (priority: {alias['priority']})")
    
    # Exportar mapeos
    print("\n7. Exportando mapeos...")
    normalizer.export_mappings("team_mappings.json")
    print("  ✓ Mapeos exportados a team_mappings.json")
    
    print("\n" + "="*80)
    print("TEST COMPLETADO EXITOSAMENTE")
    print("="*80 + "\n")
