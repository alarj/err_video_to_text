# ERR2TEXT ERD

See mudel kirjeldab ühte transkribeerimisprotsessi ja selle järjestikuseid
tegevusi. Protsess luuakse pärast kasutaja kinnitust.

```mermaid
erDiagram
    MEDIA_ITEMS ||--o{ MEDIA_ASSETS : has
    SOURCES ||--o{ PROCESSES : starts_from
    MEDIA_ITEMS ||--o{ PROCESSES : processes
    PROCESSES ||--o{ PROCESSES : parent_process
    PROCESSES ||--o{ ACTIVITIES : contains
    ACTIVITIES ||--o{ ACTIVITIES : previous_activity
    ACTIVITIES ||--o{ ACTIVITY_ARTIFACTS : produces
    ARTIFACTS ||--o{ ACTIVITY_ARTIFACTS : linked
    PROCESSES ||--o{ TRANSCRIPT_VERSIONS : creates
    ACTIVITIES ||--o{ TRANSCRIPT_VERSIONS : created_by
    TRANSCRIPT_VERSIONS ||--o{ TRANSCRIPT_ARTIFACTS : publishes
    ARTIFACTS ||--o{ TRANSCRIPT_ARTIFACTS : linked
    TRANSCRIPT_VERSIONS ||--o{ TRANSCRIPT_PARTICIPANTS : contains
    PARTICIPANTS ||--o{ TRANSCRIPT_PARTICIPANTS : identifies
    TRANSCRIPT_VERSIONS ||--o{ TRANSCRIPT_SEGMENTS : contains
    TRANSCRIPT_SEGMENTS ||--o{ TRANSCRIPT_SEGMENT_SPEAKERS : has
    TRANSCRIPT_PARTICIPANTS ||--o{ TRANSCRIPT_SEGMENT_SPEAKERS : assigned
    TRANSCRIPT_SEGMENTS ||--o{ REVIEW_CANDIDATES : flagged

    SOURCES {
        NUMBER id PK
        VARCHAR2 url
        VARCHAR2 source_type
        VARCHAR2 title
        VARCHAR2 description
        TIMESTAMP published_date
    }
    MEDIA_ITEMS {
        NUMBER id PK
        VARCHAR2 provider
        VARCHAR2 external_id
        VARCHAR2 canonical_url
        VARCHAR2 media_type
        VARCHAR2 title
        VARCHAR2 description
        TIMESTAMP published_date
        NUMBER duration_second
    }
    MEDIA_ASSETS {
        NUMBER id PK
        NUMBER media_item_id FK
        VARCHAR2 asset_type
        VARCHAR2 url
        VARCHAR2 version
    }
    PROCESSES {
        NUMBER id PK
        NUMBER parent_process_id FK
        NUMBER source_id FK
        NUMBER media_item_id FK
        VARCHAR2 status
        TIMESTAMP started_at
        TIMESTAMP finished_at
    }
    ACTIVITIES {
        NUMBER id PK
        NUMBER process_id FK
        NUMBER previous_activity_id FK
        VARCHAR2 activity_type
        TIMESTAMP started_at
        TIMESTAMP finished_at
        VARCHAR2 result
        TIMESTAMP execution_started_at
        VARCHAR2 error_code
        VARCHAR2 error_message
    }
    ARTIFACTS {
        NUMBER id PK
        VARCHAR2 artifact_type
        VARCHAR2 path
        VARCHAR2 content_type
        NUMBER size_byte
        CHAR sha256
    }
    ACTIVITY_ARTIFACTS {
        NUMBER id PK
        NUMBER activity_id FK
        NUMBER artifact_id FK
    }
    TRANSCRIPT_VERSIONS {
        NUMBER id PK
        NUMBER process_id FK
        NUMBER activity_id FK
        NUMBER version_number
        VARCHAR2 version_type
        VARCHAR2 status
    }
    TRANSCRIPT_ARTIFACTS {
        NUMBER id PK
        NUMBER transcript_version_id FK
        NUMBER artifact_id FK
    }
    PARTICIPANTS {
        NUMBER id PK
        VARCHAR2 name
        VARCHAR2 description
        VARCHAR2 organisation
        VARCHAR2 occupation
    }
    TRANSCRIPT_PARTICIPANTS {
        NUMBER id PK
        NUMBER transcript_version_id FK
        VARCHAR2 speaker_label
        NUMBER participant_id FK
        VARCHAR2 role
        VARCHAR2 mapping_status
    }
    TRANSCRIPT_SEGMENTS {
        NUMBER id PK
        NUMBER transcript_version_id FK
        NUMBER segment_number
        NUMBER start_second
        NUMBER end_second
        VARCHAR2 text
    }
    TRANSCRIPT_SEGMENT_SPEAKERS {
        NUMBER id PK
        NUMBER transcript_segment_id FK
        NUMBER transcript_participant_id FK
        NUMBER start_second
        NUMBER end_second
        NUMBER confidence
    }
    REVIEW_CANDIDATES {
        NUMBER id PK
        NUMBER transcript_segment_id FK
        VARCHAR2 candidate_type
        VARCHAR2 reason
        VARCHAR2 status
        VARCHAR2 decision
        TIMESTAMP decision_at
    }
```

## Protsessi ja tegevuse reeglid

- Protsess luuakse alles pärast seda, kui kasutaja on meedia valiku ja
  transkribeerimise alustamise kinnitanud.
- Protsessi `started_at` on esimese tegevuse algus. `finished_at` tekib alles
  BPMN-i lõpusündmuseni jõudmisel.
- Aktiivse protsessi `status` on parajasti lõpetamata tegevuse
  `activity_type`. Lõppenud protsessi staatus on `FINISHED` või `CANCELLED`.
- Tegevusel ei ole muutuvat staatust. Tegevusel on algus, lõpp ja tulemus.
- Tegevuse `result` tekib ainult koos `finished_at` väärtusega. Lubatud
  tulemused on `OK`, `ERROR` ja `CANCELLED`. Pooleli tegevusel on mõlemad
  väärtused `NULL`.
- Taustal käivitataval tegevusel võib olla tehniline
  `execution_started_at`. See näitab, et worker on tegevuse endale hõivanud;
  see ei ole tegevuse äriline staatus ega tulemus.
- Diariseerimise samaaegsuse ülempiir tuleb konfiguratsioonist
  `ERR2TEXT_MAX_CONCURRENT_DIARIZATIONS`; vaikimisi on väärtus `1`. Käimasolevaks
  diariseerimiseks loetakse tegevus, mille `activity_type` on `DIARIZING`,
  `execution_started_at` ei ole `NULL` ja `finished_at` on `NULL`.
- Worker hõivab tegevuse atomaarse andmebaasitehinguga. Hõivamata tegevust ei
  tohi teine worker samal ajal käivitada.
- Eelmise tegevuse lõpetamine, uue tegevuse lisamine ja protsessi staatuse
  uuendamine toimuvad ühe lühikese andmebaasitransaktsiooni sees.
- Pika tegevuse, nagu diariseerimise või kasutaja ülevaatuse ajal, ei hoita
  andmebaasitransaktsiooni avatuna. Alustamine ja lõpetamine on eraldi kiired
  transaktsioonid.
- Sama `activity_type` võib ühe protsessi sees korduda.

## Tegevuste ahela terviklikkus

`activities.process_id` on kohustuslik. `previous_activity_id` on esimese
tegevuse puhul `NULL`.

`activities` peab sisaldama unikaalsust `(process_id, id)` ning võõrvõti
`(process_id, previous_activity_id)` peab viitama sama tabeli samale
`process_id` väärtusele. Tegevus ei tohi viidata teise protsessi tegevusele.

## Seotud protsesside tehniline reegel

Kui kasutaja kinnitab uue protsessi, kuid sama meedia kohta on juba aktiivne
põhiprotsess, uut diariseerimist ei käivitata. Uue protsessi
`parent_process_id` viitab põhiprotsessile ja esimene tegevus on
`WAITING_FOR_RESULT`.

See tehniline sõltuvus ei ole BPMN-i põhijoonisel eraldi tegevusena kujutatud.
Taustal töötav kontroll lõpetab ootava protsessi, kui põhiprotsess lõpeb.

- Põhiprotsessi `FINISHED` korral lõpetatakse ootav protsess `FINISHED` ja
  seotakse sama transkriptsioonitulemus.
- Põhiprotsessi `CANCELLED` korral lõpetatakse ootav protsess `CANCELLED`.
- Kuni põhiprotsess kestab, puudub ootaval protsessil tulemus.

Ühel põhiprotsessil võib olla 0…n sõltuvat protsessi.

## Ühised veerud ja soft delete

Kõigil tabelitel on lisaks diagrammil näidatud veergudele järgmised ühised
veerud. `id`-veerg on diagrammil iga tabeli juures eraldi näidatud.

| Veerg | Tüüp | Reegel / tähendus |
|---|---|---|
| `start_date` | `DATE` | Kehtivuse algus; vaikimisi `SYSDATE` |
| `end_date` | `DATE` | Sulgemise aeg; füüsilist kustutamist ei kasutata |
| `created` | `TIMESTAMP` | Loomise aeg; vaikimisi `SYSTIMESTAMP` |
| `last_updated` | `TIMESTAMP` | Muutmise aeg; API määrab muutmisel |

Aktiivne kirje vastab tingimusele:

```sql
end_date IS NULL OR end_date > SYSDATE
```

## Transkriptsiooniversioonide lubatud väärtused

`transcript_versions.version_type`:

```text
AUTOMATIC_DRAFT
REVIEWED_DRAFT
FINAL
```

`transcript_participants.mapping_status`:

```text
UNCONFIRMED
CONFIRMED
UNKNOWN
```

Erandina võib `transcript_participants.participant_id` olla `NULL`, kuni
kasutaja kinnitab päris inimese või märgib kõneleja tundmatuks.
