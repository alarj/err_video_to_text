-- MVP2.3 osalejate vaikeprofiilid ja saatehetke snapshot.
-- Käivita pärast 001_core_schema.sql ja seniseid migratsioone SQL Developeris
-- ühe skriptina. Skript muudab andmestruktuuri, kuid ei käivita rakendust.

CREATE SEQUENCE parties_seq START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE participant_details_seq START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE parties (
    id NUMBER DEFAULT parties_seq.NEXTVAL NOT NULL,
    name VARCHAR2(500) NOT NULL,
    short_name VARCHAR2(120),
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT parties_pk PRIMARY KEY (id),
    CONSTRAINT parties_name_uq UNIQUE (name)
);

CREATE TABLE participant_details (
    id NUMBER DEFAULT participant_details_seq.NEXTVAL NOT NULL,
    participant_id NUMBER NOT NULL,
    organisation VARCHAR2(500),
    occupation VARCHAR2(500),
    role VARCHAR2(120),
    party_id NUMBER,
    is_politician VARCHAR2(3) DEFAULT 'EI' NOT NULL,
    political_alignment VARCHAR2(20) DEFAULT 'NONE' NOT NULL,
    start_date DATE DEFAULT SYSDATE NOT NULL,
    end_date DATE,
    created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    last_updated TIMESTAMP,
    CONSTRAINT participant_details_pk PRIMARY KEY (id),
    CONSTRAINT participant_details_participant_fk
        FOREIGN KEY (participant_id) REFERENCES participants (id),
    CONSTRAINT participant_details_party_fk
        FOREIGN KEY (party_id) REFERENCES parties (id),
    CONSTRAINT participant_details_politician_ck
        CHECK (is_politician IN ('JAH', 'EI')),
    CONSTRAINT participant_details_alignment_ck
        CHECK (political_alignment IN ('KOALITSIOON', 'OPOSITSIOON', 'NONE'))
);

-- MVP2.3 esmane erakondade nimekiri. Lühinimi on kasutajaliidese abiväli;
-- snapshot'i salvestatakse alati ka erakonna täielik nimi.
INSERT ALL
    INTO parties (name, short_name) VALUES ('Keskerakond', 'Kesk')
    INTO parties (name, short_name) VALUES ('Sotsiaaldemokraatlik erakond', 'SDE')
    INTO parties (name, short_name) VALUES ('Isamaa erakond', 'IRL')
    INTO parties (name, short_name) VALUES ('Eesti Konservatiivne Rahvaerakond', 'EKRE')
    INTO parties (name, short_name) VALUES ('Eesti 200', 'E200')
    INTO parties (name, short_name) VALUES ('Erakond Parempoolsed', 'PP')
    INTO parties (name, short_name) VALUES ('Eesti Reformierakond', 'Ref')
    INTO parties (name, short_name) VALUES ('Erakond Eestimaa Rohelised', 'Rohe')
SELECT 1 FROM dual;

-- Ühel inimesel saab olla korraga ainult üks aktiivne vaikeprofiil.
CREATE UNIQUE INDEX participant_details_active_uq
    ON participant_details (CASE WHEN end_date IS NULL THEN participant_id END);

-- Olemasolevad tööandja ja ameti väärtused saavad esimese detailiversiooni.
INSERT INTO participant_details (participant_id, organisation, occupation)
SELECT id, organisation, occupation
  FROM participants;

ALTER TABLE transcript_participants ADD (
    organisation VARCHAR2(500),
    occupation VARCHAR2(500),
    party_id NUMBER,
    party_name VARCHAR2(500),
    is_politician VARCHAR2(3),
    political_alignment VARCHAR2(20)
);

ALTER TABLE transcript_participants ADD CONSTRAINT transcript_participants_party_fk
    FOREIGN KEY (party_id) REFERENCES parties (id);

ALTER TABLE transcript_participants ADD CONSTRAINT transcript_participants_politician_ck
    CHECK (is_politician IN ('JAH', 'EI') OR is_politician IS NULL);

ALTER TABLE transcript_participants ADD CONSTRAINT transcript_participants_alignment_ck
    CHECK (political_alignment IN ('KOALITSIOON', 'OPOSITSIOON', 'NONE')
        OR political_alignment IS NULL);

ALTER TABLE transcript_participants ADD CONSTRAINT transcript_participants_party_snapshot_ck
    CHECK (
        (party_id IS NULL AND party_name IS NULL)
        OR (party_id IS NOT NULL AND party_name IS NOT NULL)
    );

-- `description` jääb inimese kirjele vabalt muudetavaks; vaikimisi
-- organisatsioon ja amet elavad edaspidi detailiversioonis.
ALTER TABLE participants DROP COLUMN organisation;
ALTER TABLE participants DROP COLUMN occupation;

CREATE OR REPLACE VIEW participants_v AS
SELECT p.id,
       p.name,
       p.description,
       pd.id AS participant_detail_id,
       pd.organisation,
       pd.occupation,
       pd.role,
       pd.party_id,
       party.name AS party_name,
       pd.is_politician,
       pd.political_alignment
  FROM participants p
  JOIN participant_details pd
    ON pd.participant_id = p.id
   AND pd.end_date IS NULL
  LEFT JOIN parties party
    ON party.id = pd.party_id
 WHERE p.end_date IS NULL;

COMMENT ON TABLE parties IS 'Erakondade keskne register';
COMMENT ON COLUMN parties.id IS 'Kirje identifikaator';
COMMENT ON COLUMN parties.name IS 'Erakonna täielik nimi';
COMMENT ON COLUMN parties.short_name IS 'Erakonna lühinimi';
COMMENT ON COLUMN parties.start_date IS 'Kirje kehtivuse algus';
COMMENT ON COLUMN parties.end_date IS 'Kirje kehtivuse lõpp; NULL tähendab aktiivset kirjet';
COMMENT ON COLUMN parties.created IS 'Kirje loomise aeg';
COMMENT ON COLUMN parties.last_updated IS 'Kirje viimase muutmise aeg';

COMMENT ON TABLE participant_details IS
    'Osaleja ajaliselt versioonitud vaikeprofiil; ei ole saatehetke snapshot';
COMMENT ON COLUMN participant_details.id IS 'Kirje identifikaator';
COMMENT ON COLUMN participant_details.participant_id IS 'Seotud püsiv osaleja';
COMMENT ON COLUMN participant_details.organisation IS 'Osaleja vaikeorganisatsioon';
COMMENT ON COLUMN participant_details.occupation IS 'Osaleja vaikeamet';
COMMENT ON COLUMN participant_details.role IS 'Osaleja vaikimisi saateroll';
COMMENT ON COLUMN participant_details.party_id IS 'Osaleja vaikimisi erakond';
COMMENT ON COLUMN participant_details.is_politician IS 'Kas osaleja on poliitik: JAH või EI';
COMMENT ON COLUMN participant_details.political_alignment IS
    'Eesti poliitiline positsioon: KOALITSIOON, OPOSITSIOON või NONE';
COMMENT ON COLUMN participant_details.start_date IS 'Detailiversiooni kehtivuse algus';
COMMENT ON COLUMN participant_details.end_date IS
    'Detailiversiooni kehtivuse lõpp; NULL tähendab aktiivset vaikeprofiili';
COMMENT ON COLUMN participant_details.created IS 'Detailiversiooni loomise aeg';
COMMENT ON COLUMN participant_details.last_updated IS 'Detailiversiooni viimase muutmise aeg';

COMMENT ON TABLE transcript_participants IS
    'Versioonipõhine speaker-labeli, inimese ja saatehetke profiili snapshot';
COMMENT ON COLUMN transcript_participants.organisation IS
    'Osaleja organisatsioon selle transkriptsiooniversiooni saatehetkel';
COMMENT ON COLUMN transcript_participants.occupation IS
    'Osaleja amet selle transkriptsiooniversiooni saatehetkel';
COMMENT ON COLUMN transcript_participants.role IS
    'Osaleja saateroll selle transkriptsiooniversiooni saatehetkel';
COMMENT ON COLUMN transcript_participants.party_id IS
    'Erakonna viide analüüside jaoks; võib olla NULL';
COMMENT ON COLUMN transcript_participants.party_name IS
    'Erakonna ilmutatud nimi saatehetke snapshot''is; võib olla NULL';
COMMENT ON COLUMN transcript_participants.is_politician IS
    'Kas osaleja oli saatehetkel poliitik: JAH või EI';
COMMENT ON COLUMN transcript_participants.political_alignment IS
    'Saatehetke Eesti poliitiline positsioon: KOALITSIOON, OPOSITSIOON või NONE';

COMMENT ON TABLE participants_v IS
    'Aktiivse osaleja ja tema aktiivse vaikeprofiili lugemisvaade';
COMMENT ON COLUMN participants_v.id IS 'Osaleja püsiv identifikaator';
COMMENT ON COLUMN participants_v.name IS 'Osaleja nimi';
COMMENT ON COLUMN participants_v.description IS 'Osaleja vabalt muudetav kirjeldus';
COMMENT ON COLUMN participants_v.participant_detail_id IS 'Aktiivse detailiversiooni identifikaator';
COMMENT ON COLUMN participants_v.organisation IS 'Aktiivse detailiversiooni organisatsioon';
COMMENT ON COLUMN participants_v.occupation IS 'Aktiivse detailiversiooni amet';
COMMENT ON COLUMN participants_v.role IS 'Aktiivse detailiversiooni saateroll';
COMMENT ON COLUMN participants_v.party_id IS 'Aktiivse detailiversiooni erakonna identifikaator';
COMMENT ON COLUMN participants_v.party_name IS 'Aktiivse detailiversiooni erakonna nimi';
COMMENT ON COLUMN participants_v.is_politician IS 'Aktiivse detailiversiooni poliitiku staatus';
COMMENT ON COLUMN participants_v.political_alignment IS 'Aktiivse detailiversiooni poliitiline positsioon';
