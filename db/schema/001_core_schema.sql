-- ERR2TEXT MVP2.1 / MVP2.2
-- Ühe failina käivitatav Oracle'i skeem.
-- Failide sisu andmebaasi ei salvestata; artifacts sisaldab ainult metaandmeid.

-- ============================================================
-- Sequences
-- ============================================================
CREATE SEQUENCE sources_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE media_items_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE media_assets_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE participants_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE job_statuses_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE jobs_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE job_events_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE runs_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE job_runs_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE artifacts_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE run_artifacts_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_versions_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_artifacts_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_participants_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_segments_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_segment_speakers_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE review_candidates_seq START WITH 1 INCREMENT BY 1 NOCACHE;

-- ============================================================
-- Independent tables
-- ============================================================
CREATE TABLE sources (
    id              NUMBER DEFAULT sources_seq.NEXTVAL NOT NULL,
    url             VARCHAR2(2048) NOT NULL,
    source_type     VARCHAR2(40) NOT NULL,
    title           VARCHAR2(1000) NOT NULL,
    description     VARCHAR2(4000),
    published_date  TIMESTAMP,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT sources_pk PRIMARY KEY (id)
);

CREATE TABLE media_items (
    id              NUMBER DEFAULT media_items_seq.NEXTVAL NOT NULL,
    provider        VARCHAR2(80) NOT NULL,
    external_id     VARCHAR2(256) NOT NULL,
    canonical_url   VARCHAR2(2048) NOT NULL,
    media_type      VARCHAR2(30) NOT NULL,
    title           VARCHAR2(1000) NOT NULL,
    description     VARCHAR2(4000),
    published_date  TIMESTAMP,
    duration_second NUMBER(12,3),
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT media_items_pk PRIMARY KEY (id),
    CONSTRAINT media_items_provider_id_uq UNIQUE (provider, external_id),
    CONSTRAINT media_items_canonical_uq UNIQUE (canonical_url),
    CONSTRAINT media_items_type_ck CHECK (media_type IN ('VIDEO', 'AUDIO', 'OTHER')),
    CONSTRAINT media_items_duration_ck CHECK (duration_second IS NULL OR duration_second >= 0)
);

CREATE TABLE participants (
    id              NUMBER DEFAULT participants_seq.NEXTVAL NOT NULL,
    name            VARCHAR2(500) NOT NULL,
    description     VARCHAR2(4000),
    organisation    VARCHAR2(500),
    occupation      VARCHAR2(500),
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT participants_pk PRIMARY KEY (id)
);

CREATE TABLE job_statuses (
    id              NUMBER DEFAULT job_statuses_seq.NEXTVAL NOT NULL,
    code            VARCHAR2(40) NOT NULL,
    name_et         VARCHAR2(120) NOT NULL,
    description_et  VARCHAR2(1000) NOT NULL,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT job_statuses_pk PRIMARY KEY (id),
    CONSTRAINT job_statuses_code_uq UNIQUE (code)
);

CREATE TABLE artifacts (
    id              NUMBER DEFAULT artifacts_seq.NEXTVAL NOT NULL,
    artifact_type   VARCHAR2(80) NOT NULL,
    path            VARCHAR2(2048) NOT NULL,
    content_type    VARCHAR2(200) NOT NULL,
    size_byte       NUMBER(19) NOT NULL,
    sha256          CHAR(64) NOT NULL,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT artifacts_pk PRIMARY KEY (id),
    CONSTRAINT artifacts_size_ck CHECK (size_byte >= 0)
);

-- ============================================================
-- Source, job and processing tables
-- ============================================================
CREATE TABLE media_assets (
    id              NUMBER DEFAULT media_assets_seq.NEXTVAL NOT NULL,
    media_item_id   NUMBER NOT NULL,
    asset_type      VARCHAR2(30) NOT NULL,
    url             VARCHAR2(2048) NOT NULL,
    version         VARCHAR2(256),
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT media_assets_pk PRIMARY KEY (id),
    CONSTRAINT media_assets_media_fk FOREIGN KEY (media_item_id) REFERENCES media_items (id),
    CONSTRAINT media_assets_type_ck CHECK (asset_type IN ('VIDEO', 'AUDIO', 'MANIFEST', 'VTT'))
);

CREATE TABLE jobs (
    id              NUMBER DEFAULT jobs_seq.NEXTVAL NOT NULL,
    source_id       NUMBER NOT NULL,
    media_item_id   NUMBER NOT NULL,
    submitted_url   VARCHAR2(2048) NOT NULL,
    job_status_id   NUMBER NOT NULL,
    error_code      VARCHAR2(80),
    error_message   VARCHAR2(2000),
    submitted_at    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    resolved_at     TIMESTAMP,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT jobs_pk PRIMARY KEY (id),
    CONSTRAINT jobs_source_fk FOREIGN KEY (source_id) REFERENCES sources (id),
    CONSTRAINT jobs_media_fk FOREIGN KEY (media_item_id) REFERENCES media_items (id),
    CONSTRAINT jobs_status_fk FOREIGN KEY (job_status_id) REFERENCES job_statuses (id)
);

CREATE TABLE job_events (
    id              NUMBER DEFAULT job_events_seq.NEXTVAL NOT NULL,
    job_id          NUMBER NOT NULL,
    job_status_id   NUMBER NOT NULL,
    event_type      VARCHAR2(80) NOT NULL,
    detail          VARCHAR2(4000) NOT NULL,
    event_at        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT job_events_pk PRIMARY KEY (id),
    CONSTRAINT job_events_job_fk FOREIGN KEY (job_id) REFERENCES jobs (id),
    CONSTRAINT job_events_status_fk FOREIGN KEY (job_status_id) REFERENCES job_statuses (id)
);

CREATE TABLE runs (
    id                NUMBER DEFAULT runs_seq.NEXTVAL NOT NULL,
    origin_job_id     NUMBER NOT NULL,
    media_item_id     NUMBER NOT NULL,
    status            VARCHAR2(40) NOT NULL,
    attempt_number    NUMBER(6) NOT NULL,
    input_fingerprint VARCHAR2(128) NOT NULL,
    started_at        TIMESTAMP,
    finished_at       TIMESTAMP,
    start_date        DATE DEFAULT SYSDATE NOT NULL,
    end_date          DATE,
    created           TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated      TIMESTAMP,
    CONSTRAINT runs_pk PRIMARY KEY (id),
    CONSTRAINT runs_origin_job_fk FOREIGN KEY (origin_job_id) REFERENCES jobs (id),
    CONSTRAINT runs_media_fk FOREIGN KEY (media_item_id) REFERENCES media_items (id),
    CONSTRAINT runs_status_ck CHECK (status IN ('STARTED', 'SUCCEEDED', 'FAILED', 'CANCELLED')),
    CONSTRAINT runs_attempt_ck CHECK (attempt_number > 0)
);

CREATE TABLE job_runs (
    id              NUMBER DEFAULT job_runs_seq.NEXTVAL NOT NULL,
    job_id          NUMBER NOT NULL,
    run_id          NUMBER NOT NULL,
    relation_type   VARCHAR2(20) NOT NULL,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT job_runs_pk PRIMARY KEY (id),
    CONSTRAINT job_runs_job_fk FOREIGN KEY (job_id) REFERENCES jobs (id),
    CONSTRAINT job_runs_run_fk FOREIGN KEY (run_id) REFERENCES runs (id),
    CONSTRAINT job_runs_relation_ck CHECK (relation_type IN ('CREATED', 'REUSED')),
    CONSTRAINT job_runs_uq UNIQUE (job_id, run_id)
);

CREATE TABLE run_artifacts (
    id              NUMBER DEFAULT run_artifacts_seq.NEXTVAL NOT NULL,
    run_id          NUMBER NOT NULL,
    artifact_id     NUMBER NOT NULL,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT run_artifacts_pk PRIMARY KEY (id),
    CONSTRAINT run_artifacts_run_fk FOREIGN KEY (run_id) REFERENCES runs (id),
    CONSTRAINT run_artifacts_artifact_fk FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
    CONSTRAINT run_artifacts_uq UNIQUE (run_id, artifact_id)
);

-- ============================================================
-- Transcript tables
-- ============================================================
CREATE TABLE transcript_versions (
    id              NUMBER DEFAULT transcript_versions_seq.NEXTVAL NOT NULL,
    run_id          NUMBER NOT NULL,
    version_number  NUMBER(6) NOT NULL,
    version_type    VARCHAR2(40) NOT NULL,
    status          VARCHAR2(40) NOT NULL,
    start_date      DATE DEFAULT SYSDATE NOT NULL,
    end_date        DATE,
    created         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated    TIMESTAMP,
    CONSTRAINT transcript_versions_pk PRIMARY KEY (id),
    CONSTRAINT transcript_versions_run_fk FOREIGN KEY (run_id) REFERENCES runs (id),
    CONSTRAINT transcript_versions_number_ck CHECK (version_number > 0),
    CONSTRAINT transcript_versions_type_ck CHECK (version_type IN ('AUTOMATIC_DRAFT', 'REVIEWED_DRAFT', 'FINAL'))
);

CREATE TABLE transcript_artifacts (
    id                    NUMBER DEFAULT transcript_artifacts_seq.NEXTVAL NOT NULL,
    transcript_version_id NUMBER NOT NULL,
    artifact_id           NUMBER NOT NULL,
    start_date            DATE DEFAULT SYSDATE NOT NULL,
    end_date              DATE,
    created               TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated          TIMESTAMP,
    CONSTRAINT transcript_artifacts_pk PRIMARY KEY (id),
    CONSTRAINT transcript_artifacts_version_fk FOREIGN KEY (transcript_version_id) REFERENCES transcript_versions (id),
    CONSTRAINT transcript_artifacts_artifact_fk FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
    CONSTRAINT transcript_artifacts_uq UNIQUE (transcript_version_id, artifact_id)
);

CREATE TABLE transcript_participants (
    id                    NUMBER DEFAULT transcript_participants_seq.NEXTVAL NOT NULL,
    transcript_version_id NUMBER NOT NULL,
    speaker_label         VARCHAR2(80) NOT NULL,
    participant_id        NUMBER,
    role                  VARCHAR2(120) NOT NULL,
    mapping_status        VARCHAR2(30) NOT NULL,
    start_date            DATE DEFAULT SYSDATE NOT NULL,
    end_date              DATE,
    created               TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated          TIMESTAMP,
    CONSTRAINT transcript_participants_pk PRIMARY KEY (id),
    CONSTRAINT transcript_participants_version_fk FOREIGN KEY (transcript_version_id) REFERENCES transcript_versions (id),
    CONSTRAINT transcript_participants_participant_fk FOREIGN KEY (participant_id) REFERENCES participants (id),
    CONSTRAINT transcript_participants_status_ck CHECK (mapping_status IN ('UNCONFIRMED', 'CONFIRMED', 'UNKNOWN')),
    CONSTRAINT transcript_participants_uq UNIQUE (transcript_version_id, speaker_label)
);

CREATE TABLE transcript_segments (
    id                    NUMBER DEFAULT transcript_segments_seq.NEXTVAL NOT NULL,
    transcript_version_id NUMBER NOT NULL,
    segment_number        NUMBER(12) NOT NULL,
    start_second          NUMBER(12,3) NOT NULL,
    end_second            NUMBER(12,3) NOT NULL,
    text                  VARCHAR2(4000) NOT NULL,
    start_date            DATE DEFAULT SYSDATE NOT NULL,
    end_date              DATE,
    created               TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated          TIMESTAMP,
    CONSTRAINT transcript_segments_pk PRIMARY KEY (id),
    CONSTRAINT transcript_segments_version_fk FOREIGN KEY (transcript_version_id) REFERENCES transcript_versions (id),
    CONSTRAINT transcript_segments_number_ck CHECK (segment_number > 0),
    CONSTRAINT transcript_segments_time_ck CHECK (end_second >= start_second)
);

CREATE TABLE transcript_segment_speakers (
    id                         NUMBER DEFAULT transcript_segment_speakers_seq.NEXTVAL NOT NULL,
    transcript_segment_id      NUMBER NOT NULL,
    transcript_participant_id  NUMBER NOT NULL,
    start_second               NUMBER(12,3) NOT NULL,
    end_second                 NUMBER(12,3) NOT NULL,
    confidence                 NUMBER(6,5) NOT NULL,
    start_date                 DATE DEFAULT SYSDATE NOT NULL,
    end_date                   DATE,
    created                    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated               TIMESTAMP,
    CONSTRAINT transcript_segment_speakers_pk PRIMARY KEY (id),
    CONSTRAINT transcript_segment_speakers_segment_fk FOREIGN KEY (transcript_segment_id) REFERENCES transcript_segments (id),
    CONSTRAINT transcript_segment_speakers_participant_fk FOREIGN KEY (transcript_participant_id) REFERENCES transcript_participants (id),
    CONSTRAINT transcript_segment_speakers_time_ck CHECK (end_second >= start_second),
    CONSTRAINT transcript_segment_speakers_confidence_ck CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT transcript_segment_speakers_uq UNIQUE (transcript_segment_id, transcript_participant_id, start_second, end_second)
);

CREATE TABLE review_candidates (
    id                    NUMBER DEFAULT review_candidates_seq.NEXTVAL NOT NULL,
    transcript_segment_id NUMBER NOT NULL,
    candidate_type        VARCHAR2(40) NOT NULL,
    reason                VARCHAR2(1000) NOT NULL,
    status                VARCHAR2(30) NOT NULL,
    decision              VARCHAR2(30),
    decision_at           TIMESTAMP,
    start_date            DATE DEFAULT SYSDATE NOT NULL,
    end_date              DATE,
    created               TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated          TIMESTAMP,
    CONSTRAINT review_candidates_pk PRIMARY KEY (id),
    CONSTRAINT review_candidates_segment_fk FOREIGN KEY (transcript_segment_id) REFERENCES transcript_segments (id),
    CONSTRAINT review_candidates_status_ck CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'MODIFIED'))
);

-- ============================================================
-- Table comments
-- ============================================================
COMMENT ON TABLE sources IS 'Kasutaja sisestatud lähte-URL ja selle metaandmed';
COMMENT ON TABLE media_items IS 'Kasutaja valitud tegelik video-, audio- või muu meediadokument';
COMMENT ON TABLE media_assets IS 'Valitud meedia tehnilised video-, audio-, manifesti- ja VTT-allikad';
COMMENT ON TABLE participants IS 'Vestluses osalevad päris inimesed';
COMMENT ON TABLE job_statuses IS 'Töö olekute klassifikaator eestikeelsete kirjeldustega';
COMMENT ON TABLE jobs IS 'Kasutaja kinnitatud töötlemiskorraldus';
COMMENT ON TABLE job_events IS 'Töö olekumuutuste ja oluliste sündmuste ajalugu';
COMMENT ON TABLE runs IS 'Üks tegelik töötlemiskatse';
COMMENT ON TABLE job_runs IS 'Töö ja tulemuse andnud töötlemiskatse seos';
COMMENT ON TABLE artifacts IS 'Failisüsteemis oleva artefakti metaandmed';
COMMENT ON TABLE run_artifacts IS 'Töötlemiskatse ja artefakti seos';
COMMENT ON TABLE transcript_versions IS 'Automaatse drafti, ülevaatusdrafti või lõppversiooni kirje';
COMMENT ON TABLE transcript_artifacts IS 'Transkriptsiooniversiooni ja artefakti seos';
COMMENT ON TABLE transcript_participants IS 'Transkriptsiooniversiooni speaker-label ja päris osaleja seos';
COMMENT ON TABLE transcript_segments IS 'Transkriptsiooniversiooni tekstilõigud';
COMMENT ON TABLE transcript_segment_speakers IS 'Segmendi ühe või mitme kõneleja ajavahemik ja kindlus';
COMMENT ON TABLE review_candidates IS 'Diarizationi kahtlane koht ja kasutaja viimane otsus';

-- Common column comments
COMMENT ON COLUMN sources.id IS 'Kirje identifikaator';
COMMENT ON COLUMN sources.url IS 'Kasutaja sisestatud lähte-URL';
COMMENT ON COLUMN sources.source_type IS 'Lähteallika liik';
COMMENT ON COLUMN sources.title IS 'Lähtelehe pealkiri';
COMMENT ON COLUMN sources.description IS 'Lähtelehe kirjeldus';
COMMENT ON COLUMN sources.published_date IS 'Lähtelehe avaldamise aeg';
COMMENT ON COLUMN sources.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN sources.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN sources.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN sources.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN media_items.id IS 'Kirje identifikaator';
COMMENT ON COLUMN media_items.provider IS 'Meedia pakkuja';
COMMENT ON COLUMN media_items.external_id IS 'Pakkuja püsiv identifikaator';
COMMENT ON COLUMN media_items.canonical_url IS 'Meedia kanooniline URL';
COMMENT ON COLUMN media_items.media_type IS 'Meedia liik';
COMMENT ON COLUMN media_items.title IS 'Meedia pealkiri';
COMMENT ON COLUMN media_items.description IS 'Meedia kirjeldus';
COMMENT ON COLUMN media_items.published_date IS 'Meedia avaldamise aeg';
COMMENT ON COLUMN media_items.duration_second IS 'Meedia kestus sekundites';
COMMENT ON COLUMN media_items.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN media_items.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN media_items.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN media_items.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN media_assets.id IS 'Kirje identifikaator';
COMMENT ON COLUMN media_assets.media_item_id IS 'Seotud meediadokument';
COMMENT ON COLUMN media_assets.asset_type IS 'Tehnilise allika liik';
COMMENT ON COLUMN media_assets.url IS 'Tehnilise allika URL';
COMMENT ON COLUMN media_assets.version IS 'Allika versioon või ETag';
COMMENT ON COLUMN media_assets.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN media_assets.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN media_assets.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN media_assets.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN participants.id IS 'Kirje identifikaator';
COMMENT ON COLUMN participants.name IS 'Isiku nimi';
COMMENT ON COLUMN participants.description IS 'Isiku kirjeldus';
COMMENT ON COLUMN participants.organisation IS 'Isikuga seotud organisatsioon';
COMMENT ON COLUMN participants.occupation IS 'Isiku amet või roll';
COMMENT ON COLUMN participants.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN participants.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN participants.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN participants.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN jobs.id IS 'Kirje identifikaator';
COMMENT ON COLUMN jobs.source_id IS 'Kasutaja sisestatud lähteallikas';
COMMENT ON COLUMN jobs.media_item_id IS 'Kasutaja valitud meedia';
COMMENT ON COLUMN jobs.submitted_url IS 'Täpselt kasutaja sisestatud URL';
COMMENT ON COLUMN jobs.job_status_id IS 'Töö praegune olek';
COMMENT ON COLUMN jobs.error_code IS 'Töötluse veakood';
COMMENT ON COLUMN jobs.error_message IS 'Töötluse inimloetav veakirjeldus';
COMMENT ON COLUMN jobs.submitted_at IS 'Töö loomise aeg pärast kasutaja kinnitust';
COMMENT ON COLUMN jobs.resolved_at IS 'URL-i ja meedia lahendamise aeg';
COMMENT ON COLUMN jobs.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN jobs.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN jobs.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN jobs.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN job_statuses.id IS 'Kirje identifikaator';
COMMENT ON COLUMN job_statuses.code IS 'Masinloetav olekukood';
COMMENT ON COLUMN job_statuses.name_et IS 'Olekueesti keelne nimetus';
COMMENT ON COLUMN job_statuses.description_et IS 'Olekueesti keelne kirjeldus';
COMMENT ON COLUMN job_statuses.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN job_statuses.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN job_statuses.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN job_statuses.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN job_events.id IS 'Kirje identifikaator';
COMMENT ON COLUMN job_events.job_id IS 'Seotud töö';
COMMENT ON COLUMN job_events.job_status_id IS 'Sündmusega seotud olek';
COMMENT ON COLUMN job_events.event_type IS 'Sündmuse liik';
COMMENT ON COLUMN job_events.detail IS 'Sündmuse detail';
COMMENT ON COLUMN job_events.event_at IS 'Sündmuse aeg';
COMMENT ON COLUMN job_events.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN job_events.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN job_events.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN job_events.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN runs.id IS 'Kirje identifikaator';
COMMENT ON COLUMN runs.origin_job_id IS 'Run-i algatanud töö';
COMMENT ON COLUMN runs.media_item_id IS 'Töödeldud meedia';
COMMENT ON COLUMN runs.status IS 'Töötlemiskatse olek';
COMMENT ON COLUMN runs.attempt_number IS 'Töötlemiskatse järjekorranumber';
COMMENT ON COLUMN runs.input_fingerprint IS 'Töödeldud sisendi sõrmejälg';
COMMENT ON COLUMN runs.started_at IS 'Töötlemise algusaeg';
COMMENT ON COLUMN runs.finished_at IS 'Töötlemise lõppaeg';
COMMENT ON COLUMN runs.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN runs.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN runs.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN runs.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN job_runs.id IS 'Kirje identifikaator';
COMMENT ON COLUMN job_runs.job_id IS 'Töö';
COMMENT ON COLUMN job_runs.run_id IS 'Töötlemiskatse';
COMMENT ON COLUMN job_runs.relation_type IS 'CREATED või REUSED';
COMMENT ON COLUMN job_runs.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN job_runs.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN job_runs.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN job_runs.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN artifacts.id IS 'Kirje identifikaator';
COMMENT ON COLUMN artifacts.artifact_type IS 'Artefakti liik';
COMMENT ON COLUMN artifacts.path IS 'Faili asukoht failisüsteemis';
COMMENT ON COLUMN artifacts.content_type IS 'Faili MIME-tüüp';
COMMENT ON COLUMN artifacts.size_byte IS 'Faili suurus baitides';
COMMENT ON COLUMN artifacts.sha256 IS 'Faili SHA-256 kontrollsumma';
COMMENT ON COLUMN artifacts.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN artifacts.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN artifacts.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN artifacts.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN transcript_versions.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_versions.run_id IS 'Versiooni loonud töötlemiskatse';
COMMENT ON COLUMN transcript_versions.version_number IS 'Versiooni järjekorranumber';
COMMENT ON COLUMN transcript_versions.version_type IS 'AUTOMATIC_DRAFT, REVIEWED_DRAFT või FINAL';
COMMENT ON COLUMN transcript_versions.status IS 'Versiooni olek';
COMMENT ON COLUMN transcript_versions.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_versions.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_versions.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN transcript_versions.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN transcript_participants.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_participants.transcript_version_id IS 'Transkriptsiooniversioon';
COMMENT ON COLUMN transcript_participants.speaker_label IS 'Selle versiooni kohalik SPEAKER_nn tähis';
COMMENT ON COLUMN transcript_participants.participant_id IS 'Kinnitatud päris inimene; võib kuni kinnitamiseni olla NULL';
COMMENT ON COLUMN transcript_participants.role IS 'Osaleja roll';
COMMENT ON COLUMN transcript_participants.mapping_status IS 'UNCONFIRMED, CONFIRMED või UNKNOWN';
COMMENT ON COLUMN transcript_participants.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_participants.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_participants.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN transcript_participants.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN transcript_segments.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_segments.transcript_version_id IS 'Transkriptsiooniversioon';
COMMENT ON COLUMN transcript_segments.segment_number IS 'Segmendi järjekorranumber';
COMMENT ON COLUMN transcript_segments.start_second IS 'Segmendi algus helis';
COMMENT ON COLUMN transcript_segments.end_second IS 'Segmendi lõpp helis';
COMMENT ON COLUMN transcript_segments.text IS 'Segmendi tekst';
COMMENT ON COLUMN transcript_segments.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_segments.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_segments.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN transcript_segments.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN transcript_segment_speakers.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_segment_speakers.transcript_segment_id IS 'Transkriptsioonisegment';
COMMENT ON COLUMN transcript_segment_speakers.transcript_participant_id IS 'Versioonipõhine kõneleja';
COMMENT ON COLUMN transcript_segment_speakers.start_second IS 'Kõneleja lõigu algus segmendis';
COMMENT ON COLUMN transcript_segment_speakers.end_second IS 'Kõneleja lõigu lõpp segmendis';
COMMENT ON COLUMN transcript_segment_speakers.confidence IS 'Diarization-i kindlus vahemikus 0 kuni 1';
COMMENT ON COLUMN transcript_segment_speakers.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_segment_speakers.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_segment_speakers.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN transcript_segment_speakers.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN review_candidates.id IS 'Kirje identifikaator';
COMMENT ON COLUMN review_candidates.transcript_segment_id IS 'Ülevaadatav segment';
COMMENT ON COLUMN review_candidates.candidate_type IS 'Kahtluse liik';
COMMENT ON COLUMN review_candidates.reason IS 'Süsteemi põhjendus';
COMMENT ON COLUMN review_candidates.status IS 'PENDING, ACCEPTED, REJECTED või MODIFIED';
COMMENT ON COLUMN review_candidates.decision IS 'Kasutaja viimane otsus';
COMMENT ON COLUMN review_candidates.decision_at IS 'Kasutaja otsuse aeg';
COMMENT ON COLUMN review_candidates.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN review_candidates.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN review_candidates.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN review_candidates.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN run_artifacts.id IS 'Kirje identifikaator';
COMMENT ON COLUMN run_artifacts.run_id IS 'Töötlemiskatse';
COMMENT ON COLUMN run_artifacts.artifact_id IS 'Artefakt';
COMMENT ON COLUMN run_artifacts.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN run_artifacts.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN run_artifacts.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN run_artifacts.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON COLUMN transcript_artifacts.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_artifacts.transcript_version_id IS 'Transkriptsiooniversioon';
COMMENT ON COLUMN transcript_artifacts.artifact_id IS 'Artefakt';
COMMENT ON COLUMN transcript_artifacts.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_artifacts.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_artifacts.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN transcript_artifacts.last_updated IS 'Kirje viimase muutmise aeg';

-- ============================================================
-- Initial job statuses
-- ============================================================
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('QUEUED', 'Järjekorras', 'Töö ootab worker-i vabanemist.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('DOWNLOADING', 'Meedia allalaadimine', 'Laetakse alla töötlemiseks vajalik meedia.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('DIARIZING', 'Kõnelejate tuvastamine', 'Leitakse kõnelejate ajavahemikud.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('MERGING', 'Transkriptsiooni koostamine', 'Seotakse tekst kõnelejate tulemustega.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('WAITING_FOR_PARTICIPANTS', 'Osalejate kinnitamine', 'Kasutaja peab kõnelejad osalejatega siduma.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('IN_REVIEW', 'Ülevaatusel', 'Kasutaja vaatab diarization-i kahtlased kohad üle.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('SUCCEEDED', 'Valmis', 'Lõplik transkriptsioon on valmis.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('FAILED', 'Ebaõnnestus', 'Töötlus lõppes veaga.');
INSERT INTO job_statuses (code, name_et, description_et) VALUES ('CANCELLED', 'Katkestatud', 'Töötlus katkestati.');

COMMIT;
