# Uurimistöö kirjeldus

> **AI kasutamise teade.** Käesolev dokument on koostatud tehisintellekti abil
> kasutaja sisendi, projekti dokumentatsiooni ja olemasoleva andmetabeli
> põhjal. Uurimistöö autor kontrollib, täiendab ja vastutab dokumendi sisu,
> meetodite, katsete ning järelduste eest.

## Sisukord

1. [Taust ja olemasolev süsteem](#1-taust-ja-olemasolev-süsteem)
2. [Uurimisprobleem ja eesmärk](#2-uurimisprobleem-ja-eesmärk)
3. [Uurimisküsimus ja hüpoteesid](#3-uurimisküsimus-ja-hüpoteesid)
4. [Andmestik](#4-andmestik)
5. [Semantiline kontrollvoor](#5-semantiline-kontrollvoor)
6. [Masinõppe ülesanne ja tunnused](#6-masinõppe-ülesanne-ja-tunnused)
7. [Planeeritud tegevused](#7-planeeritud-tegevused)
8. [Mudelite õpetamine ja hindamine](#8-mudelite-õpetamine-ja-hindamine)
9. [Oodatav praktiline tulemus ja piirangud](#9-oodatav-praktiline-tulemus-ja-piirangud)
10. [Viidatud projektimaterjalid](#10-viidatud-projektimaterjalid)

## 1. Taust ja olemasolev süsteem

ERR2TEXT on ERR-i ja Jupiteri videote transkribeerimise süsteem, mille eesmärk
on luua ajastatud transkriptsioon „kes ütles mida”. Süsteem kasutab ERR-i
olemasolevaid VTT-subtiitreid ning audio põhjal tehtavat Pyannote'i
kõnelejate diariseerimist. Diariseerimine määrab anonüümsed kohalikud
kõnelejasildid, näiteks `SPEAKER_00` ja `SPEAKER_01`, ning seob need
transkriptsioonilõikudega ajalise kattuvuse järgi.

Tehniline töövoog on ERR-i URL → VTT ja audio → diariseerimine → muutumatu
`AUTOMATIC_DRAFT` koos tehniliste kandidaatidega → osalejate määramine →
tehniline ülevaatus → semantiline ülevaatus → `FINAL`. Algne automaatne
versioon ja Pyannote'i ajavahemikud säilivad muutmata; inimese parandused
tehakse eraldi tööversiooni.

Pärast diariseerimist materialiseerib süsteem `AUTOMATIC_DRAFT` versiooni ja
loob samal ajal tehnilised ülevaatuskandidaadid: näiteks ühes VTT-lõigus on
mitu kõnelejat, kõnelejapiir asub cue sees või omistus on vastuoluline. See
toimub enne osalejate määramist. Seejärel seob inimene kohalikud
kõnelejasildid tegelike osalejatega või märgib need tundmatuks. Tehnilises
ülevaatuses otsustab inimene iga kandidaadi kohta `ACCEPTED`, `MODIFIED` või
`REJECTED`.

Praegune kandidaatide valik on reeglipõhine. See tähendab, et süsteem võib
kuvada inimesele nii valehäireid kui ka jätta mõne päris probleemse lõigu
üldse märkamata. Uurimistöö keskendub sellele, kuidas kasutada varasemaid
inimotsuseid kandidaatide kasulikkuse ennustamiseks ja ülevaatusjärjekorra
parandamiseks.

Praegune kandidaatide tootmisreegel on konservatiivne, mudelivaba
lauselõpu-baseline. See kasutab VTT cue teksti, cue ajavahemikku ja Pyannote'i
intervalle. Reegel eristab muu hulgas mikrointervalle, cue servas paiknevaid
lühikesi lekkeid, mitme järjestikuse kõnelejaga lõike, võimalikke
kõnelejapiire ja kattuvat kõnet. Reegel ei muuda transkriptsiooni
automaatselt: isegi süsteemi pakutud poolitus jõustub alles inimese
`ACCEPTED` või `MODIFIED` otsuse järel.

## 2. Uurimisprobleem ja eesmärk

Inimese aeg on transkriptsiooni kvaliteedikontrollis piiratud ressurss.
Kõiki automaatselt loodud kandidaate ei ole sama oluline kohe kontrollida:
mõni on tõenäoliselt valehäire, mõni sisaldab lihtsat kinnitatavat parandust
ning mõni nõuab põhjalikumat inimese sekkumist.

Uurimistöö eesmärk on vähendada inimese ülevaatust ilma transkriptsiooni
sisulist selgust oluliselt halvendamata. Selleks koostatakse kolm seotud
mudelit.

1. **Tehnilise kandidaadi mudel** hindab iga Pyannote'i kandidaadi tõenäolist
   tulemust: `REJECTED`, muutmata `ACCEPTED` või inimese muudatust nõudev
   `MODIFIED`.
2. **Semantilise analüüsi vajaduse mudel** hindab pärast tehnilise vooru
   tulemust, kas transkriptsioonile tasub üldse käivitada semantiline analüüs.
3. **Semantilise kandidaadi mudel** järjestab juba loodud semantilised
   kandidaadid selle järgi, milliseid neist inimesele näidata.

Esimese mudeli binaarne kõrvalsiht on `correction_required`: `1` tähendab
`ACCEPTED` või `MODIFIED`, `0` tähendab `REJECTED`. Seda kasutatakse lihtsa
võrdluskatse jaoks; põhiülesanne on kolmeklassiline ennustus.

## 3. Uurimisküsimus ja hüpoteesid

**Uurimisküsimus:** kas olemasoleva tehnilise ülevaatuse ja hiljem kogutava
semantilise ülevaatuse andmete põhjal saab vähendada inimese kontrollitavate
kohtade arvu, säilitades oluliste vigade leidmise?

Hüpoteesid:

- **H1.** Pyannote'i ajastuste, kõneleja kattuvuste, segmendi pikkuse ja
  naaberlõikude põhjal õpetatud mudel eristab parandust vajavaid kandidaate
  tagasi lükatud kandidaatidest paremini kui juhuslik järjestus.
- **H2.** Tehnilise vooru inimotsuste ja paranduste põhjal saab ennustada,
  kas semantilise analüüsi käivitamine leiab tõenäoliselt veel olulisi vigu.
- **H3.** Pärast semantilise analüüsi käivitamist sisaldab semantilise
  kandidaadimudeli järgi järjestatud kandidaatide esimene osa suuremat osa
  inimese kinnitatud parandustest kui agendi algne järjestus.
Tekstiline AI-agent ei ole uurimistöö mudel. Selle ülesanne on pärast
tehnilist ülevaatust leida tekstist võimalikud kõnelejaomistuse vead, mida
Pyannote'i kandidaatide reeglid ei pakkunud.

## 4. Andmestik

### 4.1 Analüüsiühik ja märgend

Üks andmerida vastab ühele inimese poolt üle vaadatud transkriptsioonisegmendi
juhtumile. Esimeses voorus pärineb juhtum tehnilisest kandidaadist; teises
voorus võib see pärineda sisulisest auditist või juhuslikust kontrollvalimist.
Iga rida sisaldab segmendi aja- ja tekstiandmeid, diariseerimise
kõnelejaajavahemikke, kandidaadi või kontrolli päritolu ning inimese otsusest
tuletatud märgendit.

Algandmed pärinevad järgmistest süsteemi osadest:

| Andmeliik | Projekti andmestruktuur | Kasutus uurimistöös |
|---|---|---|
| Transkriptsioonisegment | `transcript_segments` | kestus, järjekord, tekst ja naaberlõigud |
| Kõneleja ajavahemik | `transcript_segment_speakers` | kattuvused, eri kõnelejate arv ja kindlus |
| Tehniline kandidaat | `review_candidates` | kandidaadi tüüp ja inimese lõppotsus |
| Inimese tehtud parandus | ülevaatusotsus ning seotud parandused | sihtmärgend ja juhtumi kontroll |

### 4.2 Olemasolev näidisandmestik

Tegelike andmete väljavõte on failis [log/test_data.md](../log/test_data.md).
Seal on 614 inimese lahendatud tehnilist kandidaati protsessidest `#14–#66`;
kasutatud on ainult failis [evaluation_data.md](evaluation_data.md)
analüüsiks lubatud kandidaatide ID-vahemikke. Tabel näitab iga kandidaadi
segmenti, pikkust, sõnade arvu, kõneleja-ajavahemike arvu, kõnelejate arvu,
maksimaalset kindlust, kandidaaditüüpi ja inimese otsust.

Näidistabel näitab eelkõige andmete kuju ja tunnuste arvutamist; lõplik
eksperimentaalne andmestik kogutakse suuremast hulgast eri saadetest. Enne
õpetamist kontrollitakse, et kasutatavatel ridadel oleks üheselt tõlgendatav
inimotsus.

### 4.3 Projekti andmekogu hetkeseis

Andmebaasi 2026-10-11 lugemispäringu järgi sisaldab projekt praegu 64
protsessi, millel on aktiivne automaatne transkriptsiooniversioon. Nendes on
kokku 35 400 segmenti ja 2 030 tehnilist ülevaatuskandidaati.

| Kandidaadi seis | Ridade arv |
|---|---:|
| `ACCEPTED` | 288 |
| `MODIFIED` | 279 |
| `REJECTED` | 135 |
| `PENDING` | 1 328 |
| Kokku | 2 030 |

Seega on praegu 702 lõpetatud inimese otsusega kandidaati. Need on esmane
allikas tunnuste väljavõtte, andmekvaliteedi kontrolli ja pilootmudeli jaoks.
`PENDING` olekus kandidaadid ei ole veel õppesildiga read. Vanemate või
teadaolevalt ebaselge otsuseloogikaga ridade kasutuskõlblikkust kontrollitakse
enne lõpliku treening- ja testvalimi moodustamist projekti
andmekasutusregistri järgi.

### 4.4 Kavandatav andmete kogumise järjestus

Semantilist analüüsi praeguses protsessis veel ei ole. Uurimistöö jaoks tuleb
selle hilisema lisamise järel koguda järgmised andmed. Allolev järjestus on
andmekogumise kirjeldus, mitte praeguse BPMN-i muutmise ülesanne.

1. **Tehniline ülevaatus.** Süsteem loob Pyannote'i ja VTT ajastuste põhjal
   kandidaadid. Inimene otsustab igaühe kohta `ACCEPTED`, `MODIFIED` või
   `REJECTED`.
2. **Semantiline ülevaatus.** AI-agent analüüsib pärast tehnilist vooru
   allesjäänud teksti. Ta pakub uusi kandidaate kohtades, kus dialoog või
   kõnelejaomistus ei ole sisuliselt usutav. Inimene teeb nende kohta samad
   otsused.
3. **Varjatud kontrollvalim.** Semantilisse ülevaatusloendisse lisatakse ka
   juhuslikud lõigud, mida kumbki kandidaatide leidmise viis ei pakkunud.
   Kasutajale kuvatakse need tavaliste semantiliste kandidaatidena.

Kandidaadi päritolu (`PYANNOTE_RULE`, `LLM_SEMANTIC_AUDIT` või
`RANDOM_CONTROL`) salvestatakse andmestikku, kuid seda kasutaja ei näe ja
seda ei anta põhimudeli sisendtunnuseks. Õppesilt tekib ainult inimese
otsusest.

Semantilise analüüsi andmetest tuleb säilitada vähemalt: analüüsitud
transkriptsiooni versioon; agendi mudel ja prompti versioon; kandidaadi
segment või segmendivahemik; põhjendus ja pakutud paranduse liik; kandidaadi
skor või järjestus; inimese otsus; ning tunnus, kas rida oli agendi leid või
`RANDOM_CONTROL`.

## 5. Semantiline kontrollvoor

Semantiline voor toimub pärast tehnilist ülevaatust ja enne `FINAL` versiooni.
Agendile antakse ülejäänud transkriptsioon koos ajastuse ja
kõnelejanimetustega. Ta otsib kohti, kus kõneleja vahetus või omistus muudaks
vestluse sisu ebaloomulikuks: näiteks vastus on omistatud küsijale, küsimus
ja vastus on sama kõneleja all või järjestikuste lõikude dialoog ei klapi.

Agent annab iga leiu kohta segmendi või lühikese segmendivahemiku, põhjenduse
ja võimaliku paranduse. See loob `LLM_SEMANTIC_AUDIT` kandidaadi. Inimene
vaatab lõigu koos audio või videoga üle ning valib `ACCEPTED`, `MODIFIED` või
`REJECTED`. Agent ei saa ise teksti ega kõnelejaomistust muuta.

Vooru eesmärk on mõõta tehnilise kandidaadigeneraatori katvust. Kui inimene
kinnitab semantilise kandidaadi, on see viga, mis jäi Pyannote'i-põhisest
esimesest voorust välja. Samasse ülevaatusjärjekorda lisatakse varjatult
juhuslikke lõike (`RANDOM_CONTROL`). Nende inimotsused annavad võrdluse,
kui palju vigu võivad kahe kandidaatide leidmise viisi vaateväljast siiski
välja jääda.

Semantilise kandidaadi mudel kasutab ainult tunnuseid, mis on olemas pärast
semantilise analüüsi käivitamist: agendi kandidaadiinfo, teksti- ja
vestluskontekst ning tehnilise vooru kokkuvõte. Agendi leitud kandidaat võib
seega olla selle mudeli sisend, sest agent käivitatakse ka tulevasel saatel
enne inimese semantilist ülevaatust.

## 6. Masinõppe ülesanded ja andmed

Tegemist on tabelandmetel põhinevate juhendatud klassifitseerimisülesannetega.
Iga mudel kasutab ainult tunnuseid, mis on selle otsuse tegemise hetkel
olemas.

Tehnilise kandidaadi mudeli tunnused on:

| Tunnus | Sisu |
|---|---|
| `duration_s` | transkriptsioonisegmendi kestus sekundites |
| `word_count` | segmendi sõnade arv |
| `speaker_span_count` | segmendiga kattuvate diariseeritud kõnelejaajavahemike arv |
| `distinct_speaker_count` | erinevate diariseeritud kõnelejate arv segmendis |
| `dominant_overlap_ratio` | domineeriva kõneleja ajalise kattuvuse osakaal |
| `second_overlap_ratio` | pikkuselt teise kõneleja kattuvuse osakaal |
| `max_speaker_confidence` | suurim diariseerimise usaldus segmenti katvates kõnelejaajavahemikes |
| `previous_dominant_same`, `next_dominant_same` | kas naaberlõigu domineeriv kõneleja on sama |
| `ends_sentence` | kas segment lõpeb lauselõpumärgiga |
| kandidaadireegli diagnostika | mikrointervall, servaleke, kattuv kõne ning tehnilise reegli tuvastatud tingimused |
| saate tasandi tunnused | osalejate koguarv, saate kestus ja kandidaatide tihedus |

Semantilise analüüsi vajaduse mudeli üks rida on üks transkriptsioon. Selle
sisend on tehnilise vooru kokkuvõte: tehniliste kandidaatide arv ja tüübid,
tehnilise kandidaadimudeli prognooside koondid ning juhul, kui inimene tegi
tehnilise vooru, tegelikud `ACCEPTED`/`MODIFIED`/`REJECTED` otsused ja
paranduste arv. Sihtmärgend on, kas semantilises voorus kinnitati vähemalt
üks oluline viga; vajadusel lisatakse eraldi vigade arv või olulisuse klass.

Semantilise kandidaadi mudeli üks rida on üks agendi või kontrollvalimi
kandidaat. Sisend on agendi põhjendus ja skoor, teksti- ning
vestluskontekst ja tehnilise vooru kokkuvõte. Sihtmärgend on inimese
`ACCEPTED`, `MODIFIED` või `REJECTED` otsus.

Identifikaatoreid ja inimese otsust mudeli sisendiks ei anta.

## 7. Planeeritud tegevused

1. Koostada korratav eksport tehniliste kandidaatide ja tehnilise vooru
   transkriptsioonitasandi kokkuvõtete jaoks.
2. Teha 702 juba lõpetatud kandidaadist andmekvaliteedi audit ning moodustada
   sellest esimene pilootvalim.
3. Koguda ja inimese poolt üle vaadata tehnilised kandidaadid mitmest eri
   saateformaadist, sealhulgas kahe osalejaga intervjuud, vestlusringid ja
   suurema osalejate arvuga saated.
4. Pärast semantilise analüüsi protsessisammu loomist koguda semantilised
   kandidaadid, nende agendipoolsed tunnused ja inimese otsused.
5. Lisada samasse teise vooru juhuslikud kontrolllõigud ja talletada nende
   tegelik päritolu ainult analüüsi jaoks.
6. Kontrollida andmete kvaliteeti, eemaldada puudulike otsustega read ning
   kirjeldada klasside ja kandidaatide allikate jaotust.
7. Moodustada kolme mudeli jaoks eraldi treening- ja testandmestikud.
8. Õpetada ja võrrelda tehnilise kandidaadi, semantilise vajaduse ning
   semantilise kandidaadi mudeleid.
9. Hinnata, kui palju inimesele näidatavaid kandidaate või terveid
   semantilisi analüüsivoore saab vähendada sama vigade leidmise juures.

## 8. Mudelite õpetamine ja hindamine

Kursuses käsitletud meetoditest kasutatakse vähemalt Naive Bayesi ja
otsustuspuud. Võrdluseks lisatakse võimalusel k-lähima-naabri meetod ning
juhuslik mets. Otsustuspuu eelis on tõlgendatavus: selle abil saab näidata,
millised tehnilised tunnused kandidaadi riski kõige enam mõjutavad.

Andmestik jagatakse saadete, mitte üksikute segmentide alusel. Näiteks võib
suurem osa saadetest olla treeningandmetes ning mitu tervet, varem nägemata
saadet testandmetes. See väldib olukorda, kus sama vestluse sarnased lõigud
annavad testis kunstlikult liiga hea tulemuse.

Mudeleid hinnatakse vähemalt järgmiste näitajatega:

- segiajamismaatriks;
- precision, recall ja F1-skoor;
- klasside tasakaalust tulenevalt precision–recall kõver või selle kokkuvõttev
  näitaja;
- top-*k* tabamismäär: kui suur osa tegelikest parandustest paikneb inimesele
  esimesena näidatavate kandidaatide hulgas;
- kandidaatide ülevaatustöö võimalik vähenemine sama soovitud recall'i juures.

Võrdluse baasiks on olemasolev reeglipõhine kandidaatide järjestus. Eesmärk ei
ole automaatselt muuta transkriptsiooni, vaid muuta inimese ülevaatustöö
tõhusamaks ja läbipaistvamaks.

## 9. Oodatav praktiline tulemus ja piirangud

Uurimistöö tulemus on mudel, mis annab kandidaadile riskiskoori või klasside
tõenäosused. Kasutajaliides saab selle põhjal näidata kõige tõenäolisemalt
parandust vajavaid kohti enne madalama väärtusega kandidaate. Inimene jääb
kõigi paranduste ja osalejate nimede kinnitajaks.

Esialgsed piirangud on järgmised:

- varane andmestik võib olla väike ja klasside järgi tasakaalust väljas;
- tulemused võivad erineda kahe osalejaga intervjuude ja mitme osalejaga
  paneelide vahel;
- AI-agendi tekstiline audit on kandidaatide leidmise vahend, mitte tõde;
- mudel ennustab ülevaatuse kasulikkust, mitte kõneleja isikut ega kogu
  diariseerimismudeli üldist täpsust.

Osalejate hääle põhjal nime pakkumine on projekti võimalik tulevane
arendussuund, kuid see ei kuulu käesoleva uurimistöö ülesande ega mudeli
koosseisu.

## 10. Viidatud projektimaterjalid

- [Lähteülesanne ja töövoog](task_to_solve.md)
- [MVP2.2 autoriteetne ülevaatusvoog ja kandidaatide reeglid](MVP2.2.md)
- [Andmete koosseis ja tegelike näidete tabel](../log/test_data.md)
- [Andmemudel](../db/erd.md)
- [Andmebaasi põhiskeem](../db/schema/001_core_schema.sql)
- [Osalejate ülevaatuse näidete valimise loogika](../backend/app/services/participant_review.py)
- [Kandidaatide ja kasutajaotsuste API-loogika](../backend/app/api/routes.py)
- [Varasemate mudelikatsete järeldused](lessons_learned.md)
- [Projekti andmekasutuse register](evaluation_data.md)
