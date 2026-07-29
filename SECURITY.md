# Security

AI Supervisor V4.3 Cloud is an experimental administrative App.

- Ingress is administrator-only.
- Change application is disabled by default.
- Writes are restricted to one configured YAML file under `packages/`.
- Arbitrary paths, path traversal, duplicate YAML keys, repeated helper entity IDs, unsupported package roots, unknown entity IDs, and dangerous service domains are rejected.
- `homeassistant.restart`, `homeassistant.stop`, Supervisor control actions, shell commands, Python scripts, REST commands, and command-line actions are blocked.
- A Home Assistant backup is mandatory before every apply and user rollback.
- The managed file is restored automatically when the configuration check fails.
- Remote engine tokens are stored server-side and never returned to the browser.
- OpenAI/API secrets in logs and proposal text are redacted.

Do not enable change application until the managed package mechanism is configured and a current external backup exists.
