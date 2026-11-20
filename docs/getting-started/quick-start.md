# Add your first thermostat

After [installation](installation.md), edit a dashboard and choose **Add card → Manual**. Paste this example and replace `climate.office` with your thermostat’s entity ID.

```yaml
type: custom:thermostat-timeline-card
title: Office heating
entities:
  - climate.office
default_temp: 20
storage_enabled: true
auto_apply: true
```

Save the card. Check that the room name and measured temperature appear. The small pause icon on the room row affects that room; the larger pause button in the header affects the whole schedule.

![A single Office thermostat displayed on the timeline](../images/office-dashboard.png)

## Try a schedule

Use a test room for the first run. Add a short block that starts a few minutes ahead and choose a target different from the room default. Double-click or double-tap an existing block to edit its time and temperature. With shared storage and auto-apply active, close the dashboard and check the thermostat's **target temperature** at the boundary. The measured air temperature can take much longer to change.

[Explore card settings](../card/configuration.md) · [Pause a room](../card/features/pause.md)
