# Installation

1. Install **AI Supervisor V5 Connector** from the Home Assistant Apps repository.
2. Start the App and open its Web UI.
3. Install the Windows Engine on the mini PC.
4. Open `http://localhost:8765` on the mini PC.
5. Enter an OpenAI API key and copy the six-digit pairing code.
6. In the Connector, enter the displayed LAN URL and pairing code.
7. Select **Pair**.
8. Select **Scan and transfer**.

## Safe write mode

The option `allow_package_writes` is disabled by default. Enable it only after read-only scanning and proposal generation work correctly.

Alpha3 writes only `.yaml` or `.yml` files under `/config/packages/`. A maximum of three files can be included in one transaction. Every transaction requires:

- exact typed confirmation;
- a Home Assistant partial backup;
- unchanged source file hashes;
- valid YAML without duplicate mapping keys;
- a successful Home Assistant configuration check.

Home Assistant is not restarted automatically.


## Alpha3

After pairing, use **Nuskaityti ir perduoti**. A complete snapshot should show live entity states plus entity, device and area registry counts. Missing-entity findings are generated only when the entity registry was retrieved successfully.
