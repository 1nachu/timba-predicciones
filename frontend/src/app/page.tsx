import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { getDashboard } from '@/lib/api';
import { getLeagueFlag } from '@/lib/leagues';
import ProbabilityBar from '@/components/ProbabilityBar';
import LocalTime from '@/components/LocalTime';

export const metadata: Metadata = {
  title: 'Partidos de Hoy — Timba Predictor',
  alternates: { canonical: '/' },
};

export default async function DashboardPage() {
  const stats = await getDashboard();
  const partidosEntries = Object.entries(stats.partidos_hoy || {});
  const ligasEntries = Object.entries(stats.ligas || {});

  return (
    <>
      {/* Header: PARTIDOS DE HOY */}
      <div className="partidos-header d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <div className="partidos-title">
          <i className="bi bi-calendar-event"></i>
          <span>PARTIDOS DE HOY</span>
          <span className="badge bg-success ms-2">{stats.total_partidos_hoy}</span>
        </div>
        {stats.last_update && (
          <div className="text-muted small d-flex align-items-center gap-1">
            <i className="bi bi-clock"></i>{' '}
            <span>Actualizado: {stats.last_update}</span>
          </div>
        )}
      </div>

      {/* Tabs: TODOS / VIVO */}
      <div className="partidos-tabs">
        <Link href="/" className="tab-btn active">
          <i className="bi bi-grid-fill"></i> TODOS{' '}
          <span className="badge bg-secondary ms-1">
            {stats.total_partidos_hoy}
          </span>
        </Link>
        <Link href="/live" className="tab-btn">
          <i className="bi bi-broadcast text-danger"></i> EN VIVO
        </Link>
        <Link href="/fixtures" className="tab-btn">
          <i className="bi bi-calendar3"></i> PRÓXIMOS DÍAS
        </Link>
      </div>

      {partidosEntries.length > 0 ? (
        partidosEntries.map(([ligaId, ligaData]) => (
          <div key={ligaId} className="liga-bloque mb-4">
            <div className="liga-header">
              <span className="flag">{getLeagueFlag(ligaData.nombre)}</span>
              <span className="liga-name">{ligaData.nombre}</span>
              <div className="liga-actions">
                <Link
                  href={`/fixtures?liga_id=${ligaId}`}
                  title="Ver fixture completo de esta liga"
                  className="btn btn-sm btn-outline-secondary"
                >
                  <i className="bi bi-calendar3 me-1"></i> Fixture
                </Link>
              </div>
            </div>

            {ligaData.partidos.map((partido, idx) => {
              const predictHref = `/predict?liga_id=${encodeURIComponent(
                ligaId
              )}&local=${encodeURIComponent(
                partido.local
              )}&visitante=${encodeURIComponent(partido.visitante)}`;

              return (
                <Link
                  key={`${partido.local}-${partido.visitante}-${idx}`}
                  href={predictHref}
                  className="partido-card-link"
                >
                  <div className="partido-card">
                    <div className="partido-row">
                      <div className="partido-hora">
                        {partido.fecha_utc ? (
                          <LocalTime
                            utc={partido.fecha_utc}
                            fallback={partido.hora}
                            display="time"
                            className="hora"
                          />
                        ) : (
                          <span className="hora">{partido.hora}</span>
                        )}
                      </div>

                      <div className="partido-equipos">
                        <div className="partido-equipo local">
                          <span className="nombre">{partido.local}</span>
                        </div>
                        <span className="partido-vs">vs</span>
                        <div className="partido-equipo visitante">
                          <span className="nombre">{partido.visitante}</span>
                        </div>
                      </div>

                      {partido.recomendacion && partido.recomendacion !== '—' && (
                        <div className="partido-apuesta">
                          <span className="badge bg-success shadow-sm">
                            <i className="bi bi-lightning-charge-fill"></i>{' '}
                            {partido.recomendacion}
                          </span>
                        </div>
                      )}
                    </div>

                    {partido.prediccion ? (
                      <ProbabilityBar
                        prediccion={partido.prediccion}
                        variant="inline"
                      />
                    ) : (
                      <div className="partido-prediccion text-center">
                        <span className="text-muted small">
                          Haz clic para analizar probabilidades
                        </span>
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        ))
      ) : (
        <div className="card border-0 mb-4 p-4 text-center">
          <div className="card-body py-4">
            <div className="mb-3">
              <i className="bi bi-calendar-x display-4 text-muted"></i>
            </div>
            <h4 className="fw-bold mb-2">No hay partidos programados para hoy</h4>
            <p className="text-muted mb-4">
              Selecciona una liga para consultar los próximos encuentros y
              predicciones detalladas:
            </p>
            <div className="d-flex justify-content-center gap-2 flex-wrap max-w-lg mx-auto">
              {ligasEntries.map(([id, liga]) => (
                <Link
                  key={id}
                  href={`/fixtures?liga_id=${id}`}
                  className="btn btn-sm btn-outline-secondary"
                >
                  {getLeagueFlag(liga.nombre)} {liga.nombre.split('(')[0].trim()}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="row g-3 mt-2">
        <div className="col-md-6">
          <div className="card h-100 border-0 bg-dark p-2">
            <div className="card-body text-center py-4">
              <div className="mb-2">
                <i className="bi bi-broadcast display-5 text-danger"></i>
              </div>
              <h5 className="fw-bold mb-1">Partidos en Vivo</h5>
              <p className="text-muted small mb-3">
                Seguimiento en tiempo real con estadísticas y marcador minuto a
                minuto
              </p>
              <Link href="/live" className="btn btn-outline-danger btn-sm">
                <i className="bi bi-play-circle"></i> Ir al En Vivo
              </Link>
            </div>
          </div>
        </div>
        <div className="col-md-6">
          <div className="card h-100 border-0 bg-dark p-2">
            <div className="card-body text-center py-4">
              <div className="mb-2">
                <i className="bi bi-graph-up display-5 text-success"></i>
              </div>
              <h5 className="fw-bold mb-1">Auditoría &amp; Historial</h5>
              <p className="text-muted small mb-3">
                Comprobación de tasa de acierto y rendimiento histórico del
                modelo matemático
              </p>
              <Link href="/history" className="btn btn-outline-success btn-sm">
                <i className="bi bi-bar-chart"></i> Ver Auditoría
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
