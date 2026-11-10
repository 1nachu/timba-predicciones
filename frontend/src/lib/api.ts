import type {
  Aviso,
  DashboardResponse,
  FixturesResponse,
  HistoryResponse,
  LeagueTeamsResponse,
  LeaguesResponse,
  LiveResponse,
  PredictResponse,
} from './types';

function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return '';
  }
  return process.env.API_INTERNAL_URL || 'http://127.0.0.1:5000';
}

function getCacheStrategy(revalidateSeconds: number): {
  cache?: RequestCache;
  next?: { revalidate: number };
} {
  if (
    process.env.E2E_SEED_DATA === '1' ||
    process.env.NODE_ENV !== 'production'
  ) {
    return { cache: 'no-store' };
  }
  return { next: { revalidate: revalidateSeconds } };
}

export class ApiError extends Error {
  status: number;
  avisos: Aviso[];

  constructor(message: string, status: number, avisos: Aviso[] = []) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.avisos = avisos;
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { next?: { revalidate?: number } }
): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options?.headers || {}),
    },
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      data?.error || `Error HTTP ${res.status}`,
      res.status,
      data?.avisos || []
    );
  }
  return data as T;
}

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>(
    '/api/v1/dashboard',
    getCacheStrategy(60)
  );
}

export async function getLeagues(): Promise<LeaguesResponse> {
  return apiFetch<LeaguesResponse>(
    '/api/v1/leagues',
    getCacheStrategy(3600)
  );
}

export async function getLeagueTeams(ligaId: number): Promise<LeagueTeamsResponse> {
  try {
    return await apiFetch<LeagueTeamsResponse>(
      `/api/v1/leagues/${ligaId}/teams`,
      getCacheStrategy(3600)
    );
  } catch (err) {
    const avisos = err instanceof ApiError ? err.avisos : [];
    return {
      liga_id: ligaId,
      liga: '',
      equipos: [],
      avisos: avisos.length
        ? avisos
        : [{ nivel: 'warning', mensaje: 'No se pudieron cargar datos de la liga.' }],
    };
  }
}

export async function getFixtures(ligaId: number): Promise<FixturesResponse> {
  try {
    return await apiFetch<FixturesResponse>(
      `/api/v1/fixtures?liga_id=${ligaId}`,
      getCacheStrategy(300)
    );
  } catch {
    try {
      const fallback = await apiFetch<FixturesResponse>(
        '/api/v1/fixtures?liga_id=1',
        getCacheStrategy(300)
      );
      return {
        ...fallback,
        avisos: [
          { nivel: 'danger', mensaje: '❌ Liga no válida.' },
          ...(fallback.avisos || []),
        ],
      };
    } catch {
      return {
        liga_id: ligaId,
        liga: 'Premier League',
        liga_actual: {
          id: ligaId,
          nombre: 'Premier League',
          codigo: 'E0',
          bandera: '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        },
        total: 0,
        partidos: [],
        avisos: [
          {
            nivel: 'danger',
            mensaje:
              '⚠️ No se pudo conectar con la API backend (:5000). Verifica que Flask esté en ejecución.',
          },
        ],
      };
    }
  }
}

export async function getLiveMatches(): Promise<LiveResponse> {
  try {
    return await apiFetch<LiveResponse>('/api/v1/live', {
      cache: 'no-store',
    });
  } catch {
    return {
      total: 0,
      partidos: [],
      es_demo: false,
    };
  }
}

export async function getHistory(
  leagueCode: string,
  days: number
): Promise<HistoryResponse> {
  const params = new URLSearchParams({
    league_code: leagueCode,
    days: String(days),
  });
  try {
    return await apiFetch<HistoryResponse>(
      `/api/v1/history?${params.toString()}`,
      getCacheStrategy(120)
    );
  } catch {
    return {
      liga_id: 1,
      league_code: leagueCode || 'E0',
      days,
      liga_actual: {
        nombre: 'Premier League',
        bandera: '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        liga_id: 1,
        codigo: 'E0',
      },
      ligas: {},
      es_demo: false,
      avisos: [
        {
          nivel: 'danger',
          mensaje:
            '⚠️ No se pudo conectar con la API backend (:5000). Verifica que Flask esté en ejecución.',
        },
      ],
      estadisticas: {
        total_partidos: 0,
        evaluados: 0,
        aciertos: 0,
        fallos: 0,
        sin_prediccion: 0,
        precision: 0,
      },
      resultados: [],
    };
  }
}

export async function getPrediction(params: {
  ligaId: number;
  local: string;
  visitante: string;
}): Promise<{ data: PredictResponse | null; avisos: Aviso[] }> {
  if (params.local === params.visitante) {
    return {
      data: null,
      avisos: [{ nivel: 'warning', mensaje: '⚠️ Debes seleccionar dos equipos diferentes.' }],
    };
  }

  const query = new URLSearchParams({
    liga_id: String(params.ligaId),
    local: params.local,
    visitante: params.visitante,
  });

  try {
    const data = await apiFetch<PredictResponse>(
      `/api/v1/predict?${query.toString()}`,
      getCacheStrategy(300)
    );
    if (!data || !data.probabilidades || !data.goles_esperados) {
      return {
        data: null,
        avisos: [
          {
            nivel: 'danger',
            mensaje: 'No se recibieron datos válidos de predicción.',
          },
        ],
      };
    }
    return { data, avisos: data.avisos || [] };
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        data: null,
        avisos: err.avisos.length
          ? err.avisos
          : [{ nivel: 'danger', mensaje: err.message }],
      };
    }
    return {
      data: null,
      avisos: [{ nivel: 'danger', mensaje: 'Error al consultar la predicción.' }],
    };
  }
}
