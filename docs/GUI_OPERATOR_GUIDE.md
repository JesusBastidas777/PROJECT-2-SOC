# Terminal UI operator guide

Run `python3 -m soc.cli ui --once` for a snapshot or omit `--once` for periodic
refresh. Choose `--view overview|alerts|hosts|incidents|forex`. Filters include
`--host`, `--priority`, `--status`, and `--max-rows`.

Alerts may be explicitly changed with `--select-alert ID --alert-action
acknowledged|closed`. Incidents use `--select-incident ID --incident-action
investigating|contained|closed`. These actions are separate from refresh.

Red means critical/high/degraded, green healthy/success, yellow operational
information, `#808000` headings, and grey62 unavailable/unknown. On refresh
failure the last valid view remains visible with stale/degraded diagnostics.
