# Changelog

## 5.0.0-alpha14

- Reissued the Alpha13.1 Connector code under an unambiguous increasing pre-release version.
- Fixes Home Assistant showing the newer repository version while keeping the Update button disabled.
- No functional YAML-generation or write-safety behavior changed from the Alpha13.1 hotfix.

## 5.0.0-alpha14

- Updated the UI and package metadata for the Alpha13.1 Engine hotfix.
- Proposal diagnostics now identify Alpha13.1 plan-scope and anchored-operation retries.
- Root component wording was removed because package edits now require an exact automation, script or scene anchor.
- Existing preflight, backup, final Home Assistant validation and rollback protections are unchanged.

## 5.0.0-alpha13

- Added mandatory proposal preflight before an apply-ready change can be written.
- Preflight creates isolated current and proposed file copies under the Connector data directory without modifying `/config`.
- All package YAML files are parsed again with the proposed files used as overrides.
- The proposal fingerprint binds a successful preflight to the exact current and proposed file hashes.
- Any source-file change invalidates the previous preflight and blocks apply.
- The active Home Assistant configuration check is run during preflight; final post-write HA validation and rollback remain mandatory.
- The UI shows component anchors, operation retry diagnostics and preflight status.
- The apply confirmation and write button remain hidden until preflight succeeds.

## 5.0.0-alpha12

- Added support for Engine structural-YAML proposal mode.
- Blocked proposals are shown as blocked immediately instead of displaying a green success message first.
- Proposal risk is normalised to the higher of Engine risk and Connector-computed risk.
- The UI displays structural operation counts and the Engine-generated unified diff.
- Preserved explicit allowlists, review-only states, strict YAML validation, backup, configuration check and rollback.

## 5.0.0-alpha11

- Added separate proposal states: blocked, review-only and apply-ready.
- Added explicit allowlist verification and unified-diff display.

## 5.0.0-alpha10

- Added the one-way process graph and suppressed shared-helper reverse fan-out.