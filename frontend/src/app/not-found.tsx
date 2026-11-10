import React from 'react';
import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="alert alert-danger text-center py-4 my-4">
      <h4>
        <i className="bi bi-exclamation-triangle"></i> Página no encontrada
      </h4>
      <Link href="/" className="btn btn-primary mt-2">
        Volver al Inicio
      </Link>
    </div>
  );
}
