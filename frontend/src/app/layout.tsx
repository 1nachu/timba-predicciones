import type { Metadata } from 'next';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import './globals.css';
import AppShell from '@/components/layout/AppShell';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://futbol-predicciones.xyz';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'Timba Predictor — Análisis y Predicciones de Fútbol',
    template: '%s',
  },
  description:
    'Predicciones matemáticas de fútbol con modelos de Poisson, xG y probabilidades 1X2. Liga Argentina, Premier League, La Liga, Champions League y más.',
  icons: {
    icon: '/favicon.png',
    apple: '/favicon.png',
  },
  openGraph: {
    type: 'website',
    siteName: 'Timba Predictor',
    title: 'Timba Predictor — Predicciones de Fútbol',
    description:
      'Probabilidades 1X2, goles y doble oportunidad calculadas con distribución de Poisson. Premier League, La Liga, Serie A, Liga Argentina y más.',
    images: [
      {
        url: '/og_image.png',
        width: 1200,
        height: 630,
      },
    ],
    locale: 'es_AR',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Timba Predictor — Predicciones de Fútbol',
    description:
      'Probabilidades calculadas con Poisson para 8 ligas. Gratis y sin registro.',
    images: ['/og_image.png'],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" data-bs-theme="dark">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
