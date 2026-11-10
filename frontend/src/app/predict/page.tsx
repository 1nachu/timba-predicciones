import React from 'react';
import type { Metadata } from 'next';
import { getLeagueTeams, getPrediction } from '@/lib/api';
import PredictForm from '@/components/predict/PredictForm';
import PredictionResult from '@/components/predict/PredictionResult';
import AlertList from '@/components/AlertList';

type SearchParams = Promise<{
  liga_id?: string;
  local?: string;
  visitante?: string;
}>;

export async function generateMetadata({
  searchParams,
}: {
  searchParams: SearchParams;
}): Promise<Metadata> {
  const { local, visitante } = await searchParams;
  const pageTitle =
    local && visitante
      ? `${local} vs ${visitante} — Timba Predictor`
      : 'Predicción Manual — Timba Predictor';
  const ogTitle = `${local || 'Predicción'} vs ${
    visitante || 'Partido'
  } — Timba Predictor`;

  return {
    title: pageTitle,
    openGraph: {
      title: ogTitle,
    },
    twitter: {
      title: ogTitle,
    },
    alternates: { canonical: '/predict' },
  };
}

export default async function PredictPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { liga_id = '1', local = '', visitante = '' } = await searchParams;
  const ligaId = Number(liga_id) || 1;

  const [teamsData, predResult] = await Promise.all([
    getLeagueTeams(ligaId),
    local && visitante
      ? getPrediction({ ligaId, local, visitante })
      : Promise.resolve({ data: null, avisos: [] }),
  ]);

  const combinedAvisos = [
    ...(teamsData.avisos || []),
    ...(predResult.avisos || []),
  ];

  const selectedLocal = predResult.data?.local || local;
  const selectedVisitante = predResult.data?.visitante || visitante;

  return (
    <>
      <AlertList avisos={combinedAvisos} />

      <div className="row align-items-center mb-4">
        <div className="col-12">
          <h1 className="h3 fw-bold mb-1 d-flex align-items-center gap-2">
            <i className="bi bi-magic text-primary"></i>
            <span>Predicción Manual</span>
          </h1>
          <p className="text-muted small mb-0">
            Selecciona dos equipos para simular probabilidades mediante
            distribución de Poisson y xG
          </p>
        </div>
      </div>

      <PredictForm
        ligaId={ligaId}
        equipos={teamsData.equipos}
        initialLocal={selectedLocal}
        initialVisitante={selectedVisitante}
      />

      {predResult.data && <PredictionResult data={predResult.data} />}

      {!predResult.data && teamsData.equipos.length === 0 && (
        <div className="card text-center py-5 border-0">
          <div className="card-body">
            <i className="bi bi-database-x display-1 text-muted mb-3"></i>
            <h4>No hay datos disponibles</h4>
            <p className="text-muted small">
              Selecciona una liga diferente en el menú superior
            </p>
          </div>
        </div>
      )}
    </>
  );
}
