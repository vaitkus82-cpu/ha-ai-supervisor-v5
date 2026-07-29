# Changelog

## 5.0.0-alpha7

- Added raw-text package section cataloguing alongside parsed YAML cataloguing.
- Exact entity IDs are now collected from quoted Jinja, `states()`, `state_attr()`, custom variables such as `source_cover`, and custom fields such as `cover_entity`.
- Added a conservative fallback when strict YAML parsing fails.
- Parsed and raw component records are merged so automations, scripts and helpers retain complete references.
- Added source and line-range metadata to component records.
- Updated the process-map UI with file roles and exact-match explanations.

## 5.0.0-alpha6

- Added structural recognition for arbitrary include automation and script files.
- Added precise process seeds and dashboard confirmation-only behaviour.

## 5.0.0-alpha5

- Added structural component and Lovelace inventories.
