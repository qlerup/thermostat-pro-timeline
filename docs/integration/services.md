# Integration services

All services live under the domain `thermostat_timeline`. You can call them from Developer Tools → Services or in automations/scripts.

Service: `set_store` — replace full store (optionally for an instance)

```yaml
service: thermostat_timeline.set_store
data:
  instance_id: winter
  activate: true
  schedules:
    climate.living_room:
      defaultTemp: 20
      blocks:
        - { startMin: 360, endMin: 480, temp: 21 }
  settings:
    min_temp: 5
    max_temp: 25
    labels: { climate.living_room: "Living" }
```

Service: `patch_entity` — merge into a single entity

```yaml
service: thermostat_timeline.patch_entity
data:
  entity_id: climate.kitchen
  data:
    defaultTemp: 21
    blocks:
      - { startMin: 1020, endMin: 1320, temp: 22 }
```

Service: `select_instance` — make an instance active (create/copy if needed)

```yaml
service: thermostat_timeline.select_instance
data:
  instance_id: summer
  create_if_missing: true
  copy_from_active: true
```

Service: `rename_instance`

```yaml
service: thermostat_timeline.rename_instance
data:
  old_instance_id: winter
  new_instance_id: heating_2026
```

Service: `backup_now` — create backup; choose sections

```yaml
service: thermostat_timeline.backup_now
data:
  main: true
  weekday: true
  presence: true
  settings: true
  holiday: true
  colors: true
```

Service: `restore_now` — restore backup; merge or replace and choose sections

```yaml
service: thermostat_timeline.restore_now
data:
  mode: merge
  main: true
  weekday: true
  presence: false
  settings: true
  holiday: false
  colors: true
```

Utilities

- `clear`: Clear all schedules and bump version.
- `factory_reset`: Delete integration storage files and recreate empty (removes all instances, schedules, settings, backups).
