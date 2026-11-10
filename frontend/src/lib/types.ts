export interface Aviso {
  nivel: 'info' | 'warning' | 'danger' | 'success';
  mensaje: string;
}

export interface LeagueInfo {
  id: number;
  nombre: string;
  codigo: string;
  bandera: string;
  has_fixture?: boolean;
}

export interface LeaguesResponse {
  total: number;
  leagues: LeagueInfo[];
}

export interface LeagueTeamsResponse {
  liga_id: number;
  liga: string;
  equipos: string[];
  avisos?: Aviso[];
}

export interface MatchPrediction1X2 {
  local: number;
  empate: number;
  visitante: number;
}

export interface DashboardMatch {
  local: string;
  visitante: string;
  hora: string;
  fecha_utc?: string;
  recomendacion?: string;
  prediccion?: MatchPrediction1X2 | null;
}

export interface DashboardLeagueBlock {
  nombre: string;
  partidos: DashboardMatch[];
}

export interface DashboardResponse {
  total_ligas: number;
  ligas: Record<string, { nombre: string; codigo?: string; bandera?: string }>;
  partidos_hoy: Record<string, DashboardLeagueBlock>;
  total_partidos_hoy: number;
  last_update: string;
  updated_at: string;
  cache_missing: boolean;
}

export interface FixtureMatch {
  local: string;
  visitante: string;
  fecha: string;
  fecha_utc?: string | null;
  prediccion: MatchPrediction1X2 | null;
  mejor_recomendacion?: string | null;
  recomendacion?: string | null;
  error?: string | null;
}

export interface FixturesResponse {
  liga_id: number;
  liga: string;
  liga_actual: {
    id: number;
    nombre: string;
    codigo: string;
    bandera: string;
  };
  total: number;
  partidos: FixtureMatch[];
  avisos?: Aviso[];
}

export interface TopScore {
  marcador: string;
  prob: number;
}

export interface Recommendation {
  class: string;
  corto: string;
  emoji?: string;
  icon: string;
  prob: number;
  texto: string;
}

export interface ValueBetItem {
  mercado: string;
  prob_ia: number;
  cuota: number;
  ev_pct: number;
  kelly_pct: number;
}

export interface CornersData {
  total: number;
  local: number;
  visitante: number;
  prob_local_mas_corners: number;
  over_85: number;
  over_95: number;
}

export interface CardsData {
  amarillas_total: number;
  amarillas_local: number;
  amarillas_visitante: number;
  rojas_local: number;
  rojas_visitante: number;
  prob_roja: number;
  over_25: number;
  over_35: number;
  over_45: number;
  under_55: number;
}

export interface PredictResponse {
  local: string;
  visitante: string;
  liga_id: number;
  liga: string;
  avisos: Aviso[];
  probabilidades: {
    local: number;
    empate: number;
    visitante: number;
    doble_oportunidad: {
      '1X': number;
      'X2': number;
      '12': number;
    };
  };
  goles_esperados: {
    local: number;
    visitante: number;
    total: number;
  };
  mercados: {
    over_15: number;
    over_25: number;
    under_35: number;
    corners_promedio: number;
    tarjetas_promedio: number;
    prob_tarjeta_roja: number;
  };
  corners: CornersData;
  tarjetas: CardsData;
  top_marcadores: TopScore[];
  recomendaciones: Recommendation[];
  value_bets: ValueBetItem[];
}

export interface LiveInPlayPrediction {
  is_live?: boolean;
  minuto: number;
  marcador_actual?: string;
  prob_local: number;
  prob_empate: number;
  prob_visitante: number;
  xG_restante_local: number;
  xG_restante_vis: number;
  proximo_gol?: {
    local: number;
    visitante: number;
    sin_mas_goles?: number;
  };
  estado_tactico: string;
}

export interface LivePrematchPrediction {
  prob_local: number;
  prob_empate: number;
  prob_visitante: number;
  xg_local?: number;
  xg_vis?: number;
}

export interface LiveMatch {
  status: string;
  seccion?: 'live' | 'proximos' | string;
  minute?: number;
  utcDate?: string;
  _timestamp?: number;
  league?: string;
  home?: string;
  away?: string;
  home_score?: number;
  away_score?: number;
  competition?: {
    name?: string;
    area?: {
      name?: string;
    };
  };
  homeTeam?: {
    name?: string;
  };
  awayTeam?: {
    name?: string;
  };
  score?:
    | string
    | {
        fullTime?: {
          home?: number | null;
          away?: number | null;
        };
      };
  prediccion_timba?: {
    prob_local?: number;
    prob_empate?: number;
    prob_visitante?: number;
    over_25?: number;
  };
  prediccion_live?: LiveInPlayPrediction;
  prediccion_prematch?: LivePrematchPrediction;
}

export interface LiveResponse {
  total: number;
  partidos: LiveMatch[];
  es_demo?: boolean;
}

export interface HistoryLeagueMeta {
  nombre: string;
  bandera: string;
  liga_id: number;
  codigo?: string;
}

export interface HistoryStats {
  total_partidos: number;
  evaluados: number;
  aciertos: number;
  fallos: number;
  sin_prediccion: number;
  precision: number;
}

export interface HistoryResultRow {
  fecha: string;
  local: string;
  visitante: string;
  goles_local: number;
  goles_visitante: number;
  resultado_real: 'HOME_WIN' | 'AWAY_WIN' | 'DRAW' | string;
  prediccion_ia?: 'HOME_WIN' | 'AWAY_WIN' | '1X' | 'X2' | '12' | 'DRAW' | string | null;
  prediccion_prob?: number;
  prob_local?: number;
  prob_empate?: number;
  prob_visitante?: number;
  acierto: boolean | null;
}

export interface HistoryResponse {
  liga_id: number;
  league_code: string;
  days: number;
  liga_actual: HistoryLeagueMeta;
  ligas: Record<string, HistoryLeagueMeta>;
  es_demo: boolean;
  avisos: Aviso[];
  estadisticas: HistoryStats;
  resultados: HistoryResultRow[];
}
