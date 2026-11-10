'use client';

import React, { useEffect, useState } from 'react';

interface LocalTimeProps {
  utc?: string | null;
  fallback?: string;
  display?: 'time' | 'datetime';
  className?: string;
}

export default function LocalTime({
  utc,
  fallback = '--:--',
  display = 'time',
  className = '',
}: LocalTimeProps) {
  const [formatted, setFormatted] = useState<string | null>(null);

  useEffect(() => {
    if (!utc) return;
    try {
      const date = new Date(utc);
      if (isNaN(date.getTime())) return;
      const options: Intl.DateTimeFormatOptions =
        display === 'datetime'
          ? {
              day: 'numeric',
              month: 'short',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            }
          : {
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            };
      setFormatted(new Intl.DateTimeFormat('es-AR', options).format(date));
    } catch {
      // keep fallback
    }
  }, [utc, display]);

  return (
    <span
      className={`utc-time ${formatted ? 'utc-converted' : ''} ${className}`.trim()}
      data-utc={utc || undefined}
      data-display={display}
    >
      {formatted ?? fallback}
    </span>
  );
}
