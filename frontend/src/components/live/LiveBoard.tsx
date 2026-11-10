'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import useSWR from 'swr';
import { apiFetch } from '@/lib/api';
import type { LiveMatch, LiveResponse } from '@/lib/types';
import LocalTime from '@/components/LocalTime';

interface LiveBoardProps {
  initialData: LiveResponse;
}

function getLeagueName(p: LiveMatch): string {
  return p.competition?.name || p.league || 'Liga';
}

function parseScores(p: LiveMatch): { homeScore: number; awayScore: number } {
  if (p.score && typeof p.score === 'object' && p.score.fullTime) {
    return {
      homeScore: p.score.fullTime.home ?? 0,
      awayScore: p.score.fullTime.away ?? 0,
    };
  }
  if (typeof p.score === 'string' && p.score.includes('-')) {
    const clean = p.score.replace(/\s+/g, '');
    const parts = clean.split('-');
    return {
      homeScore: Number(parts[0]) || 0,
      awayScore: Number(parts[1]) || 0,
    };
  }
  return {
    homeScore: p.home_score ?? 0,
    awayScore: p.away_score ?? 0,
  };
}

function groupByLeague(matches: LiveMatch[]) {
  const groups: Array<{
    leagueName: string;
    countryName: string;
    items: LiveMatch[];
  }> = [];

  for (const match of matches) {
    const leagueName = getLeagueName(match);
    const countryName = match.competition?.area?.name || '';
    const lastGroup = groups[groups.length - 1];
    if (!lastGroup || lastGroup.leagueName !== leagueName) {
      groups.push({ leagueName, countryName, items: [match] });
    } else {
      lastGroup.items.push(match);
    }
  }
  return groups;
}

function MatchSection({
  matches,
  showInlinePrediction,
}: {
  matches: LiveMatch[];
  showInlinePrediction: boolean;
}) {
  const groups = groupByLeague(matches);

  return (
    <>
      {groups.map((group, gIdx) => (
        <div key={`${group.leagueName}-${gIdx}`} className="league-section mb-3">
          <div className="league-header">
            <i className="bi bi-trophy-fill text-warning"></i>
            <span className="league-name">{group.leagueName.toUpperCase()}</span>
            {group.countryName && (
              <span className="league-country text-muted small">
                {group.countryName}
              </span>
            )}
          </div>
          <table className="matches-table">
            <tbody>
              {group.items.map((partido, idx) => {
                const isLive = [
                  'IN_PLAY',
                  'LIVE',
                  'EN VIVO',
                  'PAUSED',
                ].includes(partido.status);
                const isFinished = partido.status === 'FINISHED';
                const isHalftime = partido.status === 'PAUSED';
                const matchMinute =
                  typeof partido.minute === 'number' ? partido.minute : 0;
                const { homeScore, awayScore } = parseScores(partido);
                const homeTeam =
                  partido.homeTeam?.name || partido.home || 'Local';
                const awayTeam =
                  partido.awayTeam?.name || partido.away || 'Visitante';

                const showPredRow =
                  showInlinePrediction &&
                  isLive &&
                  Boolean(
                    partido.prediccion_live ||
                      partido.prediccion_prematch ||
                      partido.prediccion_timba
                  );

                return (
                  <React.Fragment key={`${homeTeam}-${awayTeam}-${idx}`}>
                    <tr
                      className={`match-row ${
                        isLive
                          ? 'match-live'
                          : isFinished
                          ? 'match-finished'
                          : ''
                      }`}
                      data-timestamp={partido._timestamp ?? 0}
                    >
                      <td className="match-status-cell">
                        {isLive ? (
                          <div className="status-badge status-live">
                            {isHalftime ? (
                              <span>ET</span>
                            ) : matchMinute > 0 ? (
                              <span>{matchMinute}&apos;</span>
                            ) : (
                              <span>LIVE</span>
                            )}
                          </div>
                        ) : isFinished ? (
                          <div className="status-badge status-finished">FIN</div>
                        ) : (
                          <div className="status-badge status-scheduled">
                            {partido.utcDate ? (
                              <LocalTime
                                utc={partido.utcDate}
                                fallback="--:--"
                                display="time"
                              />
                            ) : (
                              'PROG'
                            )}
                          </div>
                        )}
                      </td>

                      <td className="team-cell team-home">
                        <span className="team-name">{homeTeam}</span>
                        {(partido.prediccion_timba?.prob_local ?? 0) > 55 && (
                          <span
                            className="badge bg-warning text-dark ms-1"
                            title={`Favorito IA ${Math.trunc(
                              partido.prediccion_timba?.prob_local ?? 0
                            )}%`}
                          >
                            ★
                          </span>
                        )}
                      </td>

                      <td className="score-cell">
                        <div
                          className={`score-box ${
                            isLive
                              ? 'score-live'
                              : isFinished
                              ? 'score-final'
                              : ''
                          }`}
                        >
                          <span>{homeScore}</span>
                          <span className="text-muted opacity-50">-</span>
                          <span>{awayScore}</span>
                        </div>
                      </td>

                      <td className="team-cell team-away">
                        {(partido.prediccion_timba?.prob_visitante ?? 0) >
                          55 && (
                          <span
                            className="badge bg-warning text-dark me-1"
                            title={`Favorito IA ${Math.trunc(
                              partido.prediccion_timba?.prob_visitante ?? 0
                            )}%`}
                          >
                            ★
                          </span>
                        )}
                        <span className="team-name">{awayTeam}</span>
                      </td>

                      <td className="stats-cell d-none d-md-table-cell text-center">
                        {partido.prediccion_timba?.over_25 !== undefined ? (
                          <span
                            className="badge bg-dark border border-secondary"
                            title={`Over 2.5: ${Math.trunc(
                              partido.prediccion_timba.over_25
                            )}%`}
                          >
                            O2.5:{' '}
                            {Math.trunc(partido.prediccion_timba.over_25)}%
                          </span>
                        ) : partido.prediccion_timba?.prob_local !==
                          undefined ? (
                          <span
                            className="badge bg-dark border border-secondary"
                            title="Prob Local"
                          >
                            1:{' '}
                            {Math.trunc(partido.prediccion_timba.prob_local)}%
                          </span>
                        ) : null}
                      </td>
                    </tr>

                    {showPredRow && (
                      <tr className="pred-row">
                        <td colSpan={5}>
                          <div className="pred-inline py-1 d-flex flex-wrap align-items-center gap-2">
                            {partido.prediccion_live && (
                              <>
                                <span className="badge bg-danger text-white">
                                  <i className="bi bi-lightning-charge-fill"></i>{' '}
                                  EN VIVO ({partido.prediccion_live.minuto}&apos;)
                                </span>
                                <span className="pred-item text-info">
                                  <b>1:</b> {partido.prediccion_live.prob_local}%
                                </span>
                                <span className="pred-item text-warning">
                                  <b>X:</b> {partido.prediccion_live.prob_empate}
                                  %
                                </span>
                                <span className="pred-item text-danger">
                                  <b>2:</b>{' '}
                                  {partido.prediccion_live.prob_visitante}%
                                </span>
                                <span className="text-muted small">|</span>
                                <span
                                  className="text-secondary small"
                                  title="Goles esperados restantes"
                                >
                                  xG rem:{' '}
                                  <b>
                                    {
                                      partido.prediccion_live
                                        .xG_restante_local
                                    }
                                    -
                                    {partido.prediccion_live.xG_restante_vis}
                                  </b>
                                </span>
                                {partido.prediccion_live.proximo_gol && (
                                  <span
                                    className="badge bg-dark border border-secondary text-info small"
                                    title="Próximo Gol"
                                  >
                                    Próx. gol:{' '}
                                    <b>
                                      {
                                        partido.prediccion_live.proximo_gol
                                          .local
                                      }
                                      % Local /{' '}
                                      {
                                        partido.prediccion_live.proximo_gol
                                          .visitante
                                      }
                                      % Vis
                                    </b>
                                  </span>
                                )}
                                <span className="badge bg-secondary opacity-75 small">
                                  {partido.prediccion_live.estado_tactico}
                                </span>
                              </>
                            )}

                            {partido.prediccion_prematch && (
                              <div className="w-100 mt-1 d-flex align-items-center gap-2 text-muted small border-top border-secondary pt-1">
                                <span className="badge bg-dark border border-secondary text-muted">
                                  PRE-MATCH
                                </span>
                                <span>
                                  <b>1:</b>{' '}
                                  {partido.prediccion_prematch.prob_local}%
                                </span>
                                <span>
                                  <b>X:</b>{' '}
                                  {partido.prediccion_prematch.prob_empate}%
                                </span>
                                <span>
                                  <b>2:</b>{' '}
                                  {partido.prediccion_prematch.prob_visitante}%
                                </span>
                                {partido.prediccion_prematch.xg_local !==
                                  undefined && (
                                  <span>
                                    xG inicial:{' '}
                                    {partido.prediccion_prematch.xg_local}-
                                    {partido.prediccion_prematch.xg_vis}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}

export default function LiveBoard({ initialData }: LiveBoardProps) {
  const { data, mutate } = useSWR<LiveResponse>(
    '/api/v1/live',
    (url: string) => apiFetch<LiveResponse>(url),
    {
      fallbackData: initialData,
      refreshInterval: 15000,
    }
  );

  const [updateTime, setUpdateTime] = useState('--:--');
  const [countdown, setCountdown] = useState(15);

  const partidos = data?.partidos || [];
  const esDemo = data?.es_demo || false;

  useEffect(() => {
    const now = new Date();
    setUpdateTime(
      now.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    );
    setCountdown(15);
  }, [data]);

  useEffect(() => {
    if (!partidos.length) return;
    const timer = setInterval(() => {
      setCountdown((prev) => (prev <= 1 ? 15 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [partidos.length]);

  const partidosLive = partidos.filter((p) => p.seccion === 'live');
  const partidosProximos = partidos.filter((p) => p.seccion === 'proximos');

  return (
    <div className="container-fluid px-0 px-md-2 py-1 live-container">
      {/* Header Live */}
      <div className="live-page-header d-flex justify-content-between align-items-center mb-3">
        <div className="d-flex align-items-center gap-2">
          <span className="live-dot"></span>
          <h1 className="live-title mb-0">PARTIDOS EN VIVO</h1>
        </div>
        <div className="d-flex align-items-center gap-2">
          <span className="badge bg-dark border border-secondary" id="lastUpdate">
            <i className="bi bi-clock text-info me-1"></i>{' '}
            <span id="updateTime">{updateTime}</span>
          </span>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={() => mutate()}
            title="Recargar ahora"
          >
            <i className="bi bi-arrow-clockwise"></i>
          </button>
        </div>
      </div>

      {esDemo && (
        <div className="alert alert-warning d-flex align-items-center gap-2 mb-3 py-2">
          <i className="bi bi-info-circle"></i>
          <span>MODO DEMO — Datos simulados de ejemplo</span>
        </div>
      )}

      {partidos.length > 0 ? (
        <>
          {partidosLive.length > 0 ? (
            <>
              <div className="d-flex align-items-center gap-2 mb-2">
                <span className="live-dot"></span>
                <span className="text-white fw-bold">EN VIVO AHORA</span>
                <span className="badge bg-danger">{partidosLive.length}</span>
              </div>
              <MatchSection matches={partidosLive} showInlinePrediction={true} />
            </>
          ) : (
            <div className="alert alert-dark text-center py-3 mb-3">
              <i className="bi bi-broadcast me-2 text-muted"></i>No hay partidos
              en juego en este momento
            </div>
          )}

          {partidosProximos.length > 0 && (
            <>
              <div className="d-flex align-items-center gap-2 mt-4 mb-2">
                <i className="bi bi-clock text-warning"></i>
                <span className="text-white fw-bold">PRÓXIMOS HOY</span>
                <span className="badge bg-secondary">
                  {partidosProximos.length}
                </span>
              </div>
              <MatchSection
                matches={partidosProximos}
                showInlinePrediction={false}
              />
            </>
          )}

          <div className="text-center mt-3 text-muted small">
            <i className="bi bi-arrow-repeat spin me-1"></i>
            Actualización automática en{' '}
            <span id="countdown" className="fw-bold text-info">
              {countdown}
            </span>
            s
          </div>
        </>
      ) : (
        <div className="card border-0 text-center py-5">
          <div className="card-body">
            <i className="bi bi-calendar-x display-1 text-muted mb-3 d-block"></i>
            <h4 className="fw-bold">No hay partidos en vivo</h4>
            <p className="text-muted small mb-4">
              No se registran partidos activos en este instante
            </p>
            <div className="d-flex justify-content-center gap-2">
              <Link href="/fixtures" className="btn btn-primary btn-sm">
                <i className="bi bi-calendar3"></i> Ver Fixtures
              </Link>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={() => mutate()}
              >
                <i className="bi bi-arrow-clockwise"></i> Recargar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
