-- Lubab materialiseerimise aktiivse protsessi oleku olemasolevas MVP2.2 baasis.

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
