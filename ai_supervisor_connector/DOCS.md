# AI Supervisor V5 Connector 5.0.0-alpha6

## What Alpha6 adds

Alpha6 builds a process map locally before the AI model is used. The map follows:

```text
device -> entities -> YAML components -> supporting helpers -> dashboards -> files
```

YAML components include automations, scripts, scenes, templates and helper definitions. Lovelace dashboards are read through the Home Assistant WebSocket API and reduced to safe metadata: dashboard title, URL path, view title/path, card count and referenced entity IDs.

## Read-only discovery

Use **Rasti proceso žemėlapį** to inspect what the system found before sending anything to OpenAI. A typical curtain process should show physical curtain devices, `cover.*` entities, related automations/scripts/helpers, dashboard references and source files.

## Write policy

Alpha6 writes only `.yaml` or `.yml` files under `/config/packages/`. A maximum of three files can be included in one transaction. Every transaction requires:

1. writes enabled in App Configuration;
2. an explicit confirmation phrase;
3. a Home Assistant backup;
4. strict YAML validation;
5. a Home Assistant configuration check;
6. automatic restoration of previous files when validation fails.

Home Assistant is not restarted automatically.
