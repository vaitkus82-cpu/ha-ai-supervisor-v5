# Changelog

## 5.0.0-alpha12

- Added support for Engine structural-YAML proposal mode.
- Blocked proposals are now shown as blocked immediately instead of displaying a green success message first.
- Proposal risk is normalised to the higher of Engine risk and Connector-computed risk.
- The UI displays structural operation counts and the Engine-generated unified diff.
- Preserved explicit allowlists, review-only states, strict YAML validation, backup, configuration check and rollback.

## 5.0.0-alpha11

- Added separate proposal states: blocked, review-only and apply-ready.
- Added explicit allowlist verification and unified-diff display.

## 5.0.0-alpha10

- Added the one-way process graph and suppressed shared-helper reverse fan-out.
