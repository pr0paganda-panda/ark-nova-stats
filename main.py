import functions_framework
import json
from datetime import date
from google.cloud import bigquery

# ── Constants ──────────────────────────────────────────────────────────────────

EXCLUDED_PROJECTS = {
    'reptiles', 'europe', 'predators', 'americas', 'australia',
    'birds', 'sea animals', 'africa', 'herbivores', 'asia',
    'primates', 'habitat diversity', 'species diversity'
}

INVALID_MAPS = [
    'Map 0', 'Map A',
    'Map 1: Observation Tower', 'Map 2: Outdoor Areas',
    'Map 3: Silver Lake',       'Map 4: Commercial Harbor',
    'Map 5: Park Restaurant',   'Map 6: Research Institute',
    'Map 7: Ice Cream Parlors', 'Map 8: Hollywood Hills',
]

VALID_MAPS = [
    'Map 1a: Observation Tower', 'Map 2a: Outdoor Areas',
    'Map 3a: Silver Lake',       'Map 4a: Commercial Harbor',
    'Map 5a: Park Restaurant',   'Map 6a: Research Institute',
    'Map 7a: Ice Cream Parlors', 'Map 8a: Hollywood Hills',
    'Map 9: Geographical Zoo',   'Map 10: Rescue Station',
    'Map 11: Caves',             'Map 12: Artificial Intelligence',
    'Map 13: Drawing Board',     'Map 14: Lagoon',
    'Map T1: Tournament 1',
]

# Round filter tokens accepted from the frontend.
# "6+" is translated to played round >= 6.
VALID_ROUNDS = {'1', '2', '3', '4', '5', '6+'}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_round_filter(raw_rounds):
    """Return (selected_round_tokens, active) for the optional played-round filter."""
    if not isinstance(raw_rounds, list):
        return [], False

    selected = []
    for value in raw_rounds:
        token = str(value).strip()
        if token in VALID_ROUNDS and token not in selected:
            selected.append(token)

    # Empty, invalid, or all rounds selected means no round filter.
    if not selected or set(selected) == VALID_ROUNDS:
        return [], False

    return selected, True


def _round_condition(alias, selected_rounds):
    """Build safe SQL for a played_* struct alias such as pa, ps, or pp."""
    exact_rounds = sorted(int(r) for r in selected_rounds if r != '6+')
    conditions = []

    if exact_rounds:
        conditions.append(f"{alias}.round IN ({', '.join(str(r) for r in exact_rounds)})")
    if '6+' in selected_rounds:
        conditions.append(f"{alias}.round >= 6")

    return "(" + " OR ".join(conditions) + ")"


def _parse_iso_date(raw_value, field_name, default=None):
    """Return a datetime.date for YYYY-MM-DD input, or raise ValueError."""
    if raw_value in (None, ""):
        return default
    if not isinstance(raw_value, str):
        raise ValueError(f"{field_name} must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid YYYY-MM-DD date") from exc


# ── Entry point ────────────────────────────────────────────────────────────────

@functions_framework.http
def get_card_stats(request):
    """HTTP Cloud Function that returns Ark Nova card statistics."""

    # CORS headers so the browser can call this from GitHub Pages
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json',
    }

    # Handle preflight OPTIONS request (browser sends this before the real request)
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    # ── Parse filter parameters from the request ───────────────────────────────
    params = request.get_json(silent=True) or {}

    is_mw                  = int(params.get('is_mw', 1))           # 1 = MW, 0 = Base
    player_elo_min         = params.get('player_elo_min', 300)
    player_elo_max         = params.get('player_elo_max', None)
    opponent_elo_min       = params.get('opponent_elo_min', 300)
    opponent_elo_max       = params.get('opponent_elo_max', None)
    try:
        date_from          = _parse_iso_date(params.get('date_from', '2025-01-01'), 'date_from', date(2025, 1, 1))
        date_to            = _parse_iso_date(params.get('date_to', None), 'date_to')
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be on or before date_to")
    except ValueError as exc:
        return (json.dumps({'status': 'error', 'message': str(exc)}), 400, headers)

    end_game_triggered     = params.get('end_game_triggered', True) # True/False/None (None = no filter)
    selected_maps          = params.get('maps', VALID_MAPS)         # list of map strings
    card_types             = params.get('card_types', ['animal', 'sponsor', 'project'])
    selected_rounds, round_filter_active = _parse_round_filter(params.get('rounds'))

    # Validate selected maps — only allow known valid maps, never the invalid ones
    selected_maps = [m for m in selected_maps if m in VALID_MAPS]
    if not selected_maps:
        selected_maps = VALID_MAPS  # fallback to all if empty

    # ── Build dynamic WHERE clause for full_filtered ───────────────────────────
    where_clauses = [
        f"is_mw = {is_mw}",
        f"Map NOT IN ({', '.join(repr(m) for m in INVALID_MAPS)})",
        f"Map IN ({', '.join(repr(m) for m in selected_maps)})",
    ]
    query_parameters = []

    if player_elo_min is not None:
        where_clauses.append(f"elo >= {int(player_elo_min)}")
    if player_elo_max is not None:
        where_clauses.append(f"elo <= {int(player_elo_max)}")
    if opponent_elo_min is not None:
        where_clauses.append(f"opponent_elo >= {int(opponent_elo_min)}")
    if opponent_elo_max is not None:
        where_clauses.append(f"opponent_elo <= {int(opponent_elo_max)}")
    if date_from:
        where_clauses.append("CAST(game_ended_at AS DATE) >= @date_from")
        query_parameters.append(bigquery.ScalarQueryParameter("date_from", "DATE", date_from))
    if date_to:
        where_clauses.append("CAST(game_ended_at AS DATE) <= @date_to")
        query_parameters.append(bigquery.ScalarQueryParameter("date_to", "DATE", date_to))
    if end_game_triggered is True:
        where_clauses.append("end_game_triggered = TRUE")
    elif end_game_triggered is False:
        where_clauses.append("end_game_triggered = FALSE")

    where_sql = " AND ".join(where_clauses)

    # ── Excluded projects as SQL array literal ─────────────────────────────────
    excluded_projects_sql = ", ".join(f"'{p}'" for p in EXCLUDED_PROJECTS)

    # Round filter SQL snippets. These are safe because selected_rounds was
    # whitelisted by _parse_round_filter().
    animal_round_sql = f" AND {_round_condition('pa', selected_rounds)}" if round_filter_active else ""
    sponsor_round_sql = f" AND {_round_condition('ps', selected_rounds)}" if round_filter_active else ""
    project_round_sql = f" AND {_round_condition('pp', selected_rounds)}" if round_filter_active else ""

    # ── Build the full query ───────────────────────────────────────────────────
    # Normal/default mode calculates all columns. Round-filter mode recalculates
    # played-only stats for the selected played rounds; in-hand/seen/playrate are
    # returned as NULL because the log does not track the round in which a card
    # was drawn or appeared on display.
    if round_filter_active:
        query = f"""
        -- ===== Step 1: Filter valid games from Full Sample =====
        WITH full_filtered AS (
          SELECT table_id, player, elo, elo_delta
          FROM `freestyle-190711.ark_nova.all_games_stat`
          WHERE {where_sql}
        ),

        -- Only keep log entries for games where both players have a log entry
        valid_log_ids AS (
          SELECT table_id
          FROM `freestyle-190711.ark_nova.game_log_stat_v2`
          GROUP BY table_id
          HAVING COUNT(*) = 2
        ),

        -- Join log sample to filtered full sample
        log_filtered AS (
          SELECT l.*
          FROM `freestyle-190711.ark_nova.game_log_stat_v2` l
          JOIN full_filtered f ON l.table_id = f.table_id AND l.player = f.player
          JOIN valid_log_ids v ON l.table_id = v.table_id
        ),

        -- ===== Step 2: PLAYED IN SELECTED ROUND(S) =====

        played_animals AS (
          SELECT l.table_id, l.player, pa.animal AS card_name, 'animal' AS card_type, f.elo_delta, f.elo
          FROM log_filtered l
          JOIN full_filtered f USING(table_id, player)
          CROSS JOIN UNNEST(l.played_animals) AS pa
          WHERE pa.animal IS NOT NULL
            {animal_round_sql}
        ),

        played_sponsors AS (
          SELECT l.table_id, l.player, ps.sponsor AS card_name, 'sponsor' AS card_type, f.elo_delta, f.elo
          FROM log_filtered l
          JOIN full_filtered f USING(table_id, player)
          CROSS JOIN UNNEST(l.played_sponsors) AS ps
          WHERE ps.sponsor IS NOT NULL
            {sponsor_round_sql}
        ),

        played_projects AS (
          SELECT l.table_id, l.player, pp.project AS card_name, 'project' AS card_type, f.elo_delta, f.elo
          FROM log_filtered l
          JOIN full_filtered f USING(table_id, player)
          CROSS JOIN UNNEST(l.played_projects) AS pp
          WHERE pp.project IS NOT NULL
            AND LOWER(pp.project) NOT IN ({excluded_projects_sql})
            {project_round_sql}
        ),

        all_played AS (
          SELECT * FROM played_animals
          UNION ALL
          SELECT * FROM played_sponsors
          UNION ALL
          SELECT * FROM played_projects
        ),

        played_agg AS (
          SELECT
            card_name,
            card_type,
            COUNT(DISTINCT table_id)    AS n_played,
            ROUND(AVG(elo_delta), 3)    AS delta_played,
            ROUND(AVG(elo), 0)          AS avg_elo
          FROM all_played
          GROUP BY card_name, card_type
        )

        SELECT
          card_type,
          card_name,
          delta_played,
          CAST(NULL AS FLOAT64) AS delta_in_hand,
          avg_elo,
          n_played,
          CAST(NULL AS INT64)   AS n_seen,
          CAST(NULL AS FLOAT64) AS playrate_pct
        FROM played_agg
        ORDER BY card_type, n_played DESC, delta_played DESC NULLS LAST
        """
    else:
        query = f"""
        -- ===== Step 1: Filter valid games from Full Sample =====
        WITH full_filtered AS (
          SELECT table_id, player, elo, elo_delta
          FROM `freestyle-190711.ark_nova.all_games_stat`
          WHERE {where_sql}
        ),

        -- Only keep log entries for games where both players have a log entry
        valid_log_ids AS (
          SELECT table_id
          FROM `freestyle-190711.ark_nova.game_log_stat_v2`
          GROUP BY table_id
          HAVING COUNT(*) = 2
        ),

        -- Join log sample to filtered full sample
        log_filtered AS (
          SELECT l.*
          FROM `freestyle-190711.ark_nova.game_log_stat_v2` l
          JOIN full_filtered f ON l.table_id = f.table_id AND l.player = f.player
          JOIN valid_log_ids v ON l.table_id = v.table_id
        ),

        -- ===== Step 2: PLAYED — unnest all three card types =====

        played_animals AS (
          SELECT l.table_id, l.player, pa.animal AS card_name, 'animal' AS card_type, f.elo_delta, f.elo
          FROM log_filtered l
          JOIN full_filtered f USING(table_id, player)
          CROSS JOIN UNNEST(l.played_animals) AS pa
          WHERE pa.animal IS NOT NULL
        ),

        played_sponsors AS (
          SELECT l.table_id, l.player, ps.sponsor AS card_name, 'sponsor' AS card_type, f.elo_delta, f.elo
          FROM log_filtered l
          JOIN full_filtered f USING(table_id, player)
          CROSS JOIN UNNEST(l.played_sponsors) AS ps
          WHERE ps.sponsor IS NOT NULL
        ),

        played_projects AS (
          SELECT l.table_id, l.player, pp.project AS card_name, 'project' AS card_type, f.elo_delta, f.elo
          FROM log_filtered l
          JOIN full_filtered f USING(table_id, player)
          CROSS JOIN UNNEST(l.played_projects) AS pp
          WHERE pp.project IS NOT NULL
            AND LOWER(pp.project) NOT IN ({excluded_projects_sql})
        ),

        all_played AS (
          SELECT * FROM played_animals
          UNION ALL
          SELECT * FROM played_sponsors
          UNION ALL
          SELECT * FROM played_projects
        ),

        -- ===== Step 3: IN HAND — card appears in cards_drawn =====

        in_hand AS (
          SELECT DISTINCT
            l.table_id,
            l.player,
            TRIM(cd) AS card_name,
            f.elo_delta
          FROM log_filtered l
          JOIN full_filtered f USING(table_id, player)
          CROSS JOIN UNNEST(IFNULL(l.cards_drawn, [])) AS cd
          WHERE TRIM(cd) != ''
            AND LOWER(TRIM(cd)) NOT IN ({excluded_projects_sql})
        ),

        -- ===== Step 4: SEEN — card in cards_drawn OR display_cards (no double count) =====

        seen_from_hand AS (
          SELECT DISTINCT l.table_id, TRIM(cd) AS card_name
          FROM log_filtered l
          CROSS JOIN UNNEST(IFNULL(l.cards_drawn, [])) AS cd
          WHERE TRIM(cd) != ''
            AND LOWER(TRIM(cd)) NOT IN ({excluded_projects_sql})
        ),

        seen_from_display AS (
          SELECT DISTINCT l.table_id, TRIM(dc) AS card_name
          FROM log_filtered l
          CROSS JOIN UNNEST(IFNULL(l.display_cards, [])) AS dc
          WHERE TRIM(dc) != ''
            AND LOWER(TRIM(dc)) NOT IN ({excluded_projects_sql})
        ),

        -- Union gives us distinct (table_id, card_name) across both sources and both players
        all_seen AS (
          SELECT table_id, card_name FROM seen_from_hand
          UNION DISTINCT
          SELECT table_id, card_name FROM seen_from_display
        ),

        -- ===== Step 5: Aggregate per card =====

        played_agg AS (
          SELECT
            card_name,
            card_type,
            COUNT(DISTINCT table_id)    AS n_played,
            ROUND(AVG(elo_delta), 3)    AS delta_played,
            ROUND(AVG(elo), 0)          AS avg_elo
          FROM all_played
          GROUP BY card_name, card_type
        ),

        in_hand_agg AS (
          SELECT
            card_name,
            COUNT(*)                    AS n_in_hand,
            ROUND(AVG(elo_delta), 3)    AS delta_in_hand
          FROM in_hand
          GROUP BY card_name
        ),

        seen_agg AS (
          SELECT
            card_name,
            COUNT(*)                    AS n_seen
          FROM all_seen
          GROUP BY card_name
        )

        -- ===== Step 6: Join everything together =====
        SELECT
          p.card_type,
          p.card_name,
          p.delta_played,
          h.delta_in_hand,
          p.avg_elo,
          p.n_played,
          s.n_seen,
          CASE
            WHEN s.n_seen IS NULL OR s.n_seen = 0 THEN NULL
            ELSE ROUND(100.0 * p.n_played / s.n_seen, 2)
          END AS playrate_pct
        FROM played_agg p
        LEFT JOIN in_hand_agg h USING(card_name)
        LEFT JOIN seen_agg     s USING(card_name)
        ORDER BY p.card_type, playrate_pct DESC NULLS LAST
        """

    # ── Run the query ──────────────────────────────────────────────────────────
    try:
        client = bigquery.Client(project='freestyle-190711')
        job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
        results = client.query(query, job_config=job_config).result()

        # Convert to list of dicts, filtering by requested card_types
        rows = []
        for row in results:
            if row.card_type in card_types:
                rows.append({
                    'card_type':     row.card_type,
                    'card_name':     row.card_name,
                    'delta_played':  row.delta_played,
                    'delta_in_hand': row.delta_in_hand,
                    'avg_elo':       row.avg_elo,
                    'n_played':      row.n_played,
                    'n_seen':        row.n_seen,
                    'playrate_pct':  row.playrate_pct,
                })

        return (json.dumps({
            'status': 'ok',
            'round_filter_active': round_filter_active,
            'data': rows,
        }), 200, headers)

    except Exception as e:
        return (json.dumps({'status': 'error', 'message': str(e)}), 500, headers)
