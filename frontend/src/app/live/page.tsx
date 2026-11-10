import React from 'react';
import type { Metadata } from 'next';
import { getLiveMatches } from '@/lib/api';
import LiveBoard from '@/components/live/LiveBoard';

export const metadata: Metadata = {
  title: 'En Vivo — Timba Predictor',
  alternates: { canonical: '/live' },
};

export default async function LivePage() {
  const initialData = await getLiveMatches();
  return <LiveBoard initialData={initialData} />;
}
