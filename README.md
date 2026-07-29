# AI Supervisor V5 Connector

Home Assistant side of the split AI Supervisor V5 architecture.

Version **5.0.0-alpha6** replaces broad graph expansion with a precise reverse index. The Connector recognises package files and arbitrary Home Assistant include files, including root-list automations and root-mapping scripts. The Windows Engine starts from exact process entities and follows only real YAML dependencies.

The Windows Engine then builds a dependency graph:

```text
exact process entity -> automation/script/helper -> file
                         -> dashboard confirmation only
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
