# AI Supervisor V5 Connector

Home Assistant side of the split AI Supervisor V5 architecture.

Version **5.0.0-alpha7** adds package- and Jinja-aware process discovery. Exact entity IDs are indexed directly from YAML text even when they appear inside templates, custom variables or custom fields. The Connector also catalogues package domains such as `automation`, `script`, helper domains and `template`.

The Windows Engine builds this dependency graph:

```text
exact process entity
  -> exact YAML/Jinja references
  -> primary package
  -> automations, scripts and helpers in that package
  -> supporting readiness/diagnostics files
  -> dashboard confirmation only
```

## Safety

- `secrets.yaml`, `.storage`, databases, logs and backups are excluded.
- Lovelace is read through the API; raw `.storage` files are not transmitted.
- Device identifiers, MAC addresses, serial numbers and credentials are omitted.
- Writes are disabled by default.
- This alpha can write only explicitly confirmed YAML transactions under `/config/packages/`.
- Backup, configuration validation and automatic file rollback are mandatory.
- Home Assistant is never restarted automatically.

Keep the existing V4 app installed until V5 has been tested successfully.
