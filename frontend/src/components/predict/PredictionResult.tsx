import React from 'react';
import type { PredictResponse } from '@/lib/types';

interface PredictionResultProps {
  data: PredictResponse;
}

export default function PredictionResult({ data }: PredictionResultProps) {
  if (!data || !data.goles_esperados || !data.probabilidades) {
    return null;
  }

  const {
    local,
    visitante,
    liga,
    probabilidades,
    goles_esperados,
    mercados,
    corners,
    tarjetas,
    top_marcadores = [],
    recomendaciones = [],
  } = data;

  const xgLocalWidth = Math.min((goles_esperados.local / 4) * 100, 100);
  const xgVisWidth = Math.min((goles_esperados.visitante / 4) * 100, 100);

  return (
    <>
      {/* Header del Encuentro Analizado */}
      <div
        className="card border-0 mb-4"
        style={{
          background:
            'linear-gradient(90deg, rgba(6, 182, 212, 0.15) 0%, rgba(19, 29, 51, 0.8) 50%, rgba(244, 63, 94, 0.15) 100%)',
        }}
      >
        <div className="card-body text-center py-3">
          <h4 className="fw-bold mb-0">
            <span className="text-info">{local}</span>
            <span className="text-muted mx-2">vs</span>
            <span className="text-danger">{visitante}</span>
          </h4>
          <small className="text-muted">
            {liga || 'Análisis Estadístico'}
          </small>
        </div>
      </div>

      {/* Probabilidades 1X2 */}
      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="card h-100 text-center p-4 border-primary shadow">
            <span className="badge bg-info align-self-center mb-2">
              1 · LOCAL
            </span>
            <h6 className="text-secondary mb-1 text-truncate">{local}</h6>
            <div className="display-4 fw-bold text-info my-2">
              {probabilidades.local.toFixed(1)}%
            </div>
            <div className="progress mt-2" style={{ height: '6px' }}>
              <div
                className="progress-bar bg-primary"
                style={{ width: `${probabilidades.local}%` }}
              ></div>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 text-center p-4 shadow">
            <span className="badge bg-warning align-self-center mb-2 text-dark">
              X · EMPATE
            </span>
            <h6 className="text-secondary mb-1">Empate</h6>
            <div className="display-4 fw-bold text-warning my-2">
              {probabilidades.empate.toFixed(1)}%
            </div>
            <div className="progress mt-2" style={{ height: '6px' }}>
              <div
                className="progress-bar bg-warning"
                style={{ width: `${probabilidades.empate}%` }}
              ></div>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 text-center p-4 border-danger shadow">
            <span className="badge bg-danger align-self-center mb-2">
              2 · VISITANTE
            </span>
            <h6 className="text-secondary mb-1 text-truncate">{visitante}</h6>
            <div className="display-4 fw-bold text-danger my-2">
              {probabilidades.visitante.toFixed(1)}%
            </div>
            <div className="progress mt-2" style={{ height: '6px' }}>
              <div
                className="progress-bar bg-danger"
                style={{ width: `${probabilidades.visitante}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        {/* Goles Esperados (xG) */}
        <div className="col-md-6">
          <div className="card p-4 h-100 border-0 shadow">
            <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
              <i className="bi bi-bullseye text-warning"></i>
              <span>Goles Esperados (xG)</span>
            </h5>

            <div className="mb-3">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <span className="fw-semibold text-info">{local}</span>
                <span className="badge bg-dark fs-6">
                  {goles_esperados.local.toFixed(2)} xG
                </span>
              </div>
              <div className="progress" style={{ height: '8px' }}>
                <div
                  className="progress-bar bg-primary"
                  style={{ width: `${xgLocalWidth}%` }}
                ></div>
              </div>
            </div>

            <div className="mb-4">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <span className="fw-semibold text-danger">{visitante}</span>
                <span className="badge bg-dark fs-6">
                  {goles_esperados.visitante.toFixed(2)} xG
                </span>
              </div>
              <div className="progress" style={{ height: '8px' }}>
                <div
                  className="progress-bar bg-danger"
                  style={{ width: `${xgVisWidth}%` }}
                ></div>
              </div>
            </div>

            <hr className="border-secondary my-3" />

            {/* Mercados de Goles */}
            <div className="row text-center g-2">
              <div className="col-4">
                <div className="p-2 rounded bg-dark border border-secondary">
                  <small className="text-muted d-block mb-1">Over 1.5</small>
                  <span className="fw-bold fs-5 text-primary">
                    {mercados.over_15.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="col-4">
                <div className="p-2 rounded bg-dark border border-secondary">
                  <small className="text-muted d-block mb-1">Over 2.5</small>
                  <span className="fw-bold fs-5 text-success">
                    {mercados.over_25.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="col-4">
                <div className="p-2 rounded bg-dark border border-secondary">
                  <small className="text-muted d-block mb-1">Under 3.5</small>
                  <span className="fw-bold fs-5 text-info">
                    {mercados.under_35.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Marcadores Más Probables & Doble Oportunidad */}
        <div className="col-md-6">
          <div className="card p-4 h-100 border-0 shadow">
            <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
              <i className="bi bi-list-ol text-info"></i>
              <span>Marcadores Más Probables</span>
            </h5>

            {top_marcadores.length > 0 && (
              <div className="d-flex flex-column gap-2 mb-3">
                {top_marcadores.map((marcador, idx) => {
                  const pct =
                    marcador.prob <= 1
                      ? (marcador.prob * 100).toFixed(1)
                      : marcador.prob.toFixed(1);
                  return (
                    <div
                      key={`${marcador.marcador}-${idx}`}
                      className="d-flex justify-content-between align-items-center p-2 rounded bg-dark border border-secondary"
                    >
                      <div className="d-flex align-items-center gap-2">
                        <span className="badge bg-secondary">#{idx + 1}</span>
                        <span className="fs-5 fw-bold font-monospace">
                          {marcador.marcador}
                        </span>
                      </div>
                      <span className="badge bg-primary fs-6">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            )}

            <hr className="border-secondary my-3" />

            {/* Doble Oportunidad */}
            <div className="row text-center g-2">
              <div className="col-4">
                <div className="p-2 rounded bg-dark border border-secondary">
                  <small className="text-muted d-block mb-1">
                    1X (Local o Empate)
                  </small>
                  <span className="fw-bold fs-5 text-success">
                    {probabilidades.doble_oportunidad['1X'].toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="col-4">
                <div className="p-2 rounded bg-dark border border-secondary">
                  <small className="text-muted d-block mb-1">
                    X2 (Empate o Visita)
                  </small>
                  <span className="fw-bold fs-5 text-info">
                    {probabilidades.doble_oportunidad['X2'].toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="col-4">
                <div className="p-2 rounded bg-dark border border-secondary">
                  <small className="text-muted d-block mb-1">
                    12 (Cualquiera)
                  </small>
                  <span className="fw-bold fs-5 text-warning">
                    {probabilidades.doble_oportunidad['12'].toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Telemetría de Córners */}
      {corners && corners.total > 0 && (
        <div className="row mb-4">
          <div className="col-12">
            <div className="card p-4 border-0 shadow">
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
                <i className="bi bi-flag text-success"></i>
                <span>Telemetría de Córners</span>
              </h5>
              <div className="row text-center g-2">
                <div className="col-6 col-md-3">
                  <div className="p-3 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block mb-1">
                      Total Esperado
                    </small>
                    <span className="fs-4 fw-bold text-success">
                      {corners.total.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div className="col-6 col-md-3">
                  <div className="p-3 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block mb-1">
                      Over 8.5 Córners
                    </small>
                    <span className="fs-4 fw-bold text-primary">
                      {corners.over_85.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="col-6 col-md-3">
                  <div className="p-3 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block mb-1">
                      Over 9.5 Córners
                    </small>
                    <span className="fs-4 fw-bold text-info">
                      {corners.over_95.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="col-6 col-md-3">
                  <div className="p-3 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block mb-1">
                      Local +Córners
                    </small>
                    <span className="fs-4 fw-bold text-warning">
                      {corners.prob_local_mas_corners.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Telemetría de Tarjetas */}
      {tarjetas && tarjetas.amarillas_total > 0 && (
        <div className="row mb-4">
          <div className="col-12">
            <div className="card p-4 border-0 shadow">
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2">
                <i className="bi bi-card-heading text-warning"></i>
                <span>Telemetría de Tarjetas</span>
              </h5>

              <div className="row g-3 mb-3">
                <div className="col-md-6">
                  <div className="p-3 rounded bg-dark border border-secondary">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className="fw-semibold text-info">{local}</span>
                      <div>
                        <span className="badge bg-warning text-dark me-1">
                          🟨 {tarjetas.amarillas_local.toFixed(1)}
                        </span>
                        {tarjetas.rojas_local > 0.05 && (
                          <span className="badge bg-danger">
                            🟥 {tarjetas.rojas_local.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="progress" style={{ height: '6px' }}>
                      <div
                        className="progress-bar bg-warning"
                        style={{
                          width: `${Math.min(
                            (tarjetas.amarillas_local / 3) * 100,
                            100
                          )}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="p-3 rounded bg-dark border border-secondary">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className="fw-semibold text-danger">
                        {visitante}
                      </span>
                      <div>
                        <span className="badge bg-warning text-dark me-1">
                          🟨 {tarjetas.amarillas_visitante.toFixed(1)}
                        </span>
                        {tarjetas.rojas_visitante > 0.05 && (
                          <span className="badge bg-danger">
                            🟥 {tarjetas.rojas_visitante.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="progress" style={{ height: '6px' }}>
                      <div
                        className="progress-bar bg-warning"
                        style={{
                          width: `${Math.min(
                            (tarjetas.amarillas_visitante / 3) * 100,
                            100
                          )}%`,
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="row text-center g-2">
                <div className="col-4 col-md-2">
                  <div className="p-2 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block">Total Esp.</small>
                    <span className="fw-bold fs-6">
                      🟨 {tarjetas.amarillas_total.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div className="col-4 col-md-2">
                  <div className="p-2 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block">Over 2.5</small>
                    <span className="fw-bold fs-6 text-success">
                      {Math.round(tarjetas.over_25)}%
                    </span>
                  </div>
                </div>
                <div className="col-4 col-md-2">
                  <div className="p-2 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block">Over 3.5</small>
                    <span className="fw-bold fs-6 text-info">
                      {Math.round(tarjetas.over_35)}%
                    </span>
                  </div>
                </div>
                <div className="col-4 col-md-2">
                  <div className="p-2 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block">Over 4.5</small>
                    <span className="fw-bold fs-6 text-warning">
                      {Math.round(tarjetas.over_45)}%
                    </span>
                  </div>
                </div>
                <div className="col-4 col-md-2">
                  <div className="p-2 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block">Under 5.5</small>
                    <span className="fw-bold fs-6 text-primary">
                      {Math.round(tarjetas.under_55)}%
                    </span>
                  </div>
                </div>
                <div className="col-4 col-md-2">
                  <div className="p-2 rounded bg-dark border border-secondary">
                    <small className="text-muted d-block">🟥 Expulsión</small>
                    <span className="fw-bold fs-6 text-danger">
                      {Math.round(tarjetas.prob_roja)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Semáforo de Recomendaciones IA */}
      {recomendaciones.length > 0 && (
        <div className="row mb-4">
          <div className="col-12">
            <div className="card border-0 shadow">
              <div className="card-header bg-dark d-flex justify-content-between align-items-center flex-wrap gap-2">
                <h5 className="fw-bold mb-0 d-flex align-items-center gap-2">
                  <i className="bi bi-lightbulb text-warning"></i>
                  <span>Recomendaciones del Algoritmo</span>
                </h5>
                <div className="d-flex gap-1">
                  <span className="badge bg-secondary">⚽ Goles</span>
                  <span className="badge bg-secondary">🚩 Córners</span>
                  <span className="badge bg-secondary">🟨 Tarjetas</span>
                </div>
              </div>
              <div className="card-body">
                <div className="row g-3">
                  {recomendaciones.map((reco, idx) => (
                    <div key={`${reco.corto}-${idx}`} className="col-md-6 col-lg-4">
                      <div
                        className={`alert alert-${reco.class} d-flex align-items-center mb-0 h-100`}
                      >
                        <div
                          className="me-3 text-center"
                          style={{ minWidth: '45px' }}
                        >
                          <span className="fs-3 d-block">
                            {reco.emoji || '⚽'}
                          </span>
                          <span className="fs-5">{reco.icon}</span>
                        </div>
                        <div className="flex-grow-1">
                          <strong>{reco.corto}</strong>
                          <div className="small text-muted">{reco.texto}</div>
                          <div
                            className="progress mt-2"
                            style={{ height: '6px' }}
                          >
                            <div
                              className={`progress-bar bg-${reco.class}`}
                              style={{ width: `${reco.prob}%` }}
                            ></div>
                          </div>
                          <small className="fw-bold d-block mt-1">
                            {reco.prob}% confianza
                          </small>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
