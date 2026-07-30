# AI Supervisor V5 Connector

Home Assistant dalis, skirta dviejų dalių AI Supervisor V5 architektūrai.

Versija **5.0.0-alpha14** išsaugo vienkryptį proceso žemėlapį, pririša struktūrines operacijas prie konkretaus YAML komponento ir prieš įrašymą reikalauja atskiros preflight patikros:

```text
aiškiai leisti packages/*.yaml failai
  -> vieną kartą sukurtas pataisymo planas
  -> po vieną failą operacijų generavimo etape
  -> konkretus automation/script/scene komponento inkaras
  -> užklausos identifikatorių ir plano apimties kontrolė
  -> komponentui santykinės struktūrinės operacijos
  -> strict YAML patikra po kiekvienos operacijos
  -> tikras unified diff
  -> izoliuota preflight kopija ir aktyvios HA konfigūracijos patikra
  -> vartotojo patvirtinimas, backup, įrašymas, galutinė HA patikra arba rollback
```

## Saugumas

- `secrets.yaml`, `.storage`, duomenų bazės, žurnalai ir atsarginės kopijos neperduodami.
- Kodo generavimas be aiškaus `packages/*.yaml` leidžiamų failų sąrašo blokuojamas.
- Operacijų etapui perduodamas tik vienas planuojamas failas; planas neperskaičiuojamas pakartojant operacijų generavimą.
- Nuo užduoties nukrypęs planas automatiškai atmetamas ir generuojamas dar kartą pagal aiškius užklausos identifikatorius.
- Po kiekvienos operacijos patvirtinama, kad už pasirinkto komponento ribų failas nepasikeitė.
- Kiekviena operacija pririšama prie konkretaus `automation`, `script` arba `scene` komponento.
- AI negali pats valdyti failo įtraukų; struktūrą ir komponento inkarą valdo Engine.
- Nulinį arba kelis komponentus atitinkantis kelias blokuojamas.
- Review-only pasiūlymai negali būti įrašomi.
- Apply-ready pasiūlymui būtina sėkminga, tam pačiam failų turiniui pririšta preflight patikra.
- Leidžiami tik aiškiai patvirtinti YAML pakeitimai po `/config/packages/`.
- Privaloma atsarginė kopija, galutinė konfigūracijos patikra ir automatinis failų grąžinimas nesėkmės atveju.
- Home Assistant automatiškai neperkraunamas.

Ryšiui su Windows Engine naudokite patikimą privatų tinklą arba Tailscale. Maršrutizatoriaus portų persiuntimas nereikalingas.