export const id = 'opening-hand';
export const title = 'Opening Hand';
export const navLabel = 'Opening Hand';

export const mainHtml = `
  <div class="main-header">
    <div class="table-meta"><strong>Opening Hand</strong></div>
  </div>
  <div class="table-wrap">
    <div class="state-overlay">
      <div class="state-title">Opening Hand</div>
      <div class="state-sub">This route is wired up. The actual statistics view can be built here next.</div>
    </div>
  </div>
`;

export const sidebarHtml = `
  <div class="sidebar-header">
    <span class="sidebar-title">Filters</span>
    <div style="display:flex;align-items:center;gap:6px;">
      <button class="reset-btn" type="button">Reset</button>
      <button class="sidebar-close-btn" onclick="toggleSidebar()" title="Close filters">✕</button>
    </div>
  </div>
  <hr class="divider" />
  <div class="filter-group">
    <span class="filter-label">Opening Hand</span>
    <div class="state-sub" style="text-align:left;max-width:none;">Page-specific filters will go here.</div>
  </div>
  <hr class="divider" />
  <div class="filter-action-stack">
    <button class="apply-btn" type="button" onclick="toggleSidebar()">Apply filters</button>
  </div>
`;

export function mount() {}
export function unmount() {}
export function setDataset() {}
