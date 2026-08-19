# Local backup and restore

`SOCService.create_backup(path)` captures events and alerts under locks ordered
by canonical path. A versioned `manifest.json` records relative names, sizes,
SHA-256 checksums, creation time, and the `soc-jsonl-v1` logical signature.

Use `verify_backup(path)` without changing active state. `restore_backup(path,
dry_run=True)` performs the same validation and reports readiness. A real
restore first creates a verified pre-restore safety backup, stages both active
files, and rolls both back if either replacement fails. Derived UID data is
rebuilt from the restored event JSONL.

CLI equivalents are `soc backup create PATH`, `soc backup verify PATH`, and
`soc backup restore PATH [--dry-run]`.
