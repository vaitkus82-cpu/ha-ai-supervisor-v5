# AI Supervisor V5 Connector 5.0.0-alpha5

The Connector is the guarded Home Assistant half of AI Supervisor V5.

Alpha5:

- reads Home Assistant files and live registries;
- creates a local structural catalogue of automations, scripts, helpers, scenes and templates;
- reads Lovelace dashboard references without exposing `.storage`;
- pairs with the Windows Engine on the trusted local network;
- sends the Engine enough structure to build a full process dependency map;
- displays the process map before AI analysis;
- keeps package writes disabled by default;
- requires backup, explicit confirmation, configuration validation and rollback for any write.
