'use client';

import React, { useEffect, useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Alert } from 'react-bootstrap';
import { SIDEBAR_LEAGUES } from '@/lib/leagues';

interface PredictFormProps {
  ligaId: number;
  equipos: string[];
  initialLocal?: string;
  initialVisitante?: string;
}

export default function PredictForm({
  ligaId,
  equipos,
  initialLocal = '',
  initialVisitante = '',
}: PredictFormProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [local, setLocal] = useState(initialLocal);
  const [visitante, setVisitante] = useState(initialVisitante);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setLocal(initialLocal);
  }, [initialLocal]);

  useEffect(() => {
    setVisitante(initialVisitante);
  }, [initialVisitante]);

  const handleLeagueChange = (newLigaId: string) => {
    setValidationError(null);
    startTransition(() => {
      router.push(`/predict?liga_id=${newLigaId}`);
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!local || !visitante) {
      setValidationError('⚠️ Debes seleccionar ambos equipos.');
      return;
    }
    if (local === visitante) {
      setValidationError('⚠️ Debes seleccionar dos equipos diferentes.');
      return;
    }
    setValidationError(null);
    const params = new URLSearchParams({
      liga_id: String(ligaId),
      local,
      visitante,
    });
    startTransition(() => {
      router.push(`/predict?${params.toString()}`);
    });
  };

  return (
    <div className="row justify-content-center mb-4">
      <div className="col-12">
        {validationError && (
          <Alert
            variant="warning"
            dismissible
            onClose={() => setValidationError(null)}
            className="mb-3"
          >
            {validationError}
          </Alert>
        )}
        <div
          className="card border-0 shadow-lg p-3 p-md-4"
          style={{
            background:
              'linear-gradient(135deg, rgba(19, 29, 51, 0.95) 0%, rgba(11, 17, 30, 0.98) 100%)',
          }}
        >
          <form onSubmit={handleSubmit}>
            {/* Selector de Liga */}
            <div className="row mb-3">
              <div className="col-12 col-md-6 mx-auto">
                <label
                  htmlFor="ligaSelect"
                  className="form-label text-center d-block mb-1"
                >
                  <i className="bi bi-trophy text-warning me-1"></i> Liga /
                  Competición
                </label>
                <select
                  id="ligaSelect"
                  name="liga_id"
                  aria-label="Liga / Competición"
                  className="form-select form-select-sm"
                  value={ligaId}
                  disabled={isPending}
                  onChange={(e) => handleLeagueChange(e.target.value)}
                >
                  {SIDEBAR_LEAGUES.map((liga) => (
                    <option key={liga.id} value={liga.id}>
                      {liga.bandera} {liga.nombreCompleto}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Matchup Head-to-Head Selector */}
            <div className="row g-3 align-items-center justify-content-center my-2">
              <div className="col-md-5">
                <div
                  className="p-3 rounded border"
                  style={{
                    background: 'rgba(6, 182, 212, 0.04)',
                    borderColor: 'rgba(6, 182, 212, 0.3)',
                  }}
                >
                  <label
                    htmlFor="localSelect"
                    className="form-label text-info d-flex align-items-center gap-1 mb-2"
                  >
                    <i className="bi bi-house-fill"></i>{' '}
                    <span>Equipo Local</span>
                  </label>
                  <select
                    id="localSelect"
                    name="local"
                    aria-label="Equipo Local"
                    className="form-select"
                    required
                    disabled={isPending}
                    value={local}
                    onChange={(e) => {
                      setLocal(e.target.value);
                      setValidationError(null);
                    }}
                  >
                    <option value="">Seleccionar local...</option>
                    {equipos.map((eq) => (
                      <option key={eq} value={eq}>
                        {eq}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="col-md-2 text-center my-2 my-md-0">
                <span className="badge bg-secondary fs-5 py-2 px-3 rounded-pill shadow-sm border border-secondary">
                  VS
                </span>
              </div>

              <div className="col-md-5">
                <div
                  className="p-3 rounded border"
                  style={{
                    background: 'rgba(244, 63, 94, 0.04)',
                    borderColor: 'rgba(244, 63, 94, 0.3)',
                  }}
                >
                  <label
                    htmlFor="visitanteSelect"
                    className="form-label text-danger d-flex align-items-center gap-1 mb-2"
                  >
                    <i className="bi bi-airplane-fill"></i>{' '}
                    <span>Equipo Visitante</span>
                  </label>
                  <select
                    id="visitanteSelect"
                    name="visitante"
                    aria-label="Equipo Visitante"
                    className="form-select"
                    required
                    disabled={isPending}
                    value={visitante}
                    onChange={(e) => {
                      setVisitante(e.target.value);
                      setValidationError(null);
                    }}
                  >
                    <option value="">Seleccionar visitante...</option>
                    {equipos.map((eq) => (
                      <option key={eq} value={eq}>
                        {eq}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="text-center mt-4">
              <button
                type="submit"
                className="btn btn-primary btn-lg px-5 shadow"
                disabled={isPending}
              >
                <i className="bi bi-lightning-charge-fill"></i>{' '}
                {isPending ? 'Analizando...' : 'Simular Predicción'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
