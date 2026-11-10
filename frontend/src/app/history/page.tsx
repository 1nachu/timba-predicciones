import React from 'react';
import type { Metadata } from 'next';
import { getHistory } from '@/lib/api';
import HistoryFilters from '@/components/history/HistoryFilters';
import AccuracySummary from '@/components/history/AccuracySummary';
import HistoryTable from '@/components/history/HistoryTable';
import AlertList from '@/components/AlertList';

export const metadata: Metadata = {
  title: 'Auditoría y Rendimiento — Timba Predictor',
  alternates: { canonical: '/history' },
};

type SearchParams = Promise<{ league_code?: string; days?: string }>;

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { league_code = 'E0', days = '7' } = await searchParams;
  const daysNum = Number(days) || 7;
  const data = await getHistory(league_code, daysNum);

  return (
    <div className="container-fluid px-0 px-md-2 py-2">
      <AlertList avisos={data.avisos} />

      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
        <div>
          <h1 className="h3 fw-bold mb-1 d-flex align-items-center gap-2">
            <i className="bi bi-clipboard-data text-primary"></i>
            <span>Auditoría de Predicciones</span>
          </h1>
          <p className="text-muted small mb-0">
            {data.liga_actual.bandera} {data.liga_actual.nombre}
            {data.es_demo && (
              <span className="badge bg-warning text-dark ms-2">
                DATOS DEMO
              </span>
            )}
          </p>
        </div>
        <div>
          <span className="badge bg-dark border border-secondary fs-6 px-3 py-2">
            <i className="bi bi-calendar3 text-info me-1"></i> Últimos{' '}
            {data.days} días
          </span>
        </div>
      </div>

      <HistoryFilters
        ligas={data.ligas}
        leagueCode={data.league_code}
        daysBack={data.days}
      />

      <AccuracySummary estadisticas={data.estadisticas} />

      <HistoryTable
        resultados={data.resultados}
        leagueCode={data.league_code}
      />

      {/* Guía de Interpretación */}
      <div className="row g-3 mt-3">
        <div className="col-md-6">
          <div className="card border-0 bg-dark p-2 h-100">
            <div className="card-body small">
              <h6 className="fw-bold mb-2 text-info">
                <i className="bi bi-question-circle-fill me-1"></i> Metodología
              </h6>
              <ul className="mb-0 ps-3 text-muted">
                <li>
                  El algoritmo calcula la fuerza de ataque y defensa de cada
                  equipo.
                </li>
                <li>
                  Genera una matriz de probabilidades exactas mediante Poisson.
                </li>
                <li>
                  <strong>Acierto:</strong> El mercado predicho por la IA
                  coincidió con el resultado final.
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div className="col-md-6">
          <div className="card border-0 bg-dark p-2 h-100">
            <div className="card-body small">
              <h6 className="fw-bold mb-2 text-warning">
                <i className="bi bi-lightbulb-fill me-1"></i> Escala de
                Rendimiento
              </h6>
              <ul className="mb-0 ps-3 text-muted">
                <li>
                  <span className="text-success fw-bold">&gt;50%</span> —
                  Rendimiento sobresaliente sobre el mercado.
                </li>
                <li>
                  <span className="text-warning fw-bold">35% - 50%</span> —
                  Rendimiento consistente esperado.
                </li>
                <li>
                  <span className="text-muted">33.3%</span> — Línea base de
                  elección aleatoria (1, X, 2).
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
