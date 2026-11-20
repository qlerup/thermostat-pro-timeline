# Tips & troubleshooting

- Resource missing: If the card isn’t found, reload the browser cache. In YAML dashboards, ensure the resource is declared with type: module and url: /local/thermostat-pro-timeline.js.
- No helper entity needed: Storage is file‑based via the integration; keep `storage_enabled: true` unless you intentionally prefer purely local (per‑browser) storage.
- Background control: With storage enabled, thermostats update even when the card is closed. Without it, commands are sent only while a card is open on a device.
- Multi‑instance: Enable `instance_enabled: true` and set a distinct `instance_id` per card or switch globally via `select_instance`.
