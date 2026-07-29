# AI Supervisor V5 split architecture

## Trust boundary

The Windows Engine may analyse and generate proposals, but it does not receive a Home Assistant administrator token and cannot write directly to `/config`.

The Home Assistant Connector is the only component that can write files. It independently validates allowed paths, YAML structure, source hashes and risk boundaries before a proposal can be applied.

## Network

Alpha4 is intended for a trusted local network. The Windows installer opens TCP port 8765 only for the Windows **Private** firewall profile and `LocalSubnet`. No router port forwarding is required or supported.

## Pairing

The Engine displays a six-digit code valid for 24 hours. Successful pairing returns a randomly generated bearer token. The Engine stores only its SHA-256 hash. The Connector stores the token in its private app data.

## Data minimisation

The Connector excludes:

- `secrets.yaml`;
- `.storage`;
- Home Assistant databases and logs;
- backups, media and hidden directories.

Known secret patterns and `!secret` references are redacted before transfer.

## Apply transaction

1. Verify the proposal exists and has not already been applied.
2. Require exact typed confirmation.
3. Restrict paths to `packages/*.yaml` or `packages/*.yml`.
4. Verify source SHA-256 hashes.
5. Parse YAML and reject duplicate keys.
6. Create a Home Assistant partial backup.
7. Write all proposed files atomically.
8. Run the Home Assistant configuration check.
9. Restore all original files automatically if the check fails.
10. Never restart Home Assistant automatically.


## Alpha4 inventory

The Connector uses the Home Assistant WebSocket proxy to collect current states and compact entity, device and area registry records. Hardware identifiers, network connections, serial numbers and credentials are not included. The Engine classifies findings as confirmed, likely conflicts or unverified.
