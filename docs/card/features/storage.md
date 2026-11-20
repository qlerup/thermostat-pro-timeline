# Shared storage, sync, backup

Use shared storage when several dashboards should see the same schedule or the schedule should run with all browsers closed. Enable auto-apply for background temperature updates. Instant and delayed sync control when edits reach the shared store. A delayed write can leave another dashboard showing the previous version until the delay expires.

Before changing several rooms, create a backup with the [backup action](../../integration/services.md). Distinct instance IDs keep separate sets of schedules and settings. Check the active instance if two dashboards disagree.

## Check the restored schedule

In the dashboard card editor, open the backup controls. Choose the slot, select the main schedule and restore it. The Office row was empty before this restore. Its 08:00 to 17:00 block now appears again at 23 degrees.

[![Office timeline after restoring its saved daytime block](../../images/restored-result.png)](../../images/restored-result.png)

## Settings

- storage_enabled: true/false. Default on. Uses file‑based storage via the integration; no helper sensor entity needed.
- instance_enabled: true to keep separate schedules/settings by `instance_id`.
- instance_id: free text (normalized to safe id) — e.g. winter, summer.
- storage_sync_mode: instant | delay (delay batches writes)
- storage_sync_min / storage_sync_sec: delay config if `storage_sync_mode: delay` (min/sec).
- backup_auto_enabled: true/false and backup_interval_days: 1..365 for automatic backups.

## Choose an instance

Use the same instance ID on dashboards that edit the same plan. Give a second plan its own ID and use the **select_instance** action to activate it. When creating an instance, choose whether to start empty or copy the active plan.

## Save and restore a backup

Create a backup slot before making a large change. Select the sections to include, such as the main schedule, weekdays or colors. To recover only a timetable, select its slot and the relevant schedule section. Choose **Merge** to combine the selected data with existing entries or **Replace** to replace the selected sections.

Enable automatic backups and set the interval in days to create recurring snapshots. To move a backup to another installation, export the backup, import it there and then restore the desired slot.
