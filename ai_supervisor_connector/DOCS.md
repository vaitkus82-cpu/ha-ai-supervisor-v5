# AI Supervisor V5 Connector 5.0.0-alpha11

## Proceso paieška

1. Nustatomos tikslios pradinės proceso entities.
2. Surandami jas tiesiogiai naudojantys automation/script komponentai.
3. Sekami tik tų komponentų kviečiami skriptai, scenos ir helperių apibrėžimai.
4. Readiness ir diagnostics failai rodomi tik kaip informacinės nuorodos.
5. Dashboardai procesą tik patvirtina ir jo neplečia.

## Kodo pasiūlymai

- Užklausoje privaloma aiškiai įvardyti vieną–tris `packages/*.yaml` failus.
- Pirma sukuriamas trumpas planas, po to – tikslios in-memory redagavimo operacijos.
- Connector gauna pilną galutinį failą ir unified diff, tada atlieka strict YAML patikrą.
- `Pakeitimų netaikyk` sukuria review-only pasiūlymą: diff matomas, bet Apply mygtuko nėra.
- Taikymui reikia naujo, aiškiai apply-ready pasiūlymo, įjungto `allow_package_writes`, tikslios patvirtinimo frazės, backup ir sėkmingos HA konfigūracijos patikros.

Rašymas pagal nutylėjimą išjungtas ir ribojamas `/config/packages/*.yaml`.
