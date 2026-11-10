'use client';

import React, { useState } from 'react';
import { Alert } from 'react-bootstrap';
import type { Aviso } from '@/lib/types';

interface AlertListProps {
  avisos?: Aviso[];
}

export default function AlertList({ avisos = [] }: AlertListProps) {
  const [dismissed, setDismissed] = useState<Record<number, boolean>>({});

  if (!avisos.length) return null;

  return (
    <>
      {avisos.map((aviso, idx) => {
        if (dismissed[idx]) return null;
        return (
          <Alert
            key={`${aviso.nivel}-${idx}`}
            variant={aviso.nivel}
            dismissible
            onClose={() => setDismissed((prev) => ({ ...prev, [idx]: true }))}
            className="mb-3"
          >
            <i className="bi bi-info-circle me-1"></i> {aviso.mensaje}
          </Alert>
        );
      })}
    </>
  );
}
