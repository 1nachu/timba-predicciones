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
import sqlite3
from typing import Optional, Union

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


def get_db_connection(db_path: Union[str, Path] = DB_PATH, readonly: bool = False, timeout: float = 10.0) -> sqlite3.Connection:
    """
    Crea y configura una conexión SQLite optimizada y segura para concurrencia.
    
    Aplica:
    - WAL Mode (Write-Ahead Logging) para permitir lecturas y escrituras simultáneas
    - Synchronous = NORMAL para acelerar escrituras seguras
    - Busy timeout de 5 segundos para evitar 'database is locked'
    - Cache size ampliado a 64MB
    """
    db_str = str(db_path)
    Path(db_str).parent.mkdir(parents=True, exist_ok=True)
    
    if readonly:
        uri = f"file:{os.path.abspath(db_str)}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=timeout)
    else:
        conn = sqlite3.connect(os.path.abspath(db_str), timeout=timeout)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            logger.debug(f"No se pudo configurar WAL en {db_str}: {e}")
            
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA cache_size=-64000;")
    return conn

# ========== CONFIGURACIÓN DE API ==========
FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk"
FOOTBALL_API_BASE_URL = "https://api.football-data.org/v4"

# ========== TEMPORADA ACTUAL ==========
CURRENT_SEASON = "2627"  # 2026-27

# ========== DICCIONARIO DE ALIAS DE EQUIPOS ==========
# Ligas con fuentes de datos confiables (7 europeas + Argentina)
ALIAS_TEAMS = {
    # --- PREMIER LEAGUE (E0) ---
    "Manchester United": "Man United", "Man Utd": "Man United", "Manchester United FC": "Man United", "Man U": "Man United",
    "Manchester City": "Man City", "Manchester City FC": "Man City", "City": "Man City", "Man City FC": "Man City",
    "Arsenal FC": "Arsenal", "The Gunners": "Arsenal",
    "Chelsea FC": "Chelsea", "The Blues": "Chelsea",
    "Liverpool FC": "Liverpool", "The Reds": "Liverpool",
    "Aston Villa FC": "Aston Villa", "Villa": "Aston Villa",
    "Tottenham Hotspur": "Tottenham", "Spurs": "Tottenham", "Tottenham Hotspur FC": "Tottenham",
    "Wolverhampton Wanderers": "Wolves", "Wolverhampton": "Wolves",
    "Nottingham Forest": "Nott'm Forest", "Nottingham": "Nott'm Forest",
    "Brighton & Hove Albion": "Brighton", "Brighton & Hove": "Brighton", "Brighton and Hove Albion": "Brighton",
    "Newcastle United": "Newcastle", "Newcastle Utd": "Newcastle",
    "West Ham United": "West Ham", "West Ham Utd": "West Ham",
    "Sheffield United": "Sheffield United",
    "AFC Bournemouth": "Bournemouth",
    "Leicester City": "Leicester",
    "Ipswich Town": "Ipswich",

    # --- LA LIGA (SP1) ---
    "Real Madrid CF": "Real Madrid", "Real Madrid": "Real Madrid", "Madrid": "Real Madrid", "El Real": "Real Madrid",
    "FC Barcelona": "Barcelona", "Barcelona": "Barcelona", "Barca": "Barcelona", "Barça": "Barcelona",
    "Atleti": "Ath Madrid", "Atletico Madrid": "Ath Madrid", "Atlético Madrid": "Ath Madrid", "Atlético de Madrid": "Ath Madrid", "Atletico de Madrid": "Ath Madrid", "Club Atlético de Madrid": "Ath Madrid", "Atletico": "Ath Madrid",
    "Athletic Club": "Ath Bilbao", "Athletic Bilbao": "Ath Bilbao", "Bilbao": "Ath Bilbao", "Athletic": "Ath Bilbao",
    "Real Betis": "Betis", "Real Betis Balompié": "Betis",
    "Celta de Vigo": "Celta", "RC Celta": "Celta",
    "RCD Mallorca": "Mallorca",
    "Rayo Vallecano": "Vallecano", "Rayo": "Vallecano",
    "Real Sociedad": "Sociedad", "La Real": "Sociedad",
    "Deportivo Alavés": "Alaves", "Alavés": "Alaves", "Deportivo Alaves": "Alaves",
    "RCD Espanyol de Barcelona": "Espanol", "Espanyol": "Espanol", "Espanol": "Espanol",
    "Villarreal CF": "Villarreal", "Villareal": "Villarreal",
    "CA Osasuna": "Osasuna",
    "Getafe CF": "Getafe",
    "UD Las Palmas": "Las Palmas",
    "Valencia CF": "Valencia", "Valencia": "Valencia",
    "Sevilla FC": "Sevilla", "Sevilla": "Sevilla",

    # --- BUNDESLIGA (D1) ---
    "Bayer 04 Leverkusen": "Leverkusen", "Bayer Leverkusen": "Leverkusen", "Leverkusen": "Leverkusen",
    "Borussia Dortmund": "Dortmund", "Dortmund": "Dortmund", "BVB": "Dortmund",
    "Borussia Monchengladbach": "M'gladbach", "Borussia Mönchengladbach": "M'gladbach", "Gladbach": "M'gladbach",
    "Eintracht Frankfurt": "Ein Frankfurt", "Frankfurt": "Ein Frankfurt",
    "Bayern Munich": "Bayern Munich", "FC Bayern München": "Bayern Munich", "Bayern München": "Bayern Munich", "Bayern": "Bayern Munich", "FC Bayern": "Bayern Munich",
    "VfB Stuttgart": "Stuttgart", "Stuttgart": "Stuttgart",
    "VfL Wolfsburg": "Wolfsburg", "Wolfsburg": "Wolfsburg",
    "Mainz 05": "Mainz", "1. FSV Mainz 05": "Mainz", "Mainz": "Mainz",
    "SV Werder Bremen": "Werder Bremen", "Werder": "Werder Bremen", "Bremen": "Werder Bremen",
    "Sport-Club Freiburg": "Freiburg", "SC Freiburg": "Freiburg", "Freiburg": "Freiburg",
    "RB Leipzig": "RB Leipzig", "RasenBallsport Leipzig": "RB Leipzig", "Leipzig": "RB Leipzig",
    "1. FC Union Berlin": "Union Berlin", "Union Berlin": "Union Berlin",
    "FC Augsburg": "Augsburg", "Augsburg": "Augsburg",
    "TSG 1899 Hoffenheim": "Hoffenheim", "TSG Hoffenheim": "Hoffenheim", "Hoffenheim": "Hoffenheim",

    # --- SERIE A (I1) ---
    "Internazionale": "Inter", "Inter Milan": "Inter", "FC Internazionale Milano": "Inter", "Inter": "Inter",
    "AC Milan": "Milan", "Milan": "Milan",
    "AS Roma": "Roma", "Roma": "Roma",
    "Hellas Verona": "Verona", "Hellas Verona FC": "Verona", "Verona": "Verona",
    "SSC Napoli": "Napoli", "Napoli": "Napoli",
    "Juventus FC": "Juventus", "Juventus": "Juventus", "Juve": "Juventus",
    "SS Lazio": "Lazio", "Lazio": "Lazio",
    "ACF Fiorentina": "Fiorentina", "Fiorentina": "Fiorentina",
    "Atalanta BC": "Atalanta", "Atalanta": "Atalanta",
    "Bologna FC 1909": "Bologna", "Bologna": "Bologna",
    "Torino FC": "Torino", "Torino": "Torino",

    # --- LIGUE 1 (F1) ---
    "Paris Saint-Germain FC": "Paris SG", "Paris Saint-Germain": "Paris SG", "Paris SG": "Paris SG", "PSG": "Paris SG", "Paris": "Paris SG",
    "Olympique de Marseille": "Marseille", "Olympique Marseille": "Marseille", "Marseille": "Marseille", "OM": "Marseille",
    "Olympique Lyonnais": "Lyon", "Olympique Lyon": "Lyon", "Lyon": "Lyon", "OL": "Lyon",
    "AS Monaco FC": "Monaco", "AS Monaco": "Monaco", "Monaco": "Monaco",
    "Stade Rennais FC": "Rennes", "Stade Rennais": "Rennes", "Rennes": "Rennes",
    "RC Lens": "Lens", "Lens": "Lens",
    "Havre Athletic Club": "Le Havre", "Le Havre AC": "Le Havre",
    "Stade Brestois 29": "Brest", "Brest": "Brest",
    "LOSC Lille": "Lille", "Lille OSC": "Lille", "Lille": "Lille",
    "OGC Nice": "Nice", "Nice": "Nice",
    "RC Strasbourg Alsace": "Strasbourg", "Strasbourg": "Strasbourg",

    # --- EREDIVISIE (N1) ---
    "AFC Ajax": "Ajax", "Ajax": "Ajax",
    "PSV": "PSV Eindhoven", "PSV Eindhoven": "PSV Eindhoven",
    "AZ": "AZ Alkmaar", "AZ Alkmaar": "AZ Alkmaar",
    "FC Twente": "Twente", "Twente": "Twente",
    "FC Utrecht": "Utrecht", "Utrecht": "Utrecht",
    "FC Groningen": "Groningen",
    "FC Volendam": "Volendam",
    "PEC Zwolle": "Zwolle",
    "Feyenoord Rotterdam": "Feyenoord", "Feyenoord": "Feyenoord",
    "sc Heerenveen": "Heerenveen", "SC Heerenveen": "Heerenveen", "Heerenveen": "Heerenveen",
    "Heracles Almelo": "Heracles",
    "N.E.C. Nijmegen": "Nijmegen", "NEC Nijmegen": "Nijmegen", "NEC": "Nijmegen",
    "Fortuna Sittard": "For Sittard",
    "Excelsior Rotterdam": "Excelsior",

    # --- PRIMEIRA LIGA (P1) ---
    "FC Porto": "Porto", "Porto": "Porto",
    "Sporting CP": "Sp Lisbon", "Sporting Lisbon": "Sp Lisbon", "Sporting": "Sp Lisbon", "Sporting de Portugal": "Sp Lisbon",
    "SL Benfica": "Benfica", "Benfica": "Benfica",
    "SC Braga": "Braga", "Sporting Braga": "Braga", "Braga": "Braga",
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
    "Boca Juniors": "Boca Juniors", "Boca": "Boca Juniors", "Boca Jrs": "Boca Juniors", "Club Atlético Boca Juniors": "Boca Juniors",
    "River Plate": "River Plate", "River": "River Plate", "Club Atlético River Plate": "River Plate",
    "Racing Club": "Racing Club", "Racing": "Racing Club", "Racing de Avellaneda": "Racing Club",
    "Independiente": "Independiente", "CA Independiente": "Independiente", "Rojo": "Independiente",
    "San Lorenzo": "San Lorenzo", "San Lorenzo de Almagro": "San Lorenzo", "CASLA": "San Lorenzo",
    "Argentinos Juniors": "Argentinos Jrs", "Argentinos": "Argentinos Jrs", "Argentinos Jrs": "Argentinos Jrs",
    "Arsenal de Sarandí": "Arsenal Sarandi", "Arsenal Sarandi": "Arsenal Sarandi",
    "Atlético Rafaela": "Atl. Rafaela", "Atletico Rafaela": "Atl. Rafaela",
    "Atlético Tucumán": "Atl. Tucuman", "Atletico Tucuman": "Atl. Tucuman", "Atl Tucuman": "Atl. Tucuman",
    "Central Córdoba": "Central Cordoba", "Central Cordoba SdE": "Central Cordoba",
    "Colón de Santa Fe": "Colon Santa Fe", "Colon": "Colon Santa Fe", "Colón": "Colon Santa Fe",
    "Deportivo Riestra": "Dep. Riestra", "Riestra": "Dep. Riestra",
    "Estudiantes de La Plata": "Estudiantes L.P.", "Estudiantes LP": "Estudiantes L.P.", "Estudiantes": "Estudiantes L.P.", "Pincha": "Estudiantes L.P.",
    "Gimnasia La Plata": "Gimnasia L.P.", "Gimnasia LP": "Gimnasia L.P.", "Gimnasia y Esgrima LP": "Gimnasia L.P.", "Lobo": "Gimnasia L.P.",
    "Gimnasia de Mendoza": "Gimnasia Mendoza", "Gimnasia y Esgrima de Mendoza": "Gimnasia Mendoza",
    "Huracán": "Huracan", "Huracan": "Huracan", "Globo": "Huracan",
    "Independiente Rivadavia": "Ind. Rivadavia", "Ind Rivadavia": "Ind. Rivadavia",
    "Lanús": "Lanus", "Lanus": "Lanus", "Granate": "Lanus",
    "Newell's Old Boys": "Newells Old Boys", "Newells": "Newells Old Boys", "Newell's": "Newells Old Boys", "NOB": "Newells Old Boys",
    "Rosario Central": "Rosario Central", "Central": "Rosario Central", "Canalla": "Rosario Central",
    "San Martín de San Juan": "San Martin S.J.", "San Martin SJ": "San Martin S.J.",
    "San Martín de Tucumán": "San Martin T.", "San Martin Tucuman": "San Martin T.",
    "Sarmiento de Junín": "Sarmiento Junin", "Sarmiento": "Sarmiento Junin",
    "Talleres de Córdoba": "Talleres Cordoba", "Talleres": "Talleres Cordoba",
    "Unión de Santa Fe": "Union de Santa Fe", "Union": "Union de Santa Fe", "Unión": "Union de Santa Fe",
    "Vélez Sarsfield": "Velez Sarsfield", "Velez": "Velez Sarsfield", "Vélez": "Velez Sarsfield", "Fortín": "Velez Sarsfield",
}



# ========== MAPEOS PARA CHAMPIONS LEAGUE ==========
# Mapea nombres aproximados de equipos (para selector UI) a la liga doméstica (código CSV).
# Los nombres no necesitan ser exactos; emparejar_equipo() hará fuzzy matching.
CHAMPIONS_EQUIPO_LIGA = {
    # Premier League (E0)
    'Arsenal': 'E0',
    'Aston Villa': 'E0',
    'Chelsea': 'E0',
    'Liverpool': 'E0',
    'Manchester City': 'E0',
    'Manchester United': 'E0',
    'Newcastle United': 'E0',
    'Tottenham': 'E0',

    # La Liga (SP1)
    'Athletic Club': 'SP1',
    'Atleti': 'SP1',
    'Barcelona': 'SP1',
    'Girona': 'SP1',
    'Real Madrid': 'SP1',
    'Real Sociedad': 'SP1',
    'Villarreal': 'SP1',

    # Bundesliga (D1)
    'Bayer Leverkusen': 'D1',
    'Bayern Munich': 'D1',
    'Borussia Dortmund': 'D1',
    'Eintracht Frankfurt': 'D1',
    'RB Leipzig': 'D1',
    'Stuttgart': 'D1',

    # Serie A (I1)
    'AC Milan': 'I1',
    'Atalanta': 'I1',
    'Bologna': 'I1',
    'Fiorentina': 'I1',
    'Inter Milan': 'I1',
    'Juventus': 'I1',
    'Lazio': 'I1',
    'Napoli': 'I1',
    'Roma': 'I1',

    # Ligue 1 (F1)
    'Brest': 'F1',
    'Lille': 'F1',
    'Lyon': 'F1',
    'Marseille': 'F1',
    'Monaco': 'F1',
    'PSG': 'F1',
    'Rennes': 'F1',

    # Primeira Liga (P1)
    'Benfica': 'P1',
    'Braga': 'P1',
    'Porto': 'P1',
    'Sporting': 'P1',
    'Sporting CP': 'P1',

    # Eredivisie (N1)
    'AZ Alkmaar': 'N1',
    'Ajax': 'N1',
    'Feyenoord': 'N1',
    'PSV': 'N1',
    'Twente': 'N1',
    'Utrecht': 'N1',
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
                    df = pd.read_csv(io.StringIO(text), usecols=usecols, on_bad_lines='skip')
                except ValueError as e:
                    # Columnas no encontradas (ej: CSV de Argentina tiene formato diferente)
                    logger.debug(f"usecols falló ({e}), cargando todas las columnas")
                    df = pd.read_csv(io.StringIO(text), on_bad_lines='skip')
            else:
                df = pd.read_csv(io.StringIO(text), on_bad_lines='skip')
            
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
    Empareja el nombre de un equipo desde el fixture/usuario con los nombres de la BD.
    
    Estrategia de resolución:
    1. Coincidencia exacta (case-insensitive)
    2. Búsqueda en ALIAS_TEAMS (case-insensitive)
    3. Substring match específico (por palabra completa o longitud >= 4)
    4. Fuzzy matching con difflib estricto (case-insensitive, cutoff=0.72)
    5. Retornar nombre original si no hay match
    """
    if not nombre_fixture or not equipos_validos:
        return nombre_fixture
        
    nombre_limpio = str(nombre_fixture).strip()
    nombre_lower = nombre_limpio.lower()
    
    # Paso 1: Coincidencia exacta case-insensitive
    for eq in equipos_validos:
        if eq.lower() == nombre_lower:
            return eq
            
    # Paso 2: Búsqueda en ALIAS_TEAMS (case-insensitive en claves)
    for alias_k, alias_v in ALIAS_TEAMS.items():
        if alias_k.lower() == nombre_lower:
            for eq in equipos_validos:
                if eq.lower() == alias_v.lower() or alias_v in equipos_validos:
                    return alias_v if alias_v in equipos_validos else eq
                    
    # Paso 3: Substring match específico (ej: "boca" en "Boca Juniors", "chelsea" en "Chelsea")
    for eq in equipos_validos:
        eq_lower = eq.lower()
        words = eq_lower.split()
        if nombre_lower in words or any(w.startswith(nombre_lower) for w in words if len(nombre_lower) >= 3):
            return eq
        if len(nombre_lower) >= 5 and (nombre_lower in eq_lower or eq_lower in nombre_lower):
            return eq
            
    # Paso 4: Fuzzy matching estricto case-insensitive (cutoff=0.72)
    eq_map = {eq.lower(): eq for eq in equipos_validos}
    coincidencias = get_close_matches(nombre_lower, list(eq_map.keys()), n=1, cutoff=0.72)
    if coincidencias:
        return eq_map[coincidencias[0]]
        
    return nombre_limpio


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
    'get_db_connection',
    'normalizar_csv', 'descargar_csv_safe',
    'emparejar_equipo', 'encontrar_equipo_similar', 'imprimir_barra',
]
