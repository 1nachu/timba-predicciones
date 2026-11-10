import React from 'react';

export default function Loading() {
  return (
    <div className="text-center py-5 text-muted">
      <div className="spinner-border text-success mb-2" role="status" />
      <div className="small">Cargando análisis...</div>
    </div>
  );
}
