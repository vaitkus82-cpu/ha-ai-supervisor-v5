# Changelog

## 5.0.0-alpha8

- Snapshot collection now prioritises root Home Assistant YAML and `packages/` before optional source code and documentation.
- Reaching the byte budget no longer prevents later critical YAML files from being considered.
- Adds snapshot-scope diagnostics: included YAML, included package YAML, omitted files and byte budget.
- The dashboard shows package YAML coverage and whether the snapshot was limited.
- Preserves all privacy exclusions and disabled-by-default writes.

## 5.0.0-alpha7

- Added raw-text package section cataloguing alongside parsed YAML cataloguing.
- Exact entity IDs are collected from Jinja, custom variables and custom fields.
- Added a conservative fallback when strict YAML parsing fails.

## 5.0.0-alpha6

- Added structural recognition for arbitrary include automation and script files.
- Added precise process seeds and dashboard confirmation-only behaviour.

## 5.0.0-alpha5

- Added structural component and Lovelace inventories.
