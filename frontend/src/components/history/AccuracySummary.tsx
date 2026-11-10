import React from 'react';
import type { HistoryStats } from '@/lib/types';

interface AccuracySummaryProps {
  estadisticas: HistoryStats;
}

export default function AccuracySummary({
  estadisticas,
}: AccuracySummaryProps) {
  const hitPct =
    estadisticas.evaluados > 0
      ? Math.round((estadisticas.aciertos / estadisticas.evaluados) * 1000) / 10
      : 0;
  const missPct =
    estadisticas.evaluados > 0
      ? Math.round((estadisticas.fallos / estadisticas.evaluados) * 1000) / 10
      : 0;

  return (
    <>
      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div
            className="card border-0 h-100 shadow"
            style={{
              background:
                'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(19, 29, 51, 0.9) 100%)',
              borderLeft: '4px solid var(--accent-emerald)',
            }}
          >
            <div className="card-body text-center py-4">
              <span className="badge bg-success mb-2">ACIERTOS</span>
              <div className="display-4 fw-bold text-success my-1">
                {estadisticas.aciertos}
              </div>
              <small className="text-muted">Predicciones correctas</small>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div
            className="card border-0 h-100 shadow"
            style={{
              background:
                'linear-gradient(135deg, rgba(244, 63, 94, 0.15) 0%, rgba(19, 29, 51, 0.9) 100%)',
              borderLeft: '4px solid var(--accent-rose)',
            }}
          >
            <div className="card-body text-center py-4">
              <span className="badge bg-danger mb-2">FALLOS</span>
              <div className="display-4 fw-bold text-danger my-1">
                {estadisticas.fallos}
              </div>
              <small className="text-muted">Predicciones no acertadas</small>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div
            className="card border-0 h-100 shadow"
            style={{
              background:
                'linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(19, 29, 51, 0.9) 100%)',
              borderLeft: '4px solid var(--accent-cyan)',
            }}
          >
            <div className="card-body text-center py-4">
              <span className="badge bg-info mb-2">PRECISIÓN GLOBAL</span>
              <div className="display-4 fw-bold text-info my-1">
                {estadisticas.precision}%
              </div>
              <small className="text-muted">Efectividad del modelo</small>
            </div>
          </div>
        </div>
      </div>

      {estadisticas.evaluados > 0 && (
        <div className="card mb-4 border-0 shadow">
          <div className="card-body py-3">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <span className="fw-semibold small d-flex align-items-center gap-1">
                <i className="bi bi-bar-chart-fill text-primary"></i> Desglose de
                Rendimiento
              </span>
              <span className="text-muted small">
                {estadisticas.evaluados} partidos evaluados
                {estadisticas.sin_prediccion > 0 &&
                  ` · ${estadisticas.sin_prediccion} sin datos`}
              </span>
            </div>
            <div className="progress" style={{ height: '20px' }}>
              <div
                className="progress-bar bg-success d-flex align-items-center justify-content-center fw-bold"
                style={{ width: `${hitPct}%`, fontSize: '11px' }}
              >
                {estadisticas.aciertos} ✓
              </div>
              <div
                className="progress-bar bg-danger d-flex align-items-center justify-content-center fw-bold"
                style={{ width: `${missPct}%`, fontSize: '11px' }}
              >
                {estadisticas.fallos} ✗
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
