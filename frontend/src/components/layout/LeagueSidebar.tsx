'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { SIDEBAR_LEAGUES } from '@/lib/leagues';

export default function LeagueSidebar() {
  const pathname = usePathname() || '/';
  const searchParams = useSearchParams();
  const currentLigaId = searchParams?.get('liga_id');

  const isLeagueActive = (id: number) => {
    if (currentLigaId === String(id)) return true;
    if (pathname === '/fixtures' && !currentLigaId && id === 1) return true;
    return false;
  };

  const destacados = SIDEBAR_LEAGUES.filter((l) => l.destacado);
  const europeas = SIDEBAR_LEAGUES.filter((l) => !l.destacado);

  return (
    <aside className="sidebar d-none d-lg-block">
      <div className="sidebar-section">
        <div className="sidebar-header">
          <i className="bi bi-star-fill"></i> DESTACADOS
        </div>
        {destacados.map((liga) => (
          <Link
            key={liga.id}
            href={`/fixtures?liga_id=${liga.id}`}
            className={`sidebar-item ${isLeagueActive(liga.id) ? 'active' : ''}`}
          >
            <span className="flag">{liga.bandera}</span> {liga.nombre}
          </Link>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-header">
          <i className="bi bi-trophy-fill"></i> LIGAS EUROPEAS
        </div>
        {europeas.map((liga) => (
          <Link
            key={liga.id}
            href={`/fixtures?liga_id=${liga.id}`}
            className={`sidebar-item ${isLeagueActive(liga.id) ? 'active' : ''}`}
          >
            <span className="flag">{liga.bandera}</span> {liga.nombre}
          </Link>
        ))}
      </div>
    </aside>
  );
}
