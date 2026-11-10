import React from 'react';
import type { MatchPrediction1X2 } from '@/lib/types';

interface ProbabilityBarProps {
  prediccion: MatchPrediction1X2;
  variant?: 'inline' | 'table' | 'mobile';
}

export default function ProbabilityBar({
  prediccion,
  variant = 'inline',
}: ProbabilityBarProps) {
  const local = Number(prediccion.local) || 0;
  const empate = Number(prediccion.empate) || 0;
  const visitante = Number(prediccion.visitante) || 0;

  if (variant === 'table') {
    return (
      <div
        className="progress"
        style={{ height: '24px' }}
        title={`1: ${local}% | X: ${empate}% | 2: ${visitante}%`}
      >
        <div
          className="progress-bar bg-primary d-flex align-items-center justify-content-center fw-bold"
          style={{ width: `${local}%`, fontSize: '11px' }}
        >
          {local >= 20 ? `${Math.trunc(local)}%` : ''}
        </div>
        <div
          className="progress-bar bg-warning d-flex align-items-center justify-content-center fw-bold text-dark"
          style={{ width: `${empate}%`, fontSize: '11px' }}
        >
          {empate >= 20 ? `${Math.trunc(empate)}%` : ''}
        </div>
        <div
          className="progress-bar bg-danger d-flex align-items-center justify-content-center fw-bold"
          style={{ width: `${visitante}%`, fontSize: '11px' }}
        >
          {visitante >= 20 ? `${Math.trunc(visitante)}%` : ''}
        </div>
      </div>
    );
  }

  if (variant === 'mobile') {
    return (
      <div className="mb-3">
        <div className="d-flex justify-content-between mb-1 small fw-bold">
          <span className="text-info">1: {Math.trunc(local)}%</span>
          <span className="text-warning">X: {Math.trunc(empate)}%</span>
          <span className="text-danger">2: {Math.trunc(visitante)}%</span>
        </div>
        <div className="progress" style={{ height: '8px' }}>
          <div
            className="progress-bar bg-primary"
            style={{ width: `${local}%` }}
          ></div>
          <div
            className="progress-bar bg-warning"
            style={{ width: `${empate}%` }}
          ></div>
          <div
            className="progress-bar bg-danger"
            style={{ width: `${visitante}%` }}
          ></div>
        </div>
      </div>
    );
  }

  return (
    <div className="partido-prediccion">
      <div className="pred-probs">
        <span className="pred-item local">
          <i className="bi bi-house-fill me-1"></i>1: {Math.trunc(local)}%
        </span>
        <span className="pred-item empate">
          <i className="bi bi-dash-lg me-1"></i>X: {Math.trunc(empate)}%
        </span>
        <span className="pred-item visitante">
          <i className="bi bi-airplane-fill me-1"></i>2: {Math.trunc(visitante)}%
        </span>
      </div>
      <div className="pred-bar">
        <div
          className="pred-bar-local"
          style={{ width: `${local}%` }}
          title={`Local: ${local}%`}
        ></div>
        <div
          className="pred-bar-empate"
          style={{ width: `${empate}%` }}
          title={`Empate: ${empate}%`}
        ></div>
        <div
          className="pred-bar-visitante"
          style={{ width: `${visitante}%` }}
          title={`Visitante: ${visitante}%`}
        ></div>
      </div>
    </div>
  );
}
