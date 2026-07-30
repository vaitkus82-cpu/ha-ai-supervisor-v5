# AI Supervisor V5 Alpha13.1 atnaujinimas

## GitHub

1. Išskleiskite `ha-ai-supervisor-v5-connector-alpha13.1.zip`.
2. Įkelkite vidinio `ha-ai-supervisor-v5` aplanko turinį į esamą GitHub saugyklą.
3. Patikrinkite `ai_supervisor_connector/config.yaml`: `version: "5.0.0-alpha13.1"`.
4. Commit pavadinimas: `Hotfix V5 alpha13.1 anchored YAML isolation`.

## Home Assistant

1. Atidarykite `Settings -> Apps -> App store`.
2. Paleiskite `Check for updates`.
3. Atnaujinkite Connector į Alpha13.1 ir paspauskite `Restart`.
4. Pirmam testui palikite `allow_package_writes: false`.
5. Patikrinkite, kad rodoma `Mini PC: prisijungęs`, `Connector 5.0.0-alpha13.1`, `Rašymas: išjungtas`.
6. Paspauskite `Nuskaityti ir perduoti`.
7. Sugeneruokite review-only pasiūlymą ir patikrinkite komponento inkarą, operacijų skaičių bei diff.
8. Tik atskiram apply-ready pasiūlymui įjunkite rašymą. Mygtukas `Įrašyti pakeitimus` atsiranda tik po sėkmingos `Patikrinti prieš įrašymą` patikros.

Pirmam Alpha13.1 bandymui rinkitės mažos rizikos diagnostinį pakeitimą. Užuolaidų ar klimato valdymo pakeitimų dar neįrašykite.