"""
Unit tests for Quantitative Backtesting Engine
=============================================
"""

import pytest
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from analytics.backtester import Backtester, BacktestResult


def test_backtester_runs_and_calculates_metrics():
    backtester = Backtester()
    result = backtester.run_backtest(
        league_code='E0',
        temporadas=1,
        min_ev=0.02,
        stake_mode='flat',
        flat_stake=10.0,
        warmup_matches=5
    )

    assert isinstance(result, BacktestResult)
    assert result.league_code == 'E0'
    assert isinstance(result.summary(), str)


def test_backtester_with_synthetic_data():
    # Synthetic DataFrame with 30 matches
    teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Tottenham']
    rows = []
    for d in range(1, 31):
        h = teams[(d - 1) % len(teams)]
        a = teams[d % len(teams)]
        rows.append({
            'Date': f'2025-09-{d:02d}',
            'HomeTeam': h,
            'AwayTeam': a,
            'FTHG': (d % 3),
            'FTAG': ((d + 1) % 2),
            'FTR': 'H' if (d % 3) > ((d + 1) % 2) else ('A' if (d % 3) < ((d + 1) % 2) else 'D'),
            'HS': 10, 'AS': 8, 'HST': 5, 'AST': 4,
            'HC': 5, 'AC': 4, 'HY': 1, 'AY': 2, 'HR': 0, 'AR': 0,
            'HTHG': 0, 'HTAG': 0,
            'B365H': 2.10, 'B365D': 3.40, 'B365A': 3.60,
            'temporada': '2526', 'league_code': 'TEST'
        })
    df_synthetic = pd.DataFrame(rows)

    class MockProvider:
        def get_data_from_db(self, league_code, temporadas=1):
            return df_synthetic

    backtester = Backtester(provider=MockProvider())
    res_flat = backtester.run_backtest(
        league_code='TEST',
        min_ev=0.01,
        stake_mode='flat',
        flat_stake=10.0,
        warmup_matches=10
    )

    assert res_flat.total_matches_evaluated > 0
    assert res_flat.total_staked > 0
    assert 0.0 <= res_flat.brier_score_1x2 <= 2.0
    assert 0.0 <= res_flat.hit_rate_pct <= 100.0

    res_kelly = backtester.run_backtest(
        league_code='TEST',
        min_ev=0.01,
        stake_mode='kelly',
        kelly_fraction=0.25,
        warmup_matches=10
    )
    assert res_kelly.total_matches_evaluated > 0

