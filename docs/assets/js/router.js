import { DEFAULT_PAGE_ID, PAGES } from './page-registry.js';

export function getRoutePageId() {
  const raw = window.location.hash.replace(/^#\/?/, '').trim();
  if (!raw) return DEFAULT_PAGE_ID;
  const pageId = raw.split('/')[0];
  return PAGES[pageId] ? pageId : DEFAULT_PAGE_ID;
}

export function onRouteChange(callback) {
  window.addEventListener('hashchange', callback);
}
