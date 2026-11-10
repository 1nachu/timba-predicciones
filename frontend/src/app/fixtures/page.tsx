import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { getFixtures } from '@/lib/api';
import { getLeagueFlag } from '@/lib/leagues';
import LeagueSelect from '@/components/fixtures/LeagueSelect';
import ProbabilityBar from '@/components/ProbabilityBar';
import LocalTime from '@/components/LocalTime';
import AlertList from '@/components/AlertList';

export const metadata: Metadata = {
  title: 'Próximos Partidos — Timba Predictor',
  description:
    'Fixture con predicciones automáticas para Premier League, La Liga, Liga Argentina y más.',
  openGraph: {
    title: 'Próximos Partidos — Timba Predictor',
    description:
      'Fixture con predicciones automáticas para Premier League, La Liga, Liga Argentina y más.',
  },
  alternates: { canonical: '/fixtures' },
};

type SearchParams = Promise<{ liga_id?: string }>;

export default async function FixturesPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { liga_id } = await searchParams;
  const requestedLigaId = Number(liga_id || 1) || 1;
  const data = await getFixtures(requestedLigaId);
  const { partidos, liga_actual, liga_id: activeLigaId, avisos } = data;

  return (
    <>
      <AlertList avisos={avisos} />

      <div className="row align-items-center mb-4 g-3">
        <div className="col-md-7">
          <h1 className="h3 fw-bold mb-1 d-flex align-items-center gap-2">
            <i className="bi bi-calendar3 text-success"></i>
            <span>Próximos Partidos</span>
          </h1>
          <p className="text-muted small mb-0">
            Análisis matemático y probabilidades calculadas para la fecha venidera
          </p>
        </div>
        <div className="col-md-5">
          <div className="d-flex align-items-center gap-2 justify-content-md-end">
            <label className="form-label mb-0 text-muted small text-nowrap d-none d-sm-inline">
              Liga:
            </label>
            <LeagueSelect ligaId={activeLigaId} basePath="/fixtures" />
          </div>
        </div>
      </div>

      {/* Barra de Liga Actual */}
      <div
        className="card mb-4 border-0"
        style={{
          background:
            'linear-gradient(90deg, rgba(16, 185, 129, 0.12) 0%, rgba(15, 23, 42, 0.6) 100%)',
          borderLeft: '4px solid var(--accent-emerald)',
        }}
      >
        <div className="card-body py-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div className="d-flex align-items-center gap-2">
            <span className="fs-4">{getLeagueFlag(liga_actual.nombre)}</span>
            <div>
              <strong className="fs-6 d-block">{liga_actual.nombre}</strong>
              <span className="text-muted small">Temporada Oficial</span>
            </div>
          </div>
          <span className="badge bg-primary fs-6 px-3 py-2">
            <i className="bi bi-calendar-event me-1"></i> {partidos.length}{' '}
            partidos
          </span>
        </div>
      </div>

      {/* VISTA MÓVIL */}
      <div className="d-block d-md-none">
        {partidos.length > 0 ? (
          partidos.map((partido, idx) => {
            const reco = partido.recomendacion || partido.mejor_recomendacion;
            const predictHref = `/predict?liga_id=${activeLigaId}&local=${encodeURIComponent(
              partido.local
            )}&visitante=${encodeURIComponent(partido.visitante)}`;

            return (
              <div
                key={`mob-${partido.local}-${partido.visitante}-${idx}`}
                className="card mb-3 border-0 shadow-sm"
              >
                <div className="card-header bg-dark py-2 d-flex justify-content-between align-items-center">
                  <small className="text-muted d-flex align-items-center gap-1">
                    <i className="bi bi-clock"></i>
                    {partido.fecha_utc ? (
                      <LocalTime
                        utc={partido.fecha_utc}
                        fallback={partido.fecha}
                        display="datetime"
                      />
                    ) : (
                      partido.fecha
                    )}
                  </small>
                  {reco && (
                    <span className="badge bg-success">
                      <i className="bi bi-lightning-charge-fill"></i> {reco}
                    </span>
                  )}
                </div>
                <div className="card-body">
                  <div className="row align-items-center text-center mb-3 g-2">
                    <div className="col-5">
                      <span className="fw-bold text-truncate d-block">
                        {partido.local}
                      </span>
                    </div>
                    <div className="col-2">
                      <span className="badge bg-secondary">vs</span>
                    </div>
                    <div className="col-5">
                      <span className="fw-bold text-truncate d-block">
                        {partido.visitante}
                      </span>
                    </div>
                  </div>

                  {partido.prediccion ? (
                    <ProbabilityBar
                      prediccion={partido.prediccion}
                      variant="mobile"
                    />
                  ) : (
                    <div className="text-center mb-3">
                      <span className="badge bg-dark text-muted">
                        Sin datos históricos suficientes
                      </span>
                    </div>
                  )}

                  <div className="d-grid">
                    <Link
                      href={predictHref}
                      className="btn btn-outline-primary btn-sm"
                    >
                      <i className="bi bi-magic"></i> Analizar Partido Completo
                    </Link>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="card border-0">
            <div className="card-body text-center py-5">
              <i className="bi bi-calendar-x display-1 text-muted mb-3 d-block"></i>
              <h5>No hay partidos programados</h5>
              <p className="text-muted small">
                Intenta seleccionar otra liga en el menú superior
              </p>
            </div>
          </div>
        )}
      </div>

      {/* VISTA DESKTOP */}
      <div className="card d-none d-md-block border-0 shadow">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th className="ps-4" style={{ width: '140px' }}>
                    Fecha / Hora
                  </th>
                  <th className="text-end" style={{ width: '22%' }}>
                    Equipo Local
                  </th>
                  <th className="text-center" style={{ width: '200px' }}>
                    Distribución 1X2
                  </th>
                  <th className="text-start" style={{ width: '22%' }}>
                    Equipo Visitante
                  </th>
                  <th className="text-center" style={{ width: '120px' }}>
                    Recomendación
                  </th>
                  <th className="text-center pe-4" style={{ width: '130px' }}>
                    Acción
                  </th>
                </tr>
              </thead>
              <tbody>
                {partidos.length > 0 ? (
                  partidos.map((partido, idx) => {
                    const reco =
                      partido.recomendacion || partido.mejor_recomendacion;
                    const predictHref = `/predict?liga_id=${activeLigaId}&local=${encodeURIComponent(
                      partido.local
                    )}&visitante=${encodeURIComponent(partido.visitante)}`;

                    return (
                      <tr key={`desk-${partido.local}-${partido.visitante}-${idx}`}>
                        <td className="ps-4 text-muted small">
                          {partido.fecha_utc ? (
                            <LocalTime
                              utc={partido.fecha_utc}
                              fallback={partido.fecha}
                              display="datetime"
                            />
                          ) : (
                            partido.fecha
                          )}
                        </td>
                        <td className="text-end fw-bold">{partido.local}</td>
                        <td className="text-center">
                          {partido.prediccion ? (
                            <ProbabilityBar
                              prediccion={partido.prediccion}
                              variant="table"
                            />
                          ) : (
                            <span className="badge bg-secondary text-muted">
                              Sin datos
                            </span>
                          )}
                        </td>
                        <td className="text-start fw-bold">
                          {partido.visitante}
                        </td>
                        <td className="text-center">
                          {reco ? (
                            <span className="badge bg-success">
                              <i className="bi bi-lightning-charge-fill"></i>{' '}
                              {reco}
                            </span>
                          ) : partido.error ? (
                            <span
                              className="badge bg-warning"
                              title={partido.error}
                            >
                              <i className="bi bi-exclamation-triangle"></i>
                            </span>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                        <td className="text-center pe-4">
                          <Link
                            href={predictHref}
                            className="btn btn-sm btn-outline-primary"
                          >
                            <i className="bi bi-magic"></i> Analizar
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} className="text-center py-5">
                      <i className="bi bi-calendar-x display-1 text-muted mb-3 d-block"></i>
                      <h5>No hay partidos próximos</h5>
                      <p className="text-muted small">
                        Selecciona otra liga en el menú para ver su fixture
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Leyenda */}
      <div className="card bg-dark border-0 mt-4">
        <div className="card-body py-3">
          <div className="d-none d-md-flex align-items-center justify-content-center gap-3 small text-muted flex-wrap">
            <span className="d-flex align-items-center gap-1">
              <i className="bi bi-info-circle text-info"></i>{' '}
              <strong>Leyenda:</strong>
            </span>
            <span className="badge bg-primary">1</span> Local
            <span className="badge bg-warning">X</span> Empate
            <span className="badge bg-danger">2</span> Visitante
            <span className="text-muted">|</span>
            <span>
              <strong>1X</strong>: Local o Empate
            </span>
            <span>
              <strong>X2</strong>: Empate o Visitante
            </span>
            <span>
              <strong>12</strong>: Local o Visitante
            </span>
          </div>
          <div className="d-block d-md-none text-center small text-muted">
            <span className="badge bg-primary">1</span> Local
            <span className="badge bg-warning ms-2">X</span> Empate
            <span className="badge bg-danger ms-2">2</span> Visitante
          </div>
        </div>
      </div>
    </>
  );
}
