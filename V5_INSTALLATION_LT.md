# AI Supervisor V5 Alpha13 atnaujinimas

## GitHub

1. Išskleiskite `ha-ai-supervisor-v5-connector-alpha13.zip`.
2. Įkelkite vidinio `ha-ai-supervisor-v5` aplanko turinį į esamą GitHub saugyklą.
3. Patikrinkite `ai_supervisor_connector/config.yaml`: `version: "5.0.0-alpha13"`.
4. Commit pavadinimas: `Upgrade V5 to alpha13 anchored edits and preflight`.

## Home Assistant

1. Atidarykite `Settings -> Apps -> App store`.
2. Paleiskite `Check for updates`.
3. Atnaujinkite Connector į Alpha13 ir paspauskite `Restart`.
4. Pirmam testui palikite `allow_package_writes: false`.
5. Patikrinkite, kad rodoma `Mini PC: prisijungęs`, `Connector 5.0.0-alpha13`, `Rašymas: išjungtas`.
6. Paspauskite `Nuskaityti ir perduoti`.
7. Sugeneruokite review-only pasiūlymą ir patikrinkite komponento inkarą, operacijų skaičių bei diff.
8. Tik atskiram apply-ready pasiūlymui įjunkite rašymą. Mygtukas `Įrašyti pakeitimus` atsiranda tik po sėkmingos `Patikrinti prieš įrašymą` patikros.

Pirmam Alpha13 bandymui rinkitės mažos rizikos diagnostinį pakeitimą. Užuolaidų ar klimato valdymo pakeitimų dar neįrašykite.