# Analüüsi- ja õppeandmete register

## 1. Dokumendi eesmärk ja kasutamine

Dokumendi eesmärk on vältida vigaste või ebaselgete otsusesiltidega protsesside
sattumist formaalsesse analüüsi ja mudeli õppeandmetesse. Register säilitab iga
protsessi või kandidaadivahemiku kohta kasutusotsuse ning konkreetse põhjuse,
miks andmeid tohib või ei tohi kasutada.

Dokument on protsessipõhine lubade register. Seda peab saama kasutada ja
uuendada ilma vestlusajaloo või varasema projektitausta teadmiseta. See ei ole
käituslogi ega katsetulemuste detailne aruanne.

Formaalses analüüsis võib kasutada ka kontrollitud `IN_REVIEW` protsessi või
selgelt piiritletud kandidaadivahemikku, kui analüüsitavad otsusesildid on
usaldusväärsed ja vahemik on käesolevas registris lubatud. **Mudeli
õppeandmestikku lähevad ainult valideeritud `FINAL` protsessid.**

Registri väärtused on binaarsed:

- `Jah` — andmeid tohib selles veerus nimetatud eesmärgil kasutada;
- `Ei` — andmeid ei tohi selles veerus nimetatud eesmärgil kasutada.

Kui piirang puudutab ainult osa protsessist, on see osa kandidaadi-ID-dega
eraldi real. Põhjuse veerg ütleb konkreetselt, miks väärtus on `Ei`.

### Otsustamise reeglid

Protsessi või kandidaadivahemiku veerg märgitakse `Jah` ainult järgmiste
reeglite alusel:

- **Analüüsiks:** inimene on hinnatavad kandidaadid üle vaadanud,
  analüüsitavad otsusesildid salvestati kehtiva otsuseloogikaga ja kasutatav
  vahemik on kandidaadi-ID-dega üheselt piiritletud. `FINAL` versioon ei ole
  nõutav. Kui mõne kandidaadi tegelikku otsuseliiki ei saa tõendada, on selle
  vahemiku väärtus `Ei`.
- **Õpetamiseks:** protsess on `FINISHED`, olemas on valideeritud muutumatu
  `FINAL` versioon, inimene on märgendid sisuliselt üle vaadanud ning
  teadaolev viga ei moonuta õpetamisel kasutatavat sihtmärki. Teadmata päritolu
  või tagantjärele oletatud märgend tähendab `Ei`.
- **Dokumentatsiooniks:** juhtumi algandmed, teadaolev piirang ja kasutusviis on
  kirjeldatud. Vigane protsess võib olla dokumentatsiooniks `Jah`, kui seda ei
  esitata korrektse analüüsi- või õppeandmestikuna.

Kui nõutav tõend puudub või info on vastuoluline, märgitakse `Ei`. Puuduvat
otsuseliiki ei taastata segmendi kuju, ajatempli ega kasutaja oletatava tegevuse
põhjal.

### Registri uuendamine

Registrit uuendab projekti omanik või tema volitatud agent järgmises korras:

1. Tuvasta protsessi ID, saate pealkiri ja hinnatavate kandidaatide ID-d.
2. Analüüsiloa puhul kontrolli kandidaadi olekut, otsuseliiki ja
   otsuseloogika versiooni. Õpetamisloa puhul kontrolli lisaks aktiivset
   `FINAL` versiooni ning selle valideerimisartefakti ID-d ja SHA-256
   kontrollsummat. Ära kasuta tõendina ainult veebivaates nähtavat teksti.
3. Kontrolli, millise koodi ja UI otsuseloogikaga märgendid salvestati ning kas
   protsessi kohta on teada andmekvaliteedi intsidente.
4. Kui piirang puudutab ainult osa kandidaatidest, lisa sellele vahemikule
   eraldi rida. Ära üldista ühe vahemiku luba kogu protsessile.
5. Täida kõik kolm kasutusveergu ainult väärtustega `Jah` või `Ei`, lisa
   valideerimisalus ja kirjuta põhjusesse kontrollitav fakt.
6. Salvesta dokumendimuudatus tavalise Git-commit'iga. Veebirakendus seda
   dokumenti automaatselt ei muuda.

`finalize` valideerib andmed enne `FINAL` versiooni ja `FINISHED` oleku
loomist. Eduka valideerimise tõend on `FINAL` versiooniga seotud
valideerimisartefakt ja kontrollsumma. Ebaõnnestunud valideerimise korral jääb
protsess `IN_REVIEW` olekusse ja õpetamise väärtus on `Ei`. Analüüsiluba võib
jääda `Jah` ainult registris nimetatud kontrollitud kandidaadivahemikule.

Enne analüüsi kontrollib andmestiku koostaja, et registris on analüüsiveerus
`Jah` ja kasutatavad kandidaadi-ID-d jäävad lubatud vahemikku. Enne õpetamist
kontrollib ta lisaks, et registris nimetatud `FINAL` versioon ja kontrollsumma
vastavad valideerimisartefaktile. Täielikku inimese ülevaatust ei korrata.

Uue `FINAL` versiooni korral tehakse uus valideerimine ja registrikirje
vaadatakse uuesti üle. Vana valideerimisotsus ei kandu uuele versioonile üle.

## 2. Veergude tähendus

| Veerg | `Jah` tähendab |
|---|---|
| Analüüsiks | Andmeid võib kasutada kvantitatiivses kandidaadi- ja otsusetüüpide analüüsis. |
| Õpetamiseks | Otsuseid või parandatud segmente võib kasutada masinõppe märgenditena. |
| Dokumentatsiooniks | Juhtumit võib kasutada näite, veakirjelduse või regressioonitesti alusena. |

## 3. Protsesside register

Registri olek on kontrollitud 2026-10-09.

| Protsess või andmevahemik | Protsessi olek | `FINAL` versioon | Analüüsiks | Õpetamiseks | Dokumentatsiooniks | Valideerimisalus | Põhjus |
|---|---|---:|---|---|---|---|---|
| `#13` — „Reinsalu: Isamaa eesmärk on pöörata 2027. aasta kevadel uus lehekülg” | `FINISHED` | olemas | Ei | Ei | Jah | Analüüsi- ja õppekasutuseks puudub usaldusväärne otsuseliikide valideerimisalus | Kõik 34 ülevaatusotsust salvestati vana UI tõttu `MODIFIED`-na. Tegelikku `ACCEPTED`, `REJECTED` ja `MODIFIED` jaotust ei saa taastada. |
| `#14`, kandidaadid `130–170` — „Herem alustab ministriametit kaitseväe laoarvestuse analüüsiga” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 41 kandidaati on lahendatud; 17 `ACCEPTED`, 16 `MODIFIED`, 8 `REJECTED`; `status`, `decision` ja `decision_at` on täielikud ning omavahel kooskõlas | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. Teadaolevad UI ja naabersegmentide piirangud on dokumenteeritud failis `docs/todo.md`. |
| `#15`, kandidaadid `171–178` — „Pevkur mürsutehingust: toode pole kasutu vaid ebakvaliteetne” | `IN_REVIEW` | puudub | Ei | Ei | Jah | Puudub | Otsused salvestati enne otsuseliikide parandust `MODIFIED`-na. Struktuurne tulemus on nähtav, kuid otsuse tegelik põhjus pole usaldusväärne. |
| `#15`, kandidaadid `179–221` — sama saade | `IN_REVIEW` | puudub | Jah | Ei | Jah | Inimese ülevaatus lõpetatud; 23 `ACCEPTED`, 10 `MODIFIED` ja 10 `REJECTED` otsust salvestati parandatud otsuseloogikaga | Vahemik sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks ei sobi enne valideeritud `FINAL` versiooni loomist. |
| `#16`, kandidaadid `222–249` — „Haridusminister: me veel ei tea mitu õpilast jääb koolikohata” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 28 kandidaati on lahendatud; 12 `ACCEPTED`, 8 `MODIFIED`, 8 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. |
| `#17` — „Vahtras: ma ei ole midagi valesti teinud” | `IN_REVIEW` | puudub | Ei | Ei | Jah | Puudub | Kõik 46 ülevaatusotsust salvestati vana UI tõttu `MODIFIED`-na. Otsuseliikide statistika ja nende põhjal loodud õppesildid pole usaldusväärsed. |
| `#18`, kandidaadid `296–334` — „Kusti Salm: Dataseliga lepingu sõlmimisele eelnes pikk eeltöö” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 39 kandidaati on lahendatud; 10 `ACCEPTED`, 14 `MODIFIED`, 15 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. |
| `#19`, kandidaadid `335–373` — „Kaimo Kuusk: kui minister mind ametist vabastab siis nii see on” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 39 kandidaati on lahendatud; 28 `ACCEPTED`, 7 `MODIFIED`, 4 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. |
| `#20`, kandidaadid `374–395` — „Perling: Tallinna linnavalitsus viljeleb sama poliitikat mis Reformierakond” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 22 kandidaati on lahendatud; 18 `ACCEPTED`, 2 `MODIFIED`, 2 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. Lahendatud kandidaadi süsteemiettepaneku API-kuvamise piirang on dokumenteeritud failis `docs/todo.md`. |
| `#21`, kandidaadid `396–406` — „Kõlvart: ei saa luua illusiooni et uue valitsusega paraneb kõik aastaga” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 11 kandidaati on lahendatud; 5 `ACCEPTED`, 1 `MODIFIED`, 5 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. |
| `#22`, kandidaadid `407–444` — „Anton ja Peek: kliimaseaduse eelnõu ei lahenda ühtegi probleemi” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 38 kandidaati on lahendatud; 32 `ACCEPTED`, 4 `MODIFIED`, 2 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. Naabersegmendi korduvpoolitamise piirang ja workaround on dokumenteeritud failis `docs/todo.md`. |
| `#23`, kandidaadid `445–462` — „Reinsalu koalitsioonist Reformierakonnaga: minu jaoks on see väga keeruline” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Kõik 18 kandidaati on lahendatud; 10 `ACCEPTED`, 3 `MODIFIED`, 5 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. |
| `#24`, kandidaadid `463–468` — „Simson EL-i ja Venemaa läbirääkija otsingutest: Kallas ei ole see tase” | `IN_REVIEW` | puudub | Jah | Ei | Jah | Vahemiku kõik 6 kandidaati on lahendatud; 4 `ACCEPTED`, 1 `MODIFIED`, 1 `REJECTED`; otsuseväljad on täielikud ja kooskõlalised | Ainult nimetatud vahemik sobib kandidaadi- ja otsusetüüpide analüüsiks. Õpetamiseks puudub valideeritud `FINAL` versioon. |
| `#24`, kandidaadid `469–504` — sama saade | `IN_REVIEW` | puudub | Ei | Ei | Jah | Kõik 36 kandidaati on olekus `PENDING` | Ootel kandidaate ei kasutata otsusetüüpide analüüsis ega õpetamisel. Neid võib kasutada poolelioleva ülevaatuse dokumenteerimiseks. |

## 4. Kasutuspiirangud

- `Dokumentatsiooniks: Jah` ei anna õigust kasutada sama rida analüüsi- või
  õppeandmestikus.
- `#13` ja `#17` sobivad paranduste, veatüüpide ja regressioonijuhtumite
  kirjeldamiseks, kuid mitte otsuseliikide osakaalude arvutamiseks.
- `#15` kandidaatide `171–178` puhul võib dokumenteerida tekkinud poolitusi ja
  ümberomistamisi, kuid neid ei loeta `ACCEPTED`, `REJECTED` või `MODIFIED`
  statistika sisse.
- Protsessist `#24` võib analüüsida ainult kandidaate `463–468`; kandidaadid
  `469–504` on endiselt üle vaatamata.
- Sama intervjuud ei kasutata korraga mudeli õpetamiseks ja selle mudeli
  sõltumatuks hindamiseks.
