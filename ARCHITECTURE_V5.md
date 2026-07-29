# AI Supervisor V5 split architecture

## Trust boundary

The Windows Engine analyses and generates proposals, but it does not receive a Home Assistant administrator token and cannot write directly to `/config`. The Home Assistant Connector is the only component that can write files.

## Network

Alpha7 is intended for a trusted local network. TCP port 8765 is opened only for the Windows Private firewall profile and local subnet. No router port forwarding is required or supported.

## Alpha7 discovery pipeline

1. Select exact physical process entities from the entity and device registries.
2. Build an exact raw-text entity-to-file index for every allowed YAML file.
3. Parse package domains structurally when possible.
4. Supplement parsed components with raw Jinja/custom-field references.
5. Identify the primary package from exact seed matches and filename/process terms.
6. Add all automations, scripts and helpers defined in the primary package.
7. Follow only real component dependencies.
8. Classify other matching files as readiness, diagnostics or supporting.
9. Use dashboards only as confirmation; dashboards never expand the graph.

## Data minimisation

The Connector excludes secrets, `.storage`, databases, logs, backups, media and hidden directories. Device identifiers, network connections, serial numbers and credentials are not included.

## Apply transaction

1. Verify proposal and confirmation.
2. Restrict paths to `packages/*.yaml` or `packages/*.yml`.
3. Verify source SHA-256 hashes.
4. Parse YAML and reject duplicate keys.
5. Create a Home Assistant backup.
6. Write files atomically.
7. Run the Home Assistant configuration check.
8. Restore originals automatically if validation fails.
9. Never restart Home Assistant automatically.
