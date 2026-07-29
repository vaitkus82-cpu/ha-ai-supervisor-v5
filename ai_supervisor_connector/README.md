# AI Supervisor V5 Connector

Home Assistant side of the split AI Supervisor V5 architecture.

The Connector:

- builds a redacted Home Assistant project snapshot;
- reads current states and compact entity, device and area registries through the official Home Assistant WebSocket proxy;
- excludes `secrets.yaml`, `.storage`, databases, logs and backups;
- excludes device identifiers, MAC addresses, serial numbers and credentials from registry snapshots;
- pairs with a Windows Engine on the same trusted LAN;
- sends the snapshot to the Engine for indexing and AI analysis;
- displays structured proposals;
- can apply an explicitly confirmed YAML transaction under `packages/` only;
- requires a Home Assistant backup and successful configuration check;
- rolls files back automatically when the check fails;
- never restarts Home Assistant automatically.

This is an experimental alpha release. Keep the existing V4 app installed until V5 has been tested successfully.
