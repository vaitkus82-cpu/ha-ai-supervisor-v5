# AI Supervisor V5 Connector

Home Assistant dalis, skirta dviejų dalių AI Supervisor V5 architektūrai.

Versija **5.0.0-alpha10** suvienodina Connector ir Windows Engine versijas bei perduoda proceso duomenis vienkrypčiam žemėlapiui:

```text
tikslios proceso entities
  -> tiesiogiai jas naudojantys komponentai
  -> tų komponentų kviečiami skriptai ir helperių apibrėžimai
  -> konkretūs YAML failai
  -> dashboardo patvirtinimas
```

Bendras helperis ar sensorius nebegali įtraukti visų kitų jį naudojančių klimato, CarPlay, roboto ar kitų procesų.

## Saugumas

- `secrets.yaml`, `.storage`, duomenų bazės, žurnalai ir atsarginės kopijos neperduodami.
- Lovelace skaitomas per API; neperduodami raw `.storage` failai.
- MAC adresai, serijos numeriai, prisijungimo duomenys ir unikalūs identifikatoriai pašalinami.
- Rašymas pagal nutylėjimą išjungtas.
- Leidžiami tik aiškiai patvirtinti YAML pakeitimai po `/config/packages/`.
- Privaloma atsarginė kopija, konfigūracijos patikra ir automatinis failų grąžinimas nesėkmės atveju.
- Home Assistant automatiškai neperkraunamas.
