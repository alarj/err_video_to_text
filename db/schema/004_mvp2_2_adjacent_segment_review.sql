-- MVP2.2 kandidaadi naaberlõigu paranduse metadata.
-- Käivita pärast 003_mvp2_2_process_status.sql.

CREATE SEQUENCE transcript_segment_modifications_seq START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE transcript_segment_modifications (
    id NUMBER DEFAULT transcript_segment_modifications_seq.NEXTVAL NOT NULL,
    transcript_segment_id NUMBER NOT NULL,
    trigger_candidate_id NUMBER NOT NULL,
    relative_position VARCHAR2(8) NOT NULL,
    change_type VARCHAR2(40) NOT NULL,
    status VARCHAR2(20) DEFAULT 'USER_MODIFIED' NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT transcript_segment_modifications_pk PRIMARY KEY (id),
    CONSTRAINT transcript_segment_modifications_segment_fk
        FOREIGN KEY (transcript_segment_id) REFERENCES transcript_segments (id),
    CONSTRAINT transcript_segment_modifications_candidate_fk
        FOREIGN KEY (trigger_candidate_id) REFERENCES review_candidates (id),
    CONSTRAINT transcript_segment_modifications_position_ck
        CHECK (relative_position IN ('PREVIOUS', 'NEXT')),
    CONSTRAINT transcript_segment_modifications_type_ck
        CHECK (change_type IN ('SPEAKER_REASSIGNMENT', 'TEXT_EDIT', 'SPLIT', 'SYSTEM_NOTICE')),
    CONSTRAINT transcript_segment_modifications_status_ck
        CHECK (status = 'USER_MODIFIED'),
    CONSTRAINT transcript_segment_modifications_uq
        UNIQUE (transcript_segment_id, trigger_candidate_id, relative_position, change_type)
);

COMMENT ON TABLE transcript_segment_modifications IS
    'Kandidaadi kõrval käsitsi muudetud REVIEWED_DRAFT segmendi päritolu';
COMMENT ON COLUMN transcript_segment_modifications.trigger_candidate_id IS
    'Kandidaat, mille ülevaatuse käigus naaberlõiku muudeti';
COMMENT ON COLUMN transcript_segment_modifications.relative_position IS
    'Naaberlõigu asukoht kandidaadi suhtes: PREVIOUS või NEXT';
COMMENT ON COLUMN transcript_segment_modifications.change_type IS
    'Naaberlõigu tehtud muudatuse liik';
COMMENT ON COLUMN transcript_segment_modifications.status IS
    'Metadata märgend, väärtus on alati USER_MODIFIED';

COMMIT;
