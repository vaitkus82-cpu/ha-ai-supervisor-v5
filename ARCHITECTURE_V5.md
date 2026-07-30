# AI Supervisor V5 architecture

## Components

- Home Assistant Connector reads a redacted configuration and inventory snapshot, validates proposals and controls all writes.
- Windows Engine builds the local index, calls OpenAI when requested and produces anchored structural YAML proposals.

## Directional process graph

The graph is directional:

```text
seed entities -> direct execution components -> dependency definitions
```

The graph does not traverse from a shared helper or sensor back to every consumer. Dashboards, readiness files, diagnostics files and same-device context cannot expand the execution graph.

## Alpha13 proposal flow

```text
allowed files
  -> repair plan created once
  -> one file per operation-generation request
  -> component anchor
  -> relative structural operations
  -> strict YAML validation and unified diff
  -> Connector preflight staging
  -> user confirmation
  -> backup, write, final HA check, rollback on failure
```

TCP port 8765 must be reachable only through a trusted private network. A private Tailscale connection is supported; public router port forwarding is not required and should not be used.