# Changelog

## 5.0.0b1 - Autonomous Lab

- Added persisted background jobs for snapshot sync, Home Assistant configuration check, process map, AI analysis, preflight and apply.
- The UI now starts long-running work and polls job status instead of keeping one long ingress HTTP request open.
- Added authenticated best-effort incident reporting to the Windows Engine Autonomous Self Lab.
- Background job failures, rejected requests, unhandled Connector errors and browser disconnects can be added to the laboratory incident queue.
- Added Connector status for the autonomous laboratory.
- Preserved package-only writes, mandatory preflight, backup, final Home Assistant validation, rollback and disabled automatic restart.

## 5.0.0-alpha13.1

- Updated diagnostics for anchored-operation retries.
- Package edits require an exact automation, script or scene anchor.
- Existing preflight, backup, final Home Assistant validation and rollback protections remain unchanged.

## 5.0.0-alpha13

- Added mandatory proposal preflight before an apply-ready change can be written.
- Preflight stages current and proposed files without modifying `/config`.
- Any source-file change invalidates the previous preflight and blocks apply.
