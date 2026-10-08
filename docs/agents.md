# Projekti tööreeglid

## 1. Charset ja failivorming

- Kõik kood, konfiguratsioon ja dokumentatsioon peavad olema UTF-8 kodeeringus.
- Uute failide loomisel ja olemasolevate failide muutmisel tuleb säilitada UTF-8.
- Kui failis esineb kodeeringuprobleem, tuleb see käsitleda veana ja parandada juurpõhjus, mitte peita sümptomit.

## 2. Enne muudatusi loe läbi allikad

- Enne sisuliste muudatuste kavandamist tuleb läbi lugeda kõik dokumendid, mis puudutavad muudetavat ala.
- Kui ülesanne puudutab arhitektuuri, andmemudelit, tööde järjekorda, deploy’d, koormust või API integratsiooni, kasuta allolevaid viiteid esmase tõeallikana.
- Kui dokumentatsiooni ja koodi vahel on vastuolu, ära eelda vaikimisi, et dokumentatsioon on õige. Tuvasta vastuolu, kirjelda seda detailselt ja küsi üle.
- Tegutse edasi ainult siis, kui oled saanud kinnituse.
- Kui töö käigus tekib kahtlus, ära oleta, vaid peatu ja küsi üle.

## 3. Tööpõhimõtted

- Ärireeglid peavad elama võimalikult tsentraalselt ja järjekindlalt; väldi reeglite dubleerimist eri kihtides.
- Muudatused peavad olema minimaalsed, sihitud ja kooskõlas olemasoleva arhitektuuriga.
- Töötavat koodi ei tohi igaks juhuks muuta ega ennetavalt parandada. Kui mingi osa töötab ja ei ole uuritava vea tõendatud juurpõhjus, siis seda ei muudeta.
- Ära muuda kõrvalisi faile ega paranda mitteseotud probleeme.
- Kõrge mõjuga otsuste puhul eelista juurpõhjuse parandamist, mitte lokaalseid ümberkäike.

### Git ja juurutus

- `git commit` vajab kasutaja iga töökorra jaoks eraldi luba.
- `git push` vajab kasutaja iga töökorra jaoks eraldi luba.
- Kuna rakendus töötab samas serveris, piisab testimiseks koodi muutmisest ning
  vajaliku konteineri ehitamisest ja taaskäivitamisest; commit'i ega push'i ei
  tohi eeldada juurutuse eeltingimusena.

### Testimine ja andmete muutmine

- Ilma kasutaja eraldi loata ei tohi käivitada teste ega kontrollskripte, mis
  kirjutavad andmebaasi või muudavad olemasolevaid andmeid.
- Ilma sellise loata on lubatud ainult dry-run'id, lugemispäringud ja muud
  mitte-muteerivad kontrollid.
- Mistahes andmeid või andmestruktuuri muutvat tegevust ei tohi teha ilma
  kasutaja eelneva eraldi loata — mitte kunagi. See hõlmab nii andmeridade
  lisamist, muutmist ja kustutamist kui ka tabeli, veeru, indeksi, piirangu või
  sequence'i lisamist, muutmist või kustutamist ning migratsiooni rakendamist.
- Kui kontroll eeldab andmete muutmist, tuleb enne peatuda ja küsida kasutajalt
  eraldi luba.

## 4. Vea käsitlemise juhis

- Vea või regressiooni korral uuri esmalt juurpõhjust.
- Uuri kogu ahelat, mitte ainult vea esinemise kohta.
- Ära piirdu ainult sümptomit eemaldava parandusega, kui juurpõhjus jääb alles.
- Tee veast, selle põhjustest ja võimalikest parandusvariantidest kokkuvõte ning küsi nõusolek parandamiseks.
- Vastuses või töö kokkuvõttes kirjelda võimalusel lühidalt:
  1. mis oli juurpõhjus;
  2. miks viga tekkis;
  3. kuidas tehtud parandus selle kõrvaldab;
  4. milline jääkrisk või eeldus alles jääb.
- Kui loogiline koht on olemas, lisa või uuenda test, mis kinnitab parandust.

## 5. Mittefunktsionaalsed ootused

- Hoia API, andmemudeli ja ärireeglite käitumine eri klientide jaoks järjekindel.
- Väldi lahendusi, mis suurendavad põhjendamatult API või andmebaasi koormust.
- API päringute arv on jõudluse seisukohalt oluline; teenused peavad tagastama ainult vajaliku hulga andmeid.
- Väldi suuri koondteenuseid; iga API teenus peab tagastama konkreetse kasutusjuhtumi jaoks vajaliku minimaalse andmehulga.
- Arvesta, et aja- ja kuupäevaloogikas on autoriteetne mudel UTC andmebaasis ja lokaalne aeg kasutajaliideses.
- Arvesta soft-delete nähtavusreeglitega: suletud kirjed ei tohi tavavoogudes lekkida.
- Kasutajaliidese tekstid peavad olema tõlgetest, mitte kõvakodeeritud.
- Koodis ei tohi olla kõvakodeeritud ekraanitekste; puudumisel kasutatakse tõlkevõtit ennast, et puuduvad tõlked nähtavale tuleksid.
- Koodis olevad tekstilabelid peavad olema kontekstis unikaalsed, et neid saaks sõltumatult muuta.
- Modal-overlayde korral on korraga aktiivne ainult kõige ülemine modal. Selle all olevad modalid ja ülejäänud leht peavad olema mitteaktiivsed, kuni ülemine modal suletakse.
- SQL-koodis ei tohi samasisulisi konstante, protseduure ja funktsioone põhjendamatult korrata; korduvkasutatav loogika tuleb teha ühisesse moodulisse.
- Eelista korduvate väärtuste puhul eeldefineeritud konstante.
- Ühendused Oracle’iga peavad kasutama ühenduste pooli, `.env`-põhiseid saladusi ja väikseimate õiguste põhimõtet.
- Mahukaid audio-, video-, VTT- ega JSON-faile ei salvestata andmebaasi; andmebaasis hoitakse nende viiteid ja metaandmeid.

## 6. Dokumentatsiooni ja tõeallikate register

### Juur-README ja sellest otse viidatud dokumendid

- [`README.md`](../README.md)
- [`docs/task_to_solve.md`](task_to_solve.md)
- [`docs/agents.md`](agents.md)
- [`docs/evaluation_data.md`](evaluation_data.md)
- [`docs/err2text_bpmn.drawio`](err2text_bpmn.drawio)
- [`docs/err2text_bpmn.drawio.png`](err2text_bpmn.drawio.png)
- [`db/erd.md`](../db/erd.md)
- [`db/schema/001_core_schema.sql`](../db/schema/001_core_schema.sql)

### Rakenduse ja juurutuse allikad

- [`compose.yaml`](../compose.yaml)
- [`Dockerfile`](../Dockerfile)
- [`Dockerfile.api`](../Dockerfile.api)
- [`backend/app/main.py`](../backend/app/main.py)
- [`backend/app/api/routes.py`](../backend/app/api/routes.py)
- [`backend/app/services/resolver.py`](../backend/app/services/resolver.py)
- [`backend/worker.py`](../backend/worker.py)
- [`.env.example`](../.env.example)

## 7. Millal mida kindlasti lugeda

- Kui muudad API vastuseid, tööde järjekorda või teenuste vahelist piiri, loe `docs/task_to_solve.md`, `docs/err2text_bpmn.drawio`, `backend/app/main.py`, `backend/app/api/routes.py` ja `backend/worker.py`.
- Kui muudad arhitektuuri või konteinerite vastutusi, loe `docs/task_to_solve.md`, `compose.yaml`, `Dockerfile` ja `Dockerfile.api`.
- Kui muudad andmestruktuure või andmebaasipoolseid reegleid, loe `db/erd.md` ja `db/schema/001_core_schema.sql`.
- Kui muudad URL-i lahendamist või meediaallikate salvestamist, loe `backend/app/services/resolver.py`, `backend/app/api/routes.py` ja BPMN-protsessi.
- Kui muudad jõudlust või diarization’i käitamist, loe `docs/task_to_solve.md`, `compose.yaml` ja `backend/worker.py`.
- Kui kasutad protsessiandmeid kvantitatiivseks analüüsiks või mudeli
  õpetamiseks või muudad nende kasutusluba, loe enne
  `docs/evaluation_data.md`. Kasutada tohib ainult registris vastava eesmärgi
  juures väärtusega `Jah` märgitud protsessi või kandidaadivahemikku.

## 8. Väljundi ootused

- Kui töö sisaldab vea parandust, too kokkuvõttes eraldi välja juurpõhjus ja paranduse loogika.
- Kui töö tugineb oletusele, nimeta oletus selgelt ning küsi enne muudatuse tegemist luba.
- Kui avastad dokumentatsiooni ja tegeliku käitumise lahknevuse, maini see kokkuvõttes välja ja küsi täiendavaid juhtnööre.
