# Changelog

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
