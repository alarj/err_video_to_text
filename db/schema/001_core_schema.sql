-- ERR2TEXT protsessi- ja tegevuspõhine Oracle'i põhiskeem.
-- Käivita SQL Developeris ühe skriptina.
-- Mahukate failide sisu andmebaasi ei salvestata; artifacts hoiab metaandmeid.

CREATE SEQUENCE sources_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE media_items_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE media_assets_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE participants_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE artifacts_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE processes_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE activities_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE activity_artifacts_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_versions_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_artifacts_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_participants_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_segments_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE transcript_segment_speakers_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE review_candidates_seq START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE sources (
    id NUMBER DEFAULT sources_seq.NEXTVAL NOT NULL,
    url VARCHAR2(2048) NOT NULL,
    source_type VARCHAR2(40) NOT NULL,
    title VARCHAR2(1000) NOT NULL,
    description VARCHAR2(4000),
    published_date TIMESTAMP,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT sources_pk PRIMARY KEY (id)
);

CREATE TABLE media_items (
    id NUMBER DEFAULT media_items_seq.NEXTVAL NOT NULL,
    provider VARCHAR2(80) NOT NULL,
    external_id VARCHAR2(256) NOT NULL,
    canonical_url VARCHAR2(2048) NOT NULL,
    media_type VARCHAR2(30) NOT NULL,
    title VARCHAR2(1000) NOT NULL,
    description VARCHAR2(4000),
    published_date TIMESTAMP,
    duration_second NUMBER(12,3),
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT media_items_pk PRIMARY KEY (id),
    CONSTRAINT media_items_provider_id_uq UNIQUE (provider, external_id),
    CONSTRAINT media_items_canonical_uq UNIQUE (canonical_url),
    CONSTRAINT media_items_type_ck CHECK (media_type IN ('VIDEO', 'AUDIO', 'OTHER')),
    CONSTRAINT media_items_duration_ck CHECK (duration_second IS NULL OR duration_second >= 0)
);

CREATE TABLE media_assets (
    id NUMBER DEFAULT media_assets_seq.NEXTVAL NOT NULL,
    media_item_id NUMBER NOT NULL,
    asset_type VARCHAR2(30) NOT NULL,
    url VARCHAR2(2048) NOT NULL,
    version VARCHAR2(256),
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT media_assets_pk PRIMARY KEY (id),
    CONSTRAINT media_assets_media_fk FOREIGN KEY (media_item_id) REFERENCES media_items (id),
    CONSTRAINT media_assets_type_ck CHECK (asset_type IN ('VIDEO', 'AUDIO', 'MANIFEST', 'VTT'))
);

CREATE TABLE participants (
    id NUMBER DEFAULT participants_seq.NEXTVAL NOT NULL,
    name VARCHAR2(500) NOT NULL,
    description VARCHAR2(4000),
    organisation VARCHAR2(500),
    occupation VARCHAR2(500),
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT participants_pk PRIMARY KEY (id)
);

CREATE TABLE artifacts (
    id NUMBER DEFAULT artifacts_seq.NEXTVAL NOT NULL,
    artifact_type VARCHAR2(80) NOT NULL,
    path VARCHAR2(2048) NOT NULL,
    content_type VARCHAR2(200) NOT NULL,
    size_byte NUMBER(19) NOT NULL,
    sha256 CHAR(64) NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT artifacts_pk PRIMARY KEY (id),
    CONSTRAINT artifacts_size_ck CHECK (size_byte >= 0),
    CONSTRAINT artifacts_sha256_ck CHECK (REGEXP_LIKE(sha256, '^[0-9A-Fa-f]{64}$'))
);

CREATE TABLE processes (
    id NUMBER DEFAULT processes_seq.NEXTVAL NOT NULL,
    parent_process_id NUMBER,
    source_id NUMBER NOT NULL,
    media_item_id NUMBER NOT NULL,
    status VARCHAR2(40) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT processes_pk PRIMARY KEY (id),
    CONSTRAINT processes_parent_fk FOREIGN KEY (parent_process_id) REFERENCES processes (id),
    CONSTRAINT processes_source_fk FOREIGN KEY (source_id) REFERENCES sources (id),
    CONSTRAINT processes_media_fk FOREIGN KEY (media_item_id) REFERENCES media_items (id),
    CONSTRAINT processes_status_ck CHECK (status IN ('DOWNLOADING', 'DIARIZING', 'WAITING_FOR_PARTICIPANTS', 'IN_REVIEW', 'WAITING_FOR_RESULT', 'FINISHED', 'CANCELLED')),
    CONSTRAINT processes_finished_ck CHECK ((finished_at IS NULL AND status NOT IN ('FINISHED', 'CANCELLED')) OR (finished_at IS NOT NULL AND status IN ('FINISHED', 'CANCELLED')))
);

CREATE TABLE activities (
    id NUMBER DEFAULT activities_seq.NEXTVAL NOT NULL,
    process_id NUMBER NOT NULL,
    previous_activity_id NUMBER,
    activity_type VARCHAR2(40) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    result VARCHAR2(20),
    execution_started_at TIMESTAMP,
    error_code VARCHAR2(80),
    error_message VARCHAR2(4000),
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT activities_pk PRIMARY KEY (id),
    CONSTRAINT activities_process_id_uq UNIQUE (process_id, id),
    CONSTRAINT activities_process_fk FOREIGN KEY (process_id) REFERENCES processes (id),
    CONSTRAINT activities_previous_fk FOREIGN KEY (process_id, previous_activity_id) REFERENCES activities (process_id, id),
    CONSTRAINT activities_type_ck CHECK (activity_type IN ('DOWNLOADING', 'DIARIZING', 'WAITING_FOR_PARTICIPANTS', 'IN_REVIEW', 'WAITING_FOR_RESULT')),
    CONSTRAINT activities_result_ck CHECK (result IN ('OK', 'ERROR', 'CANCELLED') OR result IS NULL),
    CONSTRAINT activities_finished_result_ck CHECK ((finished_at IS NULL AND result IS NULL) OR (finished_at IS NOT NULL AND result IS NOT NULL)),
    CONSTRAINT activities_error_ck CHECK ((result = 'ERROR' AND error_code IS NOT NULL AND error_message IS NOT NULL) OR (result IN ('OK', 'CANCELLED') AND error_code IS NULL AND error_message IS NULL) OR (result IS NULL AND error_code IS NULL AND error_message IS NULL))
);

CREATE TABLE activity_artifacts (
    id NUMBER DEFAULT activity_artifacts_seq.NEXTVAL NOT NULL,
    activity_id NUMBER NOT NULL,
    artifact_id NUMBER NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT activity_artifacts_pk PRIMARY KEY (id),
    CONSTRAINT activity_artifacts_activity_fk FOREIGN KEY (activity_id) REFERENCES activities (id),
    CONSTRAINT activity_artifacts_artifact_fk FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
    CONSTRAINT activity_artifacts_uq UNIQUE (activity_id, artifact_id)
);

CREATE TABLE transcript_versions (
    id NUMBER DEFAULT transcript_versions_seq.NEXTVAL NOT NULL,
    process_id NUMBER NOT NULL,
    activity_id NUMBER,
    version_number NUMBER(6) NOT NULL,
    version_type VARCHAR2(40) NOT NULL,
    status VARCHAR2(40) NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT transcript_versions_pk PRIMARY KEY (id),
    CONSTRAINT transcript_versions_process_id_uq UNIQUE (process_id, id),
    CONSTRAINT transcript_versions_process_fk FOREIGN KEY (process_id) REFERENCES processes (id),
    CONSTRAINT transcript_versions_activity_fk FOREIGN KEY (process_id, activity_id) REFERENCES activities (process_id, id),
    CONSTRAINT transcript_versions_number_ck CHECK (version_number > 0),
    CONSTRAINT transcript_versions_type_ck CHECK (version_type IN ('AUTOMATIC_DRAFT', 'REVIEWED_DRAFT', 'FINAL'))
);

CREATE TABLE transcript_artifacts (
    id NUMBER DEFAULT transcript_artifacts_seq.NEXTVAL NOT NULL,
    transcript_version_id NUMBER NOT NULL,
    artifact_id NUMBER NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT transcript_artifacts_pk PRIMARY KEY (id),
    CONSTRAINT transcript_artifacts_version_fk FOREIGN KEY (transcript_version_id) REFERENCES transcript_versions (id),
    CONSTRAINT transcript_artifacts_artifact_fk FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
    CONSTRAINT transcript_artifacts_uq UNIQUE (transcript_version_id, artifact_id)
);

CREATE TABLE transcript_participants (
    id NUMBER DEFAULT transcript_participants_seq.NEXTVAL NOT NULL,
    transcript_version_id NUMBER NOT NULL,
    speaker_label VARCHAR2(80) NOT NULL,
    participant_id NUMBER,
    role VARCHAR2(120) NOT NULL,
    mapping_status VARCHAR2(30) NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT transcript_participants_pk PRIMARY KEY (id),
    CONSTRAINT transcript_participants_version_fk FOREIGN KEY (transcript_version_id) REFERENCES transcript_versions (id),
    CONSTRAINT transcript_participants_participant_fk FOREIGN KEY (participant_id) REFERENCES participants (id),
    CONSTRAINT transcript_participants_status_ck CHECK (mapping_status IN ('UNCONFIRMED', 'CONFIRMED', 'UNKNOWN')),
    CONSTRAINT transcript_participants_confirm_ck CHECK (mapping_status <> 'CONFIRMED' OR participant_id IS NOT NULL),
    CONSTRAINT transcript_participants_uq UNIQUE (transcript_version_id, speaker_label)
);

CREATE TABLE transcript_segments (
    id NUMBER DEFAULT transcript_segments_seq.NEXTVAL NOT NULL,
    transcript_version_id NUMBER NOT NULL,
    segment_number NUMBER(12) NOT NULL,
    start_second NUMBER(12,3) NOT NULL,
    end_second NUMBER(12,3) NOT NULL,
    text VARCHAR2(4000) NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT transcript_segments_pk PRIMARY KEY (id),
    CONSTRAINT transcript_segments_version_fk FOREIGN KEY (transcript_version_id) REFERENCES transcript_versions (id),
    CONSTRAINT transcript_segments_number_ck CHECK (segment_number > 0),
    CONSTRAINT transcript_segments_time_ck CHECK (end_second >= start_second),
    CONSTRAINT transcript_segments_uq UNIQUE (transcript_version_id, segment_number)
);

CREATE TABLE transcript_segment_speakers (
    id NUMBER DEFAULT transcript_segment_speakers_seq.NEXTVAL NOT NULL,
    transcript_segment_id NUMBER NOT NULL,
    transcript_participant_id NUMBER NOT NULL,
    start_second NUMBER(12,3) NOT NULL,
    end_second NUMBER(12,3) NOT NULL,
    confidence NUMBER(6,5) NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT transcript_segment_speakers_pk PRIMARY KEY (id),
    CONSTRAINT transcript_segment_speakers_segment_fk FOREIGN KEY (transcript_segment_id) REFERENCES transcript_segments (id),
    CONSTRAINT transcript_segment_speakers_participant_fk FOREIGN KEY (transcript_participant_id) REFERENCES transcript_participants (id),
    CONSTRAINT transcript_segment_speakers_time_ck CHECK (end_second >= start_second),
    CONSTRAINT transcript_segment_speakers_confidence_ck CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT transcript_segment_speakers_uq UNIQUE (transcript_segment_id, transcript_participant_id, start_second, end_second)
);

CREATE TABLE review_candidates (
    id NUMBER DEFAULT review_candidates_seq.NEXTVAL NOT NULL,
    transcript_segment_id NUMBER NOT NULL,
    candidate_type VARCHAR2(40) NOT NULL,
    reason VARCHAR2(1000) NOT NULL,
    status VARCHAR2(30) NOT NULL,
    decision VARCHAR2(30),
    decision_at TIMESTAMP,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT review_candidates_pk PRIMARY KEY (id),
    CONSTRAINT review_candidates_segment_fk FOREIGN KEY (transcript_segment_id) REFERENCES transcript_segments (id),
    CONSTRAINT review_candidates_status_ck CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'MODIFIED'))
);

COMMENT ON TABLE sources IS 'Kasutaja sisestatud lähte-URL ja selle inimloetavad metaandmed';
COMMENT ON TABLE media_items IS 'Konkreetne valitud video-, audio- või muu meediadokument';
COMMENT ON TABLE media_assets IS 'Meediadokumendiga seotud tehnilised video-, audio-, manifesti- ja VTT-allikad';
COMMENT ON TABLE participants IS 'Globaalne vestlustes osalevate päris inimeste register';
COMMENT ON TABLE artifacts IS 'Failisüsteemis oleva artefakti metaandmed; faili sisu baasi ei salvestata';
COMMENT ON TABLE processes IS 'Üks kasutaja kinnitatud BPMN-i järgne transkribeerimisprotsess';
COMMENT ON TABLE activities IS 'Protsessi järjestikused tegevused koos alguse, lõpu ja lõpptulemusega';
COMMENT ON TABLE activity_artifacts IS 'Tegevuse ja selle loodud või kasutatud artefakti seos';
COMMENT ON TABLE transcript_versions IS 'Protsessi automaatse drafti, ülevaatusdrafti või lõppversiooni kirje';
COMMENT ON TABLE transcript_artifacts IS 'Transkriptsiooniversiooni ja artefakti seos';
COMMENT ON TABLE transcript_participants IS 'Versioonipõhise speaker-labeli ja päris osaleja seos';
COMMENT ON TABLE transcript_segments IS 'Transkriptsiooniversiooni tekstilised ja ajastatud lõigud';
COMMENT ON TABLE transcript_segment_speakers IS 'Segmendi ühe või mitme kõneleja ajavahemik ja kindlus';
COMMENT ON TABLE review_candidates IS 'Süsteemi märgitud kahtlane koht ja selle viimane ülevaatuse seis';

COMMENT ON COLUMN sources.id IS 'Kirje identifikaator';
COMMENT ON COLUMN sources.url IS 'Kasutaja sisestatud lähte-URL';
COMMENT ON COLUMN sources.source_type IS 'Lähteallika liik';
COMMENT ON COLUMN sources.title IS 'Lähtelehe või saate pealkiri';
COMMENT ON COLUMN sources.description IS 'Lähtelehe või saate inimloetav kirjeldus';
COMMENT ON COLUMN sources.published_date IS 'Lähtelehe avaldamise aeg, kui see on teada';
COMMENT ON COLUMN media_items.id IS 'Kirje identifikaator';
COMMENT ON COLUMN media_items.provider IS 'Meedia pakkuja';
COMMENT ON COLUMN media_items.external_id IS 'Pakkuja püsiv meediaidentifikaator';
COMMENT ON COLUMN media_items.canonical_url IS 'Valitud meedia kanooniline URL';
COMMENT ON COLUMN media_items.media_type IS 'Meedia liik: VIDEO, AUDIO või OTHER';
COMMENT ON COLUMN media_items.title IS 'Meedia pealkiri';
COMMENT ON COLUMN media_items.description IS 'Meedia kirjeldus, kui see on saadaval';
COMMENT ON COLUMN media_items.published_date IS 'Meedia avaldamise aeg, kui see on teada';
COMMENT ON COLUMN media_items.duration_second IS 'Meedia kestus sekundites';
COMMENT ON COLUMN media_assets.id IS 'Kirje identifikaator';
COMMENT ON COLUMN media_assets.media_item_id IS 'Seotud meediadokument';
COMMENT ON COLUMN media_assets.asset_type IS 'Tehnilise allika liik: VIDEO, AUDIO, MANIFEST või VTT';
COMMENT ON COLUMN media_assets.url IS 'Tehnilise allika URL';
COMMENT ON COLUMN media_assets.version IS 'Allika versioon või ETag, kui see on saadaval';
COMMENT ON COLUMN participants.id IS 'Kirje identifikaator';
COMMENT ON COLUMN participants.name IS 'Isiku nimi';
COMMENT ON COLUMN participants.description IS 'Isiku kirjeldus';
COMMENT ON COLUMN participants.organisation IS 'Isikuga seotud organisatsioon';
COMMENT ON COLUMN participants.occupation IS 'Isiku amet või roll';
COMMENT ON COLUMN artifacts.id IS 'Kirje identifikaator';
COMMENT ON COLUMN artifacts.artifact_type IS 'Artefakti liik';
COMMENT ON COLUMN artifacts.path IS 'Artefakti asukoht failisüsteemis';
COMMENT ON COLUMN artifacts.content_type IS 'Artefakti MIME-tüüp';
COMMENT ON COLUMN artifacts.size_byte IS 'Artefakti suurus baitides';
COMMENT ON COLUMN artifacts.sha256 IS 'Artefakti SHA-256 kontrollsumma';
COMMENT ON COLUMN processes.id IS 'Kirje identifikaator';
COMMENT ON COLUMN processes.parent_process_id IS 'Põhiprotsess; võib olla NULL';
COMMENT ON COLUMN processes.source_id IS 'Protsessi aluseks olev allikas';
COMMENT ON COLUMN processes.media_item_id IS 'Protsessis töödeldav valitud meediadokument';
COMMENT ON COLUMN processes.status IS 'Poolelioleva tegevuse liik või lõppstaatus FINISHED/CANCELLED';
COMMENT ON COLUMN processes.started_at IS 'Protsessi esimese tegevuse algusaeg';
COMMENT ON COLUMN processes.finished_at IS 'Protsessi lõppaeg; võib olla NULL';
COMMENT ON COLUMN activities.id IS 'Kirje identifikaator';
COMMENT ON COLUMN activities.process_id IS 'Protsess, mille koosseisu tegevus kuulub';
COMMENT ON COLUMN activities.previous_activity_id IS 'Sama protsessi eelmine tegevus; esimese puhul NULL';
COMMENT ON COLUMN activities.activity_type IS 'BPMN-i tegevuse liik';
COMMENT ON COLUMN activities.started_at IS 'Tegevuse äriline algusaeg';
COMMENT ON COLUMN activities.finished_at IS 'Tegevuse lõppaeg; pooleli tegevuse puhul NULL';
COMMENT ON COLUMN activities.result IS 'OK, ERROR või CANCELLED; tekib koos lõpuajaga';
COMMENT ON COLUMN activities.execution_started_at IS 'Aeg, millal worker tausttegevuse hõivas; ei ole äriline staatus';
COMMENT ON COLUMN activities.error_code IS 'Tegevuse veakood ainult ERROR tulemuse korral';
COMMENT ON COLUMN activities.error_message IS 'Inimloetav veateade ainult ERROR tulemuse korral';
COMMENT ON COLUMN activity_artifacts.id IS 'Kirje identifikaator';
COMMENT ON COLUMN activity_artifacts.activity_id IS 'Seotud tegevus';
COMMENT ON COLUMN activity_artifacts.artifact_id IS 'Seotud artefakt';
COMMENT ON COLUMN transcript_versions.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_versions.process_id IS 'Protsess, mille käigus versioon loodi';
COMMENT ON COLUMN transcript_versions.activity_id IS 'Versiooni loonud tegevus; võib olla NULL';
COMMENT ON COLUMN transcript_versions.version_number IS 'Versiooni järjekorranumber protsessis';
COMMENT ON COLUMN transcript_versions.version_type IS 'AUTOMATIC_DRAFT, REVIEWED_DRAFT või FINAL';
COMMENT ON COLUMN transcript_versions.status IS 'Transkriptsiooniversiooni sisuline seis';
COMMENT ON COLUMN transcript_artifacts.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_artifacts.transcript_version_id IS 'Seotud transkriptsiooniversioon';
COMMENT ON COLUMN transcript_artifacts.artifact_id IS 'Seotud artefakt';
COMMENT ON COLUMN transcript_participants.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_participants.transcript_version_id IS 'Seotud transkriptsiooniversioon';
COMMENT ON COLUMN transcript_participants.speaker_label IS 'Selle versiooni kohalik anonüümne SPEAKER_nn tähis';
COMMENT ON COLUMN transcript_participants.participant_id IS 'Kinnitatud päris inimene; võib kuni kinnitamiseni olla NULL';
COMMENT ON COLUMN transcript_participants.role IS 'Osaleja roll saates';
COMMENT ON COLUMN transcript_participants.mapping_status IS 'UNCONFIRMED, CONFIRMED või UNKNOWN';
COMMENT ON COLUMN transcript_segments.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_segments.transcript_version_id IS 'Seotud transkriptsiooniversioon';
COMMENT ON COLUMN transcript_segments.segment_number IS 'Segmendi järjekorranumber versioonis';
COMMENT ON COLUMN transcript_segments.start_second IS 'Segmendi algus helis sekundites';
COMMENT ON COLUMN transcript_segments.end_second IS 'Segmendi lõpp helis sekundites';
COMMENT ON COLUMN transcript_segments.text IS 'Segmendi transkriptsioonitekst';
COMMENT ON COLUMN transcript_segment_speakers.id IS 'Kirje identifikaator';
COMMENT ON COLUMN transcript_segment_speakers.transcript_segment_id IS 'Seotud transkriptsioonisegment';
COMMENT ON COLUMN transcript_segment_speakers.transcript_participant_id IS 'Versioonipõhine kõneleja';
COMMENT ON COLUMN transcript_segment_speakers.start_second IS 'Kõneleja ajavahemiku algus segmendis';
COMMENT ON COLUMN transcript_segment_speakers.end_second IS 'Kõneleja ajavahemiku lõpp segmendis';
COMMENT ON COLUMN transcript_segment_speakers.confidence IS 'Diariseerimise kindlus vahemikus 0 kuni 1';
COMMENT ON COLUMN review_candidates.id IS 'Kirje identifikaator';
COMMENT ON COLUMN review_candidates.transcript_segment_id IS 'Ülevaadatav transkriptsioonisegment';
COMMENT ON COLUMN review_candidates.candidate_type IS 'Süsteemi märgitud kahtluse liik';
COMMENT ON COLUMN review_candidates.reason IS 'Süsteemi põhjendus kahtluse märkimiseks';
COMMENT ON COLUMN review_candidates.status IS 'PENDING, ACCEPTED, REJECTED või MODIFIED';
COMMENT ON COLUMN review_candidates.decision IS 'Kasutaja viimane otsus';
COMMENT ON COLUMN review_candidates.decision_at IS 'Kasutaja viimase otsuse aeg';

COMMENT ON COLUMN sources.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN sources.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN sources.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN sources.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN media_items.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN media_items.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN media_items.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN media_items.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN media_assets.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN media_assets.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN media_assets.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN media_assets.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN participants.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN participants.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN participants.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN participants.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN artifacts.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN artifacts.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN artifacts.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN artifacts.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN processes.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN processes.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN processes.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN processes.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN activities.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN activities.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN activities.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN activities.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN activity_artifacts.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN activity_artifacts.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN activity_artifacts.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN activity_artifacts.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_versions.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_versions.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_versions.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_versions.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_artifacts.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_artifacts.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_artifacts.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_artifacts.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_participants.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_participants.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_participants.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_participants.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_segments.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_segments.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_segments.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_segments.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_segment_speakers.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN transcript_segment_speakers.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN transcript_segment_speakers.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN transcript_segment_speakers.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';
COMMENT ON COLUMN review_candidates.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN review_candidates.end_date IS 'Kirje sulgemise aeg soft delete korral';
COMMENT ON COLUMN review_candidates.created IS 'Kirje loomise aeg UTC-ajateljel';
COMMENT ON COLUMN review_candidates.last_updated IS 'Kirje viimase muutmise aeg UTC-ajateljel';

COMMIT;
