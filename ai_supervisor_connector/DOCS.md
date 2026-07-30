# AI Supervisor V5 Connector 5.0.0-alpha14

## Proceso paieška

1. Nustatomos tikslios pradinės proceso entities.
2. Surandami jas tiesiogiai naudojantys automation/script komponentai.
3. Sekami tik tų komponentų kviečiami skriptai, scenos ir helperių apibrėžimai.
4. Readiness ir diagnostics failai rodomi tik kaip informacinės nuorodos.
5. Dashboardai procesą tik patvirtina ir jo neplečia.

## Komponentu paremti kodo pasiūlymai

- Užklausoje privaloma aiškiai įvardyti vieną ar kelis `packages/*.yaml` failus.
- Pirma sukuriamas trumpas planas. Jis naudojamas ir tada, kai operacijų etapą reikia pakartoti.
- Operacijų generavimo etape Engine modeliui perduoda tik vieną planuojamą failą.
- Kiekvienas failo pakeitimas nurodo `component_kind` ir `component_id`.
- Modelio kelias yra santykinis komponentui; tikrą `automation -> id`, `script -> key` arba `scene -> id` inkarą prideda Engine.
- Įtrauką ir galutinį failo tekstą formuoja Engine, ne kalbos modelis.
- Po kiekvienos operacijos atliekama strict YAML patikra.
- Neteisingas, dviprasmis ar pakartotinai absoliutus komponento kelias blokuojamas.
- `Pakeitimų netaikyk` sukuria review-only pasiūlymą: diff matomas, bet įrašymo mygtuko nėra.

## Preflight ir įrašymas

- Apply-ready pasiūlymui Connector pirmiausia patikrina dabartinius failų hash ir visą pasiūlymą.
- Dabartinės ir siūlomos failų kopijos sukuriamos tik `/data/preflight/<proposal_id>/`; aktyvūs HA failai šiame etape nekeičiami.
- Visi `/config/packages/*.yaml` ir `*.yml` failai dar kartą parsinti, siūlomiems failams naudojant paruoštas kopijas.
- Papildomai vykdoma aktyvios Home Assistant konfigūracijos patikra.
- Sėkminga preflight būsena susiejama su pasiūlymo ir failų fingerprint. Pasikeitus šaltinio failui, preflight nebegalioja.
- Tik po sėkmingos preflight patikros, įjungto `allow_package_writes` ir tikslios patvirtinimo frazės leidžiama pradėti įrašymą.
- Prieš įrašymą sukuriama backup kopija. Po įrašymo vykdoma galutinė HA konfigūracijos patikra; nesėkmės atveju failai automatiškai grąžinami.

Rašymas pagal nutylėjimą išjungtas ir ribojamas `/config/packages/*.yaml`.