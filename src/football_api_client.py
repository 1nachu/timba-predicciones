"""
Football API Client with Rate Limiting
========================================

Cliente HTTP profesional para Football-Data.org con:
- Autenticación X-Auth-Token
- Rate limiting (Leaky Bucket algorithm)
- Reintentos con backoff exponencial
- Caching inteligente
- Logging detallado

Autor: Backend Integration Team
Versión: 1.0.0
Fecha: 30 de Enero de 2026
"""

import time
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from collections import deque
import json
from pathlib import Path
import threading
from functools import wraps

# ========== CONFIGURACIÓN DE LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler('logs/football_api_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ========== ENUMERACIONES ==========
class Competition(Enum):
    """Competiciones soportadas por Football-Data.org"""
    CHAMPIONS_LEAGUE = "CL"
    PREMIER_LEAGUE = "PL"
    PRIMERA_DIVISION = "PD"  # La Liga
    BUNDESLIGA = "BL1"
    SERIE_A = "SA"
    LIGUE_1 = "FL1"
    EREDIVISIE = "DED"
    PRIMEIRA_LIGA = "PPL"
    CHAMPIONS_PLAYOFF = "CLQL"
    WORLD_CUP = "WC"


class MatchStatus(Enum):
    """Estados posibles de un partido"""
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    IN_PLAY = "IN_PLAY"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"


# ========== RATE LIMITING - LEAKY BUCKET ALGORITHM ==========
class LeakyBucket:
    """
    Implementación del algoritmo Leaky Bucket para rate limiting.
    
    Características:
    - Límite: 10 solicitudes por minuto (política Football-Data.org)
    - Pausa mínima: 6 segundos entre llamadas
    - Thread-safe con locks
    - Permite ráfagas pequeñas
    """
    
    def __init__(self, capacity: int = 10, refill_time: int = 60):
        """
        Inicializa el Leaky Bucket.
        
        Args:
            capacity: Número máximo de solicitudes (default: 10)
            refill_time: Tiempo en segundos para reflenar (default: 60)
        """
        self.capacity = capacity
        self.refill_time = refill_time
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()
        self.request_times = deque(maxlen=capacity)
    
    def _refill(self):
        """Rellena tokens basado en el tiempo transcurrido"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calcular tokens a agregar
        tokens_to_add = (elapsed / self.refill_time) * self.capacity
        
        if tokens_to_add > 0:
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
    
    def acquire(self, timeout: int = 60) -> bool:
        """
        Intenta adquirir un token. Si no hay disponibles, espera.
        
        Args:
            timeout: Tiempo máximo de espera en segundos
        
        Returns:
            True si se obtuvo el token, False si timeout
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                self._refill()
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    self.request_times.append(time.time())
                    return True
            
            # Timeout check
            if time.time() - start_time > timeout:
                logger.warning(f"Rate limit timeout ({timeout}s) alcanzado")
                return False
            
            # Esperar 1 segundo antes de reintentar
            time.sleep(1)
    
    def get_wait_time(self) -> float:
        """Retorna tiempo de espera recomendado antes de la próxima solicitud"""
        with self.lock:
            self._refill()
            
            if self.tokens >= 1:
                return 0
            
            # Calcular tiempo hasta el próximo token
            tokens_needed = 1 - self.tokens
            wait_time = (tokens_needed / self.capacity) * self.refill_time
            
            return max(0, wait_time)


class ThrottleDecorator:
    """
    Decorador para rate limiting basado en tiempo fijo.
    Garantiza al menos 6 segundos entre llamadas.
    """
    
    def __init__(self, min_interval: float = 6.0):
        """
        Args:
            min_interval: Intervalo mínimo entre llamadas en segundos
        """
        self.min_interval = min_interval
        self.last_call = 0
        self.lock = threading.Lock()
    
    def __call__(self, func):
        """Decorador para funciones"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                elapsed = time.time() - self.last_call
                
                if elapsed < self.min_interval:
                    sleep_time = self.min_interval - elapsed
                    logger.debug(f"Rate limiting: esperando {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                
                self.last_call = time.time()
            
            return func(*args, **kwargs)
        
        return wrapper


# ========== CLIENTE FOOTBALL-DATA.ORG ==========
class FootballDataClient:
    """
    Cliente HTTP profesional para Football-Data.org
    
    Características:
    - Autenticación con X-Auth-Token
    - Rate limiting robusto (Leaky Bucket)
    - Reintentos automáticos con backoff exponencial
    - Caching local
    - Manejo completo de errores
    - Logging detallado
    """
    
    BASE_URL = "https://api.football-data.org/v4"
    
    def __init__(self, api_key: str, rate_limit_requests: int = 10, 
                 rate_limit_window: int = 60, use_cache: bool = True):
        """
        Inicializa el cliente.
        
        Args:
            api_key: Token de autenticación de Football-Data.org
            rate_limit_requests: Número máximo de solicitudes (default: 10)
            rate_limit_window: Ventana de tiempo en segundos (default: 60)
            use_cache: Usar caching local (default: True)
        """
        self.api_key = api_key
        self.use_cache = use_cache
        self.cache = {}
        self.cache_expiry = {}
        
        # Rate limiting
        self.bucket = LeakyBucket(capacity=rate_limit_requests, 
                                 refill_time=rate_limit_window)
        
        # Session con reintentos
        self.session = self._create_session()
        
        logger.info(f"✓ Cliente Football-Data.org inicializado")
        logger.info(f"  Rate limit: {rate_limit_requests} req/{rate_limit_window}s")
        logger.info(f"  Caching: {'habilitado' if use_cache else 'deshabilitado'}")
    
    def _create_session(self) -> requests.Session:
        """Crea sesión HTTP con reintentos automáticos"""
        session = requests.Session()
        
        # Configurar reintentos (usando allowed_methods en lugar de method_whitelist)
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Headers por defecto
        session.headers.update({
            "X-Auth-Token": self.api_key,
            "User-Agent": "Timba-Predictor/1.0"
        })
        
        return session
    
    def _get_cache_key(self, endpoint: str, params: Dict | None = None) -> str:
        """Genera clave de caché"""
        param_str = json.dumps(params or {}, sort_keys=True)
        return f"{endpoint}:{param_str}"
    
    def _is_cache_valid(self, cache_key: str, ttl: int = 300) -> bool:
        """Verifica si el caché es válido"""
        if cache_key not in self.cache_expiry:
            return False
        
        if time.time() > self.cache_expiry[cache_key]:
            del self.cache[cache_key]
            del self.cache_expiry[cache_key]
            return False
        
        return True
    
    def request(self, method: str, endpoint: str, params: Dict | None = None, 
               cache_ttl: int = 300, force_refresh: bool = False) -> Dict:
        """
        Realiza solicitud HTTP a Football-Data.org.
        
        Args:
            method: GET, POST, etc
            endpoint: Endpoint sin base URL (ej: /competitions/PL/matches)
            params: Parámetros de query
            cache_ttl: Tiempo de caché en segundos (0 = sin caché)
            force_refresh: Forzar actualización (ignorar caché)
        
        Returns:
            Respuesta JSON
        
        Raises:
            FootballAPIError: Si hay error en la solicitud
        """
        
        # Verificar caché
        if not force_refresh and self.use_cache and cache_ttl > 0:
            cache_key = self._get_cache_key(endpoint, params)
            if self._is_cache_valid(cache_key):
                logger.debug(f"✓ Caché hit: {endpoint}")
                return self.cache[cache_key]
        
        # Rate limiting
        wait_time = self.bucket.get_wait_time()
        if wait_time > 0:
            logger.debug(f"Rate limit: esperando {wait_time:.2f}s")
            time.sleep(wait_time)
        
        # Esperar a que haya token disponible
        if not self.bucket.acquire(timeout=60):
            raise FootballAPIError("Rate limit: no se pudo obtener token después de 60s")
        
        # Construir URL
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            logger.debug(f"→ {method} {url} (params: {params})")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=10
            )
            
            # Manejar errores HTTP
            if response.status_code == 429:
                raise RateLimitError("Rate limit alcanzado (429 Too Many Requests)")
            elif response.status_code == 401:
                raise AuthenticationError("API Key inválida (401 Unauthorized)")
            elif response.status_code == 403:
                raise AuthorizationError("Acceso prohibido (403 Forbidden)")
            elif response.status_code == 404:
                raise NotFoundError(f"Recurso no encontrado (404): {endpoint}")
            elif response.status_code >= 500:
                raise ServerError(f"Error del servidor ({response.status_code})")
            
            response.raise_for_status()
            
            data = response.json()
            
            # Guardar en caché
            if self.use_cache and cache_ttl > 0:
                cache_key = self._get_cache_key(endpoint, params)
                self.cache[cache_key] = data
                self.cache_expiry[cache_key] = time.time() + cache_ttl
                logger.debug(f"✓ Caché guardado: {endpoint} (TTL: {cache_ttl}s)")
            
            logger.debug(f"← {response.status_code} OK")
            return data
            
        except requests.exceptions.Timeout:
            raise FootballAPIError(f"Timeout en solicitud a {endpoint}")
        except requests.exceptions.ConnectionError as e:
            raise FootballAPIError(f"Error de conexión: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise FootballAPIError(f"Error en solicitud: {str(e)}")
    
    def get_competitions(self, filters: Dict | None = None) -> List[Dict]:
        """
        Obtiene lista de competiciones.
        
        Args:
            filters: Filtros opcionales (plan, código, etc)
        
        Returns:
            Lista de competiciones
        """
        response = self.request(
            "GET",
            "/competitions",
            params=filters or {},
            cache_ttl=3600  # 1 hora
        )
        
        return response.get('competitions', [])
    
    def get_matches(self, competition: str | None = None, status: str | None = None,
                   date_from: str | None = None, date_to: str | None = None) -> List[Dict]:
        """
        Obtiene partidos filtrando por competición y fecha.
        
        Args:
            competition: Código de competición (ej: 'PL')
            status: Estado del partido (SCHEDULED, LIVE, FINISHED, etc)
            date_from: Fecha desde (YYYY-MM-DD)
            date_to: Fecha hasta (YYYY-MM-DD)
        
        Returns:
            Lista de partidos
        """
        endpoint = "/matches"
        params = {}
        
        if competition:
            params['competitions'] = competition
        if status:
            params['status'] = status
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        
        # Live scores no se cachean
        cache_ttl = 60 if status == "LIVE" else 300
        
        response = self.request(
            "GET",
            endpoint,
            params=params,
            cache_ttl=cache_ttl,
            force_refresh=(status == "LIVE")
        )
        
        return response.get('matches', [])
    
    def get_live_matches(self) -> List[Dict]:
        """
        Obtiene TODOS los partidos en VIVO en este momento.
        
        Returns:
            Lista de partidos en vivo
        """
        return self.get_matches(status="LIVE")
    
    def get_competition_matches(self, competition: str, 
                               status: str | None = None) -> List[Dict]:
        """
        Obtiene partidos de una competición específica.
        
        Args:
            competition: Código de competición (ej: 'PL', 'CL')
            status: Estado opcional
        
        Returns:
            Lista de partidos
        """
        endpoint = f"/competitions/{competition}/matches"
        params = {}
        
        if status:
            params['status'] = status
        
        cache_ttl = 60 if status == "LIVE" else 300
        
        response = self.request(
            "GET",
            endpoint,
            params=params,
            cache_ttl=cache_ttl,
            force_refresh=(status == "LIVE")
        )
        
        return response.get('matches', [])
    
    def get_match_detail(self, match_id: int) -> Dict:
        """
        Obtiene detalles completos de un partido.
        
        Args:
            match_id: ID del partido
        
        Returns:
            Detalles del partido (includes, head-to-head, etc)
        """
        response = self.request(
            "GET",
            f"/matches/{match_id}",
            cache_ttl=0  # No cachear detalles de partidos
        )
        
        return response
    
    def get_team_stats(self, team_id: int) -> Dict:
        """
        Obtiene estadísticas de un equipo.
        
        Args:
            team_id: ID del equipo
        
        Returns:
            Estadísticas del equipo
        """
        response = self.request(
            "GET",
            f"/teams/{team_id}",
            cache_ttl=3600  # 1 hora
        )
        
        return response
    
    def get_finished_matches(self, competition: str, days_back: int = 7) -> List[Dict]:
        """
        Obtiene partidos FINALIZADOS de una competición en los últimos N días.
        
        Args:
            competition: Código de competición (ej: 'PL', 'PD', 'BL1')
            days_back: Días hacia atrás a buscar (default: 7)
        
        Returns:
            Lista de partidos terminados con scores
        """
        from datetime import datetime, timedelta
        
        date_to = datetime.now().strftime('%Y-%m-%d')
        date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        endpoint = f"/competitions/{competition}/matches"
        params = {
            'status': 'FINISHED',
            'dateFrom': date_from,
            'dateTo': date_to
        }
        
        response = self.request(
            "GET",
            endpoint,
            params=params,
            cache_ttl=300  # Cachear 5 min (partidos ya finalizados)
        )
        
        return response.get('matches', [])
    
    def clear_cache(self):
        """Limpia el caché de solicitudes"""
        self.cache.clear()
        self.cache_expiry.clear()
        logger.info("✓ Caché limpiado")
    
    def get_rate_limit_status(self) -> Dict:
        """Retorna estado actual del rate limiting"""
        return {
            'available_tokens': self.bucket.tokens,
            'capacity': self.bucket.capacity,
            'refill_time': self.bucket.refill_time,
            'wait_time': self.bucket.get_wait_time(),
            'cache_entries': len(self.cache)
        }


# ========== EXCEPCIONES ==========
class FootballAPIError(Exception):
    """Excepción base para errores de la API de Football-Data.org.
    
    Esta es la clase padre de todas las excepciones específicas de la API.
    Capturar esta excepción capturará cualquier error relacionado con la API.
    
    Attributes:
        message: Descripción del error
        status_code: Código HTTP de la respuesta (si aplica)
        response: Respuesta completa del servidor (si aplica)
    
    Example:
        try:
            client.get_matches()
        except FootballAPIError as e:
            logger.error(f"Error de API: {e}")
    """
    
    def __init__(self, message: str = "Error en la API de Football", 
                 status_code: int | None = None, response: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class RateLimitError(FootballAPIError):
    """Error lanzado cuando se excede el límite de solicitudes por minuto/día.
    
    La API de Football-Data.org tiene límites de 10 req/min (free tier).
    Esta excepción incluye el tiempo de espera recomendado.
    
    Attributes:
        retry_after: Segundos a esperar antes de reintentar
    
    Example:
        try:
            client.get_matches()
        except RateLimitError as e:
            time.sleep(e.retry_after or 60)
    """
    
    def __init__(self, message: str = "Límite de solicitudes excedido", 
                 retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(message, status_code=429)


class AuthenticationError(FootballAPIError):
    """Error lanzado cuando la API Key es inválida o no está configurada.
    
    Verificar:
    1. Que la variable FOOTBALL_DATA_API_KEY esté configurada
    2. Que la API Key sea válida en football-data.org
    3. Que la API Key no haya expirado o sido revocada
    
    Example:
        try:
            client.get_matches()
        except AuthenticationError:
            print("Verificar API Key en .env")
    """
    
    def __init__(self, message: str = "API Key inválida o no configurada"):
        super().__init__(message, status_code=401)


class AuthorizationError(FootballAPIError):
    """Error lanzado cuando la API Key no tiene permisos para el recurso.
    
    Algunos endpoints requieren suscripción de pago.
    Verificar el plan de suscripción en football-data.org.
    
    Example:
        try:
            client.get_premium_stats()
        except AuthorizationError:
            print("Este endpoint requiere suscripción premium")
    """
    
    def __init__(self, message: str = "Sin permisos para este recurso"):
        super().__init__(message, status_code=403)


class NotFoundError(FootballAPIError):
    """Error lanzado cuando el recurso solicitado no existe.
    
    Causas comunes:
    - ID de partido/equipo/competición inválido
    - La competición/temporada no está disponible
    - El endpoint no existe
    
    Example:
        try:
            client.get_match(match_id=99999999)
        except NotFoundError:
            print("Partido no encontrado")
    """
    
    def __init__(self, message: str = "Recurso no encontrado", resource_id: int | None = None):
        self.resource_id = resource_id
        super().__init__(message, status_code=404)


class ServerError(FootballAPIError):
    """Error lanzado cuando el servidor de la API tiene problemas internos.
    
    Acciones recomendadas:
    1. Esperar unos segundos y reintentar
    2. Verificar el estado de la API en status.football-data.org
    3. Si persiste, reportar el problema
    
    Example:
        try:
            client.get_matches()
        except ServerError:
            time.sleep(30)
            client.get_matches()  # Reintentar
    """
    
    def __init__(self, message: str = "Error interno del servidor"):
        super().__init__(message, status_code=500)


# ========== UTILIDADES ==========
def validate_api_key(api_key: str) -> bool:
    """
    Valida que la API Key sea válida.
    
    Args:
        api_key: API Key a validar
    
    Returns:
        True si es válida
    """
    if not api_key:
        return False
    
    if len(api_key) < 10:
        return False
    
    return True


if __name__ == "__main__":
    # Ejemplo de uso
    from dotenv import load_dotenv
    
    # Cargar variables de entorno desde .env
    load_dotenv()
    
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "demo_key")
    
    if not validate_api_key(api_key):
        print("❌ API Key inválida o no configurada")
        print("Configura la variable de entorno: FOOTBALL_DATA_API_KEY")
    else:
        print("✓ API Key válida")
        
        # Crear cliente
        client = FootballDataClient(api_key)
        
        # Ver estado de rate limiting
        status = client.get_rate_limit_status()
        print("\n📊 Estado de Rate Limiting:")
        print(f"  Tokens disponibles: {status['available_tokens']:.2f}/{status['capacity']}")
        print(f"  Tiempo de espera: {status['wait_time']:.2f}s")
        print(f"  Entradas en caché: {status['cache_entries']}")
