# MVP3 keskne ORDS-i tööjärjekord

## 1. Dokumendi päritolu

Dokument kirjeldab ERR2TEXT MVP3 teostust, mis lepiti kokku ERR-i projekti,
TTÜ `ttu_loeng` projekti teostuse ja keskse ORDS API kasutusjuhendi põhjal.
Keskse API autoriteetne leping asub failis
`/home/ubuntu/projektid/jenkins/docs/api.md`.

## 2. Sisukord

- [3. Autoriteetsuse piir](#3-autoriteetsuse-piir)
- [4. Kohalik andmemudel](#4-kohalik-andmemudel)
- [5. Töö loomine](#5-töö-loomine)
- [6. Diariseerimistöö ulatus](#6-diariseerimistöö-ulatus)
- [7. Workeri protokoll](#7-workeri-protokoll)
- [8. Vead ja taastamine](#8-vead-ja-taastamine)
- [9. Kasutaja ülevaatus](#9-kasutaja-ülevaatus)
- [10. Migratsioon ja kasutuselevõtt](#10-migratsioon-ja-kasutuselevõtt)

## 3. Autoriteetsuse piir

ORDS on ainus autoriteetne taustatööde järjekord. Töö tohib alata ainult
kehtiva ORDS-i claim'i alusel. ERR-i tabelid `processes` ja `activities`
kirjeldavad äriprotsessi ning selle etappe, kuid ei ole järjekord.
`execution_started_at` on ainult kohaliku etapi tegeliku alguse auditiväli.

Rakenduses ei ole kohalikku claim-päringut, `SKIP LOCKED` põhist tööde valikut,
eraldi samaaegsuse loendurit ega ORDS-i tõrke korral kasutatavat varujärjekorda.
Worker töötleb korraga ühte ORDS-i antud tööd.

Nagu TTÜ loengurakenduses, kuvab ERR iga taustatoimingu kohta ühe
autoriteetse ORDS-i oleku. Kohalik `processes.status` jääb äriprotsessi ja
rakenduse sisemise etapi jaoks ning seda ei kuvata ORDS-i toimingu kõrval ega
asemel. Enne MVP3 migratsiooni loodud, ORDS-ita ajaloolised protsessid
säilitavad oma olemasoleva olekukuvamise.

## 4. Kohalik andmemudel

Migratsioon `db/schema/008_mvp3_ords_queue.sql` lisab TTÜ projektiga sama
põhimustriga tabeli `background_operations`. Kirje sisaldab:

- kohalikku `operation_id` ja avalikku UUID-d;
- ERR-i `process_id` seost;
- toiminguliiki, katse numbrit ja eelneva toimingu viidet;
- muutumatut ORDS-i idempotentsusvõtit ning keskset `ords_job_id` väärtust;
- ORDS-i registreerimisvea koodi ja kirjeldust;
- kohaliku adapteri algus-, lõpu-, tulemi- ja veaandmeid;
- tavapäraseid audit- ja soft-delete välju.

Tabel ei dubleeri ORDS-i järjekorra staatust. `ords_job_id` unikaalsus ja
idempotentsusvõti seovad ühe kohaliku toimingu ühe keskse tööga. MVP3 esimene
ja ainus töötüüp on `diarization`.

## 5. Töö loomine

Pärast kasutaja kinnitust teeb API järgmise kohaliku tehingu:

1. salvestab allika ja valitud meedia;
2. loob uue `processes` rea staatusega `DIARIZING`;
3. loob esimese `DIARIZING` tegevuse ilma `execution_started_at` väärtuseta;
4. loob `background_operations` rea ja muutumatu idempotentsusvõtme;
5. commit'ib kohaliku tehingu.

Seejärel registreerib API töö `POST /application/jobs` kaudu. Tehniline leping
on:

```json
{
  "application_code": "err_video_to_text",
  "job_type_code": "diarization",
  "application_job_id": "<operation_id>",
  "idempotency_key": "err_video_to_text:diarization:<uuid>",
  "previous_job_id": null,
  "parameters": {
    "process_id": 123,
    "media_title": "2026-11-04 — Esimene stuudio",
    "media_published_date": "2026-11-04T00:00:00Z"
  }
}
```

`process_id` kontrollib claim'i sidumist kohaliku kontekstiga.
`media_title` ja `media_published_date` on ainult ORDS-i haldusvaate
informatiivne hetkeseis. Worker ei kasuta neid töö sisendina. Pealkiri peab
alati sisaldama saate tegelikku toimumis- või avaldamiskuupäeva.

Registreerimisvea korral säilitab rakendus sama kohaliku toimingu ja sama
idempotentsusvõtme koos veakoodiga. Tõrge ei anna õigust käivitada tööd
kohalikult.

## 6. Diariseerimistöö ulatus

Üks `diarization` töö täidab järjest kogu automaatse algvoo:

1. lahendab salvestatud allika uuesti ja leiab valitud meedia;
2. laadib alla audio ning VTT;
3. säilitab algse VTT, valideerib ja normaliseerib tööversiooni;
4. teeb audio diariseerimise;
5. liidab diariseerimise VTT tekstiga;
6. materialiseerib `AUTOMATIC_DRAFT` versiooni ja selle artefaktid;
7. viib protsessi kasutaja osalejate ülevaatuse algolekusse.

Audio ja VTT allalaadimine on diariseerimistöö osa ning toimub pärast ORDS-i
claim'i. Eraldi `DOWNLOADING` taustatööd ega ORDS-i tööd ei looda. Kui meediat
või VTT-d ei saa hankida või VTT ei ole kasutatav, lõpeb sama töö veaga ja
diariseerimist ei jätkata.

## 7. Workeri protokoll

Worker:

1. loob käivitumisel uue `worker_instance_id`, loeb hosti `boot_id` väärtuse
   ja kutsub `/worker/startup`;
2. lahendab võimaliku `active_job` kirje enne uue töö küsimist;
3. küsib jõudeolekus tööd `/worker/claim` kaudu;
4. valideerib `application_job_id`, `parameters.process_id` ja
   `job_type_code` kohaliku `background_operations` kirje vastu;
5. seob vajaduse korral claim'i `job_id` kohaliku toiminguga;
6. märgib kohaliku adapteri ja aktiivse tegevuse tegeliku alguse;
7. saadab `/start`, töö ajal heartbeat'i ning lõpus `/complete`;
8. ei claim'i töötava töö kõrvale teist tööd.

OAuth tokenit hoitakse ainult mälus. Klient küsib uue tokeni enne aegumist,
kordab ühe korra `401` vastuse järel ning teeb piiratud korduskatse võrguvea,
`429` või ajutise 5xx vastuse korral.

## 8. Vead ja taastamine

Kui claim'itud `application_job_id` järgi ei ole aktiivset kohalikku toimingut
või ärikonteksti, ei saadeta `/start` päringut ega muudeta suletud kohalikke
kirjeid. ORDS-i töö lõpetatakse:

```json
{
  "outcome": "INTERRUPTED",
  "exit_code": 0,
  "end_reason": "APPLICATION_OPERATION_NOT_FOUND"
}
```

Puuduv või vale `process_id` lõpeb `FAILED` ja `INVALID_PARAMETERS`; vale
töötüüp lõpeb `FAILED` ja `INVALID_JOB_TYPE`. Kohaliku pipeline'i viga
salvestatakse nii aktiivsele tegevusele kui `background_operations` reale ning
ORDS lõpetatakse `FAILED` tulemusega.

Kui worker taaskäivitub pärast kohaliku töö lõppu, kuid enne ORDS-i
`/complete` kinnitamist, saadetakse kohalikult säilitatud tulemus ORDS-i uuesti.
Kui restart katkestas juba alanud diariseerimise, märgitakse kohalik protsess
katkestatuks ja ORDS lõpetatakse `INTERRUPTED` põhjusega `WORKER_RESTART`;
pooleli jäänud rasket töötlust ei eeldata ohutult jätkatavaks.

## 9. Kasutaja ülevaatus

`WAITING_FOR_PARTICIPANTS` ja `IN_REVIEW` on kasutaja juhitud äriprotsessi
olekud, mitte taustatööd. Praegu ei ole kokku lepitud automaatset protsessi,
mis peab kasutaja ülevaatusele järgnema. Finaliseerimise nuppu MVP3 muudatus ei
lisa ega muuda.

Kui ülevaatusele järgnev automaatne töö hiljem otsustatakse, lisatakse selle
jaoks uus `background_operations` rida ja uus ORDS-i töö. Diariseerimise tööd
ei avata uuesti ning kohalikku järjekorda ei looda.

## 10. Migratsioon ja kasutuselevõtt

Kasutuselevõtu järjekord on:

1. luua keskse ORDS-i rakenduse ja töötüübi konfiguratsioon ning eraldi OAuth
   klient rakendusele;
2. lisada serveri `.env` faili ORDS-i baasaadress, kliendi ID ja saladus;
3. rakendada `db/schema/008_mvp3_ords_queue.sql` ERR-i skeemis;
4. ehitada API ja worker uue koodiga;
5. käivitada API ja ORDS-worker ning kontrollida startup/claim ühendust;
6. esitada uus kontrollsaade ja kontrollida kogu töö elutsüklit.

Koodi ei tohi võtta kasutusele enne migratsiooni, sest API sõltub
`background_operations` tabelist. Migratsioon ei loo toiminguid olemasolevate
saadete, varasemate protsesside ega pooleliolevate MVP2 tegevuste jaoks. Neid
ei registreerita ORDS-is tagantjärele.
