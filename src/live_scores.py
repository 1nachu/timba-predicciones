"""
Live Scores Module
==================

Módulo para obtener marcadores en vivo de múltiples competiciones.

Características:
- Polling automático de competiciones
- Actualización inteligente de marcadores
- Detección de cambios en tiempo real
- Persistencia local de datos
- Webhooks/callbacks para eventos
- State machine para seguimiento de partidos

Autor: Backend Integration Team
Versión: 1.0.0
"""

import time
import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass, asdict, field
from pathlib import Path
import sqlite3
from collections import defaultdict

# Import flexible para football_api_client (funciona desde src/ o desde raíz)
try:
    from football_api_client import (
        FootballDataClient, Competition, MatchStatus,
        FootballAPIError, RateLimitError
    )
except ImportError:
    from src.football_api_client import (
        FootballDataClient, Competition, MatchStatus,
        FootballAPIError, RateLimitError
    )

# ========== IMPORTS DE RUTAS CENTRALIZADAS ==========
try:
    from utils.shared import (
        LIVE_SCORES_DB_PATH_STR,
        CACHE_DIR,
    )
    SHARED_AVAILABLE = True
except ImportError:
    SHARED_AVAILABLE = False
    LIVE_SCORES_DB_PATH_STR = "data/databases/live_scores.db"
    CACHE_DIR = Path("data/live_scores_cache")

# ========== CONFIGURACIÓN ==========
logger = logging.getLogger(__name__)

POLL_INTERVALS = {
    'SCHEDULED': 600,    # 10 minutos
    'LIVE': 15,          # 15 segundos (tiempo real)
    'FINISHED': 3600,    # 1 hora
    'PAUSED': 30,        # 30 segundos
}

DEFAULT_COMPETITIONS = [
    'PL',    # Premier League
    'PD',    # La Liga
    'BL1',   # Bundesliga
    'SA',    # Serie A
    'FL1',   # Ligue 1
    'PPL',   # Primeira Liga (Portugal)
    'DED',   # Eredivisie (Países Bajos)
    # 'CL',  # Champions League - No disponible en API gratuita
]


# ========== EVENTOS DE PARTIDOS ==========
class MatchEvent(Enum):
    """Tipos de eventos que puede generar un partido"""
    MATCH_STARTED = "match_started"
    GOAL_HOME = "goal_home"
    GOAL_AWAY = "goal_away"
    HALFTIME = "halftime"
    FULLTIME = "fulltime"
    STATUS_CHANGE = "status_change"
    SCORE_UPDATE = "score_update"
    RED_CARD = "red_card"
    MATCH_POSTPONED = "match_postponed"


@dataclass
class MatchSnapshot:
    """Snapshot de estado de un partido"""
    match_id: int
    home_team: str
    away_team: str
    status: str
    home_score: int
    away_score: int
    timestamp: float
    competition: str
    minute: Optional[int] = None
    second_half: Optional[bool] = None
    home_possession: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MatchChangeDetection:
    """Detecta cambios entre snapshots de un partido"""
    previous: Optional[MatchSnapshot]
    current: MatchSnapshot
    events: List[MatchEvent] = field(default_factory=list)
    
    def detect(self) -> List[MatchEvent]:
        """Detecta todos los cambios y genera eventos"""
        if self.previous is None:
            # Primer snapshot
            if self.current.status == "LIVE":
                self.events.append(MatchEvent.MATCH_STARTED)
            return self.events
        
        # Cambios de estado
        if self.previous.status != self.current.status:
            self.events.append(MatchEvent.STATUS_CHANGE)
            
            if self.current.status == "LIVE":
                self.events.append(MatchEvent.MATCH_STARTED)
            elif self.current.status == "FINISHED":
                self.events.append(MatchEvent.FULLTIME)
        
        # Goles
        if self.current.home_score > self.previous.home_score:
            self.events.append(MatchEvent.GOAL_HOME)
        
        if self.current.away_score > self.previous.away_score:
            self.events.append(MatchEvent.GOAL_AWAY)
        
        # Cambio de puntuación
        if (self.current.home_score != self.previous.home_score or
            self.current.away_score != self.previous.away_score):
            self.events.append(MatchEvent.SCORE_UPDATE)
        
        # Medio tiempo
        if (self.previous.minute is not None and 
            self.current.minute is not None):
            if (self.previous.minute < 45 and self.current.minute >= 45):
                self.events.append(MatchEvent.HALFTIME)
        
        return self.events


# ========== LIVE SCORES MANAGER ==========
class LiveScoresManager:
    """
    Gestor central de marcadores en vivo.
    
    Características:
    - Polling de múltiples competiciones
    - Detección de cambios
    - Callbacks para eventos
    - Persistencia en SQLite
    - Thread-safe
    """
    
    def __init__(self, api_client: FootballDataClient, 
                 competitions: Optional[List[str]] = None,
                 db_path: Optional[str] = None,
                 cache_dir: Optional[str] = None):
        """
        Inicializa el gestor de live scores.
        
        Args:
            api_client: Cliente configurado de Football-Data.org
            competitions: Lista de competiciones a monitorear
            db_path: Ruta a BD SQLite
            cache_dir: Directorio para caché
        """
        # Usar constantes centralizadas si no se especifica
        if db_path is None:
            db_path = LIVE_SCORES_DB_PATH_STR
        if cache_dir is None:
            cache_dir = str(CACHE_DIR)
        self.api_client = api_client
        self.competitions = competitions or DEFAULT_COMPETITIONS
        self.db_path = db_path
        self.cache_dir = Path(cache_dir)
        
        # Crear directorios
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Estado
        self.match_snapshots: Dict[int, MatchSnapshot] = {}
        self.live_matches: Set[int] = set()
        self.callbacks: List[Callable] = []
        
        # Thread control
        self.running = False
        self.polling_thread = None
        self.lock = threading.RLock()
        
        # Inicializar BD
        self._init_database()
        
        logger.info(f"✓ LiveScoresManager inicializado")
        logger.info(f"  Competiciones: {', '.join(self.competitions)}")
        logger.info(f"  BD: {db_path}")
        logger.info(f"  Caché: {cache_dir}")
    
    def _init_database(self):
        """Inicializa base de datos SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de eventos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                data JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(match_id)
            )
        """)
        
        # Tabla de snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_snapshots (
                match_id INTEGER PRIMARY KEY,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                status TEXT NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                competition TEXT,
                minute INTEGER,
                timestamp REAL NOT NULL,
                data JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de matches histórico
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                home_team TEXT,
                away_team TEXT,
                final_score TEXT,
                status TEXT,
                competition TEXT,
                date_start DATETIME,
                date_end DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices para optimizar consultas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_id ON match_events(match_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON match_snapshots(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_competition ON match_snapshots(competition)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON match_snapshots(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON match_events(timestamp)")
        
        conn.commit()
        conn.close()
        
        logger.debug("✓ Base de datos inicializada")
    
    def register_callback(self, callback: Callable):
        """
        Registra un callback para eventos de partidos.
        
        Args:
            callback: Función que recibe (event_type, match_data, event_list)
        """
        self.callbacks.append(callback)
        logger.debug(f"✓ Callback registrado: {callback.__name__}")
    
    def _save_event(self, match_id: int, event: MatchEvent, 
                   match_data: Dict):
        """Guarda evento en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO match_events (match_id, event_type, timestamp, data)
                VALUES (?, ?, ?, ?)
            """, (match_id, event.value, time.time(), json.dumps(match_data)))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error guardando evento: {e}")
    
    def _save_snapshot(self, snapshot: MatchSnapshot):
        """
        Guarda snapshot en base de datos.
        
        OPTIMIZADO:
        - Ignora partidos FINISHED con más de 12 horas de antigüedad
        - Evita acumular datos viejos en la DB
        """
        try:
            # Si el partido está FINISHED, verificar antigüedad
            if snapshot.status == 'FINISHED':
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Buscar timestamp original del partido
                cursor.execute("""
                    SELECT timestamp FROM match_snapshots 
                    WHERE match_id = ?
                """, (snapshot.match_id,))
                row = cursor.fetchone()
                
                if row:
                    original_timestamp = row[0]
                    horas_transcurridas = (time.time() - original_timestamp) / 3600
                    
                    # Si tiene más de 12 horas y está FINISHED, no actualizar
                    if horas_transcurridas > 12:
                        conn.close()
                        logger.debug(f"⏭️ Ignorando partido FINISHED antiguo: {snapshot.match_id}")
                        return
                
                conn.close()
            
            # Guardar/actualizar snapshot
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO match_snapshots
                (match_id, home_team, away_team, status, home_score, away_score,
                 competition, minute, timestamp, data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                snapshot.match_id,
                snapshot.home_team,
                snapshot.away_team,
                snapshot.status,
                snapshot.home_score,
                snapshot.away_score,
                snapshot.competition,
                snapshot.minute,
                snapshot.timestamp,
                json.dumps(snapshot.to_dict())
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error guardando snapshot: {e}")
    
    def _trigger_callbacks(self, event_type: MatchEvent, 
                          match_data: Dict, events: List[MatchEvent]):
        """Dispara callbacks registrados"""
        for callback in self.callbacks:
            try:
                callback(event_type, match_data, events)
            except Exception as e:
                logger.error(f"Error en callback: {e}")
    
    def _process_match(self, match_data: Dict) -> List[MatchEvent]:
        """
        Procesa datos de un partido y detecta cambios.
        
        Args:
            match_data: Datos del partido desde API
        
        Returns:
            Lista de eventos detectados
        """
        match_id = match_data['id']
        
        # Crear snapshot actual
        current = MatchSnapshot(
            match_id=match_id,
            home_team=match_data['homeTeam']['name'],
            away_team=match_data['awayTeam']['name'],
            status=match_data['status'],
            home_score=match_data['score']['fullTime']['home'] or 0,
            away_score=match_data['score']['fullTime']['away'] or 0,
            timestamp=time.time(),
            competition=match_data.get('competition', {}).get('code', 'UNKNOWN'),
            minute=match_data.get('minute'),
            second_half=match_data.get('score', {}).get('halfTime') is not None
        )
        
        # Obtener snapshot anterior
        previous = self.match_snapshots.get(match_id)
        
        # Detectar cambios
        detector = MatchChangeDetection(previous, current)
        events = detector.detect()
        
        # Guardar estado
        with self.lock:
            self.match_snapshots[match_id] = current
            
            if current.status == "LIVE":
                self.live_matches.add(match_id)
            else:
                self.live_matches.discard(match_id)
        
        # Persistir
        self._save_snapshot(current)
        
        # Guardar eventos
        for event in events:
            self._save_event(match_id, event, current.to_dict())
        
        # Disparar callbacks
        for event in events:
            self._trigger_callbacks(event, current.to_dict(), events)
        
        return events
    
    def poll_competition(self, competition: str) -> List[Dict]:
        """
        Realiza polling de una competición.
        
        Args:
            competition: Código de competición (ej: 'PL')
        
        Returns:
            Lista de partidos encontrados
        """
        try:
            logger.debug(f"Polling {competition}...")
            
            # Obtener partidos en vivo y programados
            matches = self.api_client.get_competition_matches(competition)
            
            # Procesar cada partido
            for match in matches:
                self._process_match(match)
            
            return matches
            
        except RateLimitError:
            logger.warning(f"Rate limit alcanzado para {competition}")
            return []
        except FootballAPIError as e:
            logger.error(f"Error polling {competition}: {e}")
            return []
    
    def start_polling(self, interval: int = 30):
        """
        Inicia polling automático en thread separado.
        
        Args:
            interval: Intervalo base entre polls en segundos
        """
        if self.running:
            logger.warning("Polling ya está activo")
            return
        
        self.running = True
        self.polling_thread = threading.Thread(
            target=self._polling_loop,
            args=(interval,),
            daemon=True
        )
        self.polling_thread.start()
        
        logger.info(f"✓ Polling iniciado (intervalo: {interval}s)")
    
    def stop_polling(self):
        """Detiene polling automático"""
        if not self.running:
            return
        
        self.running = False
        
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        
        logger.info("✓ Polling detenido")
    
    def _polling_loop(self, base_interval: int):
        """Loop principal de polling"""
        poll_times = {comp: time.time() for comp in self.competitions}
        
        while self.running:
            try:
                for competition in self.competitions:
                    # Determinar intervalo basado en estado
                    interval = base_interval
                    
                    matches = self.poll_competition(competition)
                    
                    # Ajustar intervalo según partidos en vivo
                    has_live = any(m['status'] == 'LIVE' for m in matches)
                    if has_live:
                        interval = POLL_INTERVALS['LIVE']
                    else:
                        interval = POLL_INTERVALS['SCHEDULED']
                    
                    poll_times[competition] = time.time()
                    
                    # Logging
                    logger.info(
                        f"✓ {competition}: {len(matches)} partidos "
                        f"(próximo poll en {interval}s)"
                    )
                    
                    # Rate limiting: esperar entre competiciones
                    time.sleep(7)
                
                # Esperar antes del siguiente ciclo
                time.sleep(base_interval)
                
            except Exception as e:
                logger.error(f"Error en polling loop: {e}")
                time.sleep(5)
    
    def get_live_matches(self) -> List[Dict]:
        """Retorna partidos actualmente en vivo"""
        with self.lock:
            result = []
            for match_id in self.live_matches:
                if match_id in self.match_snapshots:
                    snapshot = self.match_snapshots[match_id]
                    result.append(snapshot.to_dict())
            return result
    
    def get_match_status(self, match_id: int) -> Optional[Dict]:
        """Obtiene estado actual de un partido"""
        with self.lock:
            snapshot = self.match_snapshots.get(match_id)
            return snapshot.to_dict() if snapshot else None
    
    def get_competition_status(self, competition: str) -> Dict:
        """Obtiene estado resumido de una competición"""
        with self.lock:
            matches = [
                s for s in self.match_snapshots.values()
                if s.competition == competition
            ]
        
        by_status = defaultdict(list)
        for match in matches:
            by_status[match.status].append(match)
        
        return {
            'competition': competition,
            'total_matches': len(matches),
            'live': len(by_status.get('LIVE', [])),
            'scheduled': len(by_status.get('SCHEDULED', [])),
            'finished': len(by_status.get('FINISHED', [])),
            'by_status': {
                status: [m.to_dict() for m in ms]
                for status, ms in by_status.items()
            }
        }
    
    def export_to_json(self, output_file: str):
        """Exporta estado actual a JSON"""
        with self.lock:
            data = {
                'timestamp': datetime.now().isoformat(),
                'live_matches': self.get_live_matches(),
                'competitions': {
                    comp: self.get_competition_status(comp)
                    for comp in self.competitions
                }
            }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"✓ Exportado a {output_file}")
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas de estado actual"""
        with self.lock:
            total = len(self.match_snapshots)
            live = len(self.live_matches)
            
            by_status = defaultdict(int)
            for snapshot in self.match_snapshots.values():
                by_status[snapshot.status] += 1
        
        return {
            'total_matches': total,
            'live_matches': live,
            'by_status': dict(by_status),
            'rate_limit': self.api_client.get_rate_limit_status()
        }


# ========== CALLBACKS PREDEFINIDOS ==========
class DefaultCallbacks:
    """Callbacks predefinidos para eventos"""
    
    @staticmethod
    def log_callback(event: MatchEvent, match_data: Dict, events: List[MatchEvent]):
        """Callback que registra eventos en log"""
        logger.info(
            f"🎯 {event.value}: {match_data['home_team']} "
            f"{match_data['home_score']}-{match_data['away_score']} "
            f"{match_data['away_team']}"
        )
    
    @staticmethod
    def console_callback(event: MatchEvent, match_data: Dict, events: List[MatchEvent]):
        """Callback que imprime en consola"""
        emojis = {
            MatchEvent.MATCH_STARTED: "⚽",
            MatchEvent.GOAL_HOME: "⚪",
            MatchEvent.GOAL_AWAY: "⚫",
            MatchEvent.FULLTIME: "🏁",
            MatchEvent.STATUS_CHANGE: "🔄",
        }
        
        emoji = emojis.get(event, "📍")
        print(
            f"{emoji} {match_data['home_team']} "
            f"{match_data['home_score']}-{match_data['away_score']} "
            f"{match_data['away_team']}"
        )


if __name__ == "__main__":
    print("Live Scores Module cargado")
