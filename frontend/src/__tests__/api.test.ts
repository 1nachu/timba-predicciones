import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  apiFetch,
  getDashboard,
  getLeagues,
  getLeagueTeams,
  getFixtures,
  getLiveMatches,
  getHistory,
  getPrediction,
} from '@/lib/api';
import { getLeagueFlag, SIDEBAR_LEAGUES } from '@/lib/leagues';

describe('API client & leagues helper', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returns correct flags for leagues', () => {
    expect(getLeagueFlag('Liga Profesional (Argentina)')).toBe('🇦🇷');
    expect(getLeagueFlag('Premier League')).toBe('🏴󠁧󠁢󠁥󠁮󠁧󠁿');
    expect(getLeagueFlag('La Liga')).toBe('🇪🇸');
    expect(getLeagueFlag('Serie A')).toBe('🇮🇹');
    expect(getLeagueFlag('Bundesliga')).toBe('🇩🇪');
    expect(getLeagueFlag('Ligue 1')).toBe('🇫🇷');
    expect(getLeagueFlag('Primeira Liga')).toBe('🇵🇹');
    expect(getLeagueFlag('Eredivisie')).toBe('🇳🇱');
    expect(getLeagueFlag('UEFA Champions League')).toBe('🏆');
    expect(getLeagueFlag('')).toBe('⚽');
    expect(SIDEBAR_LEAGUES.length).toBe(9);
  });

  it('fetches endpoints via apiFetch and handles errors gracefully', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok', equipos: ['Arsenal'] }),
    } as Response);

    const res = await apiFetch<{ status: string }>('/api/v1/health');
    expect(res.status).toBe('ok');
    expect(fetchSpy).toHaveBeenCalled();

    await getDashboard();
    await getLeagues();
    await getLeagueTeams(1);
    await getFixtures(1);
    await getLiveMatches();
    await getHistory('E0', 7);
    await getPrediction({ ligaId: 1, local: 'Arsenal', visitante: 'Chelsea' });

    const sameTeam = await getPrediction({
      ligaId: 1,
      local: 'Arsenal',
      visitante: 'Arsenal',
    });
    expect(sameTeam.data).toBeNull();
    expect(sameTeam.avisos.length).toBe(1);

    fetchSpy.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({
        error: 'No encontrado',
        avisos: [{ nivel: 'danger', mensaje: 'No encontrado' }],
      }),
    } as Response);

    const notFoundPred = await getPrediction({
      ligaId: 1,
      local: 'A',
      visitante: 'B',
    });
    expect(notFoundPred.data).toBeNull();
    expect(notFoundPred.avisos[0].mensaje).toBe('No encontrado');

    fetchSpy.mockRejectedValue(new Error('connect ECONNREFUSED 127.0.0.1:5000'));
    const fallbackDash = await getDashboard();
    expect(fallbackDash.total_partidos_hoy).toBe(0);
    expect(fallbackDash.cache_missing).toBe(true);

    const fallbackLeagues = await getLeagues();
    expect(fallbackLeagues.total).toBe(SIDEBAR_LEAGUES.length);

    const fallbackTeams = await getLeagueTeams(1);
    expect(fallbackTeams.equipos).toEqual([]);

    const fallbackFixtures = await getFixtures(1);
    expect(fallbackFixtures.partidos).toEqual([]);

    const fallbackLive = await getLiveMatches();
    expect(fallbackLive.partidos).toEqual([]);

    const fallbackHistory = await getHistory('E0', 7);
    expect(fallbackHistory.resultados).toEqual([]);
  });
});
