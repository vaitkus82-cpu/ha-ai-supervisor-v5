# AI Supervisor V5 Connector 5.0.0b1

## Foninės užduotys

Šios operacijos vykdomos atskirame Connector procese ir grąžina `job_id`:

- Home Assistant snapshot;
- aktyvios konfigūracijos patikra;
- proceso žemėlapis;
- AI analizė ir pasiūlymas;
- preflight;
- patvirtintas įrašymas.

Sąsaja periodiškai skaito `/api/jobs/<job_id>`. Užbaigtas rezultatas arba klaida išsaugomi `/data/background_jobs.json`, todėl naršyklės ingress ryšio nutrūkimas nebeturi nutraukti pačios operacijos.

## Komponentu paremti pasiūlymai

- Užklausoje privaloma aiškiai įvardyti leidžiamus `packages/*.yaml` failus.
- Planas sukuriamas vieną kartą, o operacijų etapas prireikus pakartojamas tam pačiam planui.
- Kiekviena operacija pririšama prie konkretaus `automation`, `script` arba `scene` komponento.
- Engine valdo YAML kelią, įtrauką, strict YAML patikrą ir unified diff.
- Review-only pasiūlymai negali būti įrašomi.

## Preflight ir įrašymas

- Connector patikrina failų hash, visą pasiūlymą, visus paketų YAML failus ir aktyvią Home Assistant konfigūraciją.
- Sėkminga preflight būsena susiejama su tiksliais šaltinio ir siūlomo turinio fingerprint.
- Pasikeitus šaltinio failui, ankstesnė preflight nebegalioja.
- Prieš įrašymą sukuriama backup kopija; po įrašymo vykdoma galutinė HA patikra; nesėkmės atveju failai grąžinami.
- Automatinis Home Assistant perkrovimas išjungtas.

## Autonominė laboratorija

Connector tik siunčia autentifikuotus incidentus Windows Engine. Savęs tobulinimo kandidatai kuriami mini PC izoliuotoje laboratorijoje ir neturi tiesioginės prieigos prie Home Assistant įrašymo kelio.
