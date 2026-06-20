import { PAGES } from './page-registry.js';
import { getRoutePageId, onRouteChange } from './router.js';
import {
  closeSidebarIfOpen,
  renderShell,
  setActiveNav,
  setTopbarDataset,
  toggleNavCollapse,
  toggleSidebar,
} from './layout.js';

const appRoot = document.getElementById('app');
let activePage = null;
let activePageId = null;
let currentDataset = 1;
let routeRenderToken = 0;

async function renderCurrentRoute() {
  const renderToken = ++routeRenderToken;
  renderShell(appRoot);

  const pageId = getRoutePageId();
  const pageDef = PAGES[pageId] || PAGES.cards;

  const page = await pageDef.load();
  if (renderToken !== routeRenderToken) return;

  if (activePage && activePage.unmount) activePage.unmount();
  activePageId = pageDef.id;
  setActiveNav(activePageId);
  closeSidebarIfOpen();
  activePage = page;

  document.title = page.title ? `${page.title} | Ark Nova Statistics` : 'Ark Nova Statistics';
  document.getElementById('pageMain').innerHTML = page.mainHtml || '';
  document.getElementById('sidebar').innerHTML = page.sidebarHtml || '';
  setTopbarDataset(currentDataset);

  if (page.mount) page.mount({ dataset: currentDataset, pageId: activePageId });
}

function setDataset(value, button) {
  currentDataset = Number(value) === 0 ? 0 : 1;
  setTopbarDataset(currentDataset);
  if (activePage && activePage.setDataset) activePage.setDataset(currentDataset);
}

window.setTab = setDataset;
window.toggleSidebar = toggleSidebar;
window.toggleNavCollapse = toggleNavCollapse;

onRouteChange(renderCurrentRoute);
renderCurrentRoute();



