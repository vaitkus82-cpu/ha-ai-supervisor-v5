# Changelog

## 5.0.0-alpha11

- Added separate proposal states: blocked, review-only and apply-ready.
- Review-only proposals can be structurally valid and show a real unified diff, but the Apply button is hidden.
- Connector refuses to apply any proposal whose `apply_ready` flag is false.
- Connector verifies that every changed file stays inside the Engine-provided explicit allowlist.
- Proposal UI shows generation mode, edit-operation count and unified diff instead of dumping the full file.
- Preserved backup, exact confirmation, strict YAML validation, configuration check and rollback controls.

## 5.0.0-alpha10

- Added the one-way process graph and suppressed shared-helper reverse fan-out.
