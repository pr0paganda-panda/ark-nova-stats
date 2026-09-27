# Ark Nova Statistics — public preview

This repository publishes the limited public dashboard at
https://pr0paganda-panda.github.io/ark-nova-stats/.

The preview intentionally exposes six pages, in this order:

1. Cards
2. Opening Hand
3. MW Action Cards
4. Maps
5. Players
6. Arena

Cards is the default route. The disabled `More coming soon ;-)` navigation item
is a placeholder, not a route. The frontend reuses the production Cloud Storage
snapshot pack and the read-only DuckDB gateway; this repository has no separate
analytical backend or refresh pipeline.

Preview-specific differences from the full dashboard are intentional:

- Cards and Opening Hand do not link card names to detail pages.
- MW Action Cards / By map has no graph view.
- Maps / Tournament H2H has no Filter sidebar.

Filtered requests are sent to the allow-listed DuckDB gateway. Default views
load from the same atomically published snapshots as the full dashboard.

Player autocomplete in General, Comparison, and Performance by map searches
the already-loaded dataset-specific player index in the browser after three
typed characters. Statistics requests remain authoritative for merged player
identities and reject selecting two aliases belonging to the same person.

