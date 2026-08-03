# AI Supervisor V5 Beta1 Autonomous Lab

Home Assistant Connector ir Windows Engine sudaro atskirtą AI Supervisor V5 sistemą.

Versija **5.0.0b1** papildo Alpha13.1 saugų struktūrinį YAML redagavimą autonomine savidiagnostikos ir savęs tobulinimo laboratorija.

```text
Home Assistant / Connector klaida
  -> autentifikuotas incidentas Windows Engine
  -> susijusių šaltinio failų atranka
  -> mažiausia AI pataisa izoliuotai kodo kopijai
  -> saugos taisyklių patikra
  -> Python, JavaScript ir regresiniai testai
  -> kandidato ZIP ir ataskaita
  -> pasirinktinai: perkėlimas tik į laboratorijos bazę
  -> atskiras žmogaus patvirtintas produkcinis diegimas
```

## Beta1 papildymai

- Connector ilgas operacijas (`snapshot`, HA patikra, proceso paieška, analizė, preflight ir įrašymas) vykdo foninėmis užduotimis ir sąsajoje periodiškai tikrina rezultatą.
- Tai pašalina priklausomybę nuo vienos ilgai atidarytos Home Assistant ingress HTTP užklausos.
- Connector perduoda Engine informaciją apie foninių užduočių klaidas, atmestas API užklausas ir netikėtus serverio sutrikimus.
- Engine laboratorija renka incidentus, ruošia pataisas ir paleidžia pilną testavimo grandinę.

## Saugos ribos

- Autonominis AI nekeičia veikiančio Engine, Home Assistant ar GitHub saugyklos.
- Kandidatai kuriami tik izoliuotoje `self_lab` srityje mini PC.
- AI leidžiama keisti tik aiškiai apibrėžtus Engine ir Connector šaltinio failus.
- Saugomi autentifikavimo, DPAPI, poravimo, `packages/` ribos, preflight, backup, galutinės HA patikros ir rollback mechanizmai.
- Savarankiškas diegimas, komandų vykdymo įterpimas, kredencialų išgavimas ir saugos testų silpninimas blokuojami.
- Home Assistant failų rašymas pagal nutylėjimą išjungtas.

Ryšiui su Windows Engine naudokite privatų tinklą arba Tailscale. Viešo maršrutizatoriaus portų persiuntimo nereikia.
