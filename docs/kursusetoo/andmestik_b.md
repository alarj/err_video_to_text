# Andmestik B ja mudeli atribuudid

Treeningfail `training_data_b.csv` sisaldab algse faili kõiki 1006 rida samas
järjekorras. Kõik vanad veerud ja väärtused on säilitatud.

Mudeli kaheksa atribuuti: `duration_s`, `words`, `show_speaker_count`,
`candidate_type`, `internal_speaker_change_count`, `distinct_speaker_count`,
`dominant_speaker_coverage`, `nearest_change_edge_ratio`.
Vanu `spans`, `speakers`, `max_confidence` veerge mudeli atribuutide hulka ei valita.
ID-d ja `no` pole mudeli atribuudid. Vastuseks vali kas `decision` või
`human_action_required`; teine vastuseveerg tuleb sisenditest eemaldada.

Lisatud väljad arvutatakse ainult AUTOMATIC_DRAFT-ga seotud algsete
transcript.json ja speakers.json failide põhjal:

- `internal_speaker_change_count`: järjestatud toorintervallides erineva
  kõneleja alguste arv rangelt VTT lõigu sees. Sama kõneleja jätkumine pärast
  pausi ei ole vahetus. Vahetuse aeg on järgmise kõneleja intervalli algus;
  pausi keskele piiri ei oletata. Servatolerantsi ega mikrointervalli filtrit pole.
- `distinct_speaker_count`: positiivse kestusega lõiku katvate eri siltide arv.
- `dominant_speaker_coverage`: iga kõneleja lõiguga kattuvate intervallide
  ühendi kestus jagatuna lõigu kestusega; neist suurim. Kattuvat aega ei liideta topelt.
- `nearest_change_edge_ratio`: lähima sisemise vahetuse kaugus lähimast
  lõiguservast jagatuna lõigu kestusega; vahemik (0, 0.5]. Vahetuseta lõigul
  tühi CSV lahter. Treeningfailis puuduvaid väärtusi ei ole.

Eksport kontrollib automaatset päritolu, kandidaatide ID-sid, teksti ja aegu,
otsuste kooskõla, kasutusregistrit ja vanade CSV väärtuste säilimist.
Erinevate kõnelejate kattuvate toorintervallide puhul eksport peatub, et mitte
oletada kõnelejate järjestust. Treeningandmed läbisid kontrollid.
Failide päritolu ja SHA-256 kontrollsummad on
[`manifestid/dataset_b_manifest.json`](manifestid/dataset_b_manifest.json) failis.
Oracle'i kasutati ainult lugemiseks, SET TRANSACTION READ ONLY režiimis.

Testfail `test_data_b.csv` säilitab varasema testi kõik 341 kandidaati samas
järjekorras, kõigi seniste väärtuste ja siltidega. Kasutaja kinnitas 2026-10-17
ka protsessi 15 kandidaatide 171–178 säilitamise selles võrdlusvalimis.
Nende kaheksa kandidaadi otsused salvestati vana UI tõttu MODIFIED-na ning
tegelikke otsuseliike ei saa taastada. Erand on kirjeldatud kasutusregistris
ja manifestis; see ei laiene treeningule ega uutele testvalimitele.
Algseid CSV-sid ei muudetud.
