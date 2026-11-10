'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Dropdown } from 'react-bootstrap';

interface TopNavbarProps {
  onOpenBitcoinModal: () => void;
}

export default function TopNavbar({ onOpenBitcoinModal }: TopNavbarProps) {
  const pathname = usePathname() || '/';

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname.startsWith(path);
  };

  return (
    <nav className="navbar navbar-promiedos">
      <div className="container-fluid px-3">
        <Link className="navbar-brand" href="/">
          <span className="live-dot me-1"></span>
          <span className="brand-text">TIMBA</span>
          <span className="brand-badge d-none d-sm-inline">PRO</span>
        </Link>

        <div className="navbar-nav-center d-none d-md-flex">
          <Link
            href="/"
            className={`nav-link-top ${isActive('/') ? 'active' : ''}`}
          >
            <i className="bi bi-house-fill"></i> INICIO
          </Link>
          <Link
            href="/fixtures"
            className={`nav-link-top ${isActive('/fixtures') ? 'active' : ''}`}
          >
            <i className="bi bi-calendar3"></i> FIXTURE
          </Link>
          <Link
            href="/live"
            className={`nav-link-top ${isActive('/live') ? 'active' : ''}`}
          >
            <i className="bi bi-broadcast"></i> EN VIVO
          </Link>
          <Link
            href="/predict"
            className={`nav-link-top ${isActive('/predict') ? 'active' : ''}`}
          >
            <i className="bi bi-magic"></i> PREDICCIÓN
          </Link>
          <Link
            href="/history"
            className={`nav-link-top ${isActive('/history') ? 'active' : ''}`}
          >
            <i className="bi bi-graph-up"></i> HISTORIAL
          </Link>
        </div>

        <div className="navbar-actions d-none d-md-flex">
          <Dropdown align="end">
            <Dropdown.Toggle
              variant="outline-success"
              size="sm"
              id="donateDropdown"
            >
              <i className="bi bi-cash-coin"></i> Apoyar
            </Dropdown.Toggle>
            <Dropdown.Menu className="shadow">
              <Dropdown.Item
                href="https://cafecito.app/timba_arg"
                target="_blank"
                rel="noopener noreferrer"
              >
                🇦🇷 Cafecito App
              </Dropdown.Item>
              <Dropdown.Item
                href="https://buymeacoffee.com/timba_global"
                target="_blank"
                rel="noopener noreferrer"
              >
                🌍 Buy Me a Coffee
              </Dropdown.Item>
              <Dropdown.Divider />
              <Dropdown.Item
                as="button"
                type="button"
                onClick={onOpenBitcoinModal}
              >
                ₿ Bitcoin / Crypto
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </div>
      </div>
    </nav>
  );
}
