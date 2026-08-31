"""
Quantitative Backtesting Engine
===============================
Motor de backtesting histórico sobre datos reales de football_data.db.
Evalúa calibración probabilística (Brier Score, Log Loss) y rendimiento financiero (Yield, ROI, Kelly, Drawdown).
"""

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Literal

import numpy as np
import pandas as pd

from db_data_provider import DatabaseDataProvider
from core.prediction import calcular_fuerzas, predecir_partido
from utils.markets import calcular_valor_esperado, calcular_criterio_kelly, evaluar_value_bets

logger = logging.getLogger(__name__)


@dataclass
class BetRecord:
    date: str
    match: str
    market: str
    odds: float
    model_prob: float
    ev_pct: float
    stake: float
    outcome: str  # 'WON' or 'LOST'
    profit: float
    bankroll_after: float


@dataclass
class BacktestResult:
    league_code: str
    total_matches_evaluated: int
    total_bets_placed: int
    bets_won: int
    bets_lost: int
    hit_rate_pct: float
    total_staked: float
    total_returned: float
    net_profit: float
    roi_pct: float
    brier_score_1x2: float
    max_drawdown_pct: float
    initial_bankroll: float
    final_bankroll: float
    bet_history: List[BetRecord] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"==================================================\n"
            f"📊 RESULTADO DE BACKTESTING - LIGA {self.league_code}\n"
            f"==================================================\n"
            f"Partidos evaluados:     {self.total_matches_evaluated}\n"
            f"Apuestas realizadas:    {self.total_bets_placed}\n"
            f"Aciertos / Fallos:      {self.bets_won} / {self.bets_lost} ({self.hit_rate_pct:.1f}% acierto)\n"
            f"Total Apostado:         ${self.total_staked:.2f}\n"
            f"Ganancia Neta:          ${self.net_profit:+.2f}\n"
            f"Yield / ROI:            {self.roi_pct:+.2f}%\n"
            f"Brier Score (1X2):      {self.brier_score_1x2:.4f} (menor es mejor)\n"
            f"Max Drawdown:           {self.max_drawdown_pct:.2f}%\n"
            f"Bankroll Inicial/Final: ${self.initial_bankroll:.2f} -> ${self.final_bankroll:.2f}\n"
            f"=================================================="
        )


class Backtester:
    """
    Ejecutor de simulaciones históricas y validación probabilística.
    """

    def __init__(self, provider: Optional[DatabaseDataProvider] = None):
        self.provider = provider or DatabaseDataProvider()

    def run_backtest(
        self,
        league_code: str = 'E0',
        temporadas: int = 2,
        min_ev: float = 0.05,
        stake_mode: Literal['flat', 'kelly'] = 'flat',
        flat_stake: float = 10.0,
        kelly_fraction: float = 0.25,
        initial_bankroll: float = 1000.0,
        warmup_matches: int = 40
    ) -> BacktestResult:
        """
        Ejecuta el backtest cronológico sobre una liga histórica.
        """
        df = self.provider.get_data_from_db(league_code, temporadas=temporadas)
        if df is None or len(df) < warmup_matches + 10:
            logger.warning(f"Insuficientes partidos para backtest en {league_code}")
            return BacktestResult(
                league_code=league_code,
                total_matches_evaluated=0,
                total_bets_placed=0,
                bets_won=0,
                bets_lost=0,
                hit_rate_pct=0.0,
                total_staked=0.0,
                total_returned=0.0,
                net_profit=0.0,
                roi_pct=0.0,
                brier_score_1x2=0.0,
                max_drawdown_pct=0.0,
                initial_bankroll=initial_bankroll,
                final_bankroll=initial_bankroll
            )

        # Ordenar cronológicamente (más antiguo al más reciente)
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, format='mixed', errors='coerce')
        df = df.sort_values('Date').reset_index(drop=True)

        bankroll = initial_bankroll
        peak_bankroll = initial_bankroll
        max_drawdown = 0.0

        brier_sum = 0.0
        brier_count = 0

        bet_history: List[BetRecord] = []
        total_staked = 0.0
        total_returned = 0.0
        bets_won = 0
        bets_lost = 0

        total_evaluated = 0

        fuerzas, ml, mv = None, 0.0, 0.0
        last_calc_idx = -1

        # Iterar a lo largo del tiempo (walk-forward test)
        for i in range(warmup_matches, len(df)):
            match = df.iloc[i]

            home_team = match.get('HomeTeam')
            away_team = match.get('AwayTeam')
            fthg = match.get('FTHG')
            ftag = match.get('FTAG')
            ftr = match.get('FTR')
            b365h = match.get('B365H')
            b365d = match.get('B365D')
            b365a = match.get('B365A')

            if pd.isna(home_team) or pd.isna(away_team) or pd.isna(fthg) or pd.isna(ftag):
                continue

            # Recalcular fuerzas por jornada (cada 8 partidos) con datos históricos disponibles
            if fuerzas is None or (i - last_calc_idx) >= 8:
                df_history = df.iloc[:i]
                fuerzas, ml, mv = calcular_fuerzas(df_history)
                last_calc_idx = i

            if home_team not in fuerzas or away_team not in fuerzas:
                continue

            pred = predecir_partido(home_team, away_team, fuerzas, ml, mv)
            if not pred:
                continue

            total_evaluated += 1

            # 1. Brier Score Calculation
            p_h = pred.get('Prob_Local', 0.0)
            p_d = pred.get('Prob_Empate', 0.0)
            p_a = pred.get('Prob_Vis', 0.0)

            y_h = 1.0 if ftr == 'H' else 0.0
            y_d = 1.0 if ftr == 'D' else 0.0
            y_a = 1.0 if ftr == 'A' else 0.0

            brier_match = (p_h - y_h) ** 2 + (p_d - y_d) ** 2 + (p_a - y_a) ** 2
            brier_sum += brier_match
            brier_count += 1

            # 2. Value Betting Simulation
            odds_dict = {}
            if pd.notna(b365h) and float(b365h) > 1.0:
                odds_dict['B365H'] = float(b365h)
            if pd.notna(b365d) and float(b365d) > 1.0:
                odds_dict['B365D'] = float(b365d)
            if pd.notna(b365a) and float(b365a) > 1.0:
                odds_dict['B365A'] = float(b365a)

            if not odds_dict:
                continue

            value_bets = evaluar_value_bets(pred, odds_dict, min_ev=min_ev)
            if not value_bets:
                continue

            # Tomar la mejor value bet para el partido
            best_bet = value_bets[0]
            market_name = best_bet['mercado']
            cuota = best_bet['cuota']
            model_p = best_bet['prob_modelo'] / 100.0
            ev_val = best_bet['ev_pct']

            # Calcular tamaño de apuesta
            if stake_mode == 'kelly':
                stake_pct = calcular_criterio_kelly(model_p, cuota, fraccion=kelly_fraction)
                stake = (bankroll * (stake_pct / 100.0))
            else:
                stake = flat_stake

            if stake <= 0 or bankroll < stake:
                continue

            # Evaluar si la apuesta ganó
            won = False
            if 'Local' in market_name and ftr == 'H':
                won = True
            elif 'Empate' in market_name and ftr == 'D':
                won = True
            elif 'Visitante' in market_name and ftr == 'A':
                won = True
            elif 'Más de 2.5' in market_name and (fthg + ftag) > 2.5:
                won = True
            elif 'Menos de 2.5' in market_name and (fthg + ftag) < 2.5:
                won = True

            total_staked += stake
            if won:
                payout = stake * cuota
                profit = payout - stake
                total_returned += payout
                bankroll += profit
                bets_won += 1
                outcome = 'WON'
            else:
                profit = -stake
                bankroll -= stake
                bets_lost += 1
                outcome = 'LOST'

            # Actualizar Drawdown
            if bankroll > peak_bankroll:
                peak_bankroll = bankroll
            dd = (peak_bankroll - bankroll) / peak_bankroll * 100.0 if peak_bankroll > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd

            bet_history.append(BetRecord(
                date=str(match['Date'])[:10],
                match=f"{home_team} vs {away_team}",
                market=market_name,
                odds=cuota,
                model_prob=model_p,
                ev_pct=ev_val,
                stake=round(stake, 2),
                outcome=outcome,
                profit=round(profit, 2),
                bankroll_after=round(bankroll, 2)
            ))

        total_bets = bets_won + bets_lost
        hit_rate = (bets_won / total_bets * 100.0) if total_bets > 0 else 0.0
        net_profit = total_returned - total_staked
        roi = (net_profit / total_staked * 100.0) if total_staked > 0 else 0.0
        avg_brier = (brier_sum / brier_count) if brier_count > 0 else 0.0

        return BacktestResult(
            league_code=league_code,
            total_matches_evaluated=total_evaluated,
            total_bets_placed=total_bets,
            bets_won=bets_won,
            bets_lost=bets_lost,
            hit_rate_pct=round(hit_rate, 2),
            total_staked=round(total_staked, 2),
            total_returned=round(total_returned, 2),
            net_profit=round(net_profit, 2),
            roi_pct=round(roi, 2),
            brier_score_1x2=round(avg_brier, 4),
            max_drawdown_pct=round(max_drawdown, 2),
            initial_bankroll=initial_bankroll,
            final_bankroll=round(bankroll, 2),
            bet_history=bet_history
        )
