# AI Supervisor V5 Alpha5 atnaujinimas – žingsnis po žingsnio

Šiame etape atnaujinamos abi dalys:

- darbo mini PC: **AI Supervisor V5 Windows Engine 5.0.0-alpha5**;
- Home Assistant Green: **AI Supervisor V5 Connector 5.0.0-alpha5**.

Alpha5 pagrindinė naujovė – autonominis proceso žemėlapis. Sistema prieš kreipdamasi į AI pati susieja fizinius įrenginius, entities, automatikas, skriptus, helperius, dashboardo nuorodas ir failus.

Rašymas į Home Assistant pagal nutylėjimą lieka išjungtas.

---

## 1 dalis. Atnaujinti Windows Engine

1. Atsisiųskite `ai-supervisor-v5-windows-engine-alpha5.zip`.
2. Paspauskite dešiniu pelės mygtuku ir pasirinkite **Extract All / Išskleisti viską**.
3. Atidarykite išskleistą aplanką.
4. Dukart paspauskite:

```text
Install-AI-Supervisor-V5.cmd
```

5. Windows administratoriaus teisių lange pasirinkite **Yes / Taip**.
6. Diegiklis sustabdys ankstesnę Engine versiją, pakeis programos failus ir vėl paleis Engine.
7. Naršyklėje turi atsidaryti:

```text
http://127.0.0.1:8765
```

8. Patikrinkite, kad rodoma:

```text
Engine 5.0.0-alpha5
OpenAI: paruošta
Connector: susietas
```

Esamas OpenAI raktas, poravimo duomenys ir pasiūlymų istorija saugomi `C:\ProgramData\AI Supervisor V5`, todėl atnaujinimas jų neturėtų ištrinti.

---

## 2 dalis. Įkelti Alpha5 Connector į GitHub

1. Atsisiųskite `ha-ai-supervisor-v5-connector-alpha5.zip`.
2. Išskleiskite ZIP.
3. Atidarykite vidinį aplanką:

```text
ha-ai-supervisor-v5
```

4. GitHub atidarykite esamą saugyklą:

```text
https://github.com/vaitkus82-cpu/ha-ai-supervisor-v5
```

5. Pasirinkite **Add file → Upload files**.
6. Įkelkite visą vidinio `ha-ai-supervisor-v5` aplanko turinį. GitHub pagrindiniame lygyje turi likti:

```text
repository.yaml
README.md
ARCHITECTURE_V5.md
ai_supervisor_connector/
tests/
```

7. Commit pavadinimas:

```text
Upgrade V5 to alpha5 autonomous process maps
```

8. Paspauskite **Commit changes**.

---

## 3 dalis. Atnaujinti Home Assistant Connector

1. Home Assistant atidarykite **Settings → Apps → App store**.
2. Viršuje dešinėje pasirinkite **⋮ → Check for updates**.
3. Atidarykite **AI Supervisor V5 Connector**.
4. Atnaujinkite:

```text
5.0.0-alpha4 → 5.0.0-alpha5
```

5. Po atnaujinimo patikrinkite:
   - **Start on boot** – įjungta;
   - **Watchdog** – įjungtas;
   - **Show in sidebar** – įjungta;
   - **Auto update** – išjungta;
   - `allow_package_writes` – `false`.
6. Paspauskite **Restart**.

---

## 4 dalis. Persiųsti naują Home Assistant indeksą

1. Kairiajame meniu atidarykite **AI Supervisor V5**.
2. Paspauskite **Nuskaityti ir perduoti**.
3. Po nuskaitymo patikrinkite, kad rodoma daugiau nei nulis:
   - failų;
   - gyvų entities;
   - entity registro įrašų;
   - įrenginių;
   - struktūrinių komponentų.
4. Dashboardų skaičius taip pat turėtų būti didesnis už nulį. Jeigu Home Assistant negrąžina Lovelace duomenų per API, sistema turi parodyti perspėjimą, bet failų ir procesų nuskaitymas vis tiek veiks.
5. Paspauskite **Patikrinti HA konfigūraciją**. Laukiamas rezultatas:

```text
Home Assistant konfigūracija tinkama.
```

---

## 5 dalis. Patikrinti autonominį proceso žemėlapį

Užduoties lauke įrašykite:

```text
užuolaidų procesas
```

Paspauskite:

```text
Rasti proceso žemėlapį
```

Alpha5 turi parodyti:

- fizinius užuolaidų įrenginius;
- visas jų `cover.*` entities;
- susijusias automatizacijas;
- skriptus;
- helperius;
- dashboardo nuorodas;
- susijusius YAML failus;
- neišspręstas nuorodas;
- ryšių grandinę tarp šių dalių.

Tikėtinos užuolaidų entities:

```text
cover.miegamasis_curtain
cover.svetaine_kaire_curtain
cover.svetaine_terasa_curtain
```

---

## 6 dalis. Pirmoji Alpha5 AI analizė

Į užduoties lauką įklijuokite:

```text
Atlik tik skaitymo režimo analizę.

Surask visą užuolaidų procesą nuo fizinių įrenginių iki dashboardo:
cover entities, automatizacijas, skriptus, helperius, įrenginius, zonas,
dashboardo korteles ir visus susijusius failus.

Sudaryk proceso žemėlapį ir patikrink:
- ar vieną fizinę užuolaidą valdo daugiau nei vienas procesas;
- ar rankinis prioritetas tikrinamas visose vykdymo šakose;
- ar nėra dubliuotų komandų;
- ar naudojamos unavailable arba unknown entities;
- ar saugus elgesys po Home Assistant perkrovimo.

Nieko nekeisk, nekurk failų ir negeneruok diegiamo pakeitimo.
Pateik tik analizę ir konkretų taisymo planą.
```

Paspauskite **Analizuoti ir parengti pasiūlymą**.

Teisingas saugos rezultatas:

- pasiūlyme matomas proceso žemėlapis;
- AI nebeturi teigti, kad užuolaidų dalys nerastos, jeigu jos yra žemėlapyje;
- pakeitimų failų sąrašas lieka tuščias;
- pasiūlymas pažymimas kaip skaitymo režimo arba užblokuotas taikymui;
- `Rašymas: išjungtas` lieka nepakeistas.

---

## Svarbi Alpha5 riba

Alpha5 pagerina autonominį proceso radimą, bet dar nėra leidimas nekontroliuojamai keisti visą Home Assistant projektą. Net įjungus rašymą, dabartinė saugos riba leidžia keisti tik aiškiai patvirtintus YAML failus po `/config/packages/`, po atsarginės kopijos, YAML patikros ir Home Assistant konfigūracijos patikros. Home Assistant automatiškai neperkraunamas.
