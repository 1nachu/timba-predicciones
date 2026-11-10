export interface SidebarLeagueItem {
  id: number;
  nombre: string;
  nombreCompleto: string;
  codigo: string;
  bandera: string;
  destacado: boolean;
}

export const SIDEBAR_LEAGUES: SidebarLeagueItem[] = [
  { id: 10, nombre: 'Liga Profesional', nombreCompleto: 'Liga Profesional (Argentina)', codigo: 'ARG', bandera: '🇦🇷', destacado: true },
  { id: 8, nombre: 'Champions League', nombreCompleto: 'UEFA Champions League', codigo: 'UCL', bandera: '🏆', destacado: true },
  { id: 1, nombre: 'Premier League', nombreCompleto: 'Premier League (Inglaterra)', codigo: 'E0', bandera: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', destacado: true },
  { id: 2, nombre: 'La Liga', nombreCompleto: 'La Liga (España)', codigo: 'SP1', bandera: '🇪🇸', destacado: true },
  { id: 3, nombre: 'Serie A', nombreCompleto: 'Serie A (Italia)', codigo: 'I1', bandera: '🇮🇹', destacado: false },
  { id: 4, nombre: 'Bundesliga', nombreCompleto: 'Bundesliga (Alemania)', codigo: 'D1', bandera: '🇩🇪', destacado: false },
  { id: 5, nombre: 'Ligue 1', nombreCompleto: 'Ligue 1 (Francia)', codigo: 'F1', bandera: '🇫🇷', destacado: false },
  { id: 6, nombre: 'Primeira Liga', nombreCompleto: 'Primeira Liga (Portugal)', codigo: 'P1', bandera: '🇵🇹', destacado: false },
  { id: 7, nombre: 'Eredivisie', nombreCompleto: 'Eredivisie (Países Bajos)', codigo: 'N1', bandera: '🇳🇱', destacado: false },
];

export function getLeagueFlag(nombre: string): string {
  if (!nombre) return '⚽';
  if (nombre.includes('Argentina')) return '🇦🇷';
  if (nombre.includes('Premier')) return '🏴󠁧󠁢󠁥󠁮󠁧󠁿';
  if (nombre.includes('La Liga') || nombre.includes('España')) return '🇪🇸';
  if (nombre.includes('Serie') || nombre.includes('Italia')) return '🇮🇹';
  if (nombre.includes('Bundesliga') || nombre.includes('Alemania')) return '🇩🇪';
  if (nombre.includes('Ligue') || nombre.includes('Francia')) return '🇫🇷';
  if (nombre.includes('Primeira') || nombre.includes('Portugal')) return '🇵🇹';
  if (nombre.includes('Eredivisie') || nombre.includes('Países Bajos')) return '🇳🇱';
  if (nombre.includes('Champions')) return '🏆';
  return '⚽';
}
