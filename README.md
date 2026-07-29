# AI Supervisor V5 Connector

Home Assistant side of the split AI Supervisor V5 architecture.

Version **5.0.0-alpha5** adds an autonomous process-discovery layer. The Connector builds a redacted Home Assistant snapshot, generates a structural catalogue of automations, scripts, helpers, scenes and templates, reads Lovelace dashboard references through the Home Assistant WebSocket API, and transfers the result to the paired Windows Engine.

The Windows Engine then builds a dependency graph:

```text
physical device -> entities -> automations/scripts/helpers -> dashboards -> files
```

## Safety

- `secrets.yaml`, `.storage`, databases, logs and backups are excluded from file snapshots.
- Lovelace is read through the API; raw `.storage` files are not transmitted.
- Device identifiers, MAC addresses, serial numbers and credentials are omitted.
- Writes are disabled by default.
- This alpha can write only explicitly confirmed YAML transactions under `/config/packages/`.
- Backup, configuration validation and automatic file rollback are mandatory.
- Home Assistant is never restarted automatically.

Keep the existing V4 app installed until V5 has been tested successfully in your environment.
