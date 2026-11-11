-- MVP3: keskse ORDS-i taustatööde järjekorra seos.
-- Ajaloolisi processes/activities kirjeid ei registreerita tagantjärele.

CREATE SEQUENCE background_operations_seq START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE background_operations (
    operation_id NUMBER(19) DEFAULT background_operations_seq.NEXTVAL NOT NULL,
    public_id VARCHAR2(36 CHAR) NOT NULL,
    process_id NUMBER NOT NULL,
    previous_operation_id NUMBER(19),
    operation_type VARCHAR2(40 CHAR) NOT NULL,
    attempt_number NUMBER(9) NOT NULL,
    idempotency_key VARCHAR2(250 CHAR) NOT NULL,
    ords_job_id NUMBER(19),
    registration_error_code VARCHAR2(100 CHAR),
    registration_error_message VARCHAR2(2000 CHAR),
    ords_registered_at TIMESTAMP,
    local_started_at TIMESTAMP,
    local_completed_at TIMESTAMP,
    local_outcome VARCHAR2(30 CHAR),
    local_error_code VARCHAR2(100 CHAR),
    local_error_message VARCHAR2(2000 CHAR),
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT background_operations_pk PRIMARY KEY (operation_id),
    CONSTRAINT background_ops_public_id_uq UNIQUE (public_id),
    CONSTRAINT background_ops_process_op_uq UNIQUE (process_id, operation_id),
    CONSTRAINT background_ops_attempt_uq UNIQUE (process_id, operation_type, attempt_number),
    CONSTRAINT background_ops_idempotency_uq UNIQUE (idempotency_key),
    CONSTRAINT background_ops_ords_job_uq UNIQUE (ords_job_id),
    CONSTRAINT background_ops_process_fk FOREIGN KEY (process_id) REFERENCES processes (id),
    CONSTRAINT background_ops_previous_fk
        FOREIGN KEY (process_id, previous_operation_id)
        REFERENCES background_operations (process_id, operation_id),
    CONSTRAINT background_ops_type_ck CHECK (operation_type IN ('diarization')),
    CONSTRAINT background_ops_attempt_ck CHECK (attempt_number > 0),
    CONSTRAINT background_ops_outcome_ck
        CHECK (local_outcome IN ('SUCCEEDED', 'FAILED', 'INTERRUPTED') OR local_outcome IS NULL),
    CONSTRAINT background_ops_local_time_ck CHECK (
        (local_completed_at IS NULL AND local_outcome IS NULL)
        OR (local_completed_at IS NOT NULL AND local_outcome IS NOT NULL)
    ),
    CONSTRAINT background_ops_local_error_ck CHECK (
        (local_outcome = 'SUCCEEDED' AND local_error_code IS NULL AND local_error_message IS NULL)
        OR (local_outcome IN ('FAILED', 'INTERRUPTED') AND local_error_code IS NOT NULL AND local_error_message IS NOT NULL)
        OR (local_outcome IS NULL AND local_error_code IS NULL AND local_error_message IS NULL)
    )
);

COMMENT ON TABLE background_operations IS
    'Rakenduse taustatoimingute seos autoriteetse ORDS-i järjekorraga; ei ole kohalik järjekord';
COMMENT ON COLUMN background_operations.operation_id IS
    'Rakenduse toimingu ID ja ORDS application_job_id';
COMMENT ON COLUMN background_operations.public_id IS 'Toimingu muutumatu UUID';
COMMENT ON COLUMN background_operations.process_id IS 'ERR-i äriprotsess, mille automaatset etappi toiming täidab';
COMMENT ON COLUMN background_operations.previous_operation_id IS
    'Sama protsessi eelnev taustatoiming; praegusel diarization-toimingul NULL';
COMMENT ON COLUMN background_operations.operation_type IS 'ORDS job_type_code';
COMMENT ON COLUMN background_operations.attempt_number IS 'Sama protsessi ja toiminguliigi katse number';
COMMENT ON COLUMN background_operations.idempotency_key IS 'ORDS-i registreerimise muutumatu idempotentsusvõti';
COMMENT ON COLUMN background_operations.ords_job_id IS 'ORDS-i autoriteetse töö ID';
COMMENT ON COLUMN background_operations.registration_error_code IS 'Viimase ORDS-i registreerimiskatse veakood';
COMMENT ON COLUMN background_operations.registration_error_message IS 'Viimase ORDS-i registreerimiskatse veateade';
COMMENT ON COLUMN background_operations.ords_registered_at IS 'ORDS-i töö ID eduka sidumise aeg';
COMMENT ON COLUMN background_operations.local_started_at IS 'Rakenduse adapteri tegelik algusaeg';
COMMENT ON COLUMN background_operations.local_completed_at IS 'Rakenduse adapteri tegelik lõppaeg';
COMMENT ON COLUMN background_operations.local_outcome IS 'Rakenduse adapteri kohalik tulemus';
COMMENT ON COLUMN background_operations.local_error_code IS 'Rakenduse adapteri kohaliku vea kood';
COMMENT ON COLUMN background_operations.local_error_message IS 'Rakenduse adapteri kohaliku vea kirjeldus';

COMMENT ON COLUMN activities.execution_started_at IS
    'Rakenduse etapi tegelik käivitusaeg; ei anna käivitamisõigust ega moodusta kohalikku järjekorda';
