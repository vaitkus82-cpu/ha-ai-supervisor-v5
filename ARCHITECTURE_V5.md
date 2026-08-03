# AI Supervisor V5 architecture

## Components

- **Home Assistant Connector** reads a redacted configuration and inventory snapshot, validates proposals and controls all Home Assistant writes.
- **Windows Engine** builds the local index, calls OpenAI and produces anchored structural YAML proposals.
- **Autonomous Self Lab** works only on an isolated source baseline, diagnoses incidents, creates patches, runs tests and produces internal candidates.

## Proposal flow

```text
allowed packages/*.yaml files
  -> repair plan created once
  -> one file per operation-generation request
  -> exact automation/script/scene anchor
  -> relative structural operations
  -> strict YAML validation and unified diff
  -> asynchronous Connector preflight job
  -> user confirmation
  -> backup, write, final HA check, rollback on failure
```

## Autonomous improvement flow

```text
Engine logs + proposal failures + Connector incidents
  -> deduplicated incident queue
  -> maximum two relevant source files
  -> exact-text patch in a copied laboratory baseline
  -> protected-fragment and forbidden-token checks
  -> Python compile + Engine tests + Connector tests + generated regression tests + JS syntax
  -> blocked or passed candidate
  -> optional promotion to laboratory baseline only
```

The Autonomous Self Lab has no code path that writes to the running installation or Home Assistant. Production deployment remains a separate explicit action.

TCP port 8765 must be reachable only through a trusted private network. Tailscale is supported; public router port forwarding should not be used.
