# Changelog

## 5.0.0-alpha3

- Added Home Assistant WebSocket inventory collection for current states.
- Added compact entity, device and area registry snapshots.
- Excluded device identifiers, connections, serial numbers and credentials from snapshots.
- Normalised successful Home Assistant configuration checks to a clear `valid` result.
- Added inventory completeness and registry counts to status and UI.
- Added problem confidence categories for the Alpha3 Windows Engine.

## 5.0.0-alpha2

- Configuration validation now uses the Supervisor `/core/check` endpoint with a Core REST fallback.
- Snapshot creation continues in file-only mode if the Home Assistant states API fails.
- API errors now identify the exact method and endpoint.
- Updated Supervisor role to `manager`, required for reliable system checks and guarded V5 operations.
- Added snapshot API warnings to status and UI.


## 5.0.0-alpha1

- Added split Home Assistant Connector and Windows Engine architecture.
- Added one-time pairing with a local Windows Engine.
- Added redacted Home Assistant project snapshots.
- Added external process indexing and structured OpenAI proposals.
- Added guarded multi-file YAML transactions under `packages/`.
- Added backup, source-hash validation, configuration check and automatic rollback.
- Automatic Home Assistant restart remains disabled.
