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
