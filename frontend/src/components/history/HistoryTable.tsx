import React from 'react';
import Link from 'next/link';
import type { HistoryResultRow } from '@/lib/types';

interface HistoryTableProps {
  resultados: HistoryResultRow[];
  leagueCode: string;
}

function renderPrediccionIA(r: HistoryResultRow) {
  if (!r.prediccion_ia) {
    return (
      <span className="badge bg-secondary text-muted">
        <i className="bi bi-question-circle"></i> Sin Datos
      </span>
    );
  }
  const prob = Math.trunc(
    r.prediccion_prob ??
      (r.prediccion_ia === 'HOME_WIN'
        ? r.prob_local ?? 0
        : r.prediccion_ia === 'AWAY_WIN'
        ? r.prob_visitante ?? 0
        : r.prob_empate ?? 0)
  );

  switch (r.prediccion_ia) {
    case 'HOME_WIN':
      return (
        <span className="badge bg-info">
          <i className="bi bi-house-fill"></i> 1 · Local {prob}%
        </span>
      );
    case 'AWAY_WIN':
      return (
        <span className="badge bg-danger">
          <i className="bi bi-airplane-fill"></i> 2 · Visita {prob}%
        </span>
      );
    case '1X':
      return (
        <span className="badge bg-success">
          <i className="bi bi-check2-all"></i> 1X {prob}%
        </span>
      );
    case 'X2':
      return (
        <span className="badge bg-warning text-dark">
          <i className="bi bi-check2-all"></i> X2 {prob}%
        </span>
      );
    case '12':
      return (
        <span
          className="badge bg-purple"
          style={{ backgroundColor: '#8b5cf6', color: '#fff' }}
        >
          <i className="bi bi-lightning-fill"></i> 12 {prob}%
        </span>
      );
    default:
      return (
        <span className="badge bg-secondary">
          <i className="bi bi-dash-lg"></i> Empate {Math.trunc(r.prob_empate ?? 0)}%
        </span>
      );
  }
}

export default function HistoryTable({
  resultados,
  leagueCode,
}: HistoryTableProps) {
  if (!resultados.length) {
    return (
      <div className="card border-0 text-center py-5">
        <div className="card-body">
          <i className="bi bi-calendar-x display-1 text-muted mb-3 d-block"></i>
          <h4 className="fw-bold">No hay partidos en este período</h4>
          <p className="text-muted small mb-3">
            Selecciona otra liga o aumenta el rango de días para auditar.
          </p>
          <Link
            href={`/history?league_code=${leagueCode}&days=30`}
            className="btn btn-outline-primary btn-sm"
          >
            Ver últimos 30 días
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="card border-0 shadow">
      <div className="card-header bg-dark d-flex justify-content-between align-items-center">
        <h5 className="mb-0 fw-bold fs-6 d-flex align-items-center gap-2">
          <i className="bi bi-table text-primary"></i> Detalle de Partidos
          Auditados
        </h5>
        <span className="badge bg-secondary">{resultados.length} partidos</span>
      </div>
      <div className="table-responsive">
        <table className="table table-hover align-middle mb-0">
          <thead>
            <tr>
              <th className="ps-4" style={{ width: '110px' }}>
                Fecha
              </th>
              <th style={{ width: '25%' }}>Local</th>
              <th style={{ width: '25%' }}>Visitante</th>
              <th className="text-center" style={{ width: '100px' }}>
                Resultado
              </th>
              <th className="text-center" style={{ width: '160px' }}>
                Predicción IA
              </th>
              <th className="text-center pe-4" style={{ width: '120px' }}>
                Estado
              </th>
            </tr>
          </thead>
          <tbody>
            {resultados.map((r, idx) => (
              <tr key={`${r.fecha}-${r.local}-${r.visitante}-${idx}`}>
                <td className="ps-4 text-muted small">{r.fecha}</td>
                <td>
                  <span className="fw-semibold">{r.local}</span>
                  {r.resultado_real === 'HOME_WIN' && (
                    <i
                      className="bi bi-trophy-fill text-warning ms-1"
                      title="Ganador"
                    ></i>
                  )}
                </td>
                <td>
                  <span className="fw-semibold">{r.visitante}</span>
                  {r.resultado_real === 'AWAY_WIN' && (
                    <i
                      className="bi bi-trophy-fill text-warning ms-1"
                      title="Ganador"
                    ></i>
                  )}
                </td>
                <td className="text-center">
                  <span className="badge bg-dark border border-secondary fs-6 px-3 py-1 font-monospace">
                    {r.goles_local} - {r.goles_visitante}
                  </span>
                </td>
                <td className="text-center">{renderPrediccionIA(r)}</td>
                <td className="text-center pe-4">
                  {r.acierto === true ? (
                    <span className="badge bg-success px-3 py-1">
                      ✅ ACIERTO
                    </span>
                  ) : r.acierto === false ? (
                    <span className="badge bg-danger px-3 py-1">❌ FALLO</span>
                  ) : (
                    <span className="badge bg-secondary px-3 py-1">
                      <i className="bi bi-dash"></i> N/A
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card-footer text-center text-muted small">
        <i className="bi bi-info-circle me-1"></i>
        La IA predice el desenlace con mayor valor estadístico según Poisson.
        Tasa esperada en fútbol: 40-55% (33% = azar).
      </div>
    </div>
  );
}
