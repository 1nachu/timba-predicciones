import React from 'react';
import Link from 'next/link';
import type { HistoryLeagueMeta } from '@/lib/types';

interface HistoryFiltersProps {
  ligas: Record<string, HistoryLeagueMeta>;
  leagueCode: string;
  daysBack: number;
}

export default function HistoryFilters({
  ligas,
  leagueCode,
  daysBack,
}: HistoryFiltersProps) {
  return (
    <div className="card mb-4 border-0 bg-transparent">
      <div className="d-flex flex-wrap gap-2 justify-content-center mb-3">
        {Object.entries(ligas).map(([code, info]) => (
          <Link
            key={code}
            href={`/history?league_code=${code}&days=${daysBack}`}
            className={`btn btn-sm ${
              code === leagueCode ? 'btn-primary' : 'btn-outline-secondary'
            }`}
          >
            {info.bandera} {info.nombre}
          </Link>
        ))}
      </div>

      <div className="d-flex justify-content-center align-items-center gap-2">
        <small className="text-muted me-1">Rango de análisis:</small>
        {[7, 14, 30].map((d) => (
          <Link
            key={d}
            href={`/history?league_code=${leagueCode}&days=${d}`}
            className={`btn btn-sm ${
              daysBack === d ? 'btn-primary' : 'btn-outline-secondary'
            } px-3`}
          >
            {d} días
          </Link>
        ))}
      </div>
    </div>
  );
}
