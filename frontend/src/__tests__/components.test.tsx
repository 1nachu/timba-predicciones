import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProbabilityBar from '@/components/ProbabilityBar';
import LocalTime from '@/components/LocalTime';
import AlertList from '@/components/AlertList';
import PredictForm from '@/components/predict/PredictForm';
import PredictionResult from '@/components/predict/PredictionResult';
import LiveBoard from '@/components/live/LiveBoard';
import HistoryTable from '@/components/history/HistoryTable';
import HistoryFilters from '@/components/history/HistoryFilters';
import AccuracySummary from '@/components/history/AccuracySummary';
import LeagueSidebar from '@/components/layout/LeagueSidebar';
import TopNavbar from '@/components/layout/TopNavbar';
import MobileNav from '@/components/layout/MobileNav';
import BitcoinModal, { BTC_ADDRESS } from '@/components/layout/BitcoinModal';
import LeagueSelect from '@/components/fixtures/LeagueSelect';
import Footer from '@/components/layout/Footer';
import AppShell from '@/components/layout/AppShell';

const pushMock = vi.fn();
let mockPathname = '/fixtures';
let mockSearchParams = new URLSearchParams('liga_id=10');

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => mockPathname,
  useSearchParams: () => mockSearchParams,
}));

vi.mock('swr', () => ({
  default: (_key: string, _fetcher: unknown, opts: { fallbackData: unknown }) => ({
    data: opts.fallbackData,
    mutate: vi.fn(),
  }),
}));

describe('Shared & Feature Components', () => {
  beforeEach(() => {
    pushMock.mockClear();
    mockPathname = '/fixtures';
    mockSearchParams = new URLSearchParams('liga_id=10');
  });

  it('renders ProbabilityBar in inline, table and mobile variants', () => {
    const pred = { local: 54.2, empate: 25.0, visitante: 20.8 };
    const { rerender } = render(<ProbabilityBar prediccion={pred} variant="inline" />);
    expect(screen.getByText(/1: 54%/)).toBeInTheDocument();

    rerender(<ProbabilityBar prediccion={pred} variant="table" />);
    expect(screen.getByText('54%')).toBeInTheDocument();

    rerender(<ProbabilityBar prediccion={pred} variant="mobile" />);
    expect(screen.getByText('X: 25%')).toBeInTheDocument();
  });

  it('formats LocalTime in browser timezone and handles fallback', () => {
    render(<LocalTime utc="2026-11-10T19:00:00Z" fallback="19:00" display="datetime" />);
    const el = document.querySelector('.utc-time');
    expect(el).toBeInTheDocument();

    render(<LocalTime utc={null} fallback="Próximamente" />);
    expect(screen.getByText('Próximamente')).toBeInTheDocument();
  });

  it('renders AlertList and allows dismissing alerts', () => {
    render(
      <AlertList
        avisos={[
          { nivel: 'info', mensaje: 'Normalizado' },
          { nivel: 'warning', mensaje: 'Advertencia' },
        ]}
      />
    );
    expect(screen.getByText(/Normalizado/)).toBeInTheDocument();
    const closeBtns = screen.getAllByRole('button');
    fireEvent.click(closeBtns[0]);
    expect(screen.queryByText(/Normalizado/)).not.toBeInTheDocument();
  });

  it('PredictForm prevents same team selection and navigates on valid submit', () => {
    render(
      <PredictForm
        ligaId={1}
        equipos={['Arsenal', 'Chelsea']}
        initialLocal="Arsenal"
        initialVisitante="Arsenal"
      />
    );

    const submitBtn = screen.getByRole('button', { name: /Simular Predicción/i });
    fireEvent.click(submitBtn);
    expect(
      screen.getByText(/Debes seleccionar dos equipos diferentes/i)
    ).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();

    const visSelect = screen.getByLabelText(/Equipo Visitante/i);
    fireEvent.change(visSelect, { target: { value: 'Chelsea' } });
    fireEvent.click(submitBtn);
    expect(pushMock).toHaveBeenCalledWith(
      '/predict?liga_id=1&local=Arsenal&visitante=Chelsea'
    );

    const ligaSelect = screen.getByLabelText(/Liga \/ Competición/i);
    fireEvent.change(ligaSelect, { target: { value: '2' } });
    expect(pushMock).toHaveBeenCalledWith('/predict?liga_id=2');
  });

  it('PredictionResult renders probabilities, xG, corners, cards and recommendations', () => {
    render(
      <PredictionResult
        data={{
          local: 'Arsenal',
          visitante: 'Chelsea',
          liga_id: 1,
          liga: 'Premier League',
          avisos: [],
          probabilidades: {
            local: 55.0,
            empate: 24.0,
            visitante: 21.0,
            doble_oportunidad: { '1X': 79.0, X2: 45.0, '12': 76.0 },
          },
          goles_esperados: { local: 1.75, visitante: 1.05, total: 2.8 },
          mercados: {
            over_15: 78.0,
            over_25: 56.0,
            under_35: 68.0,
            corners_promedio: 10.4,
            tarjetas_promedio: 4.1,
            prob_tarjeta_roja: 12.0,
          },
          corners: {
            total: 10.4,
            local: 6.0,
            visitante: 4.4,
            prob_local_mas_corners: 62.0,
            over_85: 66.0,
            over_95: 53.0,
          },
          tarjetas: {
            amarillas_total: 4.1,
            amarillas_local: 1.9,
            amarillas_visitante: 2.2,
            rojas_local: 0.06,
            rojas_visitante: 0.08,
            prob_roja: 12.0,
            over_25: 72,
            over_35: 54,
            over_45: 35,
            under_55: 80,
          },
          top_marcadores: [{ marcador: '1-0', prob: 0.142 }],
          recomendaciones: [
            {
              class: 'success',
              corto: 'Gana Arsenal o Empate (1X)',
              emoji: '🛡️',
              icon: '🟢',
              prob: 79,
              texto: 'Alta probabilidad local',
            },
          ],
          value_bets: [],
        }}
      />
    );

    expect(screen.getByText('55.0%')).toBeInTheDocument();
    expect(screen.getByText('1.75 xG')).toBeInTheDocument();
    expect(screen.getByText('Telemetría de Córners')).toBeInTheDocument();
    expect(screen.getByText('Telemetría de Tarjetas')).toBeInTheDocument();
    expect(screen.getByText('Gana Arsenal o Empate (1X)')).toBeInTheDocument();
  });

  it('LiveBoard renders live and upcoming matches and handles empty state', () => {
    const { rerender } = render(
      <LiveBoard
        initialData={{
          total: 2,
          es_demo: true,
          partidos: [
            {
              status: 'IN_PLAY',
              seccion: 'live',
              minute: 62,
              competition: { name: 'Premier League', area: { name: 'England' } },
              homeTeam: { name: 'Arsenal' },
              awayTeam: { name: 'Chelsea' },
              score: { fullTime: { home: 2, away: 1 } },
              prediccion_timba: { prob_local: 60, over_25: 70 },
              prediccion_live: {
                minuto: 62,
                prob_local: 78,
                prob_empate: 15,
                prob_visitante: 7,
                xG_restante_local: 0.5,
                xG_restante_vis: 0.3,
                proximo_gol: { local: 40, visitante: 30 },
                estado_tactico: 'Ventaja Local',
              },
              prediccion_prematch: {
                prob_local: 54,
                prob_empate: 25,
                prob_visitante: 21,
                xg_local: 1.6,
                xg_vis: 1.0,
              },
            },
            {
              status: 'TIMED',
              seccion: 'proximos',
              home: 'Boca Juniors',
              away: 'River Plate',
              score: '0 - 0',
              utcDate: '2026-11-10T21:00:00Z',
            },
          ],
        }}
      />
    );

    expect(screen.getByText('EN VIVO AHORA')).toBeInTheDocument();
    expect(screen.getByText('PRÓXIMOS HOY')).toBeInTheDocument();
    expect(screen.getByText('Arsenal')).toBeInTheDocument();
    expect(screen.getByText('Ventaja Local')).toBeInTheDocument();

    rerender(<LiveBoard initialData={{ total: 0, partidos: [] }} />);
    expect(screen.getByText('No hay partidos en vivo')).toBeInTheDocument();
  });

  it('renders HistoryFilters, AccuracySummary and HistoryTable', () => {
    render(
      <>
        <HistoryFilters
          ligas={{
            E0: { nombre: 'Premier League', bandera: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', liga_id: 1 },
          }}
          leagueCode="E0"
          daysBack={7}
        />
        <AccuracySummary
          estadisticas={{
            total_partidos: 2,
            evaluados: 2,
            aciertos: 1,
            fallos: 1,
            sin_prediccion: 0,
            precision: 50,
          }}
        />
        <HistoryTable
          leagueCode="E0"
          resultados={[
            {
              fecha: '2026-11-08',
              local: 'Arsenal',
              visitante: 'Liverpool',
              goles_local: 2,
              goles_visitante: 1,
              resultado_real: 'HOME_WIN',
              prediccion_ia: 'HOME_WIN',
              prediccion_prob: 58,
              acierto: true,
            },
            {
              fecha: '2026-11-07',
              local: 'Chelsea',
              visitante: 'Man City',
              goles_local: 0,
              goles_visitante: 2,
              resultado_real: 'AWAY_WIN',
              prediccion_ia: '1X',
              prediccion_prob: 52,
              acierto: false,
            },
          ]}
        />
      </>
    );

    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('✅ ACIERTO')).toBeInTheDocument();
    expect(screen.getByText('❌ FALLO')).toBeInTheDocument();
  });

  it('renders Layout components (AppShell, LeagueSidebar, TopNavbar, MobileNav, BitcoinModal, LeagueSelect, Footer)', () => {
    render(
      <AppShell>
        <LeagueSelect ligaId={10} />
      </AppShell>
    );

    const activeSidebarLink = screen.getByRole('link', {
      name: /Liga Profesional/i,
    });
    expect(activeSidebarLink.className).toContain('active');

    render(<BitcoinModal show={true} onHide={() => {}} />);
    expect(screen.getByText(BTC_ADDRESS)).toBeInTheDocument();
    expect(screen.getAllByText(/Timba Team/i).length).toBeGreaterThan(0);

    render(<TopNavbar onOpenBitcoinModal={() => {}} />);
    render(<MobileNav onOpenMobileDonate={() => {}} />);
    render(<LeagueSidebar />);
    render(<Footer />);
  });
});
