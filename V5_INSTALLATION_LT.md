# AI Supervisor V5 Alpha8 atnaujinimas – žingsnis po žingsnio

Alpha8 atnaujina abi dalis:

- darbo mini PC – **Windows Engine 5.0.0-alpha8**;
- Home Assistant – **Connector 5.0.0-alpha8**.

## Ką taiso Alpha8

Alpha6 teisingai rado tris užuolaidas, bet nerado `packages/50_curtains.yaml` automatikų, skriptų ir helperių, nes dalis entity nuorodų buvo Jinja šablonuose ir pasirinktiniuose laukuose. Alpha8 indeksuoja tikslius entity ID visame YAML tekste ir susieja pagrindinį package failą su visais jame aprašytais komponentais.

## 1. Atnaujinti Windows Engine

1. Atsisiųskite `ai-supervisor-v5-windows-engine-alpha8.zip`.
2. Pasirinkite **Extract All / Išskleisti viską**.
3. Atidarykite išskleistą aplanką.
4. Dukart paspauskite `Install-AI-Supervisor-V5.cmd`.
5. Patvirtinkite administratoriaus teises.
6. Palaukite, kol atsidarys Engine puslapis.
7. Patikrinkite, kad rodoma `Engine 5.0.0-alpha8`, `OpenAI: paruošta`, `Connector: susietas`.

## 2. Įkelti Connector į GitHub

1. Atsisiųskite `ha-ai-supervisor-v5-connector-alpha8.zip`.
2. Išskleiskite ZIP.
3. Atidarykite vidinį aplanką `ha-ai-supervisor-v5`.
4. GitHub atidarykite `vaitkus82-cpu/ha-ai-supervisor-v5`.
5. Pasirinkite **Add file → Upload files**.
6. Įkelkite visą vidinio aplanko turinį.
7. Commit pavadinimas: `Upgrade V5 to alpha8 package and Jinja index`.
8. Patikrinkite `ai_supervisor_connector/config.yaml`: turi būti `version: "5.0.0-alpha8"`.

## 3. Atnaujinti Home Assistant programėlę

1. Atidarykite **Settings → Apps → App store**.
2. Spauskite **⋮ → Check for updates**.
3. Atidarykite **AI Supervisor V5 Connector**.
4. Atnaujinkite `5.0.0-alpha7 → 5.0.0-alpha8`.
5. Galite įjungti **Keep backup of the last version**.
6. Po atnaujinimo spauskite **Restart**, jeigu programėlė pati nepasileido.
7. `allow_package_writes` palikite `false`.

## 4. Pakartoti užuolaidų testą

1. AI Supervisor V5 lange spauskite **Nuskaityti ir perduoti**.
2. Spauskite **Patikrinti HA konfigūraciją**.
3. Užduoties lauke įrašykite `užuolaidų procesas`.
4. Spauskite **Rasti proceso žemėlapį**.

Laukiamas rezultatas:

- pagrindinės cover entities: 3;
- pagrindinis failas: `packages/50_curtains.yaml`;
- susiję failai: `05_system_readiness.yaml`, `50_curtains.yaml`, `90_diagnostics.yaml`;
- automatikos: daugiau nei 0;
- skriptai: daugiau nei 0;
- helperiai: daugiau nei 0;
- „Valentina“ ir `vacuum.*`: nėra;
- dashboardas naudojamas tik kaip patvirtinimas.

## Saugos riba

Rašymas išjungtas pagal nutylėjimą. Šiame teste nespauskite AI pakeitimo taikymo. Net įjungus rašymą, leidžiami tik aiškiai patvirtinti pakeitimai `packages/*.yaml` po backup ir sėkmingos HA konfigūracijos patikros.
