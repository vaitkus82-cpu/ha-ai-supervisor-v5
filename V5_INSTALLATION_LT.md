# AI Supervisor V5 Alpha6 atnaujinimas – žingsnis po žingsnio

Atnaujinamos abi sistemos dalys:

- darbo mini PC – **AI Supervisor V5 Windows Engine 5.0.0-alpha6**;
- Home Assistant Green – **AI Supervisor V5 Connector 5.0.0-alpha6**.

## Ką taiso Alpha6

Alpha5 proceso žemėlapį per daug išplėsdavo per dashboardą, todėl į užuolaidų procesą pateko nesusijęs robotas „Valentina“. Be to, nebuvo rasti į atskirus `!include` failus iškelti automatikų ir skriptų blokai.

Alpha6:

- užuolaidų paiešką pradeda tik nuo realiai pavadinimą atitinkančių `cover.*` entities;
- to paties įrenginio `select.*` ir kitos entities rodomos tik kaip kontekstas, bet neplečia proceso;
- dashboardus naudoja tik kaip jau rasto proceso patvirtinimą;
- dashboardas negali pridėti naujo fizinio įrenginio;
- atpažįsta automatikas, esančias savavališkai pavadintuose šakniniuose YAML sąrašuose;
- atpažįsta skriptus, esančius savavališkai pavadintuose šakniniuose YAML žemėlapiuose;
- pagal tikslias entity nuorodas sudaro grandinę `entity → automatika → skriptas → helperis → failas`;
- prie kiekvieno komponento parodo, kodėl jis įtrauktas;
- palieka rašymą į Home Assistant išjungtą.

---

## 1 dalis. Atnaujinti Windows Engine

1. Atsisiųskite `ai-supervisor-v5-windows-engine-alpha6.zip`.
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
Engine 5.0.0-alpha6
OpenAI: paruošta
Connector: susietas
```

OpenAI raktas, poravimas ir pasiūlymų istorija saugomi `C:\ProgramData\AI Supervisor V5`, todėl atnaujinimas jų neturėtų ištrinti.

---

## 2 dalis. Įkelti Alpha6 Connector į GitHub

1. Atsisiųskite `ha-ai-supervisor-v5-connector-alpha6.zip`.
2. Išskleiskite ZIP.
3. Atidarykite vidinį aplanką:

```text
ha-ai-supervisor-v5
```

4. GitHub atidarykite:

```text
https://github.com/vaitkus82-cpu/ha-ai-supervisor-v5
```

5. Pasirinkite **Add file → Upload files**.
6. Įkelkite visą vidinio `ha-ai-supervisor-v5` aplanko turinį.
7. GitHub pagrindiniame lygyje turi likti:

```text
repository.yaml
README.md
ARCHITECTURE_V5.md
ai_supervisor_connector/
tests/
```

8. Commit pavadinimas:

```text
Upgrade V5 to alpha6 precise reverse index
```

9. Paspauskite **Commit changes**.

---

## 3 dalis. Atnaujinti Home Assistant Connector

1. Home Assistant atidarykite **Settings → Apps → App store**.
2. Viršuje dešinėje pasirinkite **⋮ → Check for updates**.
3. Atidarykite **AI Supervisor V5 Connector**.
4. Atnaujinkite:

```text
5.0.0-alpha5 → 5.0.0-alpha6
```

5. Po atnaujinimo patikrinkite:
   - **Start on boot** – įjungta;
   - **Watchdog** – įjungtas;
   - **Show in sidebar** – įjungta;
   - **Auto update** – išjungta;
   - `allow_package_writes` – `false`.
6. Paspauskite **Restart**.

---

## 4 dalis. Persiųsti naują indeksą

1. Kairiajame meniu atidarykite **AI Supervisor V5**.
2. Paspauskite **Nuskaityti ir perduoti**.
3. Patikrinkite, kad daugiau nei nulis rodoma prie:
   - failų;
   - gyvų entities;
   - entity registro;
   - įrenginių;
   - komponentų;
   - dashboardų.
4. Paspauskite **Patikrinti HA konfigūraciją**.
5. Laukiamas rezultatas:

```text
Home Assistant konfigūracija tinkama.
```

---

## 5 dalis. Patikrinti užuolaidų proceso žemėlapį

1. Užduoties lauke įrašykite:

```text
užuolaidų procesas
```

2. Paspauskite **Rasti proceso žemėlapį**.
3. Teisingame rezultate turi būti:

```text
cover.miegamasis_curtain
cover.svetaine_kaire_curtain
cover.svetaine_terasa_curtain
```

4. Turi būti daugiau nei nulis prie:
   - automatikų;
   - skriptų;
   - helperių;
   - susijusių failų.
5. „Valentina“, `vacuum.*` ir jos 100 entities neturi patekti į žemėlapį vien dėl to, kad yra tame pačiame dashboarde.
6. Dashboardo skiltyje turi būti parašyta, kad jis tik patvirtina procesą ir jo neplečia.

Kol šis testas nepatvirtintas, nespauskite **Analizuoti ir parengti pasiūlymą**.

---

## 6 dalis. Pirmoji Alpha6 skaitymo analizė

Kai proceso žemėlapis teisingas, įrašykite:

```text
Atlik tik skaitymo režimo analizę.

Išanalizuok pateiktą užuolaidų proceso žemėlapį. Patikrink:
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

- pakeitimų failų sąrašas tuščias;
- pasiūlymas užblokuotas taikymui arba pažymėtas skaitymo režimu;
- `Rašymas: išjungtas` lieka nepakeistas;
- Home Assistant failai nepakeičiami.

---

## Alpha6 saugos riba

Alpha6 dar nėra leidimas autonomiškai keisti visą Home Assistant projektą. Net įjungus rašymą, esama saugos politika leidžia keisti tik aiškiai patvirtintus YAML failus po `/config/packages/`, po atsarginės kopijos, YAML patikros ir Home Assistant konfigūracijos patikros. Home Assistant automatiškai neperkraunamas.
