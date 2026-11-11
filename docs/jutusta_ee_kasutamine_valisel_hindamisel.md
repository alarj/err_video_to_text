# Jutusta.ee kasutamine välisel hindamisel

> **AI kasutamise teade.** Käesolev dokument on koostatud tehisintellekti abil
> kasutaja sisendi, projekti dokumentatsiooni ning protsesside `#90` ja `#65`
> andmete põhjal. Uurimistöö autor kontrollib, täiendab ja vastutab dokumendi
> sisu, järelduste ning edasiste otsuste eest.

## Sisukord

1. [Lähtekoht ja mõisted](#1-lähtekoht-ja-mõisted)
2. [Võrdlusmeetod](#2-võrdlusmeetod)
3. [Hüpotees 1: Jutusta.ee saab asendada inimese tekstiparandusi](#3-hüpotees-1-jutustaee-saab-asendada-inimese-tekstiparandusi)
4. [Hüpotees 2: Jutusta.ee saab vähendada kõnelejapiiride ülevaatust](#4-hüpotees-2-jutustaee-saab-vähendada-kõnelejapiiride-ülevaatust)
5. [Hüpotees 3: binaarne masinõppemudel saab olla automaatotsuse turvavärav](#5-hüpotees-3-binaarne-masinõppemudel-saab-olla-automaatotsuse-turvavärav)
6. [Hüpotees 4: automaatotsus peab olema inimese otsusest eristatav](#6-hüpotees-4-automaatotsus-peab-olema-inimese-otsusest-eristatav)
7. [Edasise tegevuse soovitus: töövoo muutmise ettepanek](#7-edasise-tegevuse-soovitus-töövoo-muutmise-ettepanek)

Dokument koondab protsesside `#90` ja `#65` põhjal tehtud Jutusta.ee
võrdluse ning seob selle olemasolevate masinõppekatsetega. Eesmärk on hinnata,
kas Jutusta.ee saab vähendada tehnilise ülevaatuse inimtööd. Kahe saate
tulemused on uurimisandmed, mitte veel tootmisreegli tõestus.

## 1. Lähtekoht ja mõisted

ERR2TEXT-i automaatse mustandi tekst pärineb ERR VTT-st. Pyannote ei
transkribeeri teksti, vaid diariseerib audio ning aitab omistada VTT-lõigud
kõnelejatele. Tehniline kandidaat saab inimese otsuse `ACCEPTED`, `REJECTED`
või `MODIFIED`. Töövoogu ja märgendeid kirjeldavad
[uurimistöö kirjeldus](uurimistoo.md) ning
[analüüsi- ja õppeandmete register](evaluation_data.md).

Jutusta.ee on käesolevas katses teine, ERR VTT-st sõltumatu audio
transkribeerija. Selle transkriptsiooni kasutatakse välise võrdlusandmestikuna:
Jutusta.ee tulemust võrreldakse nii ERR VTT-l põhineva automaatse mustandi kui
ka inimese parandatud versiooniga. Inimese versioon on õigsuse etalon ainult
Pyannote'i kandidaatide ja inimese töölauale jõudnud naabersegmentide osas.
Ülejäänud transkriptsiooni inimene üle ei vaadanud ning seal ei tõenda
Jutusta.ee ja automaatse mustandi erinevus kummagi variandi õigsust. Inimese
kontrollitud ulatuses saab hinnata, kas Jutusta.ee oleks suutnud inimese
otsuse või paranduse iseseisvalt taastada.

Jutusta.ee tulemus säilitatakse vabatahtliku `JUTUSTA_EE_DRAFT` versioonina.
See ei osale praeguses tehnilise ülevaatuse töövoos. Impordi- ja
võrdlusloogika on failis
[backend/import_jutusta.py](../backend/import_jutusta.py) ning versioonitüübi
andmebaasireegel failis
[db/schema/007_jutusta_ee_draft.sql](../db/schema/007_jutusta_ee_draft.sql).

## 2. Võrdlusmeetod

Võrdlus tehakse ajastatud segmentide kaupa. Tekstitulemused on:

- `SEMANTIC_MATCH` – sama sisu pärast kirjavahemärkide, täitesõnade ja
  samaväärsete arvukujude normaliseerimist;
- `CLOSE` – sarnane, kuid mitte piisav automaatse tekstiparanduse
  kinnitamiseks;
- `DIFFERENT` – sisuline erinevus;
- `UNALIGNED` – segmendile ei leitud vastavat Jutusta.ee teksti.

ERR VTT `SYSTEM_NOTICE` ekraaniteated jäetakse audiovõrdlusest välja, sest
neid audios ei ole. Inimese poolituse ja Jutusta.ee sõnaajastuse väikese
erinevuse jaoks kasutatakse 250 ms tolerantsi ainult siis, kui piiri lähedal
leiduv tekst on semantiliselt sama. Selle tõttu joondus protsessi `#90`
„Mina.” õigesti, kuid protsessi `#65` puuduv „Gaasijaamad?” jäi
`UNALIGNED` tulemuseks.

Võrdluse ulatused on:

- `CANDIDATE` – Pyannote'i tehniline kandidaat, mille kohta inimene tegi
  otsuse;
- `REVIEW_REACHABLE_NEIGHBOR` – kandidaadi tõttu töölauale jõudnud
  naabersegment, sealhulgas poolitamisel kaskaadis tekkinud parandatud
  segmendid;
- `OUTSIDE_REVIEW_WORKBENCH` – segment, mida inimene ei kontrollinud.

Esimesed kaks ulatust moodustavad inimese kontrollitud referentsala.
`OUTSIDE_REVIEW_WORKBENCH` tulemused näitavad ainult kahe masintulemuse
kooskõla või erinevust. Neid ei tohi lugeda tõendatud veaks ega inimese
kinnitatud paranduseks.

`MODIFIED` kandidaadi hindamisel ei piisa kogu segmendi sarnasusest. Esmalt
eraldatakse automaatse ja inimese versiooni tekstidelta ning hinnatakse, kas
Jutusta.ee kinnitab just inimese muudetud sõnu. Kõneleja- ja
poolitusmuudatusi hinnatakse tekstist eraldi.

## 3. Hüpotees 1: Jutusta.ee saab asendada inimese tekstiparandusi

### Faktid

Protsessides `#90` ja `#65` oli kokku kümme `MODIFIED` kandidaati, kus
inimene muutis sõnu, mitte ainult kõnelejat või poolituspiiri.

| Protsess | Inimese tekstiparandusi | Jutusta.ee kinnitas täielikult | Kinnitas osaliselt | Ei kinnitanud |
|---|---:|---:|---:|---:|
| `#90` | 4 | 2 | 0 | 2 |
| `#65` | 6 | 1 | 1 | 4 |
| **Kokku** | **10** | **3** | **1** | **6** |

Tekstina täielikult kinnitatud parandused olid:

- `#90`, kandidaat `2454`: `oskab` → `maksab`;
- `#90`, kandidaat `2470`: puuduv sõna `Igaüks`;
- `#65`, kandidaat `1804`: `ENK aasist` → `LNG gaasist`.

Kandidaatidel `2454` ja `1804` ei langenud Jutusta.ee kõneleja inimese
kõnelejaga kokku. Need on seega tekstivaste, mitte kogu kandidaadi täielik
vaste.

Näide, miks kogu segmendi `CLOSE` ei ole piisav, on `#90` kandidaat `2466`:

- ERR VTT ja automaatne mustand: `Pühalaulu`;
- inimene: `Püha Laurentsius`;
- Jutusta.ee: `Püha laua peal`.

Lause ülejäänud osa kattus ning andis kogu segmendile `CLOSE` tulemuse, kuid
inimese parandatud nime Jutusta.ee ei tuvastanud.

### Järeldus

Jutusta.ee ei taastanud piisavalt suurt osa inimese tekstiparandustest:
täielik vaste oli 3/10 ehk 30%. Jutusta.ee erinevus ERR VTT-st ei näita
iseenesest, kumb variant on õige. Kõigi erinevuste automaatne asendamine
parandaks mõne vea, kuid tekitaks ka uusi vigu.

### Soovitus

Jutusta.ee tekstierinevusi võib kasutada inimesele paranduse ettepanekuna,
kuid mitte automaatse tekstimuudatusena. Automaatset tekstiparandust ei tule
esimesse rakendusetappi lisada. Uus katse on põhjendatud alles pärast suurema
referentsvalimi kogumist ja tekstidelta-põhise usaldusreegli loomist.

## 4. Hüpotees 2: Jutusta.ee saab vähendada kõnelejapiiride ülevaatust

### Faktid

Inimese otsuste jaotus oli:

| Protsess | Kandidaate | `ACCEPTED` | `MODIFIED` | `REJECTED` |
|---|---:|---:|---:|---:|
| `#90` | 29 | 2 | 13 | 14 |
| `#65` | 32 | 0 | 26 | 6 |

Pärast ekraaniteadete eemaldamist olid ERR VTT teksti ja Jutusta.ee
tekstitulemused mõlemas saates enamasti semantiliselt samad või lähedased.
Järgmine kogu saate tabel kirjeldab tehnilist kooskõla, mitte täpsust, sest
väljaspool kandidaate ja nende töölauale jõudnud naabreid puudub inimese
kontrollitud etalon.

| Protsess | Automaatse mustandi kõnesegmente | `SEMANTIC_MATCH` | `CLOSE` | `DIFFERENT` | Kõneleja `MATCH` |
|---|---:|---:|---:|---:|---:|
| `#90` | 536 | 440 | 90 | 6 | 405 |
| `#65` | 425 | 337 | 83 | 5 | 398 |

Kõnelejavaste oli `#65` puhul parem kui `#90` puhul. See on oluline, sest
`#65` saates oli kaks ning `#90` saates kolm põhikõnelejat.

Inimese `MODIFIED` otsustes, kus sõnu ei muudetud, vaid muudeti kõnelejat või
poolituspiiri, kinnitas Jutusta.ee inimese tulemuse:

- `#90`: 4 juhul 6-st;
- `#65`: 10 juhul 11-st.

`ACCEPTED` või `REJECTED` automaatotsuse jaoks hinnati ainult juhtumeid, kus
Jutusta.ee tekst, kõneleja ja tegelik kõnelejapiir andsid üheselt sama
tulemuse nagu inimene. Tulemuseks saadi:

- `#90`: kaks kindlat ning üks tolerantsema tekstireegliga `REJECTED`
  kandidaat;
- `#65`: kaks `REJECTED` kandidaati;
- kummaski saates ei olnud piisavalt kindlat automaatselt lahendatavat
  `ACCEPTED` kandidaati.

`#65` „Gaasijaamad?” näitab piirangut. Liisu Lassi lühike küsimus kattus Yoko
Alenderi kõnega ning Jutusta.ee ei tuvastanud ei teksti ega kõnelejamuutust.
Pelgalt Jutusta.ee piiri puudumise põhjal oleks selline kandidaat ekslikult
tagasi lükatud.

### Järeldus

Jutusta.ee on kahe saate põhjal kõnelejapiiride kontrollimisel kasulikum kui
tekstiparanduste taastamisel. Samas ei ole „Jutusta.ee ei näe piiri” piisav
`REJECTED` otsuse alus, sest lühike kattuv kõne võib jääda tuvastamata.

### Soovitus

Esimeses automaatikaetapis kasutada Jutusta.ee-d ainult kõnelejapiiri
tõendina. Kattuva kõne, tugeva sekundaarse Pyannote'i intervalli,
joondamisvea või alternatiivse piiri korral peab kandidaat jääma inimesele.
Tekst ja kõneleja tuleb hinnata eraldi.

## 5. Hüpotees 3: binaarne masinõppemudel saab olla automaatotsuse turvavärav

### Faktid

Olemasolevates X1 ja Y1 katsetes olid nii protsessi `#90` kui ka `#65`
kandidaadid testandmetes. X1 ja Y1 on kandidaadipõhised jaotused; varasemad
katsed ei näidanud, et saatepiiri kasutamine muudaks tulemuste üldpilti.
Jaotused on fikseeritud manifestides
[x_split_manifest.json](kursusetoo/manifestid/x_split_manifest.json) ja
[y_split_manifest.json](kursusetoo/manifestid/y_split_manifest.json).

Jutusta.ee abil lahendatavaks hinnatud kandidaatidest oli sõltumatus X1/Y1
testiosas kolm:

| Kandidaat | Inimene ja Jutusta.ee | Valitud binaarmudel | Kombineeritud tulemus |
|---|---|---|---|
| `#90 / 2444` | `REJECTED` | inimene vajalik | inimene |
| `#90 / 2445` | `REJECTED` | inimene pole vajalik | `REJECTED_AUTO` |
| `#65 / 1814` | `REJECTED` | inimene pole vajalik | `REJECTED_AUTO` |

Mõlemad automaatharusse lubatud otsused langesid kokku inimese otsusega.
Kandidaat `2444` jäi konservatiivselt inimesele. Ülejäänud kaks Jutusta.ee
abil lahendatavaks hinnatud kandidaati ei olnud X1/Y1 testiosas ning nende
kohta ei saa sõltumatut testijäreldust teha.

Binaarse inimsekkumise katse valitud mudel on `RUSBoosted Trees`, millest on
eemaldatud tunnus `words`. Kuue testi lõikes olid selle halvim
`MODIFIED`-klassi recall 80,00%, halvim automaatharu NPV 82,01% ja keskmine
automaatharu osakaal 45,10%. Täpne valikureegel ja tulemused on failis
[tulemused2.md](kursusetoo/tulemused2.md). Kolmeklassilise katse tulemused
on eraldi failis [tulemused.md](kursusetoo/tulemused.md).

### Järeldus

Jutusta.ee-ga ühendatud töövoos ei pea masinõppemudel tingimata ennustama
kolme klassi. Binaarne mudel saab vastata ohutusküsimusele „kas inimene peab
sekkuma?” ning Jutusta.ee saab anda võimaliku `ACCEPTED` või `REJECTED`
otsuse. See eraldab kaks eri ülesannet.

Valitud binaarmudeli 82,01% halvim NPV ei ole üksinda automaatseks muutmiseks
piisav. Kolme ühise testkandidaadi tulemus 2/2 õiget automaatotsust on
paljulubav, kuid statistiliseks kinnituseks liiga väike.

### Soovitus

Kasutada binaarset mudelit Jutusta.ee otsuse turvaväravana. „Parimat mudelit”
ei tule valida üldise accuracy järgi. Valikukriteeriumide järjekord peab olema:

1. võimalikult vähe tegelikke `MODIFIED` kandidaate automaatharusse;
2. võimalikult kõrge automaatharu NPV;
3. alles seejärel võimalikult suur automaatharu osakaal.

Lõplik mudel ja otsustuslävend tuleb valida kombineeritud Jutusta.ee + mudeli
värava, mitte ainult eraldiseisva mudeli mõõdikute põhjal.

## 6. Hüpotees 4: automaatotsus peab olema inimese otsusest eristatav

### Faktid

Praegused `ACCEPTED` ja `REJECTED` otsused tähistavad inimese tegevust ning
neid kasutatakse masinõppe referentsmärgenditena. Automaatotsuse salvestamine
sama väärtusega muudaks inim- ja masinotsused hilisemas analüüsis
eristamatuks.

### Järeldus

Automaatotsus ei tohi muutuda inimese referentsmärgendiks ega jätta muljet,
et inimene on kandidaadi kinnitanud. Otsuse päritolu peab olema auditeeritav
ja inimese hilisem otsus peab saama automaatotsuse asendada ilma ajalugu
kaotamata.

### Soovitus

Lisada eristatavad otsused:

- `ACCEPTED_AUTO`;
- `REJECTED_AUTO`.

Lisada eraldi `decision_source`, mis eristab vähemalt inimese ning
Jutusta.ee + masinõppe otsuse. Koos automaatotsusega tuleb säilitada
Jutusta.ee versioon, mudeli ja reegli versioon, skoor või lävend, otsuse aeg
ning otsuse aluseks olnud joondustõendid. `*_AUTO` ridu ei tohi kasutada
inimese referentsmärgendina enne inimese kinnitust.

## 7. Edasise tegevuse soovitus: töövoo muutmise ettepanek

### Hüpotees

Pyannote'i, Jutusta.ee ja binaarse mudeli sõltumatute tõendite ühendamine
võib vähendada inimese kontrollitavate kandidaatide arvu ilma
tekstiparandusi automaatselt rakendamata.

### Faktid

- Pyannote ja Jutusta.ee vajavad mõlemad audiot ning võivad töötada
  paralleelselt.
- Masinõppemudeli olemasolevad tunnused tekivad pärast Pyannote'i
  kandidaatide loomist; mudel ei vaja praegu Jutusta.ee väljundit.
- Automaatotsus eeldab siiski Jutusta.ee ja kandidaadi joondamist ning mõlema
  tulemuse ühendamist.
- Kahe saate katses oli kõnelejapiiride vaste parem kui tekstiparanduste
  vaste.
- Kolme sõltumatu testkandidaadi kombineeritud värav tegi kaks õiget
  automaatotsust ja jättis ühe inimesele.

### Järeldus

Sobiv arhitektuur ei ole rangelt järjestikune „Pyannote → Jutusta.ee → mudel
→ inimene”. Jutusta.ee ja masinõpe on kaks sisendit eraldi otsustuskihile.
Inimene peab saama ainult lahendamata, vastuolulised või auditisse valitud
kandidaadid.

### Soovitus

Katsetada järgmist töövoogu:

1. ERR VTT ja audio hankimine.
2. Pyannote'i diariseerimine ning Jutusta.ee täissaate transkriptsioon
   paralleelselt.
3. `AUTOMATIC_DRAFT` ja tehniliste kandidaatide loomine seniste reeglitega.
4. Jutusta.ee sõnade, kõnelejate ja piiride joondamine kandidaatidega.
5. Binaarse mudeliga `human_intervention_required` hindamine.
6. Otsustuskiht:
   - üheselt joondatud Jutusta.ee otsus + binaarmudeli „inimene pole
     vajalik” → `ACCEPTED_AUTO` või `REJECTED_AUTO`;
   - vastuolu, kattuv kõne, tekstiparandus, joondamisviga või mudeli „inimene
     vajalik” → inimese töölaud.
7. Automaatotsuse tõendite ja `decision_source` salvestamine.
8. Inimese võimalus automaatotsus üle vaadata ja asendada, säilitades
   otsuste ajaloo.

Kasutuselevõtt peab toimuma etappide kaupa:

1. **Varirežiim:** `*_AUTO` otsused arvutatakse, kuid inimene kontrollib
   endiselt kõik kandidaadid.
2. **Mõõtmine:** hinnatakse kombineeritud automaatharu NPV-d ning eraldi
   `ACCEPTED_AUTO` ja `REJECTED_AUTO` veamäära.
3. **Piiratud automaatika:** alustatakse ainult kõrge kindlusega
   `REJECTED_AUTO` juhtudest.
4. **Pidev audit:** juhuvalim automaatotsustest saadetakse varjatult inimese
   kontrolli, et tuvastada kvaliteedi muutus.
5. **Laiendamine:** `ACCEPTED_AUTO` lisatakse pärast piisavat referentsvalimit;
   automaatsed tekstiparandused jäävad eraldi hilisemaks uurimisküsimuseks.

Enne töövoo muutmist tuleb Jutusta.ee-ga töödelda rohkem inimese poolt juba
üle vaadatud saateid ning hinnata sama kombineeritud reeglit fikseeritud
testvalimil. Praegune kahe saate analüüs põhjendab katset, kuid mitte veel
tootmisautomaatikat.
