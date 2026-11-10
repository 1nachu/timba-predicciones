'use client';

import React, { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { SIDEBAR_LEAGUES } from '@/lib/leagues';

interface LeagueSelectProps {
  ligaId: number;
  basePath?: string;
}

export default function LeagueSelect({
  ligaId,
  basePath = '/fixtures',
}: LeagueSelectProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  return (
    <select
      aria-label="Seleccionar liga"
      className="form-select form-select-sm"
      value={ligaId}
      disabled={isPending}
      onChange={(e) => {
        const nextLiga = e.target.value;
        startTransition(() => {
          router.push(`${basePath}?liga_id=${nextLiga}`);
        });
      }}
    >
      {SIDEBAR_LEAGUES.map((liga) => (
        <option key={liga.id} value={liga.id}>
          {liga.bandera} {liga.nombreCompleto}
        </option>
      ))}
    </select>
  );
}
