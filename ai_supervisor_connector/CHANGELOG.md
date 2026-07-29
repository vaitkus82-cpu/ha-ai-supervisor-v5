# Changelog

## 5.0.0-alpha5

- Added a structural Home Assistant component catalogue generated locally with PyYAML.
- Catalogues automations, scripts, scenes, templates and helper definitions without sending `.storage` files.
- Added read-only Lovelace dashboard inventory through the Home Assistant WebSocket API.
- Sends only dashboard titles, view paths, card counts and referenced entity IDs to the Windows Engine.
- Added a dedicated process-map button and process-map display in the Home Assistant UI.
- Added component and dashboard counts to snapshot/status information.
- Added the `/api/process-map` bridge to the paired Windows Engine.
- Preserved the disabled-by-default package-only write policy, backup, validation and rollback controls.

## 5.0.0-alpha4

- Added filtered YAML problem detection and confidence categories.
- Added unique issue and occurrence counts.
