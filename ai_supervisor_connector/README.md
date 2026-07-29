# AI Supervisor V5 Connector 5.0.0-alpha6

The Connector is the guarded Home Assistant half of AI Supervisor V5.

Alpha6:

- reads Home Assistant files and live registries;
- recognises automations and scripts in arbitrary `!include` files;
- creates an exact entity-to-component reverse index;
- reads Lovelace dashboard references without exposing `.storage`;
- treats dashboards as confirmation only, never as a source for new devices;
- separates primary process entities, dependencies and same-device context;
- keeps package writes disabled by default;
- requires backup, explicit confirmation, configuration validation and rollback for any write.
