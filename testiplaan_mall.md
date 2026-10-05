> **Staatus: ülevaatamist vajav Claude’i loodud lähteversioon.** See dokument ei ole veel kinnitatud testiplaan. Enne kasutamist tuleb üle kontrollida ja täpsustada testsaated, märgendusmeetod, mõõdikute definitsioonid, läviväärtused ning otsusereeglid. Näidisväärtusi ei tohi võtta automaatselt projekti nõuetena.

# ERR2TEXT MVP testiplaan (mall)

> **Kasutusjuhend.** Kõik väärtused, mis on märgitud **(NÄIDIS)**, on lähtepunkt, mitte soovitus. Need tuleb enne lukustamist kohandada vastavalt kasutusjuhule ja Spike A tulemustele. Väljad **TÄIDA** on kohustuslikud. Pärast lukustamist (jaotis 0) ei tohi läviväärtusi, märgendust ega mõõdikute definitsioone muuta ilma uue plaani versioonita.

---

## 0. Dokumendi staatus ja lukustamine

| Väli | Väärtus |
|---|---|
| Testiplaani versioon | TÄIDA (nt `1.0`) |
| Seotud lähteülesande versioon | TÄIDA |
| Lukustamise kuupäev | TÄIDA |
| Lukustaja | TÄIDA |
| Git commit / tag | TÄIDA (nt `testplan-v1.0`) |
| Lukustatud enne esimest valideerimisjooksu? | ☐ jah |

**Lukustamise reeglid**

1. Läved (jaotis 7), mõõdikute definitsioonid (jaotis 6), testiprofiilide saated (jaotis 4) ja märgendatud kontrolllõigud (jaotis 5) lukustatakse **enne** valideerimisjooksu.
2. Pärast tulemuste nägemist ei muudeta läviväärtusi. Vajadusel koostatakse uus plaani versioon, mis märgib muudatuse põhjuse ja kehtib ainult **uue** testjooksu kohta.
3. Iga plaani muudatus lisatakse jaotisse 13.

---

## 1. Eesmärk ja otsus, mida test toetab

Test vastab küsimusele: **kas pyannote-põhine diarization + VTT liitmine annab 4 CPU-ga GPU-ta ARM64 serveris piisavalt usaldusväärse „kes ütles mida" faili, et ehitada teenusekiht (MVP2)?**

Test annab ühe neljast otsusest (vt jaotis 8): `GO`, `GO-PIIRATUD`, `PROOVI ALTERNATIIVI`, `STOP`.

Test **ei** hinda: ERR-i VTT teksti ASR-kvaliteeti (seda ainult raporteeritakse), nimelist hääletuvastust, sisuanalüüsi.

---

## 2. Testitav objekt

| Väli | Väärtus |
|---|---|
| Pipeline'i versioon | TÄIDA |
| Diarization'i mudel | TÄIDA (nt `pyannote/speaker-diarization-community-1`) |
| Mudeli revisjon (pin) | TÄIDA |
| `yt-dlp` / UglyERR versioonid (pin) | TÄIDA |
| Konteineri image digest | TÄIDA |
| Diarization'i parameetrid | TÄIDA (nt kõnelejate arvu vihje: puudub / min–max) |
| Liitmisreegli versioon ja parameetrid | TÄIDA |
| `time_offset_seconds` vaikeväärtus | TÄIDA (nt `0`, automaatdiagnostika sees) |

---

## 3. Testikeskkond ja ressursipiirid

| Parameeter | Väärtus |
|---|---|
| Server | 4 × ARM Neoverse-N1, 23 GiB RAM, GPU puudub |
| Konteineri CPU-limiit | **(NÄIDIS)** `cpus: 3.0` |
| Konteineri mälulimiit | **(NÄIDIS)** `12 GiB` |
| Diarization'i lõimede arv | **(NÄIDIS)** `3` |
| Protsessi prioriteet | **(NÄIDIS)** `nice 10` |
| Teised rakendused testi ajal | töötavad tavapärases töörežiimis (fun_o jt) |
| Baasmõõtmine | enne testi mõõdetakse teiste teenuste vastuseaeg ilma koormuseta |
| Kordusi iga saate kohta | **(NÄIDIS)** `3` (aja, ressursi ja determinismi hindamiseks) |

> Ressursipiirid tuleb enne lukustamist kontrollida Spike A 5-minutilise katsega. Kuid **aja ja mälu lõplik mõõtmine tehakse täispikkadel saadetel**, sest 5-minutiline katse ei ennusta skaleerumist.

---

## 4. Testiprofiilid ja saated

| ID | Profiil | Valikukriteerium | Saade / URL | Kestus | Kõnelejaid (tegelik) |
|---|---|---|---|---|---|
| **P0** | Tehniline spike | Kuni 5 min lõik P1 saatest | TÄIDA | ≤ 5 min | TÄIDA |
| **P1** | Kahe kõnelejaga stuudiointervjuu | 1 saatejuht + 1 külaline, vähe kattuvat kõnet | **(NÄIDIS)** Reinsalu / Ojakivi (esimene testsaade) | TÄIDA | 2 |
| **P2** | Paneel / debatt | 4–6 kõnelejat, tihe vahelehüüdmine | TÄIDA | TÄIDA | TÄIDA |
| **P3** | Reportaaž / muusikaga lõik | Reporteri etteloetud lõigud, intervjueeritavate klipid, taustamuusika | TÄIDA | TÄIDA | TÄIDA |
| **P4** | Pikk saade (skaleerumine) | ≥ 60 min, ainult ajast ja ressursist huvitatud | TÄIDA | ≥ 60 min | TÄIDA |
| **DEV** | Arenduskomplekt | **Eraldi saade** liitmisreegli ja parameetrite häälestamiseks | TÄIDA | TÄIDA | n/a |

**Reegel:** valideerimisprofiilide (P1–P3) saateid **ei kasutata häälestamiseks**. Liitmisreegli ja kindlusklasside piire häälestatakse ainult DEV komplektil.

---

## 5. Ground truth (käsitsi märgendus)

| Parameeter | Väärtus |
|---|---|
| Märgendaja(d) | TÄIDA |
| Tööriist | **(NÄIDIS)** Audacity labels / ELAN / Label Studio |
| Märgendatavad lõigud P1 | **(NÄIDIS)** ≥ 15 min: 3 × 5 min (saate algus, keskpaik, lõpp) |
| Märgendatavad lõigud P2 | **(NÄIDIS)** ≥ 20 min: 4 × 5 min, kaasa arvatud kõige tihedam vahelehüüdmise koht |
| Märgendatavad lõigud P3 | **(NÄIDIS)** ≥ 15 min, sh ≥ 2 min muusika/taustaga ja ≥ 3 reporteri ↔ stuudio üleminekut |
| Märgendatav sisu | kõneleja (nimi/silt) ajavahemiku kohta; kattuv kõne eraldi märgitud; **tekst** märgendatakse ainult P1 ja P3 lõikudes ASR-vigade mõõtmiseks |
| Märgendus tehakse | **enne** pipeline'i väljundi nägemist (pimemärgendus) |
| Topeltmärgendus | **(NÄIDIS)** 20 % minutitest märgendab teine isik |
| Märgendajate vaheline kokkulepe | **(NÄIDIS)** ≥ 95 % mittekattuva kõne ajast; allpool seda täpsustatakse märgendusjuhendit |
| Kõnelejavahetuse tolerants | **(NÄIDIS)** `collar = 0,25 s` kõnelejavahetuse ümber |

**Märgendusjuhend (täita):** kuidas märgitakse naer, vahelehüüded alla 0,5 s, vaikus, muusika, ettelugemine, salvestatud klipp.

---

## 6. Mõõdikud

Hinnatakse **mittekattuva kõne** ajaga kaalutult (kattuv kõne hinnatakse eraldi, vt M7). SPEAKER_nn sildid seotakse märgenduse kõnelejatega **optimaalse vastavusega** (Hungarian) iga saate sees.

Iga mittekattuva kõne ajavahemik kuulub täpselt ühte neljast klassi:

| Klass | Definitsioon |
|---|---|
| **Õige** | `assigned`, silt vastab märgendusele |
| **Vale kindel** | `assigned`, kindlus `high` või `medium`, silt on vale |
| **Vale madala kindlusega** | `assigned`, kindlus `low`, silt on vale |
| **Omistamata** | `unassigned` |

| ID | Mõõdik | Definitsioon |
|---|---|---|
| **M1** | Õige omistuse osakaal | Õige / kogu mittekattuv kõne |
| **M2** | **Vale kindla omistuse osakaal** | Vale kindel / kogu mittekattuv kõne. **Kõige kriitilisem mõõdik** |
| **M3** | Omistamata osakaal | Omistamata / kogu mittekattuv kõne |
| **M4** | Madala kindlusega osakaal | Kõik `low` lõigud (õiged + valed) / kogu mittekattuv kõne |
| **M5** | DER (informatiivne) | `pyannote.metrics`, `collar = 0,25 s`, kattuva kõnega ja ilma, raporteeritakse eraldi |
| **M6** | Kõnelejate arvu viga | Tuvastatud kõnelejate arv vs tegelik (arvesse võetakse ainult kõnelejaid, kelle kõneaeg ≥ 5 % või ≥ 30 s) |
| **M7** | Kattuva kõne käsitlus | Kattuva kõne ajast: mitu % märgiti `unassigned` või `low` (mitte `high`) |
| **M8** | Ajanihke diagnostika | Tuvastatud nihe vs käsitsi mõõdetud nihe (sekundites) |
| **M9** | Töötlusaja kordaja | (a) diarization'i seinaaeg / audio kestus; (b) kogu töötlus URL → väljundid / audio kestus |
| **M10** | Ressursikasutus | Tipp-RSS (GiB), keskmine CPU-kasutus, OOM-kill'ide arv |
| **M11** | Mõju teistele teenustele | Valitud teenuse (nt fun_o health-endpoint) p95 vastuseaja muutus baasväärtusega võrreldes + 5xx vigade arv |
| **M12** | Determinism | Sama sisend, kolm jooksu: `speakers.json` erinevus (% ajast, mille kõneleja erineb) |
| **M13** | Poolitamise täpsus | `split_estimated` lõikudel: poolituspiiri mediaanviga ja 90. protsentiil vs märgendatud vahetus (s) |
| **M14** | Nimede ülevaatuse kasutatavus | Ülevaataja seob kõik ≥ 5 % kõneajaga kõnelejad nimedega **ainult `speaker_review` väljundi põhjal**: õigete seoste osakaal ja kulunud aeg |
| **M15** | ERR-i VTT ASR-viga (informatiivne) | WER märgendatud tekstilõikudel; **raporteeritakse, mitte hinnata läve vastu** |

---

## 7. Läviväärtused **(NÄIDIS, kohanda ja lukusta)**

### 7.1 Tase A (täielikult kasutatav)

| Mõõdik | P1 | P2 | P3 | Märkus |
|---|---|---|---|---|
| M1 õige omistus | ≥ 95 % | ≥ 85 % | ≥ 85 % | |
| **M2 vale kindel** | **≤ 1 %** | **≤ 3 %** | **≤ 3 %** | **Kõva piir, vt 7.4** |
| M3 omistamata | ≤ 10 % | ≤ 20 % | ≤ 25 % | |
| M4 madal kindlus | ≤ 15 % | ≤ 30 % | ≤ 35 % | |
| M5 DER | raporteeri | raporteeri | raporteeri | informatiivne |
| M6 kõnelejate arv | täpne | ±1 | ±1 | P3: reporterite lõigud võivad lisada kõnelejaid |
| M7 kattuv kõne `high` | ≤ 10 % | ≤ 20 % | ≤ 20 % | kattuvat kõnet ei tohi enamasti märkida kindlaks |
| M8 ajanihke viga | ≤ 0,5 s | ≤ 0,5 s | ≤ 0,5 s | seletamatu nihe > 2 s → töö ebaõnnestub veaga |
| M13 poolitus, mediaan | ≤ 1,0 s | ≤ 1,5 s | ≤ 1,5 s | |
| M12 determinism | ≤ 1 % | ≤ 2 % | ≤ 2 % | |
| M14 ülevaatus | 100 % õige, ≤ 10 min | ≥ 90 % õige, ≤ 15 min | ≥ 90 % õige, ≤ 15 min | |
| M15 ASR WER | raporteeri | n/a | raporteeri | informatiivne |

### 7.2 Tase B (piiratud kasutus, ainult koos omistamata/madala kindluse filtreerimisega)

| Mõõdik | Lävi (kõik profiilid) |
|---|---|
| M1 | ≥ 75 % |
| **M2** | **≤ 5 %** |
| M3 | ≤ 40 % |
| M8 | ≤ 1,0 s |

### 7.3 Tase C (ei sobi)

Kõik, mis ei täida Tase B läbi.

### 7.4 Kõvad reeglid (kehtivad sõltumata teistest mõõdikutest)

1. Kui **M2** ületab Tase B piiri, on profiil automaatselt **Tase C**, ükskõik kui hea M1 on. Vale kindel silt on selle projekti kõige kahjulikum viga.
2. Kui ilmneb **seletamatu ajanihe > 2 s** ilma veateate või hoiatuseta, on profiil **Tase C**.
3. Kui **M10** näitab OOM-kill'i või **M11** 5xx vigu, on profiil **Tase C** kuni ressursipiirid parandatakse ja test korratakse.

### 7.5 Aja- ja ressursilävid (kõik profiilid, mõõdetakse P1 täispikal saatel ja P4-l)

| Mõõdik | Siht | Kõva piir (STOP) |
|---|---|---|
| M9a diarization'i seinaaeg / audio | **(NÄIDIS)** ≤ 1,0× | **(NÄIDIS)** ≤ 2,0× |
| M9b kogu töötlus / audio | **(NÄIDIS)** ≤ 1,25× | **(NÄIDIS)** ≤ 2,5× |
| M10 tipp-RSS | **(NÄIDIS)** ≤ 8 GiB | **(NÄIDIS)** ≤ 12 GiB (konteineri limiit) |
| M11 teiste teenuste p95 | **(NÄIDIS)** ≤ +25 % | **(NÄIDIS)** ≤ +100 % ja 0 × 5xx |

> **Kalibreerimine:** aja- ja mälulävi pole võimalik enne Spike A tulemust mõistlikult määrata. Spike A annab ainult „käivitub / ei käivitu" ja esialgse suurusjärgu. Lõplik lävi lukustatakse pärast Spike A-d, aga **enne** P1–P4 valideerimisjooksu.

---

## 8. Otsusereeglid (Definition of Done tasemeliselt)

| Tulemus | Otsus |
|---|---|
| P1 = **A**, P2 ≥ **B**, P3 ≥ **B**, ressursilävid täidetud | **GO**: ehita MVP2 kõigi kolme profiiliga |
| P1 = **A**, P2 või P3 = **C**, ressursilävid täidetud | **GO-PIIRATUD**: ehita MVP2, kuid toetatud kasutusjuhud piirdutakse täidetud profiilidega; ülejäänud märgitakse väljundis „ei toetata / vajab käsitsi ülevaatust" |
| P1 = **B**, **või** ressursilävid ei täitu, **või** pyannote ei käivitu ARM64-l | **PROOVI ALTERNATIIVI**: üks tsükkel alternatiiviga (CPU/ONNX või NeMo), **sama plaani** ja läviväärtustega |
| P1 = **C** | **STOP**: diarization'i lähenemine ei ole selle kasutusjuhu jaoks piisav; vaata uuesti ASR+diarization (nt WhisperX) või käsitsi ülevaatuse töövoog |

**Lisatingimused kõigile GO otsustele:**

- Väljund sisaldab päritolu- ja kindlusinfot (mudel, revisjon, `attribution_status`, `attribution_confidence`, `overlap_ratio`, `split_estimated`).
- Töö toimub ettenähtud konteineri ressursipiirangutes.
- Kõik tehnilised testid (jaotis 11) on läbitud.
- Resolveri testid (jaotis 10) on läbitud.

---

## 9. Testimise protseduur

| # | Samm | Väljund |
|---|---|---|
| 1 | **Spike A (P0):** ARM64 konteineri ehitus, mudeli allalaadimine, 5-min diarization | käivitub / ei käivitu, esialgne ressursimõõtmine |
| 2 | **Spike B:** resolveri testid (jaotis 10) | resolveri tulemuste tabel |
| 3 | **Häälestamine DEV komplektil:** liitmisreegel, kindlusklasside piirid, `time_offset` diagnostika | fikseeritud parameetrid |
| 4 | **Kalibreeri ressursilävid** (jaotis 7.5) Spike A põhjal | uuendatud jaotis 7.5 |
| 5 | **Lukusta plaan** (jaotis 0) | git tag |
| 6 | **Märgenda ground truth** pimemärgendusena (jaotis 5) | märgendusfailid |
| 7 | **Käivita pipeline** P1–P4: 3 kordust iga saate kohta, fikseeritud parameetritega, **ilma häälestamiseta** | väljundid + `run_metadata.json` |
| 8 | **Arvuta mõõdikud** versioonitud skriptiga (sama skripti commit lisatakse raportisse) | mõõdikute tabel |
| 9 | **Veaanalüüs:** liigita vead (jaotis 12.3) | veatüüpide tabel |
| 10 | **Ülevaatuse test** (M14): teine isik seob nimed ainult `speaker_review` põhjal | M14 tulemus |
| 11 | **Raport ja otsus** (jaotis 12) | mõõtmisraport |

---

## 10. Resolveri testid (Spike B)

Fiksuuritega (salvestatud HTTP/metadata vastused) ja live-päringutega.

| ID | Sisend | Ootus | Fiksuur | Live |
|---|---|---|---|---|
| R1 | ERR-i artikkel ühe seotud saatevideoga (esimene testartikkel) | `ERR_ARTICLE`, üks `media_items`, töötlus jätkub automaatselt | ☐ | ☐ |
| R2 | ERR-i artikkel mitme videoga | `media_items` nimekiri, töötlus **ei alga** ilma `--video-index`-ita | ☐ | ☐ |
| R3 | ERR-i artikkel ilma videota | `ARTICLE_WITHOUT_MEDIA` | ☐ | ☐ |
| R4 | Jupiteri saate/video URL | `JUPITER_MEDIA`, meedia leitud | ☐ | ☐ |
| R5 | Arhiivi URL (`arhiiv.err.ee`) | `ERR_ARCHIVE_MEDIA`, meedia leitud | ☐ | ☐ |
| R6 | DRM-kaitstud meedia | `DRM_PROTECTED` | ☐ | ☐ |
| R7 | Mitte-ERR-i domeen | `UNSUPPORTED_URL` | ☐ | ☐ |
| R8 | Vigane/kustutatud meedia | `MEDIA_NOT_FOUND` | ☐ | ☐ |
| R9 | Allalaadimise tõrge (simuleeritud) | `DOWNLOAD_FAILED` | ☐ | n/a |

**Läbimiskriteerium (NÄIDIS):**
- Fiksuuridega testid: **100 %** läbivad.
- Live-valim: **≥ 10 URL-i** erinevatelt ERR-i portaalidelt, **≥ 80 %** annab õige meedia või õige veakoodi.
- Üheski juhul ei tohi kasutajat suunata DevToolsi avama ega meedia-URL-i käsitsi otsima.

---

## 11. Tehnilised testid (automaatsed)

| ID | Test | Läbimiskriteerium |
|---|---|---|
| T1 | Mojibake parandus: `JÃ¤rgnevale` → `Järgnevale` | täpne vaste |
| T2 | Juba korrektne tekst (`Järgnevale`, `õäöüšž`) normaliseerimisel | **muutumatu** |
| T3 | `original.vtt` | baitide kaupa identne ERR-i vastusega |
| T4 | VTT parser: BOM, CRLF, mitmerealised lõigud, inline-tag'id, `NOTE` plokid, korduvad lõigud | ajamärgid ja tekst korrektsed fiksuuritel |
| T5 | Liitmine: lõik katab kahe kõneleja piiri | poolitatud, `split_estimated: true` |
| T6 | Liitmine: lõik, millel puudub piisav kattuvus | `unassigned`, `speaker_id: null`, `speaker_name: null` |
| T7 | Liitmine: lõik kattuvas kõnes | `overlap_ratio` salvestatud, kindlus ≠ `high` |
| T8 | `time_offset_seconds` rakendamine | lõigud nihkuvad õigesti |
| T9 | Seletamatu nihe (> 2 s) | hoiatus või veaolek, mitte vaikne väljund |
| T10 | `apply-names` ilma audio ja diarization'ita | uus JSON/MD, audio ei laeta |
| T11 | `apply-names` vale diarization'i jooksuga map | **keeldub** (map seotud `speakers.json` jooksu ID/kontrollsummaga) |
| T12 | Cache: allalaadimise tabamus | allalaadimist ei korrata |
| T13 | Cache: diarization'i tabamus samade parameetritega | `speakers.json` taaskasutatud |
| T14 | Cache: muutunud mudeli revisjon või parameeter | **mööda cache'ist**, uus arvutus |
| T15 | HF-token | puudub logides, väljundis ja Git-is (otsing) |
| T16 | WAV | kustutatud pärast edukat **ja** nurjunud töötlust |
| T17 | Embedding'uid | ei salvestata ühtegi väljundisse |
| T18 | Kõik väljundid | UTF-8 (v.a. `original.vtt`), eesti tähed säilinud |
| T19 | Väljundi päis | sisaldab märget „automaatne, kontrollimata kõneleja omistus" ja mudeli/revisjoni |
| T20 | Konteineri limiidid | rakendatud (`cpus`, mälu, lõimed, `nice`) |

---

## 12. Mõõtmisraporti mall

### 12.1 Kokkuvõte

| Väli | Väärtus |
|---|---|
| Testi kuupäev | TÄIDA |
| Plaani versioon / commit | TÄIDA |
| Mõõdikute skripti commit | TÄIDA |
| **Otsus** (GO / GO-PIIRATUD / PROOVI ALTERNATIIVI / STOP) | TÄIDA |

### 12.2 Tulemused profiilide kaupa

| Mõõdik | P1 tulemus | P1 lävi | P2 tulemus | P2 lävi | P3 tulemus | P3 lävi |
|---|---|---|---|---|---|---|
| M1 | | | | | | |
| M2 | | | | | | |
| M3 | | | | | | |
| M4 | | | | | | |
| M5 | | | | | | |
| M6 | | | | | | |
| M7 | | | | | | |
| M8 | | | | | | |
| M12 | | | | | | |
| M13 | | | | | | |
| M14 | | | | | | |
| M15 | | | | | | |
| **Tase (A/B/C)** | | | | | | |

### 12.3 Aja- ja ressursitulemused

| Saade | Kestus | M9a | M9b | M10 tipp-RSS | M10 CPU | M11 p95 muutus | OOM / 5xx |
|---|---|---|---|---|---|---|---|
| P1 | | | | | | | |
| P2 | | | | | | | |
| P3 | | | | | | | |
| P4 | | | | | | | |

### 12.4 Veatüübid

| Veatüüp | P1 | P2 | P3 | Näide (ajamärk) | Põhjus / märkus |
|---|---|---|---|---|---|
| Vale silt kattuval kõnel | | | | | |
| Lühike vahelehüüe vale sildiga | | | | | |
| Kõnelejavahetuse viivitus | | | | | |
| Üks inimene jaotatud mitmeks `SPEAKER_nn` | | | | | |
| Mitu inimest ühendatud üheks | | | | | |
| Muusika/taustaheli viga | | | | | |
| Reporteri etteloetud lõik vs stuudio | | | | | |
| Ajanihe | | | | | |
| Poolituspiiri viga | | | | | |
| ERR-i VTT ASR-viga (mitte diarization) | | | | | |

### 12.5 Avatud küsimused ja järgmised sammud

TÄIDA

### 12.6 Kinnitus

| Roll | Nimi | Kuupäev |
|---|---|---|
| Testi läbiviija | | |
| Ülevaataja | | |

---

## 13. Plaani muudatuste logi

| Versioon | Kuupäev | Muudatus | Põhjus | Kehtib testjooksu kohta |
|---|---|---|---|---|
| 1.0 | TÄIDA | Esialgne plaan | | TÄIDA |

---

## Lisa A. Mõõdikute arvutamise märkused

- Kõik osakaalud on **ajaga kaalutud** (sekundites), mitte lõikude arvu järgi.
- Kõnelejavahetuse ümber jäetakse `collar = 0,25 s` hindamisest välja.
- Kattuv kõne (märgenduse järgi) jäetakse M1–M4-st välja ja hinnatakse eraldi M7-s.
- `SPEAKER_nn` ↔ märgenduse kõneleja vastavus leitakse iga saate sees optimaalse vastendusega ja fikseeritakse enne klasside arvutamist.
- Kõnelejad, kelle kõneaeg on alla 5 % ja alla 30 s, raporteeritakse eraldi (nad ei mõjuta M6).
- Mõõdikute skript on versioonitud ja tema väljund on reprodutseeritav.

## Lisa B. Hoiatused näidisväärtuste kohta

- Näidisväärtused ei põhine ERR-i materjalil tehtud mõõtmisel. Need on struktuuri demonstreerimiseks ja tuleb kohandada.
- Kui kasutusjuht on rangem (nt tsiteerimine, avalik faktikontroll), pingutage M2 läve ja nõudke käsitsi ülevaatust enne tulemuse kasutamist.
- Väiksem lävi ei tee tulemust paremaks, kui märgendus on ebausaldusväärne: kontrollige märgendajate kokkulepet (jaotis 5) enne läviväärtuste kinnitamist.
