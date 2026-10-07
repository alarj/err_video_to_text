# MVP2.2 — kõnelejate ja kõnelejapiiride veebipõhine ülevaatus

## Dokumendi roll

See dokument on MVP2.2 detailse lähteülesande ainus autoriteetne kirjeldus.
Üldine projekti lähteülesanne viitab sellele dokumendile ega korda siin olevaid
nõudeid.

MVP2.2 jätkab paigaldatud MVP2.1 API ja veebiliidese voogu. Eesmärk on muuta
automaatselt loodud transkriptsioon kasutaja kontrollitavaks: kasutaja seob
anonüümsed kõnelejad päris inimestega, vaatab süsteemi leitud kahtlased
kõnelejapiirid üle, parandab vajaduse korral teksti või omistust ning loob
kontrollitud lõppversiooni.

MVP2.2 ei tee vaikivaid automaatparandusi. Süsteem leiab kandidaate ja esitab
tõendeid, kuid parandatud transkriptsiooni sisu tekib kasutaja kinnitatud
otsustest.

## Põhivoog

```text
DIARIZING
    ↓
AUTOMATIC_DRAFT + ülevaatuskandidaadid
    ↓
WAITING_FOR_PARTICIPANTS
    ↓ kasutaja määrab SPEAKER_nn seosed
REVIEWED_DRAFT
    ↓
IN_REVIEW
    ↓ kasutaja kinnitab või parandab kandidaadid
FINAL
    ↓
FINISHED
```

Transkriptsiooniversioonide tähendus:

- `AUTOMATIC_DRAFT` on muutumatu automaatselt loodud transkriptsioon;
- `REVIEWED_DRAFT` on ühe kasutaja jooksvalt salvestatav tööversioon;
- `FINAL` on `REVIEWED_DRAFT` põhjal loodud muutumatu lõppversioon;
- `original.vtt`, algne `speakers.json`, `AUTOMATIC_DRAFT` ja varasemad
  `FINAL` versioonid säilivad muutmata.

Ühte transkriptsiooni töötleb korraga üks kasutaja. Mitme kasutaja samaaegne
muutmine, konfliktihaldus ja ülevaatusotsuste versiooniajalugu ei kuulu
MVP2.2 skoopi. `review_candidates` säilitab kandidaadi viimase oleku ja
kasutaja viimase otsuse.

## MVP2.2-0 — Reinsalu kontrollandmestik ja legacy-import

Varasema Reinsalu intervjuu töötluse failid asuvad väljaspool Git-i
`/srv/err2text` kataloogis, kuid vastav töö ei ole Oracle'i andmebaasis. Need
failid on MVP2.2 kõnelejavahetuste kontrollandmestik ja neid ei tohi üle
kirjutada.

Enne põhilahenduse ehitamist tuleb:

1. inventeerida Reinsalu töö algsed väljundid ja fikseerida nende SHA-256
   kontrollsummad;
2. eristada muutmata automaatväljundid varasematest käsitsi parandatud või
   katseteks loodud failidest;
3. luua idempotentne administratiivne legacy-import, mis registreerib töö
   andmebaasis ja materialiseerib algse tulemuse `AUTOMATIC_DRAFT` versioonina;
4. luua selle põhjal anonüümsed kõnelejad, segmendid, Pyannote'i seosed ja
   süsteemi leitud ülevaatuskandidaadid;
5. hoida varasemad inimese märgitud kõnelejapiirid eraldi kontrollmärgendusena,
   mitte kirjutada neid automaatselt `AUTOMATIC_DRAFT` sisse.

Import registreerib kandidaadifaili ja eraldi alignment-hindamisfaili SHA-256
ning genereeritud hindamisraporti `LEGACY_CONTROL_CANDIDATES_JSON`,
`LEGACY_CONTROL_ALIGNMENT_JSON` ja `LEGACY_CONTROL_EVALUATION_JSON`
artefaktidena. Hindamisraport säilitab baseline'i kandidaatide arvu, kattuvuse,
puhaste kontrollkohtade arvu ja võimaliku kattuvuse; kontrollfailid ei ole
baseline'i ennustuse sisend.
Legacy käsitsi muudetud Markdown ja `speaker_review.json` registreeritakse
vastavalt `LEGACY_MANUAL_TRANSCRIPT_MARKDOWN` ja
`LEGACY_MANUAL_SPEAKER_REVIEW_JSON` liigina. Tavapärase uue töö samanimelised
failid on automaatsed artefaktid.

Varasemad Reinsalu märked on suures osas tehtud transkriptsiooni
lugemiskonteksti põhjal. Neid kasutatakse kandidaadi leidmise ja veebivoo
kontrollimiseks, kuid vaieldavad kohad tuleb lõplikult kinnitada heli või video
järgi.

Kontrollandmestik peab võimaldama mõõta vähemalt:

- mitu varem märgitud vigast kõnelejapiiri leiti kandidaadina;
- mitu puhast kontrollkohta märgiti ekslikult kandidaadiks;
- mitu süsteemi ettepanekut kinnitati muutmata kujul;
- mitu ettepanekut tuli käsitsi parandada;
- millised vead jäid süsteemil leidmata;
- kas lõpptranskriptsioon vastab kasutaja kinnitatud piiridele.

## MVP2.2a — automaatse transkriptsiooni materialiseerimine

Pärast diariseerimise ja VTT-ga liitmise edukat lõppu peab worker ühe lühikese
andmebaasitransaktsiooniga:

1. lugema `transcript.json` ja `speakers.json`;
2. looma `AUTOMATIC_DRAFT` versiooni anonüümsed `SPEAKER_nn` kirjed;
3. kirjutama andmebaasi kõik transkriptsioonisegmendid;
4. kirjutama iga segmendi ühe või mitme Pyannote'i kõneleja ajavahemikud ja
   omistuskindluse;
5. leidma mudelivaba reegliga võimalikud kõnelejapiiride kandidaadid;
6. kirjutama kandidaadid koos põhjusega `review_candidates` tabelisse;
7. viima protsessi olekusse `WAITING_FOR_PARTICIPANTS`.

Failide lugemist, mudelite tööd ega muud pikka operatsiooni ei tehta avatud
andmebaasitransaktsiooni sees. Kui materialiseerimine ebaõnnestub, ei tohi
protsess jõuda eksitavalt kasutaja osalejate määramise etappi.

Kandidaatide leidmise esimene tootmisreegel on MVP1.3-s katsetatud odav
lauselõpu-baseline. See kasutab muutmata VTT teksti, cue ajavahemikku ja
Pyannote'i kõnelejaspane ning võib kandidaadi tekitada näiteks cue-sisese
kõnelejamuutuse, määramata omistuse või ebakindla omistuse tõttu. Reegel ei
muuda `AUTOMATIC_DRAFT` sisu.

Whisperi uut ASR-transkriptsiooni ega CTC forced alignment'i tavapärases
MVP2.2 töövoos ei käivitata. Varasemad katsed näitasid, et need ei ületanud
odavat baseline'i piisavalt, et õigustada CPU-kulu ja uut veaallikat. Neid võib
säilitada eraldi diagnostikavahendina.

## MVP2.2b — osalejate määramine video- või audiokontekstis

Oleku `WAITING_FOR_PARTICIPANTS` veebivaates seob kasutaja iga anonüümse
`SPEAKER_nn` kõneleja päris osaleja või tundmatu kõnelejaga.

Iga anonüümse kõneleja juures tuleb näidata mitut esinduslikku kohta saate eri
osadest. Näidiskohad valitakse eelistatult piisavalt pikkade, ühe aktiivse
kõneleja ja kõrge omistuskindlusega lõikude seast. Üksik juhuslik tekstilõik
ei ole osaleja määramiseks piisav.

Video puhul liigub mängija valitud ajamärgile ning kasutaja näeb ja kuuleb,
kes räägib. Video on kasutajale visuaalne taustainfo, mitte automaatse
näotuvastuse sisend. Näiteks saab kasutaja kinnitada:

```text
SPEAKER_00 → saatejuht
SPEAKER_01 → Urmas Reinsalu
```

Raadio või ainult audio puhul kasutatakse samu ajastatud näidisklippe ilma
videota. Kui inimest ei saa kindlalt tuvastada, on `UNKNOWN` normaalne tulemus,
mitte viga.

Kasutajal peab olema võimalik:

- valida olemasolev osaleja;
- lisada uus osaleja;
- määrata inimese nimi ja soovi korral roll;
- märkida kõneleja tundmatuks;
- salvestada osalejate määramine pooleli ka siis, kui osa
  `speaker_label`-eid on veel olekus `UNCONFIRMED`;
- märkida, et ühe `SPEAKER_nn` label'i all on tõenäoliselt mitu inimest.

Kui eri näidiskohad näitavad, et üks Pyannote'i label sisaldab mitut inimest,
ei kinnitata sellele kogu saate ulatuses üht isikut. Label'i üldmapping
märgitakse `UNKNOWN` ning vastuolulised kohad lähevad
ülevaatuskandidaatideks, et nende kõnelejad saaks hiljem segmendipõhiselt
parandada. Oleku `UNCONFIRMED` jätmine blokeerib õigustatult järgmisse etappi
liikumise.

Esimesel osalise või täieliku määramise salvestamisel:

1. luuakse üks `REVIEWED_DRAFT`, kui seda veel ei ole;
2. sinna kopeeritakse automaatse drafti segmendid ja kõnelejaseosed;
3. versioonipõhised anonüümsed label'id seotakse kasutaja praeguste
   valikutega;
4. sama `REVIEWED_DRAFT` versiooni uuendatakse järgmistel salvestamistel;
5. `AUTOMATIC_DRAFT` jääb muutmata.

Osaline salvestamine ei lõpeta tegevust `WAITING_FOR_PARTICIPANTS`. Kasutaja
võib jätta ühe või mitu label'it olekusse `UNCONFIRMED`, sulgeda vaate ning
jätkata hiljem samast `REVIEWED_DRAFT` versioonist.

Backend lubab protsessi ülevaatusetappi edasi ainult siis, kui iga
`speaker_label` vastab ühele järgmistest tingimustest:

- `mapping_status = 'CONFIRMED'` ja `participant_id` viitab olemasolevale
  `participants` kirjele;
- `mapping_status = 'UNKNOWN'` ja `participant_id IS NULL`.

Oleku `UNCONFIRMED` olemasolu blokeerib edasiliikumise. Sel juhul tagastab API
kinnitamata label'ite loendi, kuid osaline salvestus ise õnnestub. Seda reeglit
kontrollib backend; ainult veebiliidese nupu keelamisest ei piisa.

Kui kõik label'id on `CONFIRMED` või `UNKNOWN`, tehakse ühe lühikese
andmebaasitransaktsiooniga:

1. salvestatakse lõplikud osalejaseosed;
2. lõpetatakse `WAITING_FOR_PARTICIPANTS` tulemusega `OK`;
3. luuakse `IN_REVIEW` tegevus;
4. protsessi olekuks saab `IN_REVIEW`.

Näotuvastust, näoembeddinguid, nägude globaalset registrit ega eri saadete
vahelist biomeetrilist isikutuvastust MVP2.2-s ei kasutata.

## MVP2.2c — kõnelejapiiride ja süsteemiteadete ülevaatus

Ülevaatus peab olema järjestikuse transkriptsiooni vaade. Kasutaja näeb
kahtlase segmendi eelnevat ja järgnevat teksti, mitte kontekstita üksiklõiku.

Kandidaadi juures kuvatakse vähemalt:

- muutmata VTT tekst ja ajavahemik;
- praegune anonüümne või kinnitatud kõneleja;
- Pyannote'i kõnelejate ajavahemikud;
- süsteemi võimalik poolitusettepanek;
- kandidaadi leidmise põhjus;
- audio- või videopleier mõne sekundi pikkuse kontekstiga enne ja pärast
  kandidaati.

Kasutaja saab:

- kinnitada süsteemi pakutud poolituse;
- lükata ettepaneku tagasi ja säilitada segmendi muutmata kujul;
- valida tekstist teise poolituskoha;
- muuta ühe või mitme osa kõnelejat;
- parandada teksti;
- märkida segmendi või selle osa süsteemseks ekraaniteateks;
- jätta koha hilisemaks ülevaatuseks.

Kandidaadi olekud on:

- `PENDING` — vajab ülevaatust;
- `ACCEPTED` — süsteemi ettepanek kinnitati;
- `REJECTED` — ettepanek lükati tagasi;
- `MODIFIED` — kasutaja salvestas teistsuguse paranduse.

„Salvesta muudatused” uuendab sama `REVIEWED_DRAFT` versiooni. Parandatud
tekst, poolitused ja kõnelejaseosed salvestatakse transkriptsioonisegmentidesse
ja nende kõnelejaseostesse. Kandidaadi kirjesse ei dubleerita parandatud
transkriptsiooni ega looda eraldi otsuste ajalugu.

Audio või video taasesitus peab võimaluse korral kasutama juba allalaaditud
meediat. Sama faili ei laadita iga kandidaadi jaoks uuesti alla ega looda iga
koha kohta eraldi püsivat klippi. API peab toetama brauseris ajamärgile
liikumist ja vajalikku HTTP Range taasesitust. Enne teostamist tuleb kontrollida,
millist püsivat meediafaili praegune pipeline `/srv/err2text` all säilitab.

### Süsteemsed ekraaniteated

ERR-i VTT failides esineb teksti, mida keegi ei ütle, vaid mis kuvatakse
ekraanil subtiitrina. Kontrollitud failides on saate alguses näiteks:

```text
Järgnevale saatele kuvatakse automaatsubtiitrid.
Teksti automaatsel tuvastamisel võib esineda ebatäpsusi.
```

Igal transkriptsioonisegmendil on liik:

```text
SPEECH
SYSTEM_NOTICE
```

Süsteem võib tuntud ja täpselt sobiva ERR-i standardteate automaatselt
`SYSTEM_NOTICE` liigiks määrata. Ebakindlama mustri puhul loob süsteem ainult
soovituse või kandidaadi. Ainult segmendi asukoht saate alguses, määramata
kõneleja või vähene audio kattuvus ei ole kustutamiseks piisav tõend.

Kasutaja saab suvalise segmendi või pärast poolitamist ainult ühe selle osa
märkida liigiks `SYSTEM_NOTICE`. See katab ka saate keskel subtiitritena
kuvatavad tehnilised või toimetuslikud teated. Kasutaja saab ekslikult
tuvastatud süsteemiteate taastada liigiks `SPEECH`.

`SYSTEM_NOTICE` segment:

- ei vaja kõnelejat ega osalejat;
- ei lähe osalejate määramise näidisklippide hulka;
- ei tekita kõnelejapiiri ega madala omistuskindluse viga;
- ei lähe tulevikus RAG-i kellegi väljaütlemisena;
- säilitab oma teksti ja ajavahemiku;
- ei muuda ega kustuta vastavat cue'd failist `original.vtt`.

Inimloetavas transkriptsioonis kuvatakse saate keskel olev süsteemiteade
näiteks järgmiselt:

```markdown
*Ekraaniteade (00:12:31.200–00:12:34.000): Saade jätkub pärast pausi.*
```

Saate alguse standardteated võib ühendada transkriptsiooni päises üheks
ERR-i märkuseks. Neid ei kuvata `OMISTAMATA` kõneleja lausungina.

## MVP2.2d — lõppversioon ja kontroll

Kasutaja võib ülevaatuse ajal jätta kandidaadi olekusse `PENDING`, kuid
`FINAL` versiooni ei looda enne, kui kõik kohustuslikud kandidaadid on
käsitletud.

Lõpetamisel:

1. kontrollitakse, et nõutud osalejaseosed ja kandidaadid on käsitletud;
2. luuakse `REVIEWED_DRAFT` põhjal uus muutumatu `FINAL` versioon;
3. genereeritakse inimesele loetav Markdown ning masinloetav JSON;
4. registreeritakse lõppversiooni artefaktid ja nende kontrollsummad;
5. lõpetatakse `IN_REVIEW` tegevus;
6. protsess saab staatuse `FINISHED` ja lõpuaja.

Lõpp-Markdownis on kõneleja ja tekst samas tavateksti suuruses, kõneleja nimi
on rasvane ning ajavahemik kaldkirjas. Süsteemiteated eristatakse kõnest ega
esitata ühegi inimese lausungina.

## Andmemudeli täpsustused

Olemasolev ERD toetab transkriptsiooniversioone, versioonipõhiseid
speaker-label'eid ja ühe segmendi mitut kõnelejat. MVP2.2 jaoks tuleb
paigaldatud põhiskeemi muuta uue migratsiooniga, näiteks
`db/schema/002_mvp2_2_review.sql`; paigaldatud `001_core_schema.sql` faili ei
kasutata olemasoleva andmebaasi ümbertegemiseks.

Minimaalsed täpsustused:

- `transcript_segments.segment_type`, väärtustega `SPEECH` ja
  `SYSTEM_NOTICE`, vaikeväärtusega `SPEECH`;
- `transcript_segments.source_segment_id`, nullable viide
  `AUTOMATIC_DRAFT` algsegmendile, et ühe algsegmendi jagunemisel säiliks seos
  kõigi parandatud segmentidega;
- `transcript_participants.role` võib kuni kasutaja määramiseni olla `NULL`;
- `transcript_participants.participant_id` jääb nullable-väljaks;
- ühe segmendi mitu kõnelejat säilitatakse tabelis
  `transcript_segment_speakers`.

`review_candidates` viitab algsele automaatse drafti segmendile ja hoiab
kandidaadi viimast olekut ning otsust. Eraldi `review_decisions` tabelit,
kohustuslikke `proposed_boundary_second` välju, näotunnuseid ega
speaker-embeddinguid ei lisata.

## API kavand

MVP2.2 minimaalne API peab võimaldama:

```text
GET  /jobs/{id}/review
PUT  /jobs/{id}/participants
PUT  /jobs/{id}/review-draft
POST /jobs/{id}/finalize
GET  /jobs/{id}/media
```

Täpseid marsruudinimesid võib rakendamisel ühtlustada olemasoleva API-ga, kuid
vastutus peab jääma samaks.

MVP2.2b osalejate määramise teostuses kasutatakse järgmisi marsruute:

```text
GET  /participants
POST /participants
GET  /jobs/{id}/participant-review
PUT  /jobs/{id}/participant-review
```

Osaline `PUT` salvestab sama `REVIEWED_DRAFT` versiooni, kuid ei muuda protsessi
olekut. `confirm = true` viib protsessi olekusse `IN_REVIEW` ainult siis, kui
kõik anonüümsed kõnelejad on `CONFIRMED` või `UNKNOWN`.

`GET /review` tagastab vähemalt:

- protsessi, allika ja valitud meedia metadata;
- automaatse ning olemasolu korral ülevaatusdrafti versiooni;
- anonüümsed kõnelejad ja nende osalejaseosed;
- järjestatud transkriptsioonisegmendid ja nende liigi;
- ülevaatuskandidaadid, põhjused ja viimase oleku;
- ülevaatuse edenemise.

`PUT /jobs/{id}/participant-review` kinnitab versioonipõhised osalejaseosed
ning alustab vajaduse korral `REVIEWED_DRAFT` ja `IN_REVIEW` etapi.

`PUT /review-draft` salvestab ühe atomaarse tegevusena kandidaadiotsused ning
nendest tulenevad asendussegmendid. Pikka kasutaja ülevaatust ei hoita avatud
andmebaasitransaktsioonis.

`POST /finalize` kontrollib eeltingimusi ning loob muutumatu lõppversiooni ja
selle artefaktid.

`GET /media` võimaldab olemasoleva audio või video taasesitust ajamärgilt,
sealhulgas brauseri Range-päringuid. See ei tohi võimaldada suvalise serveri
failitee lugemist.

## Vastuvõtukriteeriumid

MVP2.2 on valmis, kui vähemalt järgmised tingimused on täidetud:

- uue töö automaatne transkriptsioon materialiseeritakse andmebaasi
  segmentide, speaker-label'ite ja kõnelejaseostena;
- Reinsalu failipõhine kontrolltöö on muutmata algfailidest idempotentselt
  imporditav ja veebis avatav;
- `SPEAKER_nn` label'eid saab video- või audiokonteksti abil siduda päris
  osaleja või `UNKNOWN` väärtusega;
- ühe label'i all mitme inimese kahtlus ei sunni kogu label'ile vale isikut;
- süsteemi leitud kõnelejapiirid kuvatakse pideva teksti kontekstis;
- kasutaja saab kandidaadi kinnitada, tagasi lükata või käsitsi parandada;
- kasutaja saab segmendi või selle osa märkida `SYSTEM_NOTICE` liigiks ning
  taastada liigiks `SPEECH`;
- video või audio avaneb kandidaadi ja näidislõigu ajamärgilt;
- salvestatud muudatused säilivad pärast lehe uuesti avamist;
- `AUTOMATIC_DRAFT`, `original.vtt` ja algne `speakers.json` ei muutu;
- `FINAL` loomine on blokeeritud, kuni kohustuslikud kandidaadid on
  käsitletud;
- lõpp-JSON ja lõpp-Markdown kajastavad kinnitatud osalejaid, poolitusi,
  tekstiparandusi ning eristatud ekraaniteateid;
- mudelivaba kandidaadireegli tulemus mõõdetakse Reinsalu vigaste ja puhaste
  kontrollkohtade suhtes;
- tavapärane MVP2.2 voog ei käivita Whisperit, forced alignment'i,
  näotuvastust ega näoembeddingute loomist;
- olemasolevad MVP2.1 URL-i lahendamise, järjekorra, tööolekute ja artefaktide
  funktsioonid jäävad tööle.

## Teadlikult skoobist väljas

MVP2.2 ei sisalda:

- autentimist ega kasutajapõhiseid õigusi;
- sama transkriptsiooni mitme kasutaja samaaegset muutmist;
- ülevaatusotsuste versiooniajalugu;
- Pyannote'i, Whisperi või muu mudeli ümberõpet kasutaja parandustest;
- vaikivat automaatset kõnelejapiiride parandamist;
- automaatset näotuvastust või eri saadete vahelist biomeetrilist
  isikutuvastust;
- speaker-embeddingute püsivat registrit;
- RAG-i ega semantilist otsingut.

Automaatset active-speaker videoanalüüsi võib hiljem eraldi katsena hinnata,
kuid MVP2.2 osalejate tuvastamise põhimeetod on kasutaja tehtud seos
ajastatud video- või audiokonteksti põhjal.
