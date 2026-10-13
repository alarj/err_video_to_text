-- MVP2.2 ülevaatuse jaoks vajalikud skeemitäiendused.
-- Käivita pärast 001_core_schema.sql ühe Oracle'i skriptina.

ALTER TABLE activities DROP CONSTRAINT activities_type_ck;

ALTER TABLE activities ADD CONSTRAINT activities_type_ck CHECK (
    activity_type IN (
        'DOWNLOADING',
        'DIARIZING',
        'MATERIALIZING_AUTOMATIC_DRAFT',
        'WAITING_FOR_PARTICIPANTS',
        'IN_REVIEW',
        'WAITING_FOR_RESULT'
    )
);

ALTER TABLE processes DROP CONSTRAINT processes_status_ck;

ALTER TABLE processes ADD CONSTRAINT processes_status_ck CHECK (
    status IN (
        'DOWNLOADING',
        'DIARIZING',
        'MATERIALIZING_AUTOMATIC_DRAFT',
        'WAITING_FOR_PARTICIPANTS',
        'IN_REVIEW',
        'WAITING_FOR_RESULT',
        'FINISHED',
        'CANCELLED'
    )
);

ALTER TABLE transcript_participants MODIFY role VARCHAR2(120) NULL;

ALTER TABLE transcript_segments ADD (
    segment_type VARCHAR2(20) DEFAULT 'SPEECH' NOT NULL,
    source_segment_id NUMBER
);

ALTER TABLE transcript_segments ADD CONSTRAINT transcript_segments_type_ck
    CHECK (segment_type IN ('SPEECH', 'SYSTEM_NOTICE'));

ALTER TABLE transcript_segments ADD CONSTRAINT transcript_segments_source_fk
    FOREIGN KEY (source_segment_id) REFERENCES transcript_segments (id);

COMMENT ON COLUMN activities.activity_type IS
    'Protsessi tegevus; MVP2.2 sisaldab automaatse drafti materialiseerimist';
COMMENT ON COLUMN transcript_participants.role IS
    'Osaleja roll; enne kasutaja kinnitust võib olla NULL';
COMMENT ON COLUMN transcript_segments.segment_type IS
    'Segmendi liik: kõne või süsteemi ekraaniteade';
COMMENT ON COLUMN transcript_segments.source_segment_id IS
    'Algse automaatse drafti segment, millest parandatud segment tulenes';
