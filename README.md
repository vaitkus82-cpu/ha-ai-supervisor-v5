# AI Supervisor V5 Connector

Home Assistant dalis, skirta dviejų dalių AI Supervisor V5 architektūrai.

Versija **5.0.0-alpha11** išsaugo tikslų vienkryptį proceso žemėlapį ir prideda saugų dviejų etapų kodo pasiūlymų generatorių:

```text
aiškiai leisti packages/*.yaml failai
  -> trumpas pataisymo planas
  -> tikslios exact-text operacijos
  -> in-memory galutinis failas
  -> unified diff
  -> strict YAML ir saugos patikros
  -> tik tada peržiūra arba atskirai leidžiamas taikymas
```

## Saugumas

- `secrets.yaml`, `.storage`, duomenų bazės, žurnalai ir atsarginės kopijos neperduodami.
- Lovelace skaitomas per API; neperduodami raw `.storage` failai.
- MAC adresai, serijos numeriai, prisijungimo duomenys ir unikalūs identifikatoriai pašalinami.
- Kodo generavimas be aiškaus `packages/*.yaml` allowlist blokuojamas.
- Review-only pasiūlymai negali būti įrašomi.
- Leidžiami tik aiškiai patvirtinti YAML pakeitimai po `/config/packages/`.
- Privaloma atsarginė kopija, konfigūracijos patikra ir automatinis failų grąžinimas nesėkmės atveju.
- Home Assistant automatiškai neperkraunamas.
