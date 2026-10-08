# Hiljem lahendamist vajavad probleemid

## 2026-10-08 — poolitatud naabersegmendi teist osa ei saa uuesti poolitada

- **Probleem:** kandidaadi eelmist või järgmist naabersegmenti saab ühe korra
  poolitada, kuid tekkinud teist alamsegmenti ei saa sama kandidaadi kaudu
  uuesti poolitada. Pärast esimest poolitamist käsitleb loogilise naabri
  otsing naabrina ainult algse segmendi esimest aktiivset osa. Teine osa on
  küll sama `source_segment_id` järglane, kuid pole enam kandidaadi otsene
  `PREVIOUS` või `NEXT` sihtsegment.
- **Kontrollitud näide:** protsessi `#22` kandidaadi `407` järgmine segment
  `8179` poolitati segmentideks `8179` („Peek,”, Johannes Tralla) ja `8589`
  („tere õhtust. Tervist. No kliimaseadust on aastaid tehtud.”, Allar Peek).
  Mõlemad segmendid ja nende muutmismetadata on õigesti salvestatud:
  mõlemal on `SPLIT`, segmendil `8589` lisaks `SPEAKER_REASSIGNMENT`.
  Kandidaadi loogiliseks `NEXT`-naabriks jääb aga ainult `8179`, mistõttu
  segmenti `8589` ei saa samas vaates uuesti poolitada.
- **Mõju:** ühest naabersegmendist kolme või enama osa moodustamine sõltub
  poolituste järjekorrast. Salvestatud andmed ei ole vigased, kuid tavapärane
  eest tahapoole poolitamine võib jätta järgmise vajaliku alamsegmendi UI-s
  muutmatuks.
- **Ajutine workaround:** kui naabersegment tuleb jagada rohkem kui kaheks,
  teha poolitused tagant ette. Kõigepealt eraldada viimane soovitud osa ning
  seejärel poolitada allesjäänud esimene osa järgmise varasema piiri kohalt.
  Nii jääb uuesti poolitatav osa kandidaadi otseseks loogiliseks naabriks.
- **Koht koodis:** `frontend_dist/assets/app.js`, naabersegmendi aktiveerimine;
  `backend/app/api/routes.py`, loogiliste naabrite leidmine ja
  `save_review_candidate()` naabersihtmärgi valideerimine.
- **Võimalik lahendus:** käsitleda poolitatud naabersegmendi kõiki aktiivseid
  järglasi eraldi redigeeritavate osadena ning lubada
  `target_segment_id`-ga valida neist konkreetne osa. API peab kontrollima, et
  siht kuulub algse lubatud naabersegmendi aktiivsesse järglaste gruppi;
  kandidaadist kaugemale jäävaid sõltumatuid segmente ei tohi selle kaudu
  muuta.
- **Leitud:** 2026-10-08, protsessi `#22` kandidaadi `407` järgmise
  naabersegmendi korduvpoolitamisel.
- **Lahendatud:** Ei — kasutada dokumenteeritud tagant-ette poolitamise
  workaround'i.

## 2026-10-08 — lahendatud kandidaadi süsteemiettepanek kaob API vastusest

- **Probleem:** ülevaatuse API arvutab kandidaadi `proposed_*` väljad aktiivse
  `REVIEWED_DRAFT`-i esimese alamsegmendi põhjal. Pärast kandidaadi lahendamist
  võib algne segment olla poolitatud ning esimene alamsegment ei sisalda enam
  algse `AUTOMATIC_DRAFT`-i teksti ja kõnelejaintervalle. Seetõttu võivad
  lahendatud kandidaadi `proposed_boundary_second`, `proposed_split_at`,
  `proposed_left_speaker` ja `proposed_right_speaker` olla API vastuses
  tühjad, kuigi kandidaadil oli algselt süsteemi poolitusettepanek.
- **Mõju:** salvestatud `ACCEPTED`, `REJECTED` ja `MODIFIED` staatused jäävad
  õigeks, kuid API vastusest ei saa pärast lahendamist usaldusväärselt
  taastada ega auditeerida algset süsteemiettepanekut. See raskendab
  diagnostikat, kasutajaliidese selgitusi ning süsteemiettepaneku ja inimese
  lõpptulemuse hilisemat võrdlemist.
- **Koht koodis:** `backend/app/api/routes.py`, ülevaatuse vastust koostav
  loogika funktsioonis `get_review()`, kus `suggest_sentence_split()` saab
  sisendiks `reviewed_group[0]` põhjal valitud segmendi.
- **Võimalik lahendus:** arvutada ja tagastada süsteemiettepanek alati
  kandidaadi algsest `AUTOMATIC_DRAFT` segmendist või säilitada ettepaneku
  snapshot kandidaadi loomisel. `REVIEWED_DRAFT` jääb inimese tulemuse
  kuvamiseks; seda ei kasutata ajaloolise süsteemiettepaneku
  rekonstrueerimiseks.
- **Leitud:** 2026-10-08, protsessi `#20` kandidaatide staatuste kontrollimisel.
- **Lahendatud:** Ei — staatused on korrektsed, kuid API diagnostikaväljund on
  puudulik.

## 2026-10-08 — UI kuvab esimese, mitte domineeriva kõneleja

- **Probleem:** mitme kõnelejaintervalliga segmendi juures kasutab ülevaatuse
  UI rea kõnelejanimeks ajaliselt esimese intervalli kõnelejat. Lühike
  Pyannote'i servaleke võib seetõttu jätta mulje, et kogu segment kuulub valele
  inimesele. Näiteks protsessi `#14` segmendis `4294` on Martin Heremi
  intervall ainult 0,141 sekundit, kuid Johannes Tralla räägib ligikaudu 2,826
  sekundit; UI kuvab sellest hoolimata Martin Heremi nime.
- **Mõju:** kasutaja näeb eksitavat kõnelejaomistust ka juhul, kui süsteem jättis
  lühikese servaintervalli teadlikult kandidaadiks tegemata ja segmendi
  domineeriv kõneleja on õige. See võib põhjustada tarbetuid parandusi või
  jätta mulje kandidaadialgoritmi veast. Toorintervallid ise ei ole selle vea
  tõttu valed ja neid ei tule kuvamisparanduse käigus kustutada.
- **Koht koodis:** `frontend_dist/assets/app.js`, ülevaatuse segmentide
  renderdamine funktsioonis `renderReview()` ning kõnelejaintervallidest nime
  valiv loogika.
- **Võimalik lahendus:** summeerida segmendi aktiivsete intervallide kestus
  kõneleja kaupa ning kuvada rea ees suurima kogukestusega kõneleja. Võrdse
  kogukestuse puhuks tuleb määrata deterministlik reegel. Algseid
  kõnelejaintervalle ja `AUTOMATIC_DRAFT` sisu ei muudeta.
- **Leitud:** 2026-10-08
- **Lahendatud:** Ei — teadaolev kuvamisviga, lahendamine on edasi lükatud.

## 2026-10-08 — mittekandidaadist kontekstisegmendi parandamine on piiratud

- **Probleem:** kasutaja saab ülevaatuses muuta kandidaati ning selle vahetut
  eelmist või järgmist segmenti, kuid mitte kandidaadist kaugemal asuvat
  mittekandidaatsegmenti. Näiteks protsessi `#14` kandidaadi `141` juures ei
  saa kasutaja tervenisti Johannes Trallale määrata segmenti `4294`, sest see
  asub kandidaadist kaks segmenti eespool.
- **Mõju:** inimene võib audio või video põhjal leida ülevaateaknas tegeliku
  kõnelejaomistusvea, kuid ei saa seda samas töövoos parandada. Eriti puudutab
  see segmente, mida kandidaadialgoritm ei märgi, sest teise kõneleja lühike
  intervall klassifitseeritakse põhjendatult tehniliseks servalekkeks.
- **Koht koodis:** `frontend_dist/assets/app.js`, ülevaatuse kontekstisegmendi
  aktiveerimine; `backend/app/api/routes.py`, funktsioon
  `save_review_candidate()`; tabel `transcript_segment_modifications`, kus
  suhteline asukoht on praegu piiratud väärtustega `PREVIOUS` ja `NEXT`.
- **Võimalik lahendus:** võimaldada parandada suvalist aktiivset
  `REVIEWED_DRAFT` segmenti, mida kasutaja ülevaateaknas näeb. API peab saama
  täpse `target_segment_id`, kontrollima segmendi kuulumist samasse protsessi
  ja aktiivsesse tööversiooni ning salvestama paranduse märgendiga
  `USER_MODIFIED`. Säilitada tuleb paranduse käivitanud kandidaat ja arvuline
  suhteline nihe, näiteks `relative_offset = -2`; kandidaadi enda otsus jääb
  muutmata. Eraldi väärtusi nagu `PREVIOUS_2` ei lisata.
- **Leitud:** 2026-10-08
- **Lahendatud:** Ei — teadaolev funktsionaalne piirang, lahendamine on edasi
  lükatud.

## 2026-10-08 — kõnelejaseoste ajaväärtuste võrdlus

- **Probleem:** `transcript_segment_speakers` olemasolevat seost otsitakse
  praegu ajaväärtuste tolerantsiga. See väldib `float`-teisenduse tõttu tekkivat
  vale duplikaat-INSERT-i, kuid ei kasuta kanonilist normaliseeritud
  kümnendväärtust.
- **Mõju:** poolituse salvestamine võib sõltuda valitud tolerantsist ning
  erineva täpsusega ajaväärtuste korral võib tekkida liiga lai või liiga kitsas
  vaste.
- **Koht koodis:**
  `backend/app/api/routes.py`, funktsioon `save_review_candidate()`, sisemine
  funktsioon `restore_or_insert_speaker()`.
- **Võimalik lahendus:** määrata ajaväärtuste kanoniline täpsus andmemudeli ja
  pipeline'i põhjal, teisendada väärtused `Decimal`-iks ning võrrelda mõlemat
  väärtust sama normaliseeritud kümnendtäpsusega (näiteks millisekunditeni).
  SQL-i võrdlus peab kasutama sama normaliseerimist, mitte suvalist tolerantsi.
- **Leitud:** 2026-10-08
- **Lahendatud:** 2026-10-08 — ajaväärtused normaliseeritakse `NUMBER(12,3)` täpsusele enne võrdlust, deduplikatsiooni ja INSERT-i; kandidaadi 219 unikaalsuskonflikt ei tohiks enam tekkida.
