-- MVP2.3: täienda ainult pooleliolevate osalejamäärangute saatehetke snapshot.
-- Käivita SQL Developeris pärast 005_mvp2_3_participant_profiles.sql.
-- Skript puudutab vaid aktiivseid REVIEWED_DRAFT ridu protsessides, mille olek
-- on WAITING_FOR_PARTICIPANTS ja millel on juba kinnitatud osaleja.

MERGE INTO transcript_participants target
USING (
    SELECT tp.id,
           profile.organisation,
           profile.occupation,
           profile.role AS default_role,
           profile.party_id,
           profile.party_name,
           profile.is_politician,
           profile.political_alignment
      FROM transcript_participants tp
      JOIN transcript_versions version_row
        ON version_row.id = tp.transcript_version_id
       AND version_row.version_type = 'REVIEWED_DRAFT'
       AND version_row.end_date IS NULL
      JOIN processes process_row
        ON process_row.id = version_row.process_id
       AND process_row.status = 'WAITING_FOR_PARTICIPANTS'
       AND process_row.end_date IS NULL
      JOIN participants_v profile
        ON profile.id = tp.participant_id
     WHERE tp.end_date IS NULL
       AND tp.mapping_status = 'CONFIRMED'
       AND tp.participant_id IS NOT NULL
       AND tp.organisation IS NULL
       AND tp.occupation IS NULL
       AND tp.party_id IS NULL
       AND tp.party_name IS NULL
       AND tp.is_politician IS NULL
       AND tp.political_alignment IS NULL
) source
ON (target.id = source.id)
WHEN MATCHED THEN UPDATE SET
    target.organisation = source.organisation,
    target.occupation = source.occupation,
    target.role = COALESCE(target.role, source.default_role),
    target.party_id = source.party_id,
    target.party_name = source.party_name,
    target.is_politician = source.is_politician,
    target.political_alignment = source.political_alignment,
    target.last_updated = SYSTIMESTAMP;
