# AI Supervisor V5.0 Alpha1 diegimas

Šis leidimas turi dvi atskiras dalis:

1. **AI Supervisor V5 Connector** – diegiamas į Home Assistant Green.
2. **AI Supervisor V5 Windows Engine** – diegiamas į darbo mini PC.

Abi dalys šiuo metu turi būti tame pačiame patikimame vietiniame tinkle.

## Ką jau moka Alpha1

- automatiškai nuskaityti Home Assistant YAML, Python, JavaScript ir tekstinius konfigūracijos failus;
- neperduoti `secrets.yaml`, `.storage`, duomenų bazės, logų ir atsarginių kopijų;
- susieti entities su jas naudojančiais failais;
- sudaryti bazinį procesų žemėlapį;
- aptikti `unavailable`, `unknown`, neegzistuojančias entities, pasikartojančius YAML `id` ir galimą kelių failų valdymą tai pačiai fizinei entity;
- darbo PC naudoti OpenAI ir parengti struktūrinį pasiūlymą;
- sugeneruoti iki trijų pilnų YAML failų pakeitimų;
- po aiškaus patvirtinimo įrašyti tik failus po `/config/packages/`;
- prieš įrašymą sukurti Home Assistant atsarginę kopiją;
- patikrinti pradinio failo SHA-256, YAML sintaksę ir pasikartojančius raktus;
- po įrašymo paleisti Home Assistant konfigūracijos patikrą;
- nepavykus patikrai automatiškai atkurti visus keistus failus;
- niekada automatiškai neperkrauti Home Assistant.

## Svarbi Alpha1 riba

Tai pirmas realiai veikiantis dviejų dalių leidimas. Jis dar nerašo į `automations.yaml`, `scripts.yaml`, `configuration.yaml` ar `.storage`. Rašymo sritis sąmoningai apribota iki `packages/*.yaml` ir pagal nutylėjimą išjungta.

---

# A dalis – darbo mini PC

## 1 žingsnis. Išskleisti Windows Engine ZIP

1. Atsisiųskite `ai-supervisor-v5-windows-engine-alpha1.zip`.
2. Paspauskite dešiniu pelės mygtuku.
3. Pasirinkite **Extract All / Išskleisti viską**.
4. Atidarykite išskleistą aplanką.

Svarbu: nepaleiskite diegimo tiesiai iš neatidaryto ZIP lango.

## 2 žingsnis. Paleisti diegimą

Dukart paspauskite:

```text
Install-AI-Supervisor-V5.cmd
```

Windows paprašius administratoriaus teisių pasirinkite **Yes / Taip**.

Diegiklis automatiškai:

- suras Python;
- jeigu Python nėra, per `winget` tyliai įdiegs Python 3.12;
- nukopijuos programą į `C:\Program Files\AI Supervisor V5`;
- sukurs duomenų aplanką `C:\ProgramData\AI Supervisor V5`;
- sukurs automatiškai kartu su Windows paleidžiamą užduotį;
- atidarys TCP 8765 tik Windows privataus tinklo profilyje ir tik vietiniam potinkliui;
- sukurs darbalaukio nuorodą **AI Supervisor V5**;
- paleis Engine ir atidarys jo puslapį.

## 3 žingsnis. Patikrinti Engine puslapį

Naršyklėje turi atsidaryti:

```text
http://127.0.0.1:8765
```

Lange turi būti rodoma:

- Engine versija `5.0.0-alpha1`;
- mini PC vietinis IP adresas;
- šešių skaitmenų poravimo kodas;
- OpenAI būsena.

## 4 žingsnis. Įvesti OpenAI API raktą

1. Lauke **Modelis** palikite:

```text
gpt-5-mini
```

2. Lauke **OpenAI API raktas** įklijuokite savo API raktą.
3. Paspauskite **Išsaugoti**.
4. OpenAI būsena turi pasikeisti į **paruošta**.

Raktas darbo PC saugomas užšifruotas naudojant Windows DPAPI. Į Home Assistant jis neperduodamas.

## 5 žingsnis. Užsirašyti ryšio duomenis

Engine lange matysite, pavyzdžiui:

```text
Engine adresas: http://192.168.1.50:8765
Poravimo kodas: 123456
```

Šių duomenų reikės Home Assistant pusėje.

Maršrutizatoriuje 8765 prievado neatidarykite.

---

# B dalis – Home Assistant Connector

## 6 žingsnis. Įkelti V5 Connector į GitHub

Atsisiųskite ir išskleiskite:

```text
ha-ai-supervisor-v5.0-alpha1.zip
```

Pakete yra esamas V4.3 ir naujas aplankas:

```text
ai_supervisor_connector
```

GitHub saugykloje `vaitkus82-cpu/ha-ai-supervisor` įkelkite:

- visą `ai_supervisor_connector` aplanką;
- atnaujintą `README.md`;
- `ARCHITECTURE_V5.md`;
- atnaujintus `tests` failus.

Esamo `ai_supervisor` aplanko neištrinkite. V4.3 kol kas paliekamas kaip atsarginis variantas.

Rekomenduojamas commit pavadinimas:

```text
Add AI Supervisor V5 split alpha1
```

## 7 žingsnis. Atnaujinti Home Assistant programėlių sąrašą

Home Assistant atidarykite:

```text
Settings → Apps → App store
```

Viršuje dešinėje paspauskite meniu ir pasirinkite saugyklų arba atnaujinimo veiksmą. Esama GitHub saugykla jau turi būti pridėta.

Po atnaujinimo turi atsirasti atskira programėlė:

```text
AI Supervisor V5 Connector
```

## 8 žingsnis. Įdiegti Connector

1. Atidarykite **AI Supervisor V5 Connector**.
2. Paspauskite **Install**.
3. Įjunkite **Start on boot**.
4. Įjunkite **Watchdog**.
5. Paspauskite **Start**.
6. Paspauskite **Open Web UI**.

Rašymo leidimo dar neįjunkite.

---

# C dalis – abiejų dalių susiejimas

## 9 žingsnis. Suporuoti

Connector lange įveskite:

```text
Engine adresas: http://DARBO_PC_IP:8765
Poravimo kodas: 6 skaitmenys iš darbo PC
```

Paspauskite **Susieti**.

Teisinga būsena:

```text
Mini PC: prisijungęs
Connector: susietas
```

Jeigu ryšys neveikia:

1. patikrinkite, ar abiejų įrenginių IP prasideda tuo pačiu vietinio tinklo prefiksu;
2. Windows tinklo profilis turi būti **Private**;
3. darbo PC naršyklėje turi veikti `http://127.0.0.1:8765`;
4. Home Assistant laukelyje naudokite darbo PC vietinį IP, ne `127.0.0.1`;
5. maršrutizatoriaus prievadų atidaryti nereikia.

---

# D dalis – pirmas saugus bandymas

## 10 žingsnis. Nuskaityti Home Assistant

Connector lange paspauskite:

```text
Nuskaityti ir perduoti
```

Po nuskaitymo bus parodyta:

- failų skaičius;
- entities skaičius;
- aptiktų procesų skaičius;
- pradinių problemų skaičius.

Pirmas nuskaitymas gali užtrukti kelias minutes.

## 11 žingsnis. Pirmoji analizės užduotis

Į užduoties lauką įrašykite:

```text
Surask visą užuolaidų procesą. Nustatyk, kurios automatikos, skriptai, helperiai ir fizinės cover entities jame dalyvauja. Aptik dubliuotą valdymą, neteisingus prioritetus, unavailable būsenų neapdorojimą ir galimas problemas po Home Assistant perkrovimo. Paruošk sprendimo planą ir saugų YAML pasiūlymą, bet nieko automatiškai neįdiek.
```

Paspauskite:

```text
Analizuoti ir parengti pasiūlymą
```

Patikrinkite:

- ar AI rado realius failus;
- ar naudoja tik egzistuojančias entities;
- ar nekuria naujų pavadinimų be pagrindo;
- ar rodo rizikos lygį;
- ar visi keičiami failai yra po `packages/`;
- ar pateiktas pilnas failo turinys, o ne tik atskiros eilutės.

Pirmojo pasiūlymo dar netaikykite.

---

# E dalis – pirmas rašymo testas

Rašymą įjunkite tik po to, kai poravimas, nuskaitymas ir analizė veikia stabiliai.

## 12 žingsnis. Įjungti ribotą rašymą

Home Assistant atidarykite:

```text
Settings → Apps → AI Supervisor V5 Connector → Configuration
```

Nustatykite:

```yaml
allow_package_writes: true
```

Išsaugokite ir perkraukite tik Connector programėlę.

## 13 žingsnis. Sukurti mažos rizikos testą

Connector užduoties lauke įrašykite:

```text
Sukurk naują failą packages/ai_supervisor_v5_test.yaml. Jame sukurk tik vieną input_boolean helperį input_boolean.ai_supervisor_v5_test pavadinimu „AI Supervisor V5 testas“ ir ikona mdi:robot-check. Nekurk automatizacijų, skriptų ar fizinių įrenginių valdymo.
```

AI turi pasiūlyti vieną failą:

```text
packages/ai_supervisor_v5_test.yaml
```

Prieš taikymą patikrinkite YAML.

## 14 žingsnis. Patvirtinti įrašymą

Pasiūlymo kortelėje bus parodyta tiksli frazė, pavyzdžiui:

```text
PATVIRTINU A1B2C3D4
```

Įrašykite ją tiksliai ir paspauskite **Patvirtinti ir įrašyti**.

Connector tada:

1. patikrins failų hash;
2. sukurs Home Assistant backup;
3. įrašys failą;
4. paleis HA konfigūracijos patikrą;
5. nepavykus automatiškai atkurs failą;
6. sėkmės atveju neperkraus Home Assistant.

Kad naujas `input_boolean` būtų įkeltas, Home Assistant **Developer tools → Actions** paleiskite:

```text
input_boolean.reload
```

---

# Atnaujinimas

## Windows Engine

Naują ZIP išskleiskite ir dar kartą paleiskite:

```text
Install-AI-Supervisor-V5.cmd
```

Programa bus atnaujinta, o `C:\ProgramData\AI Supervisor V5` nustatymai, susiejimas ir istorija liks.

## Home Assistant Connector

Atnaujinimas vyks per Home Assistant Apps, kai GitHub aplanke bus padidinta Connector versija.

---

# Šalinimas

Windows kompiuteryje paleiskite:

```text
Uninstall-AI-Supervisor-V5.cmd
```

Programa ir Windows užduotis bus pašalintos. Nustatymai ir istorija sąmoningai paliekami:

```text
C:\ProgramData\AI Supervisor V5
```

Home Assistant Connector galima pašalinti per **Settings → Apps**. Jo pašalinimas nekeičia Home Assistant YAML failų, kurie jau buvo sėkmingai įrašyti ir patvirtinti.

---

# Problemų diagnostika

## Engine neatsidaro

Patikrinkite:

```text
C:\ProgramData\AI Supervisor V5\logs\engine.log
```

Taip pat Windows **Task Scheduler** turi būti užduotis:

```text
AI Supervisor V5 Engine
```

## OpenAI klaida 401

API raktas netinkamas, panaikintas arba priklauso projektui be aktyvaus API atsiskaitymo.

## Backup freeze klaida

Joks failas nebus pakeistas. Palaukite, kol Home Assistant baigs kitą backup ar sistemos operaciją, ir bandykite dar kartą.

## Pasiūlymas užblokuotas

Dažniausios priežastys:

- AI siūlo keisti failą ne po `packages/`;
- nuo analizės failas jau pasikeitė;
- YAML turi pasikartojančius raktus;
- AI nepateikė pilno YAML;
- siūloma keisti daugiau nei tris failus;
- rašymas App Configuration lange neįjungtas.
