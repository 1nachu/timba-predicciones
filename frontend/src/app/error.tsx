'use client';

import React from 'react';
import Link from 'next/link';

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="alert alert-danger text-center py-4 my-4">
      <h4>
        <i className="bi bi-exclamation-triangle"></i> Error interno del servidor
      </h4>
      <div className="d-flex justify-content-center gap-2 mt-3">
        <button type="button" className="btn btn-outline-light" onClick={reset}>
          Reintentar
        </button>
        <Link href="/" className="btn btn-primary">
          Volver al Inicio
        </Link>
      </div>
    </div>
  );
}
