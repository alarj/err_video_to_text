# ERR2TEXT ERD

```mermaid
erDiagram
    SOURCES ||--o{ JOBS : source
    MEDIA_ITEMS ||--o{ MEDIA_ASSETS : has
    MEDIA_ITEMS ||--o{ JOBS : selected_for
    JOB_STATUSES ||--o{ JOBS : status
    JOBS ||--o{ JOB_EVENTS : events
    JOB_STATUSES ||--o{ JOB_EVENTS : status
    JOBS ||--o{ RUNS : origin_job
    MEDIA_ITEMS ||--o{ RUNS : processed
    JOBS ||--o{ JOB_RUNS : linked
    RUNS ||--o{ JOB_RUNS : supplies
    RUNS ||--o{ RUN_ARTIFACTS : produces
    ARTIFACTS ||--o{ RUN_ARTIFACTS : linked
    RUNS ||--o{ TRANSCRIPT_VERSIONS : creates
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
    JOB_STATUSES {
        NUMBER id PK
        VARCHAR2 code
        VARCHAR2 name_et
        VARCHAR2 description_et
    }
    JOBS {
        NUMBER id PK
        NUMBER source_id FK
        NUMBER media_item_id FK
        VARCHAR2 submitted_url
        NUMBER job_status_id FK
        VARCHAR2 error_code
        VARCHAR2 error_message
        TIMESTAMP submitted_at
        TIMESTAMP resolved_at
    }
    JOB_EVENTS {
        NUMBER id PK
        NUMBER job_id FK
        NUMBER job_status_id FK
        VARCHAR2 event_type
        VARCHAR2 detail
        TIMESTAMP event_at
    }
    RUNS {
        NUMBER id PK
        NUMBER origin_job_id FK
        NUMBER media_item_id FK
        VARCHAR2 status
        NUMBER attempt_number
        VARCHAR2 input_fingerprint
        TIMESTAMP started_at
        TIMESTAMP finished_at
    }
    JOB_RUNS {
        NUMBER id PK
        NUMBER job_id FK
        NUMBER run_id FK
        VARCHAR2 relation_type
    }
    ARTIFACTS {
        NUMBER id PK
        VARCHAR2 artifact_type
        VARCHAR2 path
        VARCHAR2 content_type
        NUMBER size_byte
        CHAR sha256
    }
    RUN_ARTIFACTS {
        NUMBER id PK
        NUMBER run_id FK
        NUMBER artifact_id FK
    }
    TRANSCRIPT_VERSIONS {
        NUMBER id PK
        NUMBER run_id FK
        NUMBER version_number
        VARCHAR2 version_type
        VARCHAR2 status
    }
    TRANSCRIPT_ARTIFACTS {
        NUMBER id PK
        NUMBER transcript_version_id FK
        NUMBER artifact_id FK
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

## Ühised väljad ja soft delete

## Unikaalsused ja lubatud väärtused

| Tabel | Unikaalsus |
|---|---|
| `transcript_participants` | `UNIQUE (transcript_version_id, speaker_label)` |
| `job_runs` | `UNIQUE (job_id, run_id)` |
| `run_artifacts` | `UNIQUE (run_id, artifact_id)` |
| `transcript_artifacts` | `UNIQUE (transcript_version_id, artifact_id)` |

`transcript_versions.version_type` lubatud väärtused:

```text
AUTOMATIC_DRAFT
REVIEWED_DRAFT
FINAL
```

`review_candidates.status` lubatud väärtused:

```text
PENDING
ACCEPTED
REJECTED
MODIFIED
```

`transcript_participants.mapping_status` lubatud väärtused:

```text
UNCONFIRMED
CONFIRMED
UNKNOWN
```

Erandina võib `transcript_participants.participant_id` olla `NULL`, kuni
kasutaja kinnitab päris inimese või märgib kõneleja tundmatuks.

Kõigil tabelitel on lisaks diagrammil näidatud väljadele järgmised väljad:

| Veerg | Tüüp | Reegel / tähendus |
|---|---|---|
| `id` | `NUMBER` | Primary key; tabeli sequence'i järgmine väärtus |
| `start_date` | `DATE` | Kehtivuse algus; vaikimisi `SYSDATE` |
| `end_date` | `DATE` | Sulgemise aeg; füüsilist kustutamist ei kasutata |
| `created` | `TIMESTAMP` | Loomise aeg; vaikimisi `SYSTIMESTAMP` |
| `last_updated` | `TIMESTAMP` | Muutmise aeg; API määrab muutmisel |

Aktiivne kirje vastab tingimusele:

```sql
end_date IS NULL OR end_date > SYSDATE
```
