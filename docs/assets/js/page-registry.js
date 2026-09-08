export const DEFAULT_PAGE_ID = 'cards';

// Public temporary dashboard: keep this registry intentionally limited to the
// six published views. The disabled More coming soon item is navigation-only
// and has no route.
export const PAGES = {
  cards: {
    id: 'cards',
    title: 'Cards',
    navLabel: 'Cards',
    load: () => import('./pages/cards.js?v=20260908-temp-six-pages'),
  },
  'opening-hand': {
    id: 'opening-hand',
    title: 'Opening Hand',
    navLabel: 'Opening Hand',
    load: () => import('./pages/opening-hand.js?v=20260908-temp-six-pages'),
  },
  'mw-action-cards': {
    id: 'mw-action-cards',
    title: 'MW Action Cards',
    navLabel: 'MW Action Cards',
    load: () => import('./pages/mw-action-cards.js?v=20260908-temp-six-pages'),
  },
  maps: {
    id: 'maps',
    title: 'Maps',
    navLabel: 'Maps',
    load: () => import('./pages/maps.js?v=20260908-temp-six-pages'),
  },
  players: {
    id: 'players',
    title: 'Players',
    navLabel: 'Players',
    load: () => import('./pages/players.js?v=20260908-temp-six-pages'),
  },
  arena: {
    id: 'arena',
    title: 'Arena',
    navLabel: 'Arena',
    load: () => import('./pages/arena.js?v=20260908-temp-six-pages'),
  },
};
