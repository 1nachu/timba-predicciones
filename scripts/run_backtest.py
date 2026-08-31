#!/usr/bin/env python3
"""
CLI Runner for Backtesting Engine
=================================
Ejecuta backtests cuantitativos sobre ligas históricas.

Uso:
    python scripts/run_backtest.py --league E0 --seasons 2 --min-ev 0.05
    python scripts/run_backtest.py --league SP1 --stake-mode kelly --kelly-fraction 0.25
"""

import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from analytics.backtester import Backtester


def main():
    parser = argparse.ArgumentParser(description="Timba Predictor Quantitative Backtester")
    parser.add_argument('--league', type=str, default='E0', help='Código de liga (E0, SP1, D1, I1, F1, ARG, etc.)')
    parser.add_argument('--seasons', type=int, default=2, help='Número de temporadas históricas a incluir')
    parser.add_argument('--min-ev', type=float, default=0.04, help='Umbral mínimo de EV (default: 0.04 = 4%%)')
    parser.add_argument('--stake-mode', type=str, choices=['flat', 'kelly'], default='flat', help='Modo de stake (flat o kelly)')
    parser.add_argument('--flat-stake', type=float, default=10.0, help='Monto fijo por apuesta')
    parser.add_argument('--kelly-fraction', type=float, default=0.25, help='Fracción de Kelly (default: 0.25)')
    parser.add_argument('--bankroll', type=float, default=1000.0, help='Bankroll inicial')

    args = parser.parse_args()

    print(f"🚀 Iniciando Backtesting para liga {args.league.upper()}...")
    backtester = Backtester()
    result = backtester.run_backtest(
        league_code=args.league.upper(),
        temporadas=args.seasons,
        min_ev=args.min_ev,
        stake_mode=args.stake_mode,
        flat_stake=args.flat_stake,
        kelly_fraction=args.kelly_fraction,
        initial_bankroll=args.bankroll
    )

    print(result.summary())


if __name__ == '__main__':
    main()
