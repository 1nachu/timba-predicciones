"""
Utilidades compartidas para Timba Predictor v2
==============================================

Módulo centralizado con:
- Constantes de rutas y configuración
- Diccionario de alias de equipos (7 ligas europeas + Liga Argentina)
- Funciones de normalización CSV y descarga segura
- Utilidades de fuzzy matching para nombres de equipos

Autor: Timba Team
Última actualización: Febrero 2026
"""

import os
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import io
import requests
from difflib import get_close_matches

# ========== CONFIGURACIÓN DE LOGGING ==========
logger = logging.getLogger(__name__)

# ========== RUTAS CENTRALIZADAS ==========
# Directorio raíz del proyecto (un nivel arriba de src/)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Rutas de directorios
DATA_DIR = PROJECT_ROOT / "data"
DATABASES_DIR = DATA_DIR / "databases"
CACHE_DIR = DATA_DIR / "live_scores_cache"
LOGS_DIR = PROJECT_ROOT / "logs"

# ========== ARCHIVOS DE BASE DE DATOS ==========
# NOTA: TODOS los archivos .db DEBEN estar en data/databases/
# Esto centraliza la persistencia y facilita backups

# Base de datos principal (datos históricos del ETL)
DB_PATH = DATABASES_DIR / "football_data.db"

# Caché de API-Football (predicciones externas)
API_CACHE_DB_PATH = DATABASES_DIR / "api_football_cache.db"

# Base de datos del normalizador de equipos
TEAM_NORMALIZER_DB_PATH = DATABASES_DIR / "team_normalizer.db"

# Base de datos de live scores (partidos en vivo)
LIVE_SCORES_DB_PATH = DATABASES_DIR / "live_scores.db"

# Crear directorios si no existen
DATABASES_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ========== CONSTANTES DE CONEXIÓN ==========
# String de conexión SQLite por defecto
SQLITE_CONNECTION_STRING = f"sqlite:///{DB_PATH}"

# Rutas absolutas como strings (para módulos que requieren str)
DB_PATH_STR = str(DB_PATH)
TEAM_NORMALIZER_DB_PATH_STR = str(TEAM_NORMALIZER_DB_PATH)
LIVE_SCORES_DB_PATH_STR = str(LIVE_SCORES_DB_PATH)

# ========== CONFIGURACIÓN DE API ==========
FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk"
FOOTBALL_API_BASE_URL = "https://api.football-data.org/v4"

# ========== TEMPORADA ACTUAL ==========
CURRENT_SEASON = "2526"  # 2025-26

# ========== DICCIONARIO DE ALIAS DE EQUIPOS ==========
# Ligas con fuentes de datos confiables (7 europeas + Argentina)
ALIAS_TEAMS = {
    # --- PREMIER LEAGUE (E0) ---
    "Manchester United": "Man United", "Man Utd": "Man United", "Manchester United FC": "Manchester United",
    "Manchester City": "Man City", "Manchester City FC": "Man City",
    "Arsenal FC": "Arsenal",
    "Chelsea FC": "Chelsea",
    "Liverpool FC": "Liverpool",
    "Aston Villa FC": "Aston Villa",
    "Tottenham Hotspur": "Tottenham", "Spurs": "Tottenham",
    "Wolverhampton Wanderers": "Wolves", "Wolverhampton": "Wolves",
    "Nottingham Forest": "Nott'm Forest",
    "Brighton & Hove Albion": "Brighton",
    "Newcastle United": "Newcastle",
    "West Ham United": "West Ham",
    "Sheffield United": "Sheffield United",
    "AFC Bournemouth": "Bournemouth",
    "Leicester City": "Leicester",
    "Ipswich Town": "Ipswich",

    # --- LA LIGA (SP1) ---
    "Real Madrid CF": "Real Madrid",
    "FC Barcelona": "Barcelona",
    "Atleti": "Ath Madrid", "Atletico Madrid": "Ath Madrid", "Atlético de Madrid": "Ath Madrid", "Atletico de Madrid": "Ath Madrid", "Club Atlético de Madrid": "Ath Madrid",
    "Athletic Club": "Ath Bilbao", "Athletic Bilbao": "Ath Bilbao",
    "Real Betis": "Betis", "Real Betis Balompié": "Betis",
    "Celta de Vigo": "Celta", "RC Celta": "Celta",
    "RCD Mallorca": "Mallorca",
    "Rayo Vallecano": "Vallecano",
    "Real Sociedad": "Sociedad",
    "Deportivo Alavés": "Alaves", "Alavés": "Alaves", "Deportivo Alaves": "Alaves",
    "RCD Espanyol de Barcelona": "Espanol", "Espanyol": "Espanol",
    "Villarreal CF": "Villarreal",
    "CA Osasuna": "Osasuna",
    "Getafe CF": "Getafe",
    "UD Las Palmas": "Las Palmas",

    # --- BUNDESLIGA (D1) ---
    "Bayer 04 Leverkusen": "Leverkusen", "Bayer Leverkusen": "Leverkusen",
    "Borussia Dortmund": "Dortmund",
    "Borussia Monchengladbach": "M'gladbach", "Borussia Mönchengladbach": "M'gladbach",
    "Eintracht Frankfurt": "Ein Frankfurt",
    "Bayern Munich": "Bayern Munich", "FC Bayern München": "Bayern Munich", "Bayern München": "Bayern Munich",
    "VfB Stuttgart": "Stuttgart",
    "VfL Wolfsburg": "Wolfsburg",
    "Mainz 05": "Mainz", "1. FSV Mainz 05": "Mainz",
    "SV Werder Bremen": "Werder Bremen",
    "Sport-Club Freiburg": "Freiburg", "SC Freiburg": "Freiburg",
    "RB Leipzig": "RB Leipzig", "RasenBallsport Leipzig": "RB Leipzig",
    "1. FC Union Berlin": "Union Berlin",
    "FC Augsburg": "Augsburg",
    "TSG 1899 Hoffenheim": "Hoffenheim", "TSG Hoffenheim": "Hoffenheim",

    # --- SERIE A (I1) ---
    "Internazionale": "Inter", "Inter Milan": "Inter", "FC Internazionale Milano": "Inter",
    "AC Milan": "Milan",
    "AS Roma": "Roma",
    "Hellas Verona": "Verona", "Hellas Verona FC": "Verona",
    "SSC Napoli": "Napoli",
    "Juventus FC": "Juventus",
    "SS Lazio": "Lazio",
    "ACF Fiorentina": "Fiorentina",
    "Atalanta BC": "Atalanta",
    "Bologna FC 1909": "Bologna",
    "Torino FC": "Torino",

    # --- LIGUE 1 (F1) ---
    "Paris Saint-Germain FC": "Paris SG", "Paris Saint-Germain": "Paris SG", "Paris SG": "Paris SG", "PSG": "Paris SG",
    "Olympique de Marseille": "Marseille", "Olympique Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon", "Olympique Lyon": "Lyon",
    "AS Monaco FC": "Monaco", "AS Monaco": "Monaco",
    "Stade Rennais FC": "Rennes", "Stade Rennais": "Rennes",
    "RC Lens": "Lens",
    "Havre Athletic Club": "Le Havre", "Le Havre AC": "Le Havre",
    "Stade Brestois 29": "Brest",
    "LOSC Lille": "Lille", "Lille OSC": "Lille",
    "OGC Nice": "Nice",
    "RC Strasbourg Alsace": "Strasbourg",

    # --- EREDIVISIE (N1) ---
    "AFC Ajax": "Ajax",
    "PSV": "PSV Eindhoven", "PSV Eindhoven": "PSV Eindhoven",
    "AZ": "AZ Alkmaar",
    "FC Twente": "Twente",
    "FC Utrecht": "Utrecht",
    "FC Groningen": "Groningen",
    "FC Volendam": "Volendam",
    "PEC Zwolle": "Zwolle",
    "Feyenoord Rotterdam": "Feyenoord",
    "sc Heerenveen": "Heerenveen", "SC Heerenveen": "Heerenveen",
    "Heracles Almelo": "Heracles",
    "N.E.C. Nijmegen": "Nijmegen", "NEC Nijmegen": "Nijmegen", "NEC": "Nijmegen",
    "Fortuna Sittard": "For Sittard",
    "Excelsior Rotterdam": "Excelsior",

    # --- PRIMEIRA LIGA (P1) ---
    "FC Porto": "Porto",
    "Sporting CP": "Sp Lisbon", "Sporting Lisbon": "Sp Lisbon", "Sporting": "Sp Lisbon",
    "SL Benfica": "Benfica", "Benfica": "Benfica",
    "SC Braga": "Braga", "Sporting Braga": "Braga",
    "Vitória SC": "Guimaraes", "Vitória Guimarães": "Guimaraes",
    "Gil Vicente FC": "Gil Vicente",
    "CD Santa Clara": "Santa Clara",
    "Boavista FC": "Boavista",
    "FC Famalicão": "Famalicao", "Famalicão": "Famalicao",
    "Moreirense FC": "Moreirense",
    "Rio Ave FC": "Rio Ave",
    "Casa Pia AC": "Casa Pia",
    "FC Arouca": "Arouca",
    "GD Estoril Praia": "Estoril",
    "Estrela Amadora": "Estrela",

    # --- LIGA PROFESIONAL ARGENTINA (ARG) ---
    # Mapeo: Promiedos/API-Football → football-data.co.uk
    "Argentinos Juniors": "Argentinos Jrs",
    "Arsenal de Sarandí": "Arsenal Sarandi", "Arsenal Sarandi": "Arsenal Sarandi",
    "Atlético Rafaela": "Atl. Rafaela", "Atletico Rafaela": "Atl. Rafaela",
    "Atlético Tucumán": "Atl. Tucuman", "Atletico Tucuman": "Atl. Tucuman",
    "Central Córdoba": "Central Cordoba", "Central Cordoba SdE": "Central Cordoba",
    "Colón de Santa Fe": "Colon Santa Fe", "Colon": "Colon Santa Fe", "Colón": "Colon Santa Fe",
    "Deportivo Riestra": "Dep. Riestra", "Riestra": "Dep. Riestra",
    "Estudiantes de La Plata": "Estudiantes L.P.", "Estudiantes LP": "Estudiantes L.P.", "Estudiantes": "Estudiantes L.P.",
    "Gimnasia La Plata": "Gimnasia L.P.", "Gimnasia LP": "Gimnasia L.P.", "Gimnasia y Esgrima LP": "Gimnasia L.P.",
    "Gimnasia de Mendoza": "Gimnasia Mendoza", "Gimnasia y Esgrima de Mendoza": "Gimnasia Mendoza",
    "Huracán": "Huracan",
    "Independiente Rivadavia": "Ind. Rivadavia",
    "Lanús": "Lanus",
    "Newell's Old Boys": "Newells Old Boys", "Newells": "Newells Old Boys",
    "San Martín de San Juan": "San Martin S.J.", "San Martin SJ": "San Martin S.J.",
    "San Martín de Tucumán": "San Martin T.", "San Martin Tucuman": "San Martin T.",
    "Sarmiento de Junín": "Sarmiento Junin", "Sarmiento": "Sarmiento Junin",
    "Talleres de Córdoba": "Talleres Cordoba", "Talleres": "Talleres Cordoba",
    "Unión de Santa Fe": "Union de Santa Fe", "Union": "Union de Santa Fe", "Unión": "Union de Santa Fe",
    "Vélez Sarsfield": "Velez Sarsfield", "Velez": "Velez Sarsfield",
}


# ========== MAPEOS PARA CHAMPIONS LEAGUE ==========
# Mapea nombres aproximados de equipos (para selector UI) a la liga doméstica (código CSV).
# Los nombres no necesitan ser exactos; emparejar_equipo() hará fuzzy matching.
CHAMPIONS_EQUIPO_LIGA = {
    #Premier League (E0)
    'Arsenal': 'E0',
    'Chelsea': 'E0',
    'Manchester City': 'E0',
    'Liverpool': 'E0',
    'Manchester United': 'E0',
    'Newcastle United': 'E0',
    'Tottenham': 'E0',

    #La Liga (SP1)
    'Real Madrid': 'SP1',
    'Barcelona': 'SP1',
    'Atleti': 'SP1',

    #Bundesliga (D1)
    'Bayern Munich': 'D1',
    'Borussia Dortmund': 'D1',
    'Bayern Leverkusen': 'D1',

    #Serie A (I1)
    'Juventus': 'I1',
    'AC Milan': 'I1',
    'Inter Milan': 'I1',
    'Atalanta': 'I1',

    #Ligue 1 (F1)
    'PSG': 'F1',
    'Lyon': 'F1',

    #Primeira Liga (P1)
    'Benfica': 'P1',
    'Porto': 'P1',
    'Sporting': 'P1',

    #Eredivisie (N1)
    'Ajax': 'N1',
    'PSV': 'N1',
}


# ========== FUNCIONES DE NORMALIZACIÓN ==========

def normalizar_csv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas de CSV heterogéneos.
    
    Soporta formatos de:
    - football-data.co.uk (europeo estándar)
    - football-data.co.uk/new/ (Argentina, Brasil, etc.)
    - fixturedownload.com
    - footballcsv (GitHub)
    
    Args:
        df: DataFrame crudo
    
    Returns:
        DataFrame con columnas estandarizadas
    """
    # Limpiar nombres de columnas (quitar BOM y espacios)
    df.columns = df.columns.str.replace('ï»¿', '').str.strip()
    
    # Mapeo de columnas: formato_alterno → formato_estandar
    rename_map = {
        # Nombres de equipos
        'Team 1': 'HomeTeam', 'Team 2': 'AwayTeam',
        'Team1': 'HomeTeam', 'Team2': 'AwayTeam',
        'Home Team': 'HomeTeam', 'Away Team': 'AwayTeam',
        'home': 'HomeTeam', 'away': 'AwayTeam',
        'Home': 'HomeTeam', 'Away': 'AwayTeam',  # Argentina/Brasil format
        
        # Goles
        'HG': 'FTHG', 'AG': 'FTAG',  # Argentina/Brasil format
        
        # Resultado
        'Res': 'FTR',  # Argentina/Brasil format
        'Result': 'FTR',
        
        # Odds de cierre → Odds estándar (Argentina usa closing odds)
        'B365CH': 'B365H', 'B365CD': 'B365D', 'B365CA': 'B365A',
        'PSCH': 'PSH', 'PSCD': 'PSD', 'PSCA': 'PSA',
        'MaxCH': 'MaxH', 'MaxCD': 'MaxD', 'MaxCA': 'MaxA',
        'AvgCH': 'AvgH', 'AvgCD': 'AvgD', 'AvgCA': 'AvgA',
        
        # Otros
        'Date': 'Date', 'Score': 'FT',
        'Season': 'Temporada',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    
    # Parsear score si viene como "X-Y"
    if 'FT' in df.columns and 'FTHG' not in df.columns:
        try:
            ft_split = df['FT'].astype(str).str.split('-', expand=True)
            if ft_split.shape[1] >= 2:
                df['FTHG'] = pd.to_numeric(ft_split[0], errors='coerce')
                df['FTAG'] = pd.to_numeric(ft_split[1], errors='coerce')
        except Exception:
            pass
    
    # Asegurar columnas mínimas requeridas
    required_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0 if col in ['FTHG', 'FTAG'] else ''
    
    return df


def descargar_csv_safe(url_or_list, timeout: int = 15, usecols: Optional[list] = None) -> pd.DataFrame:
    """
    Descarga un CSV desde una URL o lista de URLs alternativas.
    
    Args:
        url_or_list: URL única o lista de URLs para intentar
        timeout: Timeout en segundos
        usecols: Lista de columnas a cargar (None = todas). Para optimizar RAM.
                 Si las columnas no existen, se cargan todas automáticamente.
    
    Returns:
        DataFrame con datos normalizados
    
    Raises:
        ValueError: Si no se pudo descargar de ninguna URL
    """
    urls = []
    if isinstance(url_or_list, (list, tuple)):
        urls = list(url_or_list)
    elif isinstance(url_or_list, str):
        urls = [url_or_list]
    else:
        raise ValueError("url_or_list debe ser str o lista de URLs")

    headers = {'User-Agent': 'Mozilla/5.0 (Timba Predictor/2.0)'}
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            content = response.content
            
            # Decodificar con fallback
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('latin1')
                except UnicodeDecodeError:
                    text = content.decode('utf-8', errors='replace')
            
            # Intentar cargar con usecols para optimizar RAM
            # Si falla (columnas no existen), cargar todo el CSV
            df = None
            if usecols:
                try:
                    df = pd.read_csv(io.StringIO(text), usecols=usecols)
                except ValueError as e:
                    # Columnas no encontradas (ej: CSV de Argentina tiene formato diferente)
                    logger.debug(f"usecols falló ({e}), cargando todas las columnas")
                    df = pd.read_csv(io.StringIO(text))
            else:
                df = pd.read_csv(io.StringIO(text))
            
            if df is None or df.empty:
                logger.warning(f"CSV vacío desde {url}")
                continue
            
            df = normalizar_csv(df)
            logger.info(f"✓ Descargados {len(df)} registros desde {url[:50]}...")
            return df
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout descargando {url}")
            continue
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP Error {e.response.status_code} para {url}")
            continue
        except Exception as e:
            logger.warning(f"Error descargando {url}: {e}")
            continue

    raise ValueError("No se pudo descargar CSV desde ninguna URL")


# ========== FUNCIONES DE MATCHING ==========

def emparejar_equipo(nombre_fixture: str, equipos_validos: list) -> str:
    """
    Empareja el nombre del equipo con el más similar en la BD.
    
    Estrategia (en orden):
    1. Buscar en ALIAS_TEAMS (mapeo exacto)
    2. Fuzzy matching con difflib (cutoff=0.6)
    3. Retornar nombre original si no hay match
    
    Args:
        nombre_fixture: Nombre del equipo desde fixture/API
        equipos_validos: Lista de nombres válidos en datos históricos
    
    Returns:
        Nombre normalizado o el original si no hay match
    """
    if not nombre_fixture or not equipos_validos:
        return nombre_fixture
    
    # Paso 1: Buscar en ALIAS_TEAMS
    if nombre_fixture in ALIAS_TEAMS:
        nombre_normalizado = ALIAS_TEAMS[nombre_fixture]
        if nombre_normalizado in equipos_validos:
            return nombre_normalizado
    
    # Paso 2: Buscar alias inverso
    for alias_key, alias_value in ALIAS_TEAMS.items():
        if nombre_fixture.lower() == alias_value.lower():
            if alias_value in equipos_validos:
                return alias_value
    
    # Paso 3: Fuzzy matching
    coincidencias = get_close_matches(nombre_fixture, equipos_validos, n=1, cutoff=0.6)
    if coincidencias:
        return coincidencias[0]
    
    return nombre_fixture


def encontrar_equipo_similar(nombre: str, equipos_validos: list, n: int = 5) -> list:
    """
    Encuentra equipos similares usando fuzzy matching.
    
    Args:
        nombre: Nombre a buscar
        equipos_validos: Lista de nombres válidos
        n: Número máximo de resultados
    
    Returns:
        Lista de nombres similares
    """
    return get_close_matches(nombre, equipos_validos, n=n, cutoff=0.5)


def imprimir_barra(valor: float, maximo: float = 100, ancho: int = 25) -> str:
    """
    Genera una barra visual de progreso para consola.
    
    Args:
        valor: Valor actual
        maximo: Valor máximo
        ancho: Ancho de la barra en caracteres
    
    Returns:
        String con barra visual
    """
    porcentaje = (valor / maximo) * 100 if maximo > 0 else 0
    bloques_llenos = int((porcentaje / 100) * ancho)
    barra = "█" * bloques_llenos + "░" * (ancho - bloques_llenos)
    return f"[{barra}] {porcentaje:.1f}%"


# ========== EXPORTS ==========
__all__ = [
    # Constantes de rutas
    'PROJECT_ROOT', 'DATA_DIR', 'DATABASES_DIR', 'CACHE_DIR', 'LOGS_DIR',
    'DB_PATH', 'API_CACHE_DB_PATH', 'TEAM_NORMALIZER_DB_PATH', 'LIVE_SCORES_DB_PATH',
    'DB_PATH_STR', 'TEAM_NORMALIZER_DB_PATH_STR', 'LIVE_SCORES_DB_PATH_STR',
    'SQLITE_CONNECTION_STRING',
    # Constantes de API
    'FOOTBALL_DATA_BASE_URL', 'FOOTBALL_API_BASE_URL', 'CURRENT_SEASON',
    # Datos
    'ALIAS_TEAMS',
    'CHAMPIONS_EQUIPO_LIGA',
    # Funciones
    'normalizar_csv', 'descargar_csv_safe',
    'emparejar_equipo', 'encontrar_equipo_similar', 'imprimir_barra',
]
