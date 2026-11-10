'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface MobileNavProps {
  onOpenMobileDonate: () => void;
}

export default function MobileNav({ onOpenMobileDonate }: MobileNavProps) {
  const pathname = usePathname() || '/';

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname.startsWith(path);
  };

  return (
    <div
      className="mobile-nav d-md-none"
      role="navigation"
      aria-label="Navegación móvil"
    >
      <Link
        href="/"
        className={`mobile-nav-item ${isActive('/') ? 'active' : ''}`}
        aria-label="Inicio"
      >
        <i className="bi bi-house-fill" aria-hidden="true"></i>
        <span>Inicio</span>
      </Link>
      <Link
        href="/fixtures"
        className={`mobile-nav-item ${isActive('/fixtures') ? 'active' : ''}`}
        aria-label="Fixture"
      >
        <i className="bi bi-calendar3" aria-hidden="true"></i>
        <span>Fixture</span>
      </Link>
      <Link
        href="/live"
        className={`mobile-nav-item ${isActive('/live') ? 'active' : ''}`}
        aria-label="En Vivo"
      >
        <i className="bi bi-broadcast" aria-hidden="true"></i>
        <span>En Vivo</span>
      </Link>
      <Link
        href="/predict"
        className={`mobile-nav-item ${isActive('/predict') ? 'active' : ''}`}
        aria-label="Predicción"
      >
        <i className="bi bi-magic" aria-hidden="true"></i>
        <span>Predecir</span>
      </Link>
      <Link
        href="/history"
        className={`mobile-nav-item ${isActive('/history') ? 'active' : ''}`}
        aria-label="Historial"
      >
        <i className="bi bi-graph-up" aria-hidden="true"></i>
        <span>Historial</span>
      </Link>
      <a
        href="#apoyar"
        className="mobile-nav-item"
        aria-label="Donar"
        onClick={(e) => {
          e.preventDefault();
          onOpenMobileDonate();
        }}
      >
        <i className="bi bi-cash-coin" aria-hidden="true"></i>
        <span>Apoyar</span>
      </a>
    </div>
  );
}
