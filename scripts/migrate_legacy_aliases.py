#!/usr/bin/env python3
"""
Script de Migración: Legacy ALIAS_TEAMS → TeamNormalizer
=========================================================

Migra el diccionario hardcodeado ALIAS_TEAMS desde src/utils/shared.py
hacia la base de datos SQLite gestionada por TeamNormalizer.

Uso:
    python scripts/migrate_legacy_aliases.py
    python scripts/migrate_legacy_aliases.py --dry-run
    python scripts/migrate_legacy_aliases.py --db path/to/db.sqlite

Autor: Data Engineering Team
Fecha: 2026-01-31
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Añadir directorio raíz al path para imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / 'src'))

# Imports de módulos del proyecto
try:
    from src.utils.shared import ALIAS_TEAMS
except ImportError:
    from utils.shared import ALIAS_TEAMS

try:
    from src.team_normalization import TeamNormalizer
except ImportError:
    from team_normalization import TeamNormalizer


def migrate_aliases(
    db_path: str = 'data/databases/football_data.db',
    dry_run: bool = False,
    verbose: bool = True
) -> dict:
    """
    Migra los alias legacy del diccionario ALIAS_TEAMS a TeamNormalizer.
    
    Args:
        db_path: Ruta a la base de datos SQLite
        dry_run: Si True, solo simula sin escribir en BD
        verbose: Si True, imprime progreso detallado
    
    Returns:
        Diccionario con estadísticas de migración
    """
    
    stats = {
        'total_aliases': len(ALIAS_TEAMS),
        'migrated': 0,
        'skipped_duplicate': 0,
        'new_teams_created': 0,
        'errors': [],
        'start_time': datetime.now().isoformat(),
    }
    
    print("\n" + "=" * 70)
    print("🔄 MIGRACIÓN DE ALIAS LEGACY → TEAM NORMALIZER")
    print("=" * 70)
    print(f"📂 Base de datos: {db_path}")
    print(f"📊 Total aliases a migrar: {len(ALIAS_TEAMS)}")
    print(f"🏃 Modo: {'DRY-RUN (sin cambios)' if dry_run else 'PRODUCCIÓN'}")
    print("=" * 70 + "\n")
    
    if dry_run:
        print("⚠️  MODO DRY-RUN: No se realizarán cambios en la base de datos\n")
    
    # Inicializar normalizer
    if not dry_run:
        normalizer = TeamNormalizer(db_path=db_path)
    
    # Track de equipos oficiales ya procesados (para evitar duplicados)
    teams_created = set()
    
    # Iterar sobre cada alias
    for alias, nombre_oficial in ALIAS_TEAMS.items():
        try:
            if verbose:
                print(f"  📝 Procesando: '{alias}' → '{nombre_oficial}'")
            
            if dry_run:
                # En dry-run solo mostramos lo que haríamos
                stats['migrated'] += 1
                if verbose:
                    print(f"     [DRY-RUN] Se agregaría alias")
                continue
            
            # ========== PASO A: Obtener o crear el equipo oficial ==========
            # Esto asegura que el equipo destino exista en la BD
            team_uuid, similarity = normalizer.normalize_team(
                team_name=nombre_oficial,
                create_if_missing=True
            )
            
            if not team_uuid:
                raise ValueError(f"No se pudo obtener/crear UUID para '{nombre_oficial}'")
            
            # Registrar si es un equipo nuevo
            if nombre_oficial not in teams_created:
                if similarity == 0.0:  # similarity=0 indica que fue creado nuevo
                    stats['new_teams_created'] += 1
                    if verbose:
                        print(f"     ✨ Equipo creado: {nombre_oficial} → {team_uuid[:8]}...")
                teams_created.add(nombre_oficial)
            
            # ========== PASO B: Registrar el alias ==========
            # Solo si el alias es diferente al nombre oficial
            if alias.lower() != nombre_oficial.lower():
                try:
                    alias_id = normalizer.add_alias(
                        team_uuid=team_uuid,
                        alias_name=alias,
                        priority=0,
                        source='legacy_shared_py'
                    )
                    stats['migrated'] += 1
                    
                    if verbose:
                        print(f"     ✓ Migrado: {alias} → {team_uuid[:8]}...")
                        
                except Exception as alias_error:
                    # El alias probablemente ya existe (constraint UNIQUE)
                    if 'UNIQUE constraint' in str(alias_error) or 'already exists' in str(alias_error).lower():
                        stats['skipped_duplicate'] += 1
                        if verbose:
                            print(f"     ⏭️  Alias ya existe, saltando...")
                    else:
                        raise alias_error
            else:
                # Alias igual al nombre oficial, no hace falta agregarlo
                stats['skipped_duplicate'] += 1
                if verbose:
                    print(f"     ⏭️  Alias igual a nombre oficial, saltando...")
                    
        except Exception as e:
            error_msg = f"Error con '{alias}' → '{nombre_oficial}': {str(e)}"
            stats['errors'].append(error_msg)
            print(f"     ❌ {error_msg}")
    
    # ========== RESUMEN FINAL ==========
    stats['end_time'] = datetime.now().isoformat()
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE MIGRACIÓN")
    print("=" * 70)
    print(f"  Total procesados:     {stats['total_aliases']}")
    print(f"  Migrados exitosamente: {stats['migrated']}")
    print(f"  Saltados (duplicados): {stats['skipped_duplicate']}")
    print(f"  Equipos nuevos creados: {stats['new_teams_created']}")
    print(f"  Errores:               {len(stats['errors'])}")
    
    if stats['errors']:
        print("\n⚠️  ERRORES ENCONTRADOS:")
        for err in stats['errors'][:10]:  # Mostrar máximo 10
            print(f"    • {err}")
        if len(stats['errors']) > 10:
            print(f"    ... y {len(stats['errors']) - 10} errores más")
    
    print("=" * 70)
    
    if not dry_run and stats['migrated'] > 0:
        print("\n✅ Migración completada exitosamente!")
        print(f"   Los alias legacy ahora están en: {db_path}")
    
    print()
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Migra ALIAS_TEAMS legacy a TeamNormalizer SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/migrate_legacy_aliases.py
  python scripts/migrate_legacy_aliases.py --dry-run
  python scripts/migrate_legacy_aliases.py --db data/custom.db --quiet
        """
    )
    
    parser.add_argument(
        '--db', '--database',
        type=str,
        default='data/databases/football_data.db',
        help='Ruta a la base de datos SQLite (default: data/databases/football_data.db)'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Simular migración sin escribir en la base de datos'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso (solo mostrar resumen)'
    )
    
    args = parser.parse_args()
    
    # Verificar que la base de datos existe o crear directorio
    db_path = Path(args.db)
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"📁 Creado directorio: {db_path.parent}")
    
    # Ejecutar migración
    stats = migrate_aliases(
        db_path=str(db_path),
        dry_run=args.dry_run,
        verbose=not args.quiet
    )
    
    # Exit code basado en errores
    sys.exit(1 if stats['errors'] else 0)


if __name__ == '__main__':
    main()
