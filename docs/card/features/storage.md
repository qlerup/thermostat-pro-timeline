# Shared storage, sync, backup

Use shared storage when several dashboards should see the same schedule or the schedule should run with all browsers closed. Enable auto-apply for background temperature updates. Instant and delayed sync control when edits reach the shared store. A delayed write can leave another dashboard showing the previous version until the delay expires.

Before changing several rooms, create a backup with the [backup action](../../integration/services.md). Distinct instance IDs keep separate sets of schedules and settings. Check the active instance if two dashboards disagree.

## Settings

- storage_enabled: true/false. Default on. Uses file‑based storage via the integration; no helper sensor entity needed.
- instance_enabled: true to keep separate schedules/settings by `instance_id`.
- instance_id: free text (normalized to safe id) — e.g. winter, summer.
- storage_sync_mode: instant | delay (delay batches writes)
- storage_sync_min / storage_sync_sec: delay config if `storage_sync_mode: delay` (min/sec).
- backup_auto_enabled: true/false and backup_interval_days: 1..365 for automatic backups.
