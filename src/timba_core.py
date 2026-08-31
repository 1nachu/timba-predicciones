"""
Timba Predictor - Core Engine v2.0
===================================

Motor central de análisis y predicción de partidos de fútbol.
Utiliza Distribución de Poisson para calcular probabilidades.

Características:
- Cálculo de fuerzas de ataque/defensa por equipo
- Predicción de resultados 1X2 y mercados (Over/Under, BTTS)
- Integración con bases de datos locales
- Normalización de nombres de equipos vía utils.shared

Autor: Timba Team
Última actualización: Febrero 2026
"""

# ========== IMPORTS ESTÁNDAR ==========
import gc
import os
import sys
import io
import json
import logging
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, List, Any

# ========== IMPORTS DE TERCEROS ==========
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from scipy.stats import poisson
from urllib3.util.retry import Retry

# Cargar variables desde .env (si existe)
load_dotenv()

# ========== CONFIGURACIÓN DE LOGGING ==========
logger = logging.getLogger(__name__)

# ========== IMPORTAR MÓDULO CYTHON OPTIMIZADO ==========
try:
    from src.timba_fast import predecir_partido_optimizado
    USE_CYTHON = True
    logger.info("✓ Módulo Cython (timba_fast) cargado correctamente")
except ImportError:
    USE_CYTHON = False
    logger.warning("⚠️  Módulo Cython no disponible, usando Python puro")

# ========== IMPORTAR PROVEEDOR DE DATOS ==========
try:
    from db_data_provider import DatabaseDataProvider
    DB_PROVIDER_AVAILABLE = True
    _data_provider = DatabaseDataProvider()
    logger.info("✓ Proveedor de BD inicializado")
except ImportError:
    DB_PROVIDER_AVAILABLE = False
    _data_provider = None
    logger.warning("⚠️  Proveedor de BD no disponible, usando solo CSVs")

# ========== IMPORTAR UTILIDADES COMPARTIDAS ==========
try:
    from utils.shared import (
        get_db_connection,
        normalizar_csv,
        descargar_csv_safe,
        emparejar_equipo,
        encontrar_equipo_similar,
        imprimir_barra,
        ALIAS_TEAMS,
        CHAMPIONS_EQUIPO_LIGA,
        DB_PATH,
        API_CACHE_DB_PATH as API_CACHE_PATH,
        LOGS_DIR,
    )
    from utils.markets import (
        obtener_mejor_recomendacion,
        determinar_prediccion_1x2,
        generar_recomendaciones,
        calcular_semaforo,
        calcular_mercados_adicionales,
        PREDICCION_UMBRAL_GANA,
        PREDICCION_UMBRAL_DOBLE,
    )
except ImportError:
    logger.warning("⚠️  utils.shared no disponible, usando funciones locales")
    from difflib import get_close_matches
    
    ALIAS_TEAMS = {}
    CHAMPIONS_EQUIPO_LIGA = {}
    DB_PATH = Path("data/databases/football_data.db")
    LOGS_DIR = Path("logs")
    
    def normalizar_csv(df):
        df.columns = df.columns.str.strip()
        return df
    
    def emparejar_equipo(nombre_fixture, equipos_validos):
        matches = get_close_matches(nombre_fixture, equipos_validos, n=1, cutoff=0.6)
        return matches[0] if matches else nombre_fixture
    
    def encontrar_equipo_similar(nombre, equipos_validos):
        return get_close_matches(nombre, equipos_validos, n=3, cutoff=0.6)
    
    def imprimir_barra(valor, maximo=100, ancho=25):
        porcentaje = (valor / maximo) * 100 if maximo > 0 else 0
        relleno = int((porcentaje / 100) * ancho)
        barra = '█' * relleno + '░' * (ancho - relleno)
        return f"[{barra}] {porcentaje:.1f}%"
    
    def descargar_csv_safe(url_or_list, timeout=15, usecols=None):
        response = requests.get(url_or_list, timeout=timeout)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text), usecols=usecols)

# ========== DICCIONARIO DE LIGAS ==========
# 7 ligas europeas + Argentina (datos de football-data.co.uk)
LIGAS = {
    1: {
        'nombre': 'Premier League (Inglaterra) - Temporada 26/27',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/E0.csv',
        'codigo': 'E0',
        'bandera': '🏴󠁧󠁢󠁥󠁮󠁧󠁿'
    },
    2: {
        'nombre': 'La Liga (España) - Temporada 26/27',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/SP1.csv',
        'codigo': 'SP1',
        'bandera': '🇪🇸'
    },
    3: {
        'nombre': 'Serie A (Italia) - Temporada 26/27',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/I1.csv',
        'codigo': 'I1',
        'bandera': '🇮🇹'
    },
    4: {
        'nombre': 'Bundesliga (Alemania) - Temporada 26/27',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/D1.csv',
        'codigo': 'D1',
        'bandera': '🇩🇪'
    },
    5: {
        'nombre': 'Ligue 1 (Francia) - Temporada 26/27',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/F1.csv',
        'codigo': 'F1',
        'bandera': '🇫🇷'
    },
    6: {
        'nombre': 'Primeira Liga (Portugal) - Temporada 26/27',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/P1.csv',
        'codigo': 'P1',
        'bandera': '🇵🇹'
    },
    7: {
        'nombre': 'Eredivisie (Países Bajos) - Temporada 26/27',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/N1.csv',
        'codigo': 'N1',
        'bandera': '🇳🇱'
    },
    8: {
        'nombre': 'UEFA Champions League - Temporada 26/27',
        'url': None,
        'codigo': 'CL',
        'es_torneo': True,
        'bandera': '🏆'
    },
    10: {
        'nombre': 'Liga Profesional (Argentina) - Temporada 2026',
        'url': 'https://www.football-data.co.uk/new/ARG.csv',
        'codigo': 'ARG',
        'pais': 'Argentina',
        'bandera': '🇦🇷'
    },
}

# ========== DICCIONARIO DE FIXTURES (CALENDARIOS) ==========
URLS_FIXTURE = {
    1: {'url': 'https://fixturedownload.com/feed/json/epl-2026', 'liga': 'Premier League'},
    2: {'url': 'https://fixturedownload.com/feed/json/la-liga-2026', 'liga': 'La Liga'},
    3: {'url': 'https://fixturedownload.com/feed/json/serie-a-2026', 'liga': 'Serie A'},
    4: {'url': 'https://fixturedownload.com/feed/json/bundesliga-2026', 'liga': 'Bundesliga'},
    5: {'url': 'https://fixturedownload.com/feed/json/ligue-1-2026', 'liga': 'Ligue 1'},
    6: {'url': 'https://fixturedownload.com/feed/json/primeira-liga-2026', 'liga': 'Primeira Liga'},
    7: {'url': 'https://fixturedownload.com/feed/json/eredivisie-2026', 'liga': 'Eredivisie'},
    8: {'url': 'https://fixturedownload.com/feed/json/champions-league-2026', 'liga': 'Champions League'},
    10: {'url': 'https://www.promiedos.com.ar/league/liga-profesional/hc', 'liga': 'Liga Profesional'},
}

# Mapea código CSV (football-data.co.uk) a liga_id interno (LIGAS)
CSV_A_LIGA_ID = {'E0': 1, 'SP1': 2, 'I1': 3, 'D1': 4, 'F1': 5, 'P1': 6, 'N1': 7}


# ========== DESCARGA DE CSV - ELIMINADO CÓDIGO DUPLICADO ==========
# REFACTORIZADO: Se eliminó función descargar_csv_safe() duplicada.
# Usar exclusivamente: from utils.shared import descargar_csv_safe
# Esto centraliza la lógica y evita inconsistencias.

# ========== DICCIONARIO DE ALIAS DE EQUIPOS ==========
# REFACTORIZADO: Se eliminó ALIAS_TEAMS duplicado.
# Usar exclusivamente: from utils.shared import ALIAS_TEAMS
# La fuente canónica está en utils/shared.py


# ========== IMPORTAR MÓDULOS DE CORE Y SCRAPERS ==========
from core.models import (
    MatchStatus,
    PredictionType,
    APIQuotaStatus,
    MatchPrediction,
    MatchFixture,
    MLFeatures,
)
from core.prediction import (
    calcular_fuerzas,
    predecir_partido,
    predecir_partido_champions,
    obtener_h2h,
)
from scrapers.fixtures_scraper import (
    obtener_proximos_partidos,
    _scrape_promiedos,
)


# ========== CACHÉ Y PERSISTENCIA ==========

class APIFootballCache:
    """Gestor de caché SQLite para API-Football"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Inicializa caché"""
        self.db_path = db_path or API_CACHE_PATH
        self._init_db()
    
    def _init_db(self):
        """Inicializa base de datos"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla de fixtures
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fixtures (
                    match_id INTEGER PRIMARY KEY,
                    league_id INTEGER,
                    season INTEGER,
                    round INTEGER,
                    date TEXT,
                    home_team_id INTEGER,
                    home_team TEXT,
                    away_team_id INTEGER,
                    away_team TEXT,
                    status TEXT,
                    venue TEXT,
                    referee TEXT,
                    cached_at DATETIME,
                    UNIQUE(match_id, league_id, season)
                )
            """)
            
            # Tabla de predicciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    match_id INTEGER PRIMARY KEY,
                    home_team TEXT,
                    away_team TEXT,
                    match_date TEXT,
                    prob_home_win REAL,
                    prob_draw REAL,
                    prob_away_win REAL,
                    prob_under_2_5 REAL,
                    prob_over_2_5 REAL,
                    xg_home REAL,
                    xg_away REAL,
                    prediction TEXT,
                    confidence REAL,
                    cached_at DATETIME,
                    FOREIGN KEY(match_id) REFERENCES fixtures(match_id)
                )
            """)
            
            # Tabla de uso de API
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT,
                    cost INTEGER,
                    success BOOLEAN,
                    response_time REAL,
                    timestamp DATETIME,
                    quota_remaining INTEGER
                )
            """)
            
            # Tabla de cuota diaria
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_quota (
                    date DATE PRIMARY KEY,
                    requests_used INTEGER,
                    reset_time TEXT
                )
            """)
            
            conn.commit()
    
    def get_fixture(self, match_id: int) -> Optional[MatchFixture]:
        """Obtiene fixture del caché"""
        with get_db_connection(self.db_path, readonly=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM fixtures WHERE match_id = ?", (match_id,))
            row = cursor.fetchone()
        
        if not row:
            return None
        
        return MatchFixture(**dict(row))
    
    def save_fixture(self, fixture: MatchFixture):
        """Guarda fixture en caché"""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO fixtures
                (match_id, league_id, season, round, date, home_team_id, home_team,
                 away_team_id, away_team, status, venue, referee, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fixture.match_id, fixture.league_id, fixture.season, fixture.round,
                fixture.date, fixture.home_team_id, fixture.home_team,
                fixture.away_team_id, fixture.away_team, fixture.status,
                fixture.venue, fixture.referee, datetime.now(timezone.utc)
            ))
            
            conn.commit()
    
    def get_prediction(self, match_id: int) -> Optional[MatchPrediction]:
        """Obtiene predicción del caché"""
        with get_db_connection(self.db_path, readonly=True) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM predictions WHERE match_id = ?", (match_id,))
            row = cursor.fetchone()
        
        if not row:
            return None
        
        return MatchPrediction(**dict(row))
    
    def save_prediction(self, prediction: MatchPrediction):
        """Guarda predicción en caché"""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO predictions
                (match_id, home_team, away_team, match_date, prob_home_win,
                 prob_draw, prob_away_win, prob_under_2_5, prob_over_2_5,
                 xg_home, xg_away, prediction, confidence, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction.match_id, prediction.home_team, prediction.away_team,
                prediction.match_date, prediction.probability_home_win,
                prediction.probability_draw, prediction.probability_away_win,
                prediction.under_2_5_probability, prediction.over_2_5_probability,
                prediction.expected_goals_home, prediction.expected_goals_away,
                prediction.prediction, prediction.confidence, datetime.now(timezone.utc)
            ))
            
            conn.commit()
    
    def log_api_usage(self, endpoint: str, cost: int, success: bool,
                     response_time: float, quota_remaining: int):
        """Registra uso de API"""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO api_usage_log
                (endpoint, cost, success, response_time, timestamp, quota_remaining)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (endpoint, cost, success, response_time, datetime.now(timezone.utc), quota_remaining))
            
            conn.commit()
    
    def get_today_usage(self) -> int:
        """Obtiene consumo de hoy"""
        today = datetime.now(timezone.utc).date()
        
        with get_db_connection(self.db_path, readonly=True) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT SUM(cost) as total FROM api_usage_log
                WHERE DATE(timestamp) = ? AND success = 1
            """, (today,))
            result = cursor.fetchone()
            
        return (result[0] if result and result[0] else 0)


# ========== CLIENTE API-FOOTBALL ==========

class APIFootballClient:
    """Cliente para API-Football v3"""
    
    def __init__(self, api_key: str):
        """Inicializa cliente"""
        if not api_key or len(api_key) < 10:
            raise ValueError("API Key inválida para API-Football")
        
        self.api_key = api_key
        self.session = self._create_session()
        self.cache = APIFootballCache()
        self.lock = threading.RLock()
        
        logger.info("Cliente API-Football inicializado")
    
    def _create_session(self) -> requests.Session:
        """Crea sesión con retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def check_quota_status(self) -> APIQuotaStatus:
        """Verifica estado de cuota (gratuito)"""
        logger.info("Verificando estado de cuota...")
        
        try:
            start_time = time.time()
            
            response = self.session.get(
                f"{API_BASE_URL}/status",
                headers={"x-apisports-key": self.api_key},
                timeout=10
            )
            
            response_time = time.time() - start_time
            response.raise_for_status()
            
            data = response.json().get("response", {})
            
            status = APIQuotaStatus(
                requests_used=data.get("requests", 0),
                requests_available=data.get("requests_remaining", 0),
                requests_remaining=data.get("requests_remaining", 0),
                reset_date=data.get("results", ""),
                plan_name=data.get("plan", "STARTER")
            )
            
            logger.info(f"Cuota: {status.requests_available} llamadas disponibles")
            
            return status
        
        except Exception as e:
            logger.error(f"Error verificando cuota: {e}")
            raise
    
    def request(self, endpoint: str, params: Dict[str, Any],
                cost: int = 1) -> Dict[str, Any]:
        """Hace request a API con verificación de cuota"""
        with self.lock:
            # Verificar cuota
            quota = self.check_quota_status()
            
            if quota.is_exhausted:
                raise Exception("Cuota diaria agotada (100 llamadas/día)")
            
            if quota.requests_available < cost:
                logger.warning(
                    f"Cuota insuficiente: disponibles {quota.requests_available}, "
                    f"necesarias {cost}"
                )
                raise Exception("Cuota insuficiente para esta solicitud")
            
            # Hacer request
            logger.info(f"Solicitando {endpoint} (costo: {cost})")
            
            try:
                start_time = time.time()
                
                response = self.session.get(
                    f"{API_BASE_URL}{endpoint}",
                    params=params,
                    headers={"x-apisports-key": self.api_key},
                    timeout=30
                )
                
                response_time = time.time() - start_time
                response.raise_for_status()
                
                data = response.json()
                
                # Log de uso
                self.cache.log_api_usage(
                    endpoint=endpoint,
                    cost=cost,
                    success=True,
                    response_time=response_time,
                    quota_remaining=quota.requests_available - cost
                )
                
                logger.info(
                    f"✓ {endpoint} - Tiempo: {response_time:.2f}s "
                    f"- Cuota restante: {quota.requests_available - cost}"
                )
                
                return data
            
            except Exception as e:
                logger.error(f"Error en request: {e}")
                
                self.cache.log_api_usage(
                    endpoint=endpoint,
                    cost=0,
                    success=False,
                    response_time=time.time() - start_time,
                    quota_remaining=quota.requests_available
                )
                
                raise


# ========== ESTRATEGIA DE BATCHING ==========

class BatchFetcher:
    """Fetch batch de fixtures una vez al día"""
    
    def __init__(self, client: APIFootballClient):
        """Inicializa fetcher"""
        self.client = client
        self.cache = client.cache
        self.last_fetch = None
    
    def should_fetch_today(self) -> bool:
        """Verifica si ya se ejecutó hoy"""
        if self.last_fetch is None:
            return True
        
        today_utc = datetime.now(timezone.utc).date()
        fetch_date = self.last_fetch.date()
        
        return today_utc > fetch_date
    
    def fetch_daily_fixtures(self, league_id: int = 39, season: int = 2026) -> List[MatchFixture]:
        """Fetch batch una sola vez al día (00:00 UTC)"""
        logger.info("="*70)
        logger.info("BATCH FETCH: Obteniendo fixtures del día")
        logger.info("="*70)
        
        if not self.should_fetch_today():
            logger.info("✓ Ya se ejecutó batch hoy, usando caché")
            return []
        
        try:
            data = self.client.request(
                endpoint="/fixtures",
                params={
                    "league": league_id,
                    "season": season,
                    "timezone": "UTC"
                },
                cost=FIXTURE_REQUEST_COST
            )
            
            fixtures = []
            
            for match_data in data.get("response", []):
                fixture = self._parse_fixture(match_data)
                self.cache.save_fixture(fixture)
                fixtures.append(fixture)
            
            self.last_fetch = datetime.now(timezone.utc)
            
            logger.info(f"✓ Batch completado: {len(fixtures)} fixtures obtenidos")
            
            return fixtures
        
        except Exception as e:
            logger.error(f"Error en batch fetch: {e}")
            return []
    
    def _parse_fixture(self, data: Dict[str, Any]) -> MatchFixture:
        """Parsea dato de fixture desde API"""
        fixture = data.get("fixture", {})
        league = data.get("league", {})
        teams = data.get("teams", {})
        
        return MatchFixture(
            match_id=fixture.get("id"),
            league_id=league.get("id"),
            season=league.get("season"),
            round=int(league.get("round", "1").split()[-1]),
            date=fixture.get("date"),
            home_team_id=teams.get("home", {}).get("id"),
            home_team=teams.get("home", {}).get("name"),
            away_team_id=teams.get("away", {}).get("id"),
            away_team=teams.get("away", {}).get("name"),
            status=fixture.get("status"),
            venue=fixture.get("venue", {}).get("name", ""),
            referee=data.get("league", {}).get("referee")
        )


# ========== ESTRATEGIA DE PREDICCIONES ==========

class PredictionFetcher:
    """Fetch predicciones 30 minutos antes del inicio"""
    
    def __init__(self, client: APIFootballClient):
        """Inicializa fetcher"""
        self.client = client
        self.cache = client.cache
        self.scheduled_matches = {}
    
    def schedule_prediction_fetch(self, match_id: int, match_date: str,
                                  home_team: str, away_team: str):
        """Agenda fetch de predicción para 30 min antes"""
        match_dt = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
        fetch_time = match_dt - timedelta(minutes=30)
        
        self.scheduled_matches[match_id] = {
            'fetch_time': fetch_time,
            'match_date': match_date,
            'home_team': home_team,
            'away_team': away_team
        }
        
        logger.info(f"Predicción agendada para {home_team} vs {away_team}")
        logger.info(f"  Hora partido: {match_dt.isoformat()}")
        logger.info(f"  Hora fetch: {fetch_time.isoformat()}")
    
    def get_pending_predictions(self) -> List[int]:
        """Obtiene IDs de partidos listos para fetch"""
        now_utc = datetime.now(timezone.utc)
        pending = []
        
        for match_id, data in self.scheduled_matches.items():
            fetch_time = data['fetch_time']
            
            if now_utc >= fetch_time and now_utc < fetch_time + timedelta(minutes=1):
                pending.append(match_id)
        
        return pending
    
    def fetch_prediction(self, match_id: int) -> Optional[MatchPrediction]:
        """Fetch predicción para un partido específico"""
        cached = self.cache.get_prediction(match_id)
        if cached:
            logger.info(f"✓ Predicción en caché para match {match_id}")
            return cached
        
        try:
            logger.info(f"Fetch predicción para match {match_id}...")
            
            data = self.client.request(
                endpoint="/predictions",
                params={"fixture": match_id},
                cost=PREDICTION_REQUEST_COST
            )
            
            predictions = data.get("response", [])
            
            if not predictions:
                logger.warning(f"No predictions available for match {match_id}")
                return None
            
            prediction = self._parse_prediction(match_id, predictions[0])
            self.cache.save_prediction(prediction)
            
            logger.info(f"✓ Predicción obtenida para {prediction.home_team} vs {prediction.away_team}")
            
            return prediction
        
        except Exception as e:
            logger.error(f"Error fetching prediction: {e}")
            return None
    
    def _parse_prediction(self, match_id: int, data: Dict[str, Any]) -> MatchPrediction:
        """Parsea predicción desde API"""
        predictions = data.get("predictions", {})
        teams = data.get("teams", {})
        fixture = data.get("fixture", {})
        
        prob_home = predictions.get("win", {}).get("home", 0)
        prob_draw = predictions.get("draw", 0)
        prob_away = predictions.get("win", {}).get("away", 0)
        
        total = prob_home + prob_draw + prob_away
        if total > 0:
            prob_home /= total
            prob_draw /= total
            prob_away /= total
        
        probs = {'HOME_WIN': prob_home, 'DRAW': prob_draw, 'AWAY_WIN': prob_away}
        prediction_label = max(probs.keys(), key=lambda k: probs[k])
        confidence = probs[prediction_label]
        
        return MatchPrediction(
            match_id=match_id,
            home_team=teams.get("home", {}).get("name", ""),
            away_team=teams.get("away", {}).get("name", ""),
            match_date=fixture.get("date", ""),
            probability_home_win=prob_home,
            probability_draw=prob_draw,
            probability_away_win=prob_away,
            under_2_5_probability=predictions.get("under_over", {}).get("under", 0),
            over_2_5_probability=predictions.get("under_over", {}).get("over", 0),
            expected_goals_home=predictions.get("goals", {}).get("home", 0),
            expected_goals_away=predictions.get("goals", {}).get("away", 0),
            prediction=prediction_label,
            confidence=confidence,
            comparison=data.get("comparison", "")
        )


# ========== EXTRACCIÓN DE FEATURES ==========

class MLFeatureExtractor:
    """Extrae features para modelo ML"""
    
    @staticmethod
    def extract_features(match_id: int, prediction: MatchPrediction) -> MLFeatures:
        """Extrae features matemáticas para modelo ML"""
        xg_diff = prediction.expected_goals_home - prediction.expected_goals_away
        
        if prediction.probability_home_win > max(prediction.probability_draw, prediction.probability_away_win):
            label = "HOME_WIN"
        elif prediction.probability_away_win > max(prediction.probability_draw, prediction.probability_home_win):
            label = "AWAY_WIN"
        else:
            label = "DRAW"
        
        return MLFeatures(
            match_id=match_id,
            home_win_prob=prediction.probability_home_win,
            draw_prob=prediction.probability_draw,
            away_win_prob=prediction.probability_away_win,
            over_2_5_prob=prediction.over_2_5_probability,
            under_2_5_prob=prediction.under_2_5_probability,
            xg_home=prediction.expected_goals_home,
            xg_away=prediction.expected_goals_away,
            xg_diff=xg_diff,
            prediction_label=label,
            prediction_confidence=prediction.confidence,
            last_updated=datetime.now(timezone.utc).isoformat()
        )
    
    @staticmethod
    def features_to_dict(features: MLFeatures) -> Dict[str, Any]:
        """Convierte features a diccionario"""
        return asdict(features)


# ========== FUNCIÓN CACHEADA PARA DATOS HISTÓRICOS ==========
# LRU Cache standalone (no puede usarse directamente en métodos de instancia)
# Cacheamos la carga de datos por liga+temporadas para evitar múltiples lecturas

@lru_cache(maxsize=32)
def _get_cached_historical_data(liga_codigo: str, temporadas: int, url_csv: str) -> pd.DataFrame:
    """
    Función cacheada para obtener datos históricos.
    El decorator @lru_cache mantiene los DataFrames en memoria RAM.
    
    Primera llamada: Carga desde BD/CSV (lento, ~1-3s)
    Llamadas siguientes: Retorna desde caché (instantáneo, ~0.001s)
    
    Args:
        liga_codigo: Código de liga (E0, SP1, D1, etc.)
        temporadas: Número de temporadas a cargar
        url_csv: URL del CSV como identificador único
    
    Returns:
        DataFrame cacheado con datos históricos
    """
    logger.info(f"📥 Cache MISS: Cargando datos para {liga_codigo} ({temporadas} temporadas)")
    
    # Intentar cargar desde BD local primero
    if _data_provider and DB_PROVIDER_AVAILABLE:
        try:
            df = _data_provider.get_smart_data(
                liga_codigo=liga_codigo,
                url_csv=url_csv,
                temporadas=temporadas,
                enrich=True
            )
            logger.info(f"✓ Datos cargados desde BD local: {len(df)} partidos")
            return df
        except Exception as e:
            logger.warning(f"Error con BD local: {e}, usando CSV")
    
    # Fallback a CSV online
    if url_csv:
        # OPTIMIZADO: Solo cargar columnas necesarias para ahorrar RAM
        columnas_necesarias = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 
                               'HS', 'AS', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
                               'HST', 'AST', 'HTHG', 'HTAG']
        df = descargar_csv_safe(url_csv, timeout=15, usecols=columnas_necesarias)
        logger.info(f"✓ Datos cargados desde CSV: {len(df)} partidos")
        return df
    
    raise ValueError(f"No hay fuentes de datos disponibles para {liga_codigo}")


def clear_historical_data_cache():
    """Limpia el caché de datos históricos (útil para forzar recarga)"""
    _get_cached_historical_data.cache_clear()
    logger.info("🗑️ Cache de datos históricos limpiado")


def get_cache_stats() -> dict:
    """Retorna estadísticas del caché LRU"""
    info = _get_cached_historical_data.cache_info()
    return {
        'hits': info.hits,
        'misses': info.misses,
        'maxsize': info.maxsize,
        'currsize': info.currsize,
        'hit_rate': f"{(info.hits / (info.hits + info.misses) * 100):.1f}%" if (info.hits + info.misses) > 0 else "N/A"
    }


# ========== CLASE PRINCIPAL DE TIMBA CORE CON API ==========

class TimbaCoreAPI:
    """Clase principal que centraliza el cálculo con datos de API-Football y BD local"""
    
    def __init__(self, api_key: Optional[str] = None, use_local_db: bool = True):
        """
        Inicializa Timba Core con soporte de API y BD local
        
        Args:
            api_key: API key para API-Football
            use_local_db: Si debe usar la base de datos local prioritariamente
        """
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        self.use_local_db = use_local_db and DB_PROVIDER_AVAILABLE
        self.data_provider = _data_provider if self.use_local_db else None
        self.client = None
        self.batch_fetcher = None
        self.prediction_fetcher = None
        self.feature_extractor = MLFeatureExtractor()
        
        if self.api_key:
            try:
                self.client = APIFootballClient(self.api_key)
                self.batch_fetcher = BatchFetcher(self.client)
                self.prediction_fetcher = PredictionFetcher(self.client)
                logger.info("✓ Timba Core API inicializado correctamente")
            except Exception as e:
                logger.error(f"Error inicializando API: {e}")
        else:
            logger.warning("⚠️  API_FOOTBALL_KEY no configurada, API-Football deshabilitado")
        
        if self.use_local_db:
            logger.info("✓ Modo BD local activado (mayor precisión)")
        else:
            logger.info("ℹ️  Modo CSV online (menor precisión)")
    
    # ========== FUNCIONALIDADES DE DATOS ==========
    
    def get_historical_data(self, liga_codigo: Optional[str] = None, temporadas: int = 3, 
                           url_csv: Optional[str] = None) -> pd.DataFrame:
        """
        Obtiene datos históricos de forma inteligente con caché LRU.
        Prioriza BD local si está disponible.
        
        OPTIMIZADO: Usa @lru_cache para mantener DataFrames en memoria.
        - Primera llamada: ~1-3s (carga desde BD/CSV)
        - Llamadas siguientes: ~0.001s (desde caché RAM)
        
        Args:
            liga_codigo: Código de liga (E0, SP1, D1)
            temporadas: Número de temporadas recientes
            url_csv: URL del CSV como fallback
        
        Returns:
            DataFrame con datos históricos (posiblemente cacheado)
        """
        # Validar parámetros para el caché
        cache_key_liga = liga_codigo or "ALL"
        cache_key_url = url_csv or "NO_URL"
        
        try:
            # Usar función cacheada (standalone para compatibilidad con lru_cache)
            df = _get_cached_historical_data(cache_key_liga, temporadas, cache_key_url)
            logger.debug(f"📊 Datos obtenidos para {liga_codigo}: {len(df)} partidos")
            return df.copy()  # Retornar copia para evitar mutaciones del caché
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            raise
    
    def get_db_stats(self) -> Dict:
        """Obtiene estadísticas de la base de datos"""
        if self.data_provider:
            return self.data_provider.get_db_stats()
        return {'available': False, 'message': 'BD no disponible'}
    
    # ========== FUNCIONALIDADES DE API ==========
    
    def fetch_daily_fixtures(self, league_id: int = 39, season: int = 2026) -> List[MatchFixture]:
        """Obtiene fixtures diarios desde API"""
        if not self.batch_fetcher:
            raise Exception("API-Football no está configurada")
        
        return self.batch_fetcher.fetch_daily_fixtures(league_id, season)
    
    def fetch_prediction(self, match_id: int) -> Optional[MatchPrediction]:
        """Obtiene predicción de un partido"""
        if not self.prediction_fetcher:
            raise Exception("API-Football no está configurada")
        
        return self.prediction_fetcher.fetch_prediction(match_id)
    
    def schedule_predictions(self, fixtures: List[MatchFixture]):
        """Agenda predicciones para una lista de fixtures"""
        if not self.prediction_fetcher:
            raise Exception("API-Football no está configurada")
        
        for fixture in fixtures:
            self.prediction_fetcher.schedule_prediction_fetch(
                match_id=fixture.match_id,
                match_date=fixture.date,
                home_team=fixture.home_team,
                away_team=fixture.away_team
            )
    
    def extract_ml_features(self, match_id: int, prediction: MatchPrediction) -> MLFeatures:
        """Extrae features ML de una predicción"""
        return self.feature_extractor.extract_features(match_id, prediction)
    
    def get_quota_status(self) -> Optional[APIQuotaStatus]:
        """Obtiene estado de cuota de API"""
        if not self.client:
            return None
        
        return self.client.check_quota_status()
    
    def get_usage_today(self) -> int:
        """Obtiene uso de API de hoy"""
        if not self.client:
            return 0
        
        return self.client.cache.get_today_usage()
    
    # ========== FUNCIONALIDADES DE CÁLCULO PRINCIPALES ==========
    
    def calcular_fuerzas(self, df) -> tuple:
        """Calcula fuerzas de equipos usando datos históricos"""
        return calcular_fuerzas(df)
    
    def predecir_partido(self, local: str, visitante: str, fuerzas: dict, 
                        media_liga_local: float, media_liga_visitante: float) -> Optional[dict]:
        """Predice resultado de un partido combinando fuerzas históricas"""
        return predecir_partido(local, visitante, fuerzas, media_liga_local, media_liga_visitante)
    
    def obtener_h2h(self, local: str, visitante: str, df) -> List[dict]:
        """Obtiene histórico de encuentros entre dos equipos"""
        return obtener_h2h(local, visitante, df)
    
    def obtener_proximos_partidos(self, fixture_url: str) -> List[dict]:
        """Obtiene próximos partidos desde URL de fixture"""
        return obtener_proximos_partidos(fixture_url)


# ========== INSTANCIA GLOBAL ==========

# Esta instancia global será usada por app.py, cli.py y otros módulos
timba_api = None

def inicializar_timba_core():
    """Inicializa la instancia global de Timba Core"""
    global timba_api
    timba_api = TimbaCoreAPI()
    return timba_api

def obtener_timba_core() -> TimbaCoreAPI:
    """Obtiene la instancia global de Timba Core"""
    global timba_api
    if timba_api is None:
        timba_api = inicializar_timba_core()
    return timba_api
