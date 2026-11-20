# Color ranges

- color_global: true/false (use a single palette for all rooms when true)
- color_ranges: mapping of room or `*` to intervals:

```yaml
color_global: true
color_ranges:
  "*":
    - { from: 5, to: 18, color: "#4da3ff" }
    - { from: 18, to: 21, color: "#ffd166" }
    - { from: 21, to: 26, color: "#ff7f50" }
```

## Use a shared or per-room palette

Enable the global palette to give the same temperature the same color in every room. With the example above, a 20-degree block appears yellow and a 23-degree block appears orange. To give rooms their own palettes, disable the global option and use each room's entity ID in place of `"*"`. Colors change how blocks appear on the timeline.
