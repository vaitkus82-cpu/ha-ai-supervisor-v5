# AI Supervisor V5 Connector 5.0.0-alpha9

## What Alpha8 adds

Alpha8 supplements strict YAML parsing with an exact raw-text catalogue. This captures entity references such as:

```yaml
cover_entity: cover.svetaine_terasa_curtain
source_cover: cover.svetaine_kaire_curtain
value_template: "{{ states('cover.miegamasis_curtain') }}"
position: "{{ state_attr('cover.svetaine_terasa_curtain', 'current_position') }}"
```

Package domains are split into individual automations, scripts, helpers, scenes and template blocks. Parsed and raw records are merged.

## Write boundary

Only `.yaml` or `.yml` files under `/config/packages/` can be changed, with at most three files in one transaction. Every write requires explicit confirmation, source-hash verification, a Home Assistant backup, duplicate-key validation, configuration validation and automatic rollback on failure. Home Assistant is not restarted automatically.
