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

Iga anonüümse kõneleja kaardil näidatakse kolme ajaliselt hajutatud
esinduslikku kohta saate eri osadest. Näidiskohad valitakse eelistatult
piisavalt pikkade, ühe aktiivse kõneleja ja kõrge omistuskindlusega lõikude
seast. Kui sobivaid lõike on vähem kui kolm, kuvatakse kõik sobivad lõigud;
puuduvaid näiteid ei asendata mitme kõnelejaga või `SYSTEM_NOTICE`
segmentidega. Üksik juhuslik tekstilõik ei ole osaleja määramiseks piisav.

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

### MVP2.2b veebivaade ja meedia taasesitus

Veebivaates on iga `SPEAKER_nn` kohta eraldi kaart, mis sisaldab:

- anonüümset kõnelejalabel'it;
- olemasoleva osaleja valikut;
- uue osaleja lisamist;
- vabatahtlikku rolli;
- `UNCONFIRMED` ja `UNKNOWN` valikut;
- kuni kolme näidislõigu teksti ning nähtavat algus- ja lõpuaega;
- video- või audiomängijat.

Näidise valimisel liigub mängija `start_second` ajale, alustab taasesitust ja
peatub `end_second` ajal. Brauserites, mis toetavad Media Source Extensions'it,
kasutatakse vendordatud ja versioonitud `hls.js` teeki. Safari puhul kasutatakse
native HLS-i fallback'i. Mängija laadimisviga või HLS-toe puudumine kuvatakse
kasutajale kaardil; viga ei tohi vaikides jätta muljet, et näidis mängis.

Meedia URL võetakse valitud `media_item` kirjest. MVP2.2b ei loo iga näidise
jaoks eraldi faili ega laadi sama saadet serverisse uuesti. Kui edasises etapis
võetakse kasutusele serveris säilitatav meediafail, võib sama UI kasutada API
vahendatud Range-taasesitust.

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

Poolelioleva määramise vaate uuesti avamisel loetakse valikud olemasolevast
`REVIEWED_DRAFT` versioonist, mitte algse `AUTOMATIC_DRAFT` seostest. Nii
taastuvad varem valitud osalejad, rollid ning `UNKNOWN` olekud.

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
Kahtlased kohad märgitakse terviktekstis nähtavalt. Kasutaja saab liikuda
eelmise ja järgmise kandidaadi juurde ning näeb ülevaatuse edenemist ja
lahendamata kandidaatide arvu.

Kandidaadi juures kuvatakse vähemalt:

- muutmata VTT tekst ja ajavahemik;
- praegune anonüümne või kinnitatud kõneleja;
- Pyannote'i kõnelejate ajavahemikud;
- süsteemi võimalik poolitusettepanek;
- kandidaadi leidmise põhjus;
- audio- või videopleier mõne sekundi pikkuse kontekstiga enne ja pärast
  kandidaati.

### Kõnelejaintervallide tähendus ja cue poolitamine

Ühel VTT cue'l või transkriptsioonisegmendil võib olla mitu
`transcript_segment_speakers` kirjet. Need kirjed kirjeldavad Pyannote'i
kõnelejaintervalle koos algus- ja lõpuajaga; need ei tähenda automaatselt, et
kõik nimetatud inimesed ütlesid kogu segmendi teksti koos või samal ajal.

Kui sama `transcript_participant_id` esineb ühe segmendi juures mitmes
intervallis, kuvatakse inimese nimi segmendi ees ainult üks kord. Intervallid
säilitatakse tehnilise tõendina, kuid kasutajale ei kuvata näiteks
`Urmas Reinsalu, Urmas Reinsalu, Urmas Reinsalu`.

Kui ühe segmendi juures esineb mitu erinevat kõnelejat ja nende intervallid on
ajas järjestikused, käsitletakse seda võimaliku cue-sisese kõnelejamuutusena,
mitte kooskõnena. Ülevaatevaade ei tohi sellisel juhul kuvada kõiki nimesid
kogu teksti ühise prefiksina, näiteks:

```text
Urmas Reinsalu, saatejuht: kogu algne cue tekst
```

Selle asemel näitab UI:

- algset muutmata VTT cue teksti ja ajavahemikku;
- iga Pyannote'i intervalli kõnelejat, algus- ja lõpuaega;
- intervallide põhjal hinnatud kõnelejapiiri;
- tekstis võimalikku poolituskohta;
- vasaku ja parema tekstiosa praegust või pakutud kõnelejat.

Pyannote'i ajapiir ei määra üksinda täpset tekstisõna, mille juures vahetus
toimus. Süsteem võib teha poolitusettepaneku ajapiiri, kirjavahemärkide ja
teksti struktuuri põhjal, kuid kasutaja kinnitab kuulamise või video abil
täpse tekstilise poolituskoha ja mõlema osa kõneleja.

Näiteks algne cue:

```text
Urmas Reinsalu: ka meie õpetajatest. | No mis see alampalganumber
```

salvestatakse pärast kinnitamist kahe järjestikuse segmendina:

```text
Urmas Reinsalu: ka meie õpetajatest.
saatejuht: No mis see alampalganumber
```

Poolitamisel:

1. algne `AUTOMATIC_DRAFT` segment jääb muutmata;
2. `REVIEWED_DRAFT` algsegment asendatakse kahe või enama järjestatud
   segmendiga;
3. kõigil tekkinud segmentidel säilib sama `source_segment_id` viide algsele
   automaatsele segmendile;
4. igale uuele segmendile luuakse ainult selle tekstiosa kõnelejaseos või
   kõnelejaseosed;
5. tekstiosade ajapiirid arvutatakse kinnitatud kõnelejapiiri järgi ja peavad
   jääma algse segmendi ajavahemikku;
6. kandidaadi olekuks saab `ACCEPTED`, kui kinnitati süsteemi pakutud jaotus,
   või `MODIFIED`, kui kasutaja valis teise piiri, teksti või kõneleja;
7. tööversiooni Markdownis ja JSON-is kuvatakse tekkinud osad eraldi
   lausungitena, mitte mitme nimega ühise lausungina.

Mitut erinevat kõnelejat võib ühe segmendi juures säilitada ainult siis, kui
nende intervallid päriselt ajaliselt kattuvad ja heli või video kinnitab
kattuva kõne. Ka sel juhul ei järeldata, et mõlemad ütlesid kogu segmendi
teksti. UI märgib koha selgelt kattuvaks kõneks ning võimaldab võimaluse korral
teksti osade kaupa omistada. Kui sõnu ei saa usaldusväärselt eristada, jääb
tekst kattuva kõne märgendiga ülevaatusse, mitte ei esitata seda mõlema inimese
ühise tsitaadina.

Kui allpool kirjeldatud filtreerimise järel jääb segmenti vähemalt kaks
sisulist kõneleja-label'it, peab süsteem looma sellele ühe `PENDING`
ülevaatuskandidaadi. Alla lävendi jääv mikrointervall või lühike tekstilise
tõendita servaleke säilitatakse diagnostikas, kuid ei tekita üksinda
ülevaatuskohustust. Ühtegi segmenti ei tohi lõpptulemusse viia mitme nimega
ühe lausungina: kohustuslik kandidaat tuleb enne lõpptulemust lahendada ning
diagnostilise kõrval-label'i korral kuvatakse lausungi ees ainult domineeriv
kõneleja.

### Kohustuslikud kandidaadireeglid

MVP1.3 mudelivaba lauselõpu-baseline oli teadlikult kõrge täpsuse ja väikese
valepositiivide arvu jaoks konservatiivne. See loob kandidaadi ainult siis,
kui cue sees on täpselt üks Pyannote'i kõnelejamuutus ning selle lähedal leidub
sobiv lauselõpp. Baseline on kasulik tekstilise poolituskoha pakkuja, kuid see
ei tohi olla ainus värav, mis otsustab, kas mitme kõnelejaga segment vajab
ülevaatust.

Kandidaatide loomisel kasutatakse allpool toodud täpset järjestust. Lävendid
on MVP2.2 esialgsed tootmiskonstandid ning need peavad olema koodis nimega
konstandid ja testidega kaetud:

```text
MICRO_SPEAKER_SECONDS = 0.100
EDGE_ONLY_SPEAKER_SECONDS = 0.500
EDGE_TOUCH_SECONDS = 0.050
SENTENCE_BOUNDARY_WINDOW_SECONDS = 2.000
```

Enne reeglite rakendamist:

1. lõigatakse kõik Pyannote'i intervallid cue ajavahemikku;
2. eemaldatakse null- või negatiivse kestusega kattuvused;
3. säilitatakse kõik positiivse kestusega toorintervallid diagnostikas;
4. summeeritakse iga `speaker_label`-i cue sisse jääv kogukestus;
5. sama label'i mitu intervalli deduplikeeritakse ainult nime kuvamisel, mitte
   ei kustutata tehnilistest andmetest;
6. domineerivaks label'iks loetakse suurima kogukestusega label ning teisi
   käsitletakse kõrval-label'itena.

Seejärel kehtivad järgmised reeglid:

1. `SYSTEM_NOTICE` segment ei tekita kõnelejapiiri kandidaati.
2. Kui cue's on ainult üks erinev label, ei tekita sama label'i korduvad
   intervallid kandidaati.
3. Kõrval-label, mille summeeritud kestus cue sees on alla 0,100 sekundi, on
   `DIARIZATION_MICROSPAN`. See säilitatakse diagnostikas, kuid ei tekita
   üksinda kohustuslikku ülevaatuskandidaati. Selline intervall on liiga lühike,
   et sisaldada iseseisvat kõnevooru.
4. Kõrval-label on `edge-only`, kui kõik selle intervallid algavad kuni 0,050
   sekundit cue algusest või lõpevad kuni 0,050 sekundit cue lõpust ning sellel
   pole cue sisemuses eraldi intervalli.
5. Kui kõigi kõrval-label'ite kogukestus on alla 0,500 sekundi ja need on ainult
   cue servas, ei teki kohustuslikku kandidaati pelgalt kahe label'i
   olemasolust. Juhtum säilib diagnostilise servalekkena.
6. Eelmise punkti servajuhtum muutub siiski `SPEAKER_BOUNDARY` kandidaadiks,
   kui tekstis leidub enne viimast sõna lauselõpp ning selle hinnanguline aeg
   jääb kuni 2,000 sekundi kaugusele toorintervallide kõnelejamuutusest.
   Serva lähedus ei tohi blokeerida tekstiga toetatud lühikest vooru nagu
   „Nii”, „Jah” või „Ei”.
7. Kui vähemalt kahe sisulise label'i intervallid on järjestikused ja
   lauselõpu-baseline leiab sobiva tekstipiiri, kasutatakse kandidaaditüüpi
   `SPEAKER_BOUNDARY` ning UI kuvab süsteemi poolitusettepaneku.
8. Kui vähemalt kahe sisulise label'i intervallid on järjestikused, vähemalt
   üks kõrval-label ei ole lühike servaleke ja usaldusväärset tekstipiiri ei
   leita, kasutatakse kandidaaditüüpi `MULTI_SPEAKER_SEGMENT`. UI ei mõtle
   poolituskohta välja, vaid palub kasutajal see kuulamise põhjal valida.
9. Kui kõrval-label esineb ainult cue servas vähemalt 0,500 sekundit, kuid
   tekstiline poolitusettepanek puudub, kasutatakse kandidaaditüüpi
   `SPEAKER_ATTRIBUTION_CONFLICT`. See tähendab, et kontrollida tuleb nii
   võimalikku cue-sisest vahetust kui ka võimalust, et terve cue on omistatud
   valele inimesele; UI ei eelda automaatselt poolitamist.
10. Kui vähemalt kahe sisulise label'i intervallid ajaliselt kattuvad,
    kasutatakse kandidaaditüüpi `OVERLAPPING_SPEECH`. Kattuvust ei esitata
    automaatselt mõlema inimese ühise tsitaadina.
11. Ühe algsegmendi kohta peab olema üks aktiivne sisuline
    ülevaatuskandidaat. Kui segment vastab mitmele reeglile, kasutatakse
    prioriteeti `OVERLAPPING_SPEECH` → `SPEAKER_BOUNDARY` →
    `SPEAKER_ATTRIBUTION_CONFLICT` → `MULTI_SPEAKER_SEGMENT`. Põhjuses ja
    diagnostikas säilitatakse kõik tuvastatud tunnused; samale segmendile ei
    looda UI-s dubleerivaid `PENDING` ridu.

`SPEAKER_BOUNDARY`, `MULTI_SPEAKER_SEGMENT`,
`SPEAKER_ATTRIBUTION_CONFLICT` ja `OVERLAPPING_SPEECH` on enne `FINAL`
versiooni loomist käsitlemist vajavad kandidaadid. `DIARIZATION_MICROSPAN` ja
lühike tekstilise tõendita servaleke on diagnostilised tunnused, mitte eraldi
kohustuslikud kandidaadid. Toorintervallid jäävad alles, et lävendeid saaks
hiljem mõõtmise põhjal muuta.

Osalejate määramise järel võivad mitu erinevat anonüümset label'it osutuda
samaks päris inimeseks. Sellisel juhul kandidaati automaatselt ei kustutata ega
märgita lahendatuks: kasutaja võib heli põhjal kinnitada, et tegelikku
kõnelejamuutust ei olnud, ja valida `REJECTED`. Nii säilib automaatse analüüsi
päritolu ja otsus ei teki vaikimisi.

### Olemasoleva Reinsalu protsessi kandidaatide täiendamine

Protsessi `#13` diariseerimist ei käivitata uute reeglite pärast uuesti.
Puuduvad kandidaadid leitakse olemasoleva `AUTOMATIC_DRAFT` segmentide ja
`transcript_segment_speakers` intervallide põhjal.

Enne andmebaasi kirjutamist tehakse ainult lugemisega kuivkäik, mis raporteerib
vähemalt:

- olemasolevate aktiivsete kandidaatide arvu;
- mitme erineva `speaker_label`-iga `SPEECH` segmentide arvu;
- mitu neist on juba kandidaadid;
- mitu uut `MULTI_SPEAKER_SEGMENT` kandidaati lisanduks;
- mitu uut `SPEAKER_ATTRIBUTION_CONFLICT` kandidaati lisanduks;
- mitu uut `OVERLAPPING_SPEECH` kandidaati lisanduks;
- mitu segmenti jäeti välja alla 0,100 sekundi mikrointervalli tõttu;
- mitu segmenti jäeti kohustuslikust ülevaatusest välja alla 0,500 sekundi
  tekstilise tõendita servalekkena;
- mitu segmenti sisaldab ainult sama kõneleja korduvaid intervalle ja seetõttu
  kandidaadiks ei lisandu;
- milliste segmentide olemasolev kandidaadiotsus või staatus tuleb muutmata
  säilitada.

Esimene laiendatud kuivkäik, milles iga kahe label'iga segment muudeti
kandidaadiks, andis 37 uut kandidaati. Selle raport
`log/mvp2_2_candidate_dry_run_process_13.md` näitas, et:

- 24 kandidaadis oli väiksema kõneleja kogukestus alla 0,500 sekundi;
- 17 kandidaadis oli see alla 0,250 sekundi;
- 10 kandidaadis oli see alla 0,100 sekundi;
- 24 kandidaadis esines väiksem kõneleja ainult cue servas.

Seetõttu ei tohi neid 37 kirjet muutmata kujul andmebaasi lisada. Uus kuivkäik
tehakse käesoleva täpsustatud reegli alusel.

Reinsalu kontrollandmestikus peab uus reegel säilitama vähemalt teadaolevad
olulised juhud:

- segment 537: „vaates. Miks, kui …”;
- segment 578: „kindlustunne. Nii”;
- segment 630: „päästjate palka? Ma arvan,”;
- segment 682: võimalik terve segmendi vale kõneleja;
- segment 746: võimalik terve segmendi vale kõneleja.

Samal ajal ei tohi üksnes tehnilise mikrointervalli tõttu kohustuslikuks
kandidaadiks muutuda näiteks segmendid 427, 452, 456 ja 674. Segmendid 415,
424, 428 ja 803 on servalekke kontrolljuhud: need võivad kandidaadiks saada
ainult siis, kui lisaks servaintervallile leidub eespool kirjeldatud tekstiline
tõend.

Täiendamine peab olema idempotentne: korduskäivitus ei loo duplikaate, ei
muuda olemasolevaid `ACCEPTED`, `REJECTED` või `MODIFIED` otsuseid ega kirjuta
ümber `AUTOMATIC_DRAFT` sisu. Rakendamine tehakse alles pärast kuivkäigu
tulemuste kontrollimist.

Kasutaja saab:

- kinnitada süsteemi pakutud poolituse;
- lükata ettepaneku tagasi ja säilitada segmendi muutmata kujul;
- valida tekstist teise poolituskoha;
- muuta ühe või mitme osa kõnelejat;
- parandada teksti;
- märkida segmendi või selle osa süsteemseks ekraaniteateks;
- avada parandamiseks ka kandidaadile vahetult eelneva või järgneva segmendi,
  kui süsteem leidis probleemi lähedalt, kuid tegelik viga paikneb naaberlõigus;
- jätta koha hilisemaks ülevaatuseks.

### Kandidaadi naaberlõigu parandamine

Kandidaadi juures kuvatavad eelmine ja järgmine segment ei ole ainult
lugemiskontekst. Kasutaja peab saama valida parandamiseks kandidaadi enda,
vahetult eelmise segmendi või vahetult järgmise segmendi. Valitud segmendis
peab saama muuta kõnelejat ja teksti ning vajaduse korral jagada segment
kaheks. Ühe kandidaadi käsitlemisel võib muuta nii kandidaati kui ka ühte või
mõlemat naabersegmenti.

Naabersegment ei muutu selle tõttu ülevaatuskandidaadiks ja talle ei anta
`ACCEPTED`, `REJECTED` ega `MODIFIED` kandidaadiolekut. Käsitsi parandatud
naabersegment märgitakse `USER_MODIFIED`. Selle paranduse juures säilitatakse
vähemalt:

- paranduse käivitanud kandidaadi ID (`trigger_candidate_id`);
- asukoht kandidaadi suhtes: `PREVIOUS` või `NEXT`;
- muudatuse liik või liigid: `SPEAKER_REASSIGNMENT`, `TEXT_EDIT`, `SPLIT`
  ja/või `SYSTEM_NOTICE`.

`USER_MODIFIED` kirjeldab segmendi paranduse päritolu, mitte kandidaadi
otsust. Nimetust ega olekut `ADJACENT_SEGMENT_EDIT` ei kasutata.

### Korduv poolitus juba poolitatud segmendis

Üks kandidaat võib vajada rohkem kui ühte poolitust. Pärast esimese poolituse
kinnitamist peab kasutaja saama valida konkreetse `REVIEWED_DRAFT`-i alamsegmendi
ja selle uuesti poolitada. Päring sisaldab selleks `reviewed_segment_id` väärtust;
see ei ole naaberlõigu `target_segment_id` alias ega tohi kasutada
`TRANSCRIPT_SEGMENT_MODIFICATIONS` tabelit.

Korduv poolitus muudab ainult valitud alamsegmenti. Kõik sama algsegmendi teised
juba loodud alamsegmendid, nende tekst, kõnelejad, ajad ja metadata jäävad
muutmata. Uus alamsegment säilitab sama `source_segment_id` ning poolituse
metadata seotakse kandidaadi enda otsusega.

Korduva poolituse järel jääb kandidaat üle vaadatud olekusse; kui tulemus erineb
süsteemi ettepanekust, on kandidaadi otsus `MODIFIED`, mitte uus `PENDING`.

### Segmentide nummerdamine poolitamisel

`transcript_segments.segment_number` on transkriptsiooniversiooni sees unikaalne
ka lõpetatud ehk soft-delete'itud segmentide korral. Lõpetatud segmendi
`segment_number` jääb ajaloo osaks: seda segmenti ei taasaktiveerita, selle
numbrit ei muudeta ja sama numbrit ei anta uuele segmendile.

Iga poolitus, sealhulgas varem ühendatud segmendi uuesti poolitamine, peab looma
uue parempoolse segmendi uue reana. Enne nummerdamist lukustatakse asjaomane
transkriptsiooniversioon ning leitakse selle versiooni suurim `segment_number`
kõigi ridade seast, sõltumata `end_date` väärtusest. Uus number ja vajaduse
korral järgnevate aktiivsete segmentide uued numbrid võetakse sellest
ajaloolisest maksimumist kõrgemast vahemikust.

Kui poolitatavale segmendile järgnevad aktiivsed segmendid, nummerdatakse
aktiivne järelsaba samas tehingus ümber nii, et lõplik
`ORDER BY segment_number` säilitab transkriptsiooni ajalise järjekorra:

1. poolituse vasak osa säilitab olemasoleva rea ja numbri;
2. uus parem osa saab väärtuse `senine_maximum + 1`;
3. varem järgnenud aktiivsed segmendid saavad nende senises järjekorras
   väärtused `senine_maximum + 2`, `senine_maximum + 3` jne;
4. lõpetatud segmente ja nende numbreid ei muudeta.

Nummerdusse võivad seetõttu jääda augud ning numbrid ei pea algama uuesti ühest
ega olema järjestikused. `segment_number` ei ole püsiv segmendiidentifikaator;
seosed kasutavad `transcript_segments.id` väärtust. Pelk ajutine suure nihke
lisamine ja hilisem vana vahemiku lähedale tagasi nihutamine ei ole lubatud,
sest see võib uuesti põrkuda lõpetatud rea reserveeritud numbriga.

Nummerdamine, uue segmendi loomine, teksti ja aegade jaotamine,
kõnelejaseoste loomine ning metadata salvestamine tehakse ühe tehinguna.
Versiooni lukk peab välistama sama versiooni samaaegsed poolitused. Unikaalsus-,
valideerimis- või salvestusvea korral tehakse täielik rollback, sealhulgas
taastatakse aktiivsete segmentide varasem nummerdus.

Kohustuslik regressioonijuhtum on järgmine: segment poolitatakse, poolitus
eemaldatakse merge'iga nii, et üks alamsegment jääb soft-delete'ituks, ning
aktiivne segment poolitatakse uuesti. Test peab kinnitama, et:

- uus alamsegment ei kasuta ühegi aktiivse ega lõpetatud rea numbrit;
- soft-delete'itud rida, selle number ja ajalugu ei muutu;
- aktiivsete segmentide nummerdus vastab endiselt ajalisele järjekorrale;
- tekst, ajad, `source_segment_id`, kõnelejaseosed ja metadata on õiged;
- sama tulemuse uut alamsegmenti saab veel kord poolitada;
- vea korral ei jää andmebaasi osaliselt muudetud nummerdust ega uusi ridu.

Kandidaadi olek määratakse ainult süsteemi pakutud kandidaadi enda kohta:

- kui süsteemi ettepanek oli vale ja kandidaat jäi muutmata, on kandidaat
  `REJECTED` ka siis, kui kasutaja parandas selle kõrval naabersegmendi;
- kui kasutaja muutis kandidaadi enda teksti, kõnelejat või poolitust, on
  kandidaat `MODIFIED`;
- kui süsteemi ettepanek kinnitati muutmata kujul, on kandidaat `ACCEPTED`;
- kui muudeti nii kandidaati kui ka naabersegmenti, on kandidaat `MODIFIED`
  ning naabersegment eraldi `USER_MODIFIED`.

Näiteks võib kandidaat olla `REJECTED`, kuid tema järgmine segment
`USER_MODIFIED`, asukohaga `NEXT` ja muudatuse liigiga `SPLIT`. Sellest peab
hiljem olema üheselt järeldatav, et süsteem leidis probleemi lähedalt, kuid
tegeliku vea täpse asukoha leidis kasutaja. See eristus on vajalik
kandidaadialgoritmi analüüsiks ja võimalike õppeandmete koostamiseks.

Kandidaadi olekud on:

- `PENDING` — vajab ülevaatust;
- `ACCEPTED` — süsteemi ettepanek kinnitati;
- `REJECTED` — ettepanek lükati tagasi;
- `MODIFIED` — kasutaja salvestas teistsuguse paranduse.

Ülevaatuse UI värviloogika ei väljenda otsuse sisu, vaid ülevaatuse lõpetatust:

- `PENDING` on kollase taustaga — kasutaja pole kandidaati veel käsitlenud;
- `ACCEPTED`, `REJECTED` ja `MODIFIED` on rohelise taustaga — kasutaja on
  kandidaadi üle vaadanud ja otsus on salvestatud.

Kõigi nelja oleku puhul jäävad kasutajaliidese paigutus, nuppude arv ja
kasutaja tegevuste üldine vorm samaks. Olekut eristab tekstiline märgis ning
ülevaatamata/ülevaadatud taustavärv; roheline ei tähenda, et süsteemi ettepanek
oli õige, vaid üksnes seda, et kandidaat on läbi vaadatud.

„Salvesta muudatused” uuendab sama `REVIEWED_DRAFT` versiooni. Parandatud
tekst, poolitused ja kõnelejaseosed salvestatakse transkriptsioonisegmentidesse
ja nende kõnelejaseostesse. Kandidaadi kirjesse ei dubleerita parandatud
transkriptsiooni ega looda eraldi otsuste ajalugu.

Audio või video taasesitus peab võimaluse korral kasutama juba allalaaditud
meediat. Sama faili ei laadita iga kandidaadi jaoks uuesti alla ega looda iga
koha kohta eraldi püsivat klippi. API peab toetama brauseris ajamärgile
liikumist ja vajalikku HTTP Range taasesitust. Enne teostamist tuleb kontrollida,
millist püsivat meediafaili praegune pipeline `/srv/err2text` all säilitab.

Kui sobivat püsivat kohalikku meediafaili ei ole, kasutatakse sama valitud HLS
allikat ja sama `hls.js`/Safari fallback'i, mida kasutatakse MVP2.2b
näidislõikudes. Kandidaadi taasesitus algab mõni sekund enne probleemset kohta
ja lõpeb mõni sekund pärast seda; kandidaadi täpne ajavahemik kuvatakse eraldi.

### Allalaaditav tööversioon

Transkriptsiooni Markdown ja JSON ei teki ainult protsessi lõpetamisel.
Kasutajal peab olema igal hetkel võimalik alla laadida parim parajasti olemas
olev tulemus:

- enne kasutaja esimest salvestust on allalaaditav `AUTOMATIC_DRAFT` tulemus;
- pärast `REVIEWED_DRAFT` loomist on allalaaditav selle viimane salvestatud
  seis;
- pärast lõpetamist on vaikimisi allalaaditav muutumatu `FINAL` tulemus.

Pärast iga edukat osalejate, kandidaadi, teksti, poolituse, kõnelejaseose või
segmendiliigi salvestamist genereeritakse commit'itud `REVIEWED_DRAFT` seisust
uuesti inimesele loetav Markdown ja masinloetav JSON. Need registreeritakse
selgelt tööversiooni artefaktidena, näiteks `REVIEWED_DRAFT_MD` ja
`REVIEWED_DRAFT_JSON`. Allalaadimine ei kinnita ülevaatust, ei muuda kandidaadi
olekut ega vii protsessi `FINISHED` olekusse.

Ühel `REVIEWED_DRAFT` versioonil on korraga üks aktiivne Markdown ja üks
aktiivne JSON. Uus genereerimine asendab aktiivse tööartefakti või lõpetab
eelmise artefaktikirje kehtivuse; eraldi kasutajaotsuste või tööartefaktide
versiooniajalugu MVP2.2 ei loo. Artefakti genereerimine toimub pärast
andmebaasimuudatuse edukat commit'i, mitte pika failitööna avatud
andmebaasitransaktsiooni sees. Genereerimisvea korral jääb kasutaja muudatus
andmebaasi alles, UI näitab, et allalaaditav tööfail on aegunud või puudub, ning
genereerimist peab saama ohutult korrata.

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
3. genereeritakse `FINAL` versioonist uuesti inimesele loetav Markdown ning
   masinloetav JSON;
4. registreeritakse need tööversiooni artefaktidest eraldi muutumatute
   lõppartefaktidena koos kontrollsummadega;
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

Käsitsi parandatud naabersegmendi kohta peab andmemudel säilitama märgendi
`USER_MODIFIED`, paranduse käivitanud kandidaadi viite, suhtelise asukoha
`PREVIOUS` või `NEXT` ning tehtud muudatuse liigi või liigid. Need andmed võib
teostada segmendi muutmismetadata või eraldi segmendiparanduse seosena, kuid
need ei ole uus kandidaadiolek ega ülevaatusotsuste versiooniajalugu. Kui
parandus jagab ühe naabersegmendi mitmeks, peab sama päritolu olema jälgitav
kõigi tekkinud `REVIEWED_DRAFT` segmentide juures.

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
andmebaasitransaktsioonis. Pärast edukat salvestust genereeritakse
`REVIEWED_DRAFT` Markdown ja JSON uuesti.

Naaberlõigu parandamisel sisaldab sama päring `target_segment_id` ja
`relative_position` väärtust (`PREVIOUS` või `NEXT`). Sellisel juhul rakendatakse
muudatus ainult `REVIEWED_DRAFT` naaberlõigule, salvestatakse `USER_MODIFIED`
metadata ning kandidaadi enda otsust ei muudeta.

### Salvestatud naaberlõigu poolituse eemaldamine

`split_at = null` tähendab tavalisel naaberlõigu salvestamisel ainult valitud
`target_segment_id` segmendi muutmist. See ei sulge ega ühenda sama
`source_segment_id` teisi aktiivseid alamsegmente.

Salvestatud poolituse eemaldamine on eraldi eksplitsiitne tegevus, mille jaoks
saadetakse `merge_segment_group = true`. Seda lippu võib kasutada ainult
aktiivse kandidaadi lubatud `PREVIOUS` või `NEXT` naabergrupi puhul ning koos
`split_at` väärtusega seda kasutada ei tohi.

Merge'i kõneleja valik saadetakse eraldi väljal `speaker_assignment`: väärtus
`PARTICIPANT` kasutab valideeritud `left_transcript_participant_id` väärtust,
`UNKNOWN` kasutab reviewed-versiooni tundmatu kõneleja seost ning puuduv väärtus
lubab rakendada süsteemi fallback-järjekorda. `SYSTEM_NOTICE` jääb eraldi
`segment_type` väärtuseks ega tähenda tundmatut kõnelejat.

Merge'i korral kontrollitakse, et kõik grupi aktiivsed osad kuuluvad samasse
aktiivsesse `REVIEWED_DRAFT` versiooni, neil on sama algne segment ja nad on
transkriptsiooni järjekorras üheselt järjestatavad. Grupi esimene aktiivne osa
jääb segmendi identiteediks; ülejäänud osad ja nende aktiivsed kõnelejaseosed
ning muutmismetadata lõpetatakse soft-delete'iga. Tekst säilitatakse kõigist
osadest nende järjekorras ning ühendatud ajavahemik katab kogu grupi.

Ühendatud aktiivsele segmendile jääb üks kõneleja: eelistatult grupi esimese
aktiivse osa kõneleja, selle puudumisel algse automaatsegmendi domineeriv
kõneleja ning viimase võimalusena `UNKNOWN`. Teiste osade kõnelejaseoseid ei
kanta aktiivsele segmendile, kuid need jäävad lõpetatud alamsegmentidesse,
muutmismetadatasse ja muutmata `AUTOMATIC_DRAFT` versiooni. Kasutaja võib
ühendatud segmendi kõnelejat muuta või selle uuesti poolitada.

Lokaalse, veel salvestamata poolituse eemaldamine toimub ainult kasutajaliideses
ning ei tee API-päringut. Kõik salvestatud merge'i muudatused tehakse ühe
andmebaasitehinguna; valideerimis- või salvestusvea korral tehakse täielik
rollback. Kandidaadi enda otsus ning kandidaadi poolitamise ja korduvpoolitamise
loogika jäävad naaberlõigu merge'ist sõltumatuks.

Poolitamisel ei tohi uue rea `segment_number` korduda ka lõpetatud
(soft-delete'itud) ajaloolise rea numbriga. Aktiivne transkriptsiooniversioon
lukustatakse tehingu ajaks, uus parempoolne osa saab kogu versiooni ajaloolisest
`MAX(segment_number)` väärtusest järgmise numbri ning aktiivne kronoloogiline
järelsaba nummerdatakse samast värskest vahemikust edasi. Lõpetatud ajaloolisi
ridu ei muudeta ega taasaktiveerita.

Praeguses skeemis ei lisata merge'i jaoks uut `change_type` väärtust ega tehta
andmebaasimigratsiooni. Ühendamisel lõpetatakse varasemate alamsegmentide
aktiivne `SPLIT`-metadata ning säilitatakse ülejäänud ajalugu lõpetatud
kirjetena; kasutaja tekstimuudatus ja kõneleja muutus märgitakse olemasolevate
metadata-tüüpidega.

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
- automaatse või ülevaatuse tööversiooni Markdown ja JSON on igal hetkel
  allalaaditavad ning kajastavad viimast edukalt salvestatud seisu;
- tööversiooni allalaadimine ei lõpeta ülevaatust ega loo `FINAL` versiooni;
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
