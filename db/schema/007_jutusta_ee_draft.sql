-- Vabatahtlik Jutusta.ee uurimisversioon.
-- See versioon ei kuulu protsessi olekumasinasse ega kasutaja ülevaatuse voogu.
-- Käivita pärast 006_mvp2_3_backfill_waiting_participants.sql.

ALTER TABLE transcript_versions DROP CONSTRAINT transcript_versions_type_ck;

ALTER TABLE transcript_versions ADD CONSTRAINT transcript_versions_type_ck CHECK (
    version_type IN ('AUTOMATIC_DRAFT', 'REVIEWED_DRAFT', 'JUTUSTA_EE_DRAFT', 'FINAL')
);

COMMENT ON COLUMN transcript_versions.version_type IS
    'AUTOMATIC_DRAFT, REVIEWED_DRAFT, vabatahtlik JUTUSTA_EE_DRAFT või FINAL';

COMMIT;
