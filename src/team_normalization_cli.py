"""
Team Normalization CLI (v2.0)
=============================

Interfaz de línea de comandos para gestionar la normalización de equipos.
Ahora con soporte para filtrado por league_code.

Usage:
    python3 src/team_normalization_cli.py stats
    python3 src/team_normalization_cli.py add-team "Manchester United" --league-code E0
    python3 src/team_normalization_cli.py add-alias "Man Utd" "Manchester United"
    python3 src/team_normalization_cli.py normalize "Man United" --league E0
    python3 src/team_normalization_cli.py list-teams --league E0
    python3 src/team_normalization_cli.py search "Arsenal"
    python3 src/team_normalization_cli.py export --output teams.json
"""
# pyright: reportOptionalCall=false, reportUnknownMemberType=false

import sys
from pathlib import Path

# ============================================================================
# CONFIGURACIÓN DE PATH
# ============================================================================
# Asegurar que el directorio raíz del proyecto esté en sys.path
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import click
import json
import logging
import os
from typing import Any, Optional, List, Dict
from collections import defaultdict
from datetime import datetime, timedelta

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None  # type: ignore

# ============================================================================
# IMPORTS DE MÓDULOS LOCALES
# ============================================================================
_import_error_msg: Optional[str] = None
TeamNormalizer: Any = None
TEAM_NORMALIZER_DB_PATH_STR = "data/databases/team_normalizer.db"

try:
    from src.team_normalization import TeamNormalizer as _TN
    from src.utils.shared import TEAM_NORMALIZER_DB_PATH_STR as _DB_PATH
    TeamNormalizer = _TN
    TEAM_NORMALIZER_DB_PATH_STR = _DB_PATH
except ImportError as e:
    _import_error_msg = str(e)
    try:
        from team_normalization import TeamNormalizer as _TN
        from utils.shared import TEAM_NORMALIZER_DB_PATH_STR as _DB_PATH
        TeamNormalizer = _TN
        TEAM_NORMALIZER_DB_PATH_STR = _DB_PATH
        _import_error_msg = None
    except ImportError as e2:
        _import_error_msg = str(e2)

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    tabulate = None  # type: ignore
    TABULATE_AVAILABLE = False

# Cliente API para auditoría
try:
    from src.football_api_client import FootballDataClient
    API_CLIENT_AVAILABLE = True
except ImportError:
    try:
        from football_api_client import FootballDataClient
        API_CLIENT_AVAILABLE = True
    except ImportError:
        FootballDataClient = None  # type: ignore
        API_CLIENT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================
VALID_LEAGUES = ['E0', 'SP1', 'D1', 'I1', 'F1', 'P1', 'N1']

LEAGUE_NAMES: Dict[str, str] = {
    'E0': 'Premier League (Inglaterra)',
    'SP1': 'La Liga (España)',
    'D1': 'Bundesliga (Alemania)',
    'I1': 'Serie A (Italia)',
    'F1': 'Ligue 1 (Francia)',
    'P1': 'Primeira Liga (Portugal)',
    'N1': 'Eredivisie (Holanda)',
}

LEAGUE_TO_COUNTRY: Dict[str, str] = {
    'E0': 'England',
    'SP1': 'Spain',
    'D1': 'Germany',
    'I1': 'Italy',
    'F1': 'France',
    'P1': 'Portugal',
    'N1': 'Netherlands',
}

# Mapeo: Código API Football-Data.org → Código CSV interno
API_TO_LEAGUE_CODE: Dict[str, str] = {
    'PL': 'E0',     # Premier League
    'PD': 'SP1',    # La Liga (Primera División)
    'BL1': 'D1',    # Bundesliga
    'SA': 'I1',     # Serie A
    'FL1': 'F1',    # Ligue 1
    'PPL': 'P1',    # Primeira Liga (Portugal)
    'DED': 'N1',    # Eredivisie (Países Bajos)
}


# ============================================================================
# HELPERS
# ============================================================================
def get_normalizer() -> Any:
    """Obtiene una instancia de TeamNormalizer con la ruta centralizada."""
    if TeamNormalizer is None:
        raise RuntimeError("TeamNormalizer no disponible. Verifica que team_normalization.py exista.")
    return TeamNormalizer(db_path=TEAM_NORMALIZER_DB_PATH_STR)


def format_table(data: List[List[Any]], headers: List[str], tablefmt: str = 'grid') -> str:
    """Formatea datos como tabla usando tabulate o fallback simple."""
    if TABULATE_AVAILABLE and tabulate is not None:
        return tabulate(data, headers=headers, tablefmt=tablefmt)  # type: ignore
    
    # Fallback simple si tabulate no está disponible
    if not data:
        return "Sin datos"
    
    # Calcular anchos de columna
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Construir tabla
    lines = []
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in col_widths)
    lines.append(header_line)
    lines.append(separator)
    
    for row in data:
        row_line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        lines.append(row_line)
    
    return "\n".join(lines)


def validate_league_code(ctx: Any, param: Any, value: Optional[str]) -> Optional[str]:
    """Callback de Click para validar league_code."""
    if value is None:
        return None
    
    value_upper = value.upper()
    if value_upper not in VALID_LEAGUES:
        raise click.BadParameter(
            f"Liga inválida: '{value}'. Opciones válidas: {', '.join(VALID_LEAGUES)}"
        )
    return value_upper


def check_dependencies() -> None:
    """Verifica que las dependencias estén disponibles."""
    if TeamNormalizer is None:
        click.secho("❌ No se pudo importar TeamNormalizer", fg='red')
        if _import_error_msg:
            click.secho(f"   Error: {_import_error_msg}", fg='yellow')
        click.secho("   Verifica que src/team_normalization.py exista", fg='yellow')
        click.secho("\n   Si falta 'thefuzz': pip install thefuzz python-Levenshtein", fg='cyan')
        raise SystemExit(1)
    
    if not TABULATE_AVAILABLE:
        click.secho("⚠️  tabulate no disponible. Usando formato básico.", fg='yellow')
        click.secho("   Instalar con: pip install tabulate", fg='yellow')


# ============================================================================
# CLI GROUP
# ============================================================================
@click.group()
@click.version_option(version='2.0.0', prog_name='team-normalizer')
def cli() -> None:
    """
    Team Normalization CLI v2.0
    
    Sistema de normalización de nombres de equipos con soporte
    para filtrado por liga (league_code).
    
    Ligas soportadas: E0, SP1, D1, I1, F1
    """
    check_dependencies()


# ============================================================================
# COMANDO: stats
# ============================================================================
@cli.command('stats')
def stats() -> None:
    """
    Muestra estadísticas del sistema de normalización.
    
    Incluye totales generales y desglose por liga (league_code).
    """
    normalizer = get_normalizer()
    
    # Obtener todos los equipos
    all_teams = normalizer.get_all_teams()
    
    # Agrupar por league_code
    teams_by_league: Dict[str, List[Any]] = defaultdict(list)
    teams_without_league: List[Any] = []
    
    for team in all_teams:
        league_code = team.get('league_code') or team.get('league')
        if league_code:
            teams_by_league[league_code].append(team)
        else:
            teams_without_league.append(team)
    
    # Mostrar resumen general
    click.echo("\n" + "=" * 70)
    click.secho("📊 ESTADÍSTICAS DEL SISTEMA DE NORMALIZACIÓN", fg='cyan', bold=True)
    click.echo("=" * 70)
    click.echo(f"\n📁 Base de datos: {TEAM_NORMALIZER_DB_PATH_STR}")
    click.echo(f"\n{'─' * 40}")
    click.secho("RESUMEN GENERAL", fg='white', bold=True)
    click.echo(f"{'─' * 40}")
    click.echo(f"  Total equipos registrados:  {len(all_teams):>6}")
    click.echo(f"  Equipos sin liga asignada:  {len(teams_without_league):>6}")
    
    # Tabla por liga
    if teams_by_league:
        click.echo(f"\n{'─' * 40}")
        click.secho("EQUIPOS POR LIGA", fg='white', bold=True)
        click.echo(f"{'─' * 40}\n")
        
        league_data: List[List[Any]] = []
        for league_code in VALID_LEAGUES:
            count = len(teams_by_league.get(league_code, []))
            league_name = LEAGUE_NAMES.get(league_code, league_code)
            league_data.append([league_code, league_name, count])
        
        # Agregar ligas no reconocidas
        for league_code in teams_by_league:
            if league_code not in VALID_LEAGUES:
                count = len(teams_by_league[league_code])
                league_data.append([league_code, "(No reconocida)", count])
        
        click.echo(format_table(
            league_data,
            headers=['Código', 'Liga', 'Equipos'],
            tablefmt='grid'
        ))
    
    # Top equipos por liga
    if teams_by_league:
        click.echo(f"\n{'─' * 40}")
        click.secho("MUESTRA DE EQUIPOS POR LIGA", fg='white', bold=True)
        click.echo(f"{'─' * 40}")
        
        for league_code in VALID_LEAGUES:
            teams = teams_by_league.get(league_code, [])
            if teams:
                click.echo(f"\n  {league_code} - {LEAGUE_NAMES.get(league_code, '')}:")
                for team in teams[:3]:  # Mostrar solo 3 por liga
                    name = team.get('official_name', 'N/A')
                    uuid_short = team.get('team_uuid', '')[:8]
                    click.echo(f"    • {name} ({uuid_short}...)")
                if len(teams) > 3:
                    click.echo(f"    ... y {len(teams) - 3} más")
    
    click.echo("\n")


# ============================================================================
# COMANDO: add-team
# ============================================================================
@cli.command('add-team')
@click.argument('name')
@click.option(
    '--league-code', '-l',
    required=True,
    callback=validate_league_code,
    help=f'Código de liga (obligatorio). Opciones: {", ".join(VALID_LEAGUES)}'
)
def add_team(name: str, league_code: str) -> None:
    """
    Agrega un nuevo equipo a la tabla maestra.
    
    NAME: Nombre oficial del equipo (ej: "Manchester United")
    
    El país se infiere automáticamente del código de liga.
    """
    normalizer = get_normalizer()
    
    # Inferir país desde league_code
    country = LEAGUE_TO_COUNTRY.get(league_code, 'Unknown')
    
    # Agregar equipo
    uuid = normalizer.add_team(
        official_name=name,
        country=country,
        league_code=league_code
    )
    
    click.echo("\n" + "=" * 50)
    click.secho("✓ EQUIPO AGREGADO EXITOSAMENTE", fg='green', bold=True)
    click.echo("=" * 50)
    click.echo(f"  UUID:        {uuid}")
    click.echo(f"  Nombre:      {name}")
    click.echo(f"  País:        {country}")
    click.echo(f"  Liga:        {league_code} ({LEAGUE_NAMES.get(league_code, '')})")
    click.echo()


# ============================================================================
# COMANDO: add-alias
# ============================================================================
@cli.command('add-alias')
@click.argument('alias')
@click.argument('official_name')
def add_alias(alias: str, official_name: str) -> None:
    """
    Agrega un alias para un equipo existente.
    
    ALIAS: El nombre alternativo (ej: "Man Utd", "MUFC")
    
    OFFICIAL_NAME: El nombre oficial del equipo al que se vincula
    """
    normalizer = get_normalizer()
    
    # Buscar equipo por nombre oficial
    all_teams = normalizer.get_all_teams()
    matching_team = None
    
    for team in all_teams:
        if team.get('official_name', '').lower() == official_name.lower():
            matching_team = team
            break
    
    if not matching_team:
        click.secho(f"\n❌ Error: No se encontró equipo con nombre '{official_name}'", fg='red')
        click.echo("\nEquipos disponibles con nombres similares:")
        
        # Buscar similares
        similar = [t for t in all_teams 
                   if official_name.lower() in t.get('official_name', '').lower()]
        
        if similar:
            for t in similar[:5]:
                click.echo(f"  • {t.get('official_name')}")
        else:
            click.echo("  (ninguno encontrado)")
        
        raise SystemExit(1)
    
    team_uuid = matching_team['team_uuid']
    
    # Agregar alias
    alias_id = normalizer.add_alias(
        team_uuid=team_uuid,
        alias_name=alias,
        priority=0,
        source='cli'
    )
    
    click.echo("\n" + "=" * 50)
    click.secho("✓ ALIAS AGREGADO EXITOSAMENTE", fg='green', bold=True)
    click.echo("=" * 50)
    click.echo(f"  Alias ID:      {alias_id}")
    click.echo(f"  Alias:         {alias}")
    click.echo(f"  Equipo:        {matching_team.get('official_name')}")
    click.echo(f"  UUID:          {team_uuid}")
    click.echo(f"  Liga:          {matching_team.get('league_code', 'N/A')}")
    click.echo()


# ============================================================================
# COMANDO: normalize
# ============================================================================
@cli.command('normalize')
@click.argument('name')
@click.option(
    '--league', '-l',
    required=True,
    callback=validate_league_code,
    help=f'Código de liga para filtrar (obligatorio). Opciones: {", ".join(VALID_LEAGUES)}'
)
def normalize(name: str, league: str) -> None:
    """
    Normaliza un nombre de equipo buscando en la liga especificada.
    
    NAME: Nombre del equipo a normalizar (puede ser variante/alias)
    
    Muestra el UUID, nombre oficial y confianza del match.
    """
    normalizer = get_normalizer()
    
    # Normalizar con filtro de liga
    uuid, confidence = normalizer.normalize_team(
        team_name=name,
        league_id=league,
        create_if_missing=False
    )
    
    click.echo("\n" + "=" * 60)
    click.secho("🔍 RESULTADO DE NORMALIZACIÓN", fg='cyan', bold=True)
    click.echo("=" * 60)
    click.echo(f"  Input:         {name}")
    click.echo(f"  Liga filtro:   {league} ({LEAGUE_NAMES.get(league, '')})")
    click.echo(f"{'─' * 60}")
    
    if uuid:
        # Obtener detalles del equipo
        team = normalizer.get_team(uuid)
        official_name = team.get('official_name', 'N/A') if team else 'N/A'
        
        # Determinar color según confianza
        if confidence >= 90:
            conf_color = 'green'
            conf_label = '🟢 Alta'
        elif confidence >= 70:
            conf_color = 'yellow'
            conf_label = '🟡 Media'
        else:
            conf_color = 'red'
            conf_label = '🔴 Baja'
        
        click.secho(f"\n  ✓ MATCH ENCONTRADO", fg='green', bold=True)
        click.echo(f"\n  UUID:          {uuid}")
        click.echo(f"  Nombre Oficial: {official_name}")
        click.secho(f"  Confianza:     {confidence:.1f}% ({conf_label})", fg=conf_color)
        
        if team:
            click.echo(f"  País:          {team.get('country', 'N/A')}")
            click.echo(f"  Liga:          {team.get('league_code', 'N/A')}")
    else:
        click.secho(f"\n  ✗ NO SE ENCONTRÓ MATCH", fg='red', bold=True)
        click.echo(f"\n  El equipo '{name}' no fue encontrado en la liga {league}.")
        click.echo(f"\n  Sugerencias:")
        click.echo(f"    • Verificar ortografía del nombre")
        click.echo(f"    • Verificar que el equipo existe en la liga {league}")
        click.echo(f"    • Usar 'list-teams --league {league}' para ver equipos disponibles")
    
    click.echo("\n")


# ============================================================================
# COMANDO: list-teams
# ============================================================================
@cli.command('list-teams')
@click.option(
    '--league', '-l',
    callback=validate_league_code,
    help=f'Filtrar por código de liga. Opciones: {", ".join(VALID_LEAGUES)}'
)
@click.option(
    '--limit', '-n',
    default=50,
    type=int,
    help='Número máximo de equipos a mostrar (default: 50)'
)
def list_teams(league: Optional[str], limit: int) -> None:
    """
    Lista equipos registrados en el sistema.
    
    Sin filtro, muestra todos los equipos. Con --league, filtra por liga.
    """
    normalizer = get_normalizer()
    
    # Obtener equipos (con filtro opcional)
    if league:
        teams = normalizer.get_all_teams(league_code=league)
        title = f"EQUIPOS EN {league} ({LEAGUE_NAMES.get(league, '')})"
    else:
        teams = normalizer.get_all_teams()
        title = "TODOS LOS EQUIPOS"
    
    if not teams:
        click.secho(f"\n❌ No se encontraron equipos", fg='yellow')
        if league:
            click.echo(f"   en la liga {league}")
        click.echo()
        return
    
    # Limitar resultados
    total = len(teams)
    teams = teams[:limit]
    
    # Preparar datos para tabla
    teams_data: List[List[Any]] = []
    for t in teams:
        teams_data.append([
            t.get('official_name', 'N/A')[:35],
            t.get('country', 'N/A'),
            t.get('league_code', t.get('league', 'N/A')),
            t.get('team_uuid', '')[:12] + '...'
        ])
    
    click.echo("\n" + "=" * 80)
    click.secho(f"📋 {title}", fg='cyan', bold=True)
    click.echo("=" * 80 + "\n")
    
    click.echo(format_table(
        teams_data,
        headers=['Nombre Oficial', 'País', 'Liga', 'UUID'],
        tablefmt='grid'
    ))
    
    click.echo(f"\nMostrando {len(teams)} de {total} equipos")
    if total > limit:
        click.echo(f"Usa --limit para ver más resultados")
    click.echo()


# ============================================================================
# COMANDO: search
# ============================================================================
@cli.command('search')
@click.argument('query')
@click.option(
    '--league', '-l',
    callback=validate_league_code,
    help=f'Filtrar por código de liga. Opciones: {", ".join(VALID_LEAGUES)}'
)
def search(query: str, league: Optional[str]) -> None:
    """
    Busca equipos por nombre (búsqueda parcial).
    
    QUERY: Texto a buscar en los nombres de equipos
    """
    normalizer = get_normalizer()
    
    # Obtener todos los equipos
    if league:
        all_teams = normalizer.get_all_teams(league_code=league)
    else:
        all_teams = normalizer.get_all_teams()
    
    # Filtrar por query (case insensitive)
    query_lower = query.lower()
    matching = [
        t for t in all_teams
        if query_lower in t.get('official_name', '').lower()
    ]
    
    if not matching:
        click.secho(f"\n❌ No se encontraron equipos con '{query}'", fg='yellow')
        if league:
            click.echo(f"   en la liga {league}")
        click.echo()
        return
    
    # Preparar datos
    search_data: List[List[Any]] = []
    for t in matching[:20]:  # Limitar a 20 resultados
        search_data.append([
            t.get('official_name', 'N/A'),
            t.get('country', 'N/A'),
            t.get('league_code', t.get('league', 'N/A')),
            t.get('team_uuid', '')[:12] + '...'
        ])
    
    click.echo("\n" + "=" * 70)
    click.secho(f"🔍 RESULTADOS PARA '{query}'", fg='cyan', bold=True)
    if league:
        click.echo(f"   Filtrado por liga: {league}")
    click.echo("=" * 70 + "\n")
    
    click.echo(format_table(
        search_data,
        headers=['Nombre', 'País', 'Liga', 'UUID'],
        tablefmt='grid'
    ))
    
    if len(matching) > 20:
        click.echo(f"\n... y {len(matching) - 20} resultados más")
    
    click.echo(f"\nTotal encontrados: {len(matching)}\n")


# ============================================================================
# COMANDO: export
# ============================================================================
@cli.command('export')
@click.option(
    '--output', '-o',
    default='teams_export.json',
    help='Archivo de salida (default: teams_export.json)'
)
@click.option(
    '--league', '-l',
    callback=validate_league_code,
    help=f'Exportar solo una liga. Opciones: {", ".join(VALID_LEAGUES)}'
)
@click.option(
    '--format', '-f',
    'output_format',
    type=click.Choice(['json', 'csv']),
    default='json',
    help='Formato de salida (default: json)'
)
def export(output: str, league: Optional[str], output_format: str) -> None:
    """
    Exporta equipos a archivo JSON o CSV.
    """
    normalizer = get_normalizer()
    
    # Obtener equipos
    if league:
        teams = normalizer.get_all_teams(league_code=league)
    else:
        teams = normalizer.get_all_teams()
    
    if not teams:
        click.secho("❌ No hay equipos para exportar", fg='red')
        return
    
    # Exportar según formato
    output_path = Path(output)
    
    if output_format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(teams, f, indent=2, ensure_ascii=False, default=str)
    else:  # csv
        import csv
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            if teams:
                fieldnames = ['team_uuid', 'official_name', 'country', 'league_code']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for team in teams:
                    # Normalizar league_code
                    team['league_code'] = team.get('league_code') or team.get('league', '')
                    writer.writerow(team)
    
    click.echo("\n" + "=" * 50)
    click.secho("✓ EXPORTACIÓN COMPLETADA", fg='green', bold=True)
    click.echo("=" * 50)
    click.echo(f"  Archivo:   {output_path.absolute()}")
    click.echo(f"  Formato:   {output_format.upper()}")
    click.echo(f"  Equipos:   {len(teams)}")
    if league:
        click.echo(f"  Liga:      {league}")
    click.echo()


# ============================================================================
# COMANDO: get-team
# ============================================================================
@cli.command('get-team')
@click.argument('uuid')
def get_team(uuid: str) -> None:
    """
    Muestra información detallada de un equipo por su UUID.
    
    UUID: Identificador único del equipo (completo o parcial)
    """
    normalizer = get_normalizer()
    
    # Buscar por UUID completo o parcial
    team = normalizer.get_team(uuid)
    
    if not team:
        # Intentar buscar por UUID parcial
        all_teams = normalizer.get_all_teams()
        matches = [t for t in all_teams if t.get('team_uuid', '').startswith(uuid)]
        
        if len(matches) == 1:
            team = normalizer.get_team(matches[0]['team_uuid'])
        elif len(matches) > 1:
            click.secho(f"\n⚠️  UUID parcial '{uuid}' tiene múltiples coincidencias:", fg='yellow')
            for m in matches[:5]:
                click.echo(f"  • {m.get('team_uuid')[:16]}... - {m.get('official_name')}")
            click.echo("\nProporciona un UUID más específico.")
            return
    
    if not team:
        click.secho(f"\n❌ Equipo no encontrado: {uuid}", fg='red')
        return
    
    click.echo("\n" + "=" * 70)
    click.secho(f"📋 DETALLE DE EQUIPO", fg='cyan', bold=True)
    click.echo("=" * 70)
    click.echo(f"\n  UUID:          {team.get('team_uuid', 'N/A')}")
    click.echo(f"  Nombre:        {team.get('official_name', 'N/A')}")
    click.echo(f"  País:          {team.get('country', 'N/A')}")
    click.echo(f"  Liga:          {team.get('league_code', team.get('league', 'N/A'))}")
    click.echo(f"  Creado:        {team.get('created_at', 'N/A')}")
    click.echo(f"  Actualizado:   {team.get('updated_at', 'N/A')}")
    
    # Mostrar aliases si existen
    aliases = team.get('aliases', [])
    if aliases:
        click.echo(f"\n  📝 Aliases ({len(aliases)}):")
        for alias in aliases:
            click.echo(f"     • {alias.get('alias_name', 'N/A')}")
    
    # Mostrar mappings si existen
    mappings = team.get('mappings', [])
    if mappings:
        click.echo(f"\n  🔗 Mapeos externos ({len(mappings)}):")
        for m in mappings:
            source = m.get('source', 'N/A')
            ext_name = m.get('external_name', 'N/A')
            similarity = m.get('similarity_score', 0)
            click.echo(f"     • [{source}] {ext_name} ({similarity:.0f}%)")
    
    click.echo("\n")


# ============================================================================
# COMANDO: audit (Auditoría de equipos faltantes)
# ============================================================================
@cli.command('audit')
@click.option('--days', default=7, help='Días hacia adelante para buscar partidos (default: 7)')
@click.option('--league', '-l', default=None, help='Filtrar por liga API (PL, PD, PPL, DED, etc)')
@click.option('--output', '-o', default=None, help='Guardar resultado en archivo JSON')
def audit(days: int, league: Optional[str], output: Optional[str]) -> None:
    """
    Audita equipos faltantes en partidos próximos.
    
    Conecta con la API Football-Data.org, obtiene partidos programados
    y detecta qué equipos no pueden ser normalizados.
    
    Genera sugerencias de comandos para agregar los aliases faltantes.
    
    Ejemplos:
    
        python -m src.team_normalization_cli audit
        
        python -m src.team_normalization_cli audit --days 14
        
        python -m src.team_normalization_cli audit --league PPL
        
        python -m src.team_normalization_cli audit --output faltantes.json
    """
    click.echo("\n" + "=" * 70)
    click.secho("🔍 AUDITORÍA DE EQUIPOS FALTANTES", fg='cyan', bold=True)
    click.echo("=" * 70)
    
    # Verificar dependencias
    if not DOTENV_AVAILABLE:
        click.secho("❌ python-dotenv no está instalado.", fg='red')
        click.echo("   Instalar con: pip install python-dotenv")
        raise SystemExit(1)
    
    if not API_CLIENT_AVAILABLE:
        click.secho("❌ FootballDataClient no está disponible.", fg='red')
        click.echo("   Verifica que src/football_api_client.py exista.")
        raise SystemExit(1)
    
    # Cargar variables de entorno
    if load_dotenv:
        load_dotenv()
    
    api_key = os.environ.get('FOOTBALL_DATA_API_KEY')
    if not api_key:
        click.secho("❌ FOOTBALL_DATA_API_KEY no configurada en .env", fg='red')
        click.echo("   Agrega: FOOTBALL_DATA_API_KEY=tu_api_key")
        raise SystemExit(1)
    
    click.echo(f"\n📡 Conectando a Football-Data.org API...")
    click.echo(f"📅 Buscando partidos programados para los próximos {days} días...")
    
    try:
        # Inicializar cliente y normalizer
        client = FootballDataClient(api_key)
        normalizer = get_normalizer()
        
        # Calcular fechas
        date_from_str = datetime.now().strftime('%Y-%m-%d')
        date_to_str = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Filtrar por liga si se especifica
        competition_filter = None
        if league:
            league_upper = league.upper()
            if league_upper not in API_TO_LEAGUE_CODE:
                click.secho(f"⚠️  Liga '{league}' no reconocida. Ligas válidas:", fg='yellow')
                for code, csv_code in API_TO_LEAGUE_CODE.items():
                    click.echo(f"   • {code} → {csv_code} ({LEAGUE_NAMES.get(csv_code, 'Desconocida')})")
                raise SystemExit(1)
            competition_filter = league_upper
        
        # Hacer request a la API (usando parámetros snake_case del método)
        # Construir kwargs dinámicamente para evitar pasar None
        match_kwargs: Dict[str, str] = {
            'status': 'SCHEDULED',
            'date_from': date_from_str,
            'date_to': date_to_str
        }
        if competition_filter:
            match_kwargs['competition'] = competition_filter
        
        matches = client.get_matches(**match_kwargs)
        
        if not matches:
            click.secho(f"\n📭 No se encontraron partidos programados.", fg='yellow')
            return
        
        click.echo(f"✅ Encontrados {len(matches)} partidos programados.\n")
        
        # Auditar equipos
        faltantes: List[Dict[str, Any]] = []
        equipos_procesados: set = set()
        
        for match in matches:
            # Obtener código de liga de la API
            competition = match.get('competition', {})
            api_code = competition.get('code', '')
            
            if not api_code:
                continue
            
            # Traducir a código CSV
            csv_code = API_TO_LEAGUE_CODE.get(api_code)
            if not csv_code:
                continue
            
            # Obtener nombres de equipos
            home_team = match.get('homeTeam', {})
            away_team = match.get('awayTeam', {})
            
            home_name = home_team.get('name', '')
            away_name = away_team.get('name', '')
            
            # Procesar cada equipo
            for team_name in [home_name, away_name]:
                if not team_name:
                    continue
                
                # Evitar duplicados
                team_key = f"{csv_code}:{team_name}"
                if team_key in equipos_procesados:
                    continue
                equipos_procesados.add(team_key)
                
                # Intentar normalizar
                try:
                    team_uuid, confidence = normalizer.normalize_team(
                        team_name=team_name,
                        league_id=csv_code,
                        create_if_missing=False
                    )
                    
                    # Si no se encontró o confianza muy baja
                    if team_uuid is None or confidence < 60.0:
                        # Generar sugerencia de comando
                        escaped_name = team_name.replace('"', '\\"')
                        # Intentar obtener nombre corto (primera palabra significativa)
                        short_name = team_name.split()[0] if ' ' in team_name else team_name
                        
                        faltantes.append({
                            'liga': csv_code,
                            'liga_nombre': LEAGUE_NAMES.get(csv_code, api_code),
                            'nombre_api': team_name,
                            'confianza': confidence if confidence else 0,
                            'sugerencia': f'python -m src.team_normalization_cli add-alias "{escaped_name}" "{short_name}" --league {csv_code}'
                        })
                        
                except Exception as e:
                    # Error en normalización = faltante
                    escaped_name = team_name.replace('"', '\\"')
                    short_name = team_name.split()[0] if ' ' in team_name else team_name
                    
                    faltantes.append({
                        'liga': csv_code,
                        'liga_nombre': LEAGUE_NAMES.get(csv_code, api_code),
                        'nombre_api': team_name,
                        'confianza': 0,
                        'sugerencia': f'python -m src.team_normalization_cli add-alias "{escaped_name}" "{short_name}" --league {csv_code}'
                    })
        
        # Mostrar resultados
        if not faltantes:
            click.secho("\n✅ ¡Todos los equipos están correctamente mapeados!", fg='green', bold=True)
            click.echo(f"   Equipos verificados: {len(equipos_procesados)}")
            return
        
        # Ordenar por liga
        faltantes.sort(key=lambda x: (x['liga'], x['nombre_api']))
        
        click.secho(f"\n⚠️  EQUIPOS FALTANTES: {len(faltantes)}", fg='yellow', bold=True)
        click.echo("-" * 70)
        
        # Mostrar tabla
        table_data = []
        for f in faltantes:
            table_data.append([
                f['liga'],
                f['nombre_api'][:40],  # Truncar nombres muy largos
                f"{f['confianza']:.0f}%"
            ])
        
        click.echo(format_table(
            table_data,
            headers=['Liga', 'Nombre API', 'Conf.']
        ))
        
        # Mostrar sugerencias de comandos
        click.echo("\n" + "=" * 70)
        click.secho("📋 COMANDOS SUGERIDOS PARA AGREGAR ALIASES:", fg='cyan', bold=True)
        click.echo("=" * 70 + "\n")
        
        for f in faltantes:
            click.echo(f"# {f['liga_nombre']}: {f['nombre_api']}")
            click.secho(f"{f['sugerencia']}", fg='green')
            click.echo()
        
        # Guardar en archivo si se especifica
        if output:
            output_path = Path(output)
            with open(output_path, 'w', encoding='utf-8') as f_out:
                json.dump({
                    'fecha_auditoria': datetime.now().isoformat(),
                    'dias_analizados': days,
                    'total_partidos': len(matches),
                    'equipos_verificados': len(equipos_procesados),
                    'equipos_faltantes': len(faltantes),
                    'faltantes': faltantes
                }, f_out, indent=2, ensure_ascii=False)
            
            click.secho(f"\n💾 Resultados guardados en: {output_path}", fg='cyan')
        
        # Resumen final
        click.echo("\n" + "=" * 70)
        click.secho("📊 RESUMEN", fg='cyan', bold=True)
        click.echo("=" * 70)
        click.echo(f"  Partidos analizados:    {len(matches)}")
        click.echo(f"  Equipos verificados:    {len(equipos_procesados)}")
        click.echo(f"  Equipos faltantes:      {len(faltantes)}")
        
        # Agrupar por liga
        por_liga: Dict[str, int] = defaultdict(int)
        for f in faltantes:
            por_liga[f['liga']] += 1
        
        if por_liga:
            click.echo("\n  Por liga:")
            for liga, count in sorted(por_liga.items()):
                liga_nombre = LEAGUE_NAMES.get(liga, liga)
                click.echo(f"    • {liga} ({liga_nombre}): {count} equipos")
        
        click.echo("\n")
        
    except Exception as e:
        click.secho(f"\n❌ Error durante la auditoría: {e}", fg='red')
        import traceback
        traceback.print_exc()
        raise SystemExit(1)


# ============================================================================
# MAIN
# ============================================================================
if __name__ == '__main__':
    cli()
