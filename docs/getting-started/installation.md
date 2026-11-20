# Installation

## With HACS

1. [Open Thermostat Pro Timeline in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=qlerup&repository=thermostat-pro-timeline). For a custom repository, use `https://github.com/qlerup/thermostat-pro-timeline` and select **Integration**.
2. Download the release and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration** and select **Thermostat Pro Timeline**. If it is already configured, continue to the [quick start](quick-start.md).

## From a release ZIP

1. Download **thermostat-pro-timeline-sync.zip** from the [latest release](https://github.com/qlerup/thermostat-pro-timeline/releases/latest).
2. Extract the contents to `config/custom_components/thermostat_timeline/`. The folder should contain `manifest.json` and `www/thermostat-pro-timeline.js`.
3. Restart Home Assistant and add the integration under **Settings → Devices & services**.

## Dashboard resources

During integration setup, the bundled card is copied to `config/www/thermostat-pro-timeline.js`. Storage-managed dashboards support automatic resource registration. If you manage resources in YAML, include this entry in the Lovelace resource list:

```yaml
- url: /local/thermostat-pro-timeline.js
  type: module
```

If a newly created `www` folder returns a 404, restart Home Assistant and check the resource URL again. Then [add your first room](quick-start.md).
