# AI Supervisor V5 architecture

## Components

- Home Assistant Connector reads a redacted configuration and inventory snapshot.
- Windows Engine builds the local index and calls OpenAI when requested.

## Alpha10 process graph

The graph is directional:

```text
seed entities -> direct execution components -> dependency definitions
```

The graph does not traverse from a shared helper or sensor back to every consumer. Dashboards, readiness files, diagnostics files and same-device context cannot expand the execution graph.

TCP port 8765 is intended only for the trusted local network. No router port forwarding is required.
