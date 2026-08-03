# AI Supervisor V5 Beta1 Autonomous Lab atnaujinimas

Versija: `5.0.0b1`

## GitHub

1. Išskleiskite `ha-ai-supervisor-v5-connector-beta1-autonomous-lab.zip`.
2. Atidarykite vidinį aplanką `ha-ai-supervisor-v5`.
3. Įkelkite visą jo turinį į esamą GitHub saugyklą, pakeisdami ankstesnius failus.
4. Patikrinkite `ai_supervisor_connector/config.yaml`:

```yaml
version: "5.0.0b1"
```

5. Commit pavadinimas:

```text
Add V5 Beta1 autonomous self-improvement lab
```

## Home Assistant

1. Atidarykite `Settings -> Apps -> App store`.
2. Pasirinkite `Check for updates`.
3. Atnaujinkite Connector į `5.0.0b1` ir paspauskite `Restart`.
4. Pirmajam testui palikite `allow_package_writes: false`.
5. Patikrinkite, kad rodoma `Mini PC: prisijungęs`, `Connector 5.0.0b1`, `Rašymas: išjungtas`.
6. Paspauskite `Nuskaityti ir perduoti` ir `Patikrinti HA konfigūraciją`.

Ilgos operacijos dabar vykdomos foninėmis užduotimis. Mygtuke rodomas praėjęs laikas, o naršyklė kas kelias sekundes pasiima būseną, todėl viena ilga ingress užklausa nebelaikoma atidaryta.
