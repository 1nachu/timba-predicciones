"""
Fixtures Scraper Module
=======================
Módulo para extracción y descarga de próximos partidos desde feeds JSON,
CSVs y portales web como Promiedos.com.ar.
"""

import io
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import requests

logger = logging.getLogger(__name__)


def _scrape_promiedos(url: str) -> List[Dict]:
    """
    Extrae los próximos partidos desde Promiedos.com.ar.
    
    Promiedos usa Next.js con datos JSON embebidos en __NEXT_DATA__.
    Esta función extrae los partidos de la Liga Profesional Argentina (ID: hc).
    
    Args:
        url: URL de la liga en Promiedos (ej: https://www.promiedos.com.ar/league/liga-profesional/hc)
    
    Returns:
        Lista de dicts con 'local', 'visitante', 'fecha', 'fecha_utc'
    """
    partidos = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
        }
        
        base_url = 'https://www.promiedos.com.ar/'
        response = requests.get(base_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
        
        if not match:
            logger.warning("Promiedos: No se encontró __NEXT_DATA__ en la página")
            return []
        
        data = json.loads(match.group(1))
        page_props = data.get('props', {}).get('pageProps', {})
        data_content = page_props.get('data', {})
        leagues = data_content.get('leagues', [])
        
        liga_id = url.rstrip('/').split('/')[-1] if '/' in url else 'hc'
        
        liga_target = None
        for league in leagues:
            if league.get('id') == liga_id:
                liga_target = league
                break
        
        if not liga_target:
            for league in leagues:
                league_name = league.get('name', '').lower()
                if 'copa' in league_name or 'reserva' in league_name:
                    continue
                if 'liga profesional' in league_name:
                    liga_target = league
                    break
        
        if not liga_target:
            logger.warning(f"Promiedos: Liga con ID '{liga_id}' no encontrada")
            return []
        
        games = liga_target.get('games', [])
        hoy = datetime.now()
        
        for game in games:
            try:
                teams = game.get('teams', [])
                if len(teams) < 2:
                    continue
                
                local = teams[0].get('name', '').strip()
                visitante = teams[1].get('name', '').strip()
                
                if not local or not visitante:
                    continue
                
                status = game.get('status', {})
                status_enum = status.get('enum', 0) if isinstance(status, dict) else 0
                
                if status_enum != 1:
                    continue
                
                hora_display = game.get('game_time_to_display', '')
                start_time = game.get('start_time', '')
                
                fecha_str = 'Próximo'
                fecha_utc = None
                
                if start_time:
                    try:
                        if isinstance(start_time, str):
                            fecha_dt = pd.to_datetime(start_time, dayfirst=True, errors='coerce')
                            if pd.notna(fecha_dt):
                                fecha_str = fecha_dt.strftime('%Y-%m-%d %H:%M')
                                fecha_utc = fecha_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                    except Exception:
                        pass
                
                if fecha_str == 'Próximo' and hora_display:
                    hora_match = re.match(r'^(\d{1,2}):(\d{2})$', str(hora_display).strip())
                    if hora_match:
                        hora = int(hora_match.group(1))
                        minuto = int(hora_match.group(2))
                        fecha_partido = hoy.replace(hour=hora, minute=minuto, second=0, microsecond=0)
                        
                        if fecha_partido < hoy:
                            fecha_partido += timedelta(days=1)
                        
                        fecha_str = fecha_partido.strftime('%Y-%m-%d %H:%M')
                        fecha_utc = fecha_partido.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                partidos.append({
                    'local': local,
                    'visitante': visitante,
                    'fecha': fecha_str,
                    'fecha_utc': fecha_utc
                })
                
            except Exception as e:
                logger.debug(f"Error parseando partido de Promiedos: {e}")
                continue
        
        logger.info(f"✓ Promiedos: {len(partidos)} partidos encontrados para {liga_target.get('name', 'Liga')}")
        return partidos[:20]
        
    except requests.RequestException as e:
        logger.warning(f"Error conectando a Promiedos: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"Error parseando JSON de Promiedos: {e}")
        return []
    except Exception as e:
        logger.warning(f"Error scrapeando Promiedos: {e}")
        return []


def obtener_proximos_partidos(fixture_url: str) -> List[Dict]:
    """
    Obtiene los próximos partidos desde una URL de fixtures.
    Retorna lista de dicts con 'local', 'visitante', 'fecha' y 'fecha_utc'.
    
    Soporta:
    - JSON (fixturedownload.com)
    - CSV
    - HTML/Promiedos (promiedos.com.ar)
    """
    if 'promiedos.com' in fixture_url.lower():
        return _scrape_promiedos(fixture_url)
    
    partidos = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(fixture_url, headers=headers, timeout=15)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type', '').lower()
        raw_text = r.content.decode('utf-8', errors='ignore')

        is_json = 'application/json' in content_type or raw_text.lstrip().startswith('{') or raw_text.lstrip().startswith('[')
        if is_json:
            try:
                data = r.json()
            except Exception:
                data = None

            if isinstance(data, dict):
                if 'fixtures' in data and isinstance(data['fixtures'], list):
                    items = data['fixtures']
                elif 'data' in data and isinstance(data['data'], list):
                    items = data['data']
                else:
                    items = []
            elif isinstance(data, list):
                items = data
            else:
                items = []

            def pick_value(obj, keys):
                for k in keys:
                    if k in obj and obj[k] not in (None, ''):
                        return obj[k]
                for k in obj.keys():
                    if k.lower() in keys:
                        return obj[k]
                return None

            ahora = datetime.now()
            ahora_plus_7 = ahora + timedelta(days=7)

            for item in items:
                if not isinstance(item, dict):
                    continue

                local = pick_value(item, ['HomeTeam', 'homeTeam', 'home_team', 'home', 'local'])
                visita = pick_value(item, ['AwayTeam', 'awayTeam', 'away_team', 'away', 'visitante'])
                fecha_raw = pick_value(item, ['Date', 'date', 'DateUtc', 'dateUtc', 'utcDate', 'matchDate'])

                if not local or not visita:
                    continue

                fecha = 'Próximo'
                if fecha_raw:
                    fecha_dt = pd.to_datetime(fecha_raw, errors='coerce', utc=True)
                    if pd.notna(fecha_dt):
                        fecha_dt = fecha_dt.tz_convert(None)
                        if ahora < fecha_dt < ahora_plus_7:
                            fecha = fecha_dt.strftime('%Y-%m-%d %H:%M')
                            fecha_utc = fecha_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                            partidos.append({
                                'local': str(local).strip(), 
                                'visitante': str(visita).strip(), 
                                'fecha': fecha,
                                'fecha_utc': fecha_utc
                            })
                        else:
                            continue
                    else:
                        partidos.append({'local': str(local).strip(), 'visitante': str(visita).strip(), 'fecha': fecha})
                else:
                    partidos.append({'local': str(local).strip(), 'visitante': str(visita).strip(), 'fecha': fecha})

            return partidos[:20]

        # Fallback: Parsear como CSV
        df = pd.read_csv(io.StringIO(raw_text))
        df.columns = df.columns.str.strip()

        col_local = None
        col_visita = None
        col_fecha = None

        for col in df.columns:
            col_lower = col.lower()
            if 'home' in col_lower or 'local' in col_lower:
                col_local = col
            elif 'away' in col_lower or 'visitante' in col_lower or 'away_team' in col_lower:
                col_visita = col
            elif 'date' in col_lower or 'fecha' in col_lower:
                col_fecha = col

        if not col_local or not col_visita:
            return []

        ahora = datetime.now()
        ahora_plus_7 = ahora + timedelta(days=7)

        for _, fila in df.iterrows():
            try:
                local = str(fila[col_local]).strip() if col_local else ''
                visita = str(fila[col_visita]).strip() if col_visita else ''

                if not local or not visita or local == 'nan' or visita == 'nan':
                    continue

                fecha = 'Próximo'
                if col_fecha:
                    fecha_dt = pd.to_datetime(fila[col_fecha], errors='coerce')
                    if pd.notna(fecha_dt) and ahora < fecha_dt < ahora_plus_7:
                        fecha = fecha_dt.strftime('%Y-%m-%d %H:%M')
                        partidos.append({'local': local, 'visitante': visita, 'fecha': fecha})
                    elif pd.isna(fecha_dt):
                        partidos.append({'local': local, 'visitante': visita, 'fecha': fecha})
                else:
                    partidos.append({'local': local, 'visitante': visita, 'fecha': fecha})

            except Exception:
                continue

        return partidos[:20]
        
    except Exception as e:
        logger.warning(f"Error descargando fixtures: {e}")
        return []
