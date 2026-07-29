# AI Supervisor V5 Connector

Home Assistant dalis, skirta dviejų dalių AI Supervisor V5 architektūrai.

Versija **5.0.0-alpha12** išsaugo tikslų vienkryptį proceso žemėlapį ir naudoja struktūrinį YAML pataisymų generatorių:

```text
aiškiai leisti packages/*.yaml failai
  -> trumpas pataisymo planas
  -> esamo YAML medžio keliai
  -> struktūrinės operacijos esamuose mazguose
  -> strict YAML patikra po kiekvienos operacijos
  -> tikras unified diff
  -> peržiūra arba atskirai leidžiamas taikymas
```

## Saugumas

- `secrets.yaml`, `.storage`, duomenų bazės, žurnalai ir atsarginės kopijos neperduodami.
- Kodo generavimas be aiškaus `packages/*.yaml` leidžiamų failų sąrašo blokuojamas.
- AI negali pats nustatyti įtraukų ar pridėti antro viršutinio `automation:` rakto: struktūrą valdo Engine.
- Po kiekvienos operacijos visas YAML failas iš naujo parsintas.
- Nulinį arba kelis komponentus atitinkantis struktūrinis kelias blokuojamas.
- Review-only pasiūlymai negali būti įrašomi.
- Leidžiami tik aiškiai patvirtinti YAML pakeitimai po `/config/packages/`.
- Privaloma atsarginė kopija, konfigūracijos patikra ir automatinis failų grąžinimas nesėkmės atveju.
- Home Assistant automatiškai neperkraunamas.
