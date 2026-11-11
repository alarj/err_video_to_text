# Binaarse inimsekkumise mudeli tulemused

## Eesmärk ja märgend

See katse hindab enne otsuse `ACCEPTED` või `REJECTED` tegemist ainult seda,
kas kandidaat vajab inimese sisulist sekkumist. Vastus on tuletatud juba
kontrollitud kolme klassi otsusest; uusi käsitsi määratud silte ei lisata.

| Algne `decision` | `human_interaction_required` | Tähendus |
|---|---:|---|
| `ACCEPTED` | 0 | inimsekkumine ei ole vajalik |
| `REJECTED` | 0 | inimsekkumine ei ole vajalik |
| `MODIFIED` | 1 | inimsekkumine on vajalik |

Binaarne katse on seotud olemasoleva kolme klassi katsega, kuid ei asenda
seda. Kolme klassi tulemused jäävad faili [tulemused.md](tulemused.md) ja
kõik selle lähte- ning tulemusefailid säilivad muutmata kujul.

## Andmed ja atribuudid

Kasutatakse samu kuut treeningu/testi jaotust B1, B2, C1, D1, X1 ja Y1 ning
samu kaheksat atribuuti nagu kolme klassi katses.

| Atribuut | Tähendus |
|---|---|
| `duration_s` | kandidaadilõigu kestus sekundites |
| `words` | kandidaadilõigu sõnade arv |
| `show_speaker_count` | saates tuvastatud eri kõnelejate arv |
| `candidate_type` | kandidaadi tüüp |
| `internal_speaker_change_count` | kandidaadilõigu sees olevate kõnelejavahetuste arv |
| `distinct_speaker_count` | kandidaadilõiku katvate eri kõnelejate arv |
| `dominant_speaker_coverage` | kõige enam lõiku katva kõneleja osakaal lõigu kestusest |
| `nearest_change_edge_ratio` | lähima sisemise kõnelejavahetuse kaugus lähimast lõiguservast, jagatuna lõigu kestusega |

Igas uues CSV-failis on vana `decision` veerg asendatud ainult veeruga
`human_interaction_required`. Seetõttu ei saa algset otsust mudeli sisendina
kasutada. Täpne failide koosseis, klassijaotused ja kontrollsummad on failis
[manifestid/inimsekkumise_andmed.json](manifestid/inimsekkumise_andmed.json).

| Tähis | Treening ja test | Treeninguridu | Testiridu |
|---|---|---:|---:|
| B1 | B-treening ja fikseeritud Test1 | 1 006 | 488 |
| B2 | B-treening ja fikseeritud Test2 | 1 006 | 337 |
| C1 | C 70/30 jaotus | 1 277 | 554 |
| D1 | D 70/30 jaotus | 1 283 | 548 |
| X1 | X kandidaatipõhine 70/30 jaotus | 1 281 | 550 |
| Y1 | Y kandidaatipõhine 70/30 jaotus | 1 281 | 550 |

## Mudelivariandid

Katseplaanis on samad 498 mudeli-/atribuudivarianti nagu kolme klassi
katses: otsustuspuud (`Fine`, `Medium`, `Coarse`), lineaarne, kvadraatne ja
kuup-SVM, Gaussian SVM-id (`Fine`, `Medium`, `Coarse`), SVM-kernel,
ansamblid (`Boosted Trees`, `Bagged Trees`, `RUSBoosted Trees`), Kernel Naive
Bayes, Logistic Regression Kernel ja kNN. kNN-is kasutatakse naabrite arve
`1`, `3`, `5`, `7`, `10`, `15`, `21`, `31`, `51`, `75`, `100` ning kaale
`equal`, `inverse`, `squaredinverse`. Iga sobiva mudeli puhul katsetatakse
kõiki kaheksat atribuuti ja variante, kus üks atribuut on eemaldatud.

Kuue `templateSVM` mudeli tolerants on `1e-3`, nagu senistes Octave'i
katsetes.

## Mudelite hindamine ja valik

Esimese astme mudel otsustab ainult, kas inimsekkumine on vajalik. Ennustatud
`0` liigub hiljem automaatse otsuse harusse; ennustatud `1` on `MODIFIED`.

Mudelite valikul ei kasutata suvaliste kaaludega koondskoori. Iga B1, B2, C1,
D1, X1 ja Y1 testi kohta arvutatakse:

| Näitaja | Tähendus | Soovitud suund |
|---|---|---|
| Recall(1) / TPR(1) | tegelikult inimsekkumist vajavate kandidaatide leitavus | kõrgem |
| FNR(1) | inimsekkumist vajavate kandidaatide osa, mis liigub ekslikult automaatharusse | madalam |
| Automaatharu õigsus / NPV(0) | ennustatud nullide osakaal, mille puhul inimsekkumist tegelikult ei olnud vaja | kõrgem |
| Automaatharu osakaal | kõigi kandidaatide osa, mis mudeli järgi liigub automaatharusse | kõrgem |
| Balanced accuracy | 0 ja 1 klassi recall'ide keskmine | kõrgem |
| F1(1) | inimsekkumist vajava klassi precision'i ja recall'i harmooniline keskmine | kõrgem |

Valikukõlblik on variant, millel on automaatharu kõigis kuues testis; seega
peab igas testis olema vähemalt üks ennustatud `0` ning NPV(0) peab olema
arvutatav. Valik tehakse kuue testi põhjal järjekorras: esmalt võrreldakse
halvimat Recall(1) tulemust, seejärel halvimat NPV(0) tulemust, siis
automaatharu keskmist osakaalu; balanced accuracy keskmine ja F1(1) keskmine
on viigilahendajad. See on esimese astme valikureegel. Teise astme
`ACCEPTED`/`REJECTED` mudel ei kuulu veel sellesse katsetesse.

## Tulemused

Kõik 498 mudeli-/atribuudivarianti on hinnatud B1, B2, C1, D1, X1 ja Y1
testil. Neist 489 on esimese astme automaatotsuse jaoks valikukõlblikud.
Üheksa `Logistic Regression Kernel` varianti ennustasid kõigis testides ainult
klassi `1`; neil automaatharu puudub ning NPV(0) ei ole määratav.

Praeguse valikureegli järgi on esikohal `RUSBoosted Trees`, millelt on
eemaldatud atribuut `words`. Selle halvim Recall(1) kuue testi hulgas on
80,00%, halvim NPV(0) 82,01%, automaatharu keskmine osakaal 45,10%, balanced
accuracy keskmine 72,72% ja F1(1) keskmine 67,59%.

| Test | Recall(1) / TPR(1) | NPV(0) | Automaatharu osakaal | Balanced accuracy | F1(1) |
|---|---:|---:|---:|---:|---:|
| B1 | 82,24% | 93,97% | 64,55% | 79,97% | 62,86% |
| B2 | 90,73% | 86,00% | 29,67% | 68,48% | 70,62% |
| C1 | 80,00% | 82,01% | 43,14% | 68,91% | 64,91% |
| D1 | 84,33% | 85,47% | 42,70% | 72,38% | 68,93% |
| X1 | 81,31% | 84,19% | 46,00% | 72,35% | 68,10% |
| Y1 | 85,05% | 86,94% | 44,55% | 74,22% | 70,13% |

Täielik 498 variandi tabel on failis
[mudelivariantide_koondtulemused2.md](mudelivariantide_koondtulemused2.md).
