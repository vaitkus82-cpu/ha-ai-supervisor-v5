# AI Supervisor V5 Connector 5.0.0-alpha12

## Proceso paieška

1. Nustatomos tikslios pradinės proceso entities.
2. Surandami jas tiesiogiai naudojantys automation/script komponentai.
3. Sekami tik tų komponentų kviečiami skriptai, scenos ir helperių apibrėžimai.
4. Readiness ir diagnostics failai rodomi tik kaip informacinės nuorodos.
5. Dashboardai procesą tik patvirtina ir jo neplečia.

## Struktūriniai kodo pasiūlymai

- Užklausoje privaloma aiškiai įvardyti vieną–tris `packages/*.yaml` failus.
- Pirma sukuriamas trumpas planas, po to Engine gauna struktūrines operacijas su tiksliu YAML keliu.
- Įtrauką ir galutinį failo tekstą formuoja Engine, ne kalbos modelis.
- Po kiekvienos operacijos atliekama strict YAML patikra.
- Connector dar kartą patikrina galutinį YAML ir dubliuotus raktus prieš rodydamas taikymo galimybę.
- `Pakeitimų netaikyk` sukuria review-only pasiūlymą: diff matomas, bet įrašymo mygtuko nėra.
- Taikymui reikia naujo apply-ready pasiūlymo, įjungto `allow_package_writes`, tikslios patvirtinimo frazės, backup ir sėkmingos HA konfigūracijos patikros.

Rašymas pagal nutylėjimą išjungtas ir ribojamas `/config/packages/*.yaml`.
