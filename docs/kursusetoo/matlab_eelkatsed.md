# MATLABi eelkatsed ja teostusvõrdlus

See on ajalooline taustadokument. Siin kirjeldatud katsed ei ole praeguse
kolmeklassilise B1/B2/C1/D1/X1 mudelivaliku osa. Praegused võrreldavad
tulemused on failis [tulemused.md](tulemused.md).

## Binaarne `human_action_required` eeluuring

Esimeses ülesandes oli sihtmuutuja `human_action_required`: `MODIFIED` = 1
ning `ACCEPTED` ja `REJECTED` = 0. Treeningus oli 1 006 kandidaati ning
välises testis 341 kandidaati protsessidest 14–29. See ülesanne asendati
hiljem kolmeklassilise `decision`-ülesandega, sest algne inimotsus on
informatiivsem kui ainult küsimus, kas kandidaati muudeti.

| Mudel | Tunnused | Väline accuracy | Klassi 0 TPR | `MODIFIED` TPR/recall | `MODIFIED` FNR |
|---|---:|---:|---:|---:|---:|
| Fine Tree | 7 | 71,6% | 78,0% | 52,3% | 47,7% |
| Quadratic SVM | 7 | 78,6% | 84,7% | 60,5% | 39,5% |
| Efficient Logistic Regression | 7 | 77,4% | 85,5% | 53,5% | 46,5% |
| Boosted Trees | 7 | 78,6% | 84,7% | 60,5% | 39,5% |
| Fine Tree, `speakers` eemaldatud | 6 | 70,4% | 78,0% | 47,7% | 52,3% |
| Boosted Trees, `speakers` eemaldatud | 6 | 78,3% | 85,5% | 57,0% | 43,0% |
| Quadratic SVM, `speakers` eemaldatud | 6 | **78,6%** | 84,3% | **61,6%** | **38,4%** |
| Optimizable SVM, `speakers` eemaldatud | 6 | 77,7% | 83,1% | **61,6%** | **38,4%** |
| Quadratic SVM, `speakers` ja `max_confidence` eemaldatud | 5 | 77,7% | 83,5% | 60,5% | 39,5% |

Selles eeluuringus oli valitud binaarne kandidaat kuue tunnusega Quadratic
SVM. Seda valikut ei kanta üle praegusesse kolmeklassilisse mudelivõrdlusse.

Optimiseeritud SVM-i permutation importance'is olid tugevaimad
`candidate_type` (u 0,169), `words` (u 0,068), `spans` (u 0,041),
`show_speaker_count` (u 0,022) ja `duration_s` (u 0,019); `max_confidence`
oli peaaegu null (u 0,001). Olulisus kirjeldab mudeli sõltuvust tunnusest,
mitte põhjuslikku mõju inimese otsusele.

## Algne kuue tunnusega `decision`-eeluuring MATLABis

Seejärel katsetati sama välise testiga kolmeklassilist märgendit
`ACCEPTED`/`MODIFIED`/`REJECTED`, kuid kuue tunnusega (tunnus `speakers`
eemaldatud). See oli enne praegust kaheksa atribuudiga katseraami.

| Mudel | Valideerimisaccuracy | Väline accuracy | `ACCEPTED` recall | `MODIFIED` recall | `REJECTED` recall |
|---|---:|---:|---:|---:|---:|
| Quadratic SVM | 67,4% | 66,0% | 75,9% | **68,6%** | 32,8% |
| Boosted Trees | **69,0%** | **78,3%** | 95,3% | 62,8% | 48,4% |
| Bagged Trees | 65,6% | 71,6% | 88,0% | 50,0% | 51,6% |
| RUSBoosted Trees | 67,5% | 77,4% | **97,4%** | 41,9% | **65,6%** |
| Fine Gaussian SVM | 61,8% | 64,2% | 71,7% | **70,9%** | 32,8% |

Toona oli kandidaat Boosted Trees, kuid see tabel ei ole võrreldav praeguste
kaheksa atribuudiga 498 variandi tulemustega.

## Kaheksa atribuudiga Test1 MATLABis

2026-10-19 hinnati Test1-l 498 eelnevalt fikseeritud kaheksa atribuudiga
mudelivarianti. Test1 sisaldas 488 kandidaati 15 terviksaatest
(290 `ACCEPTED`, 107 `MODIFIED`, 91 `REJECTED`); treeningus oli 1 006
kandidaati 51 saatest. Testiridu ei kasutatud õpetamiseks ega eeltöötluse
parameetrite leidmiseks.

| Mudel | Tunnusevariant | Accuracy | Macro-F1 | Balanced accuracy |
|---|---|---:|---:|---:|
| kNN, k=10, equal | `duration_s` eemaldatud | **83,61%** | 74,83% | 73,90% |
| kNN, k=21, equal | `duration_s` eemaldatud | **83,61%** | 74,18% | 73,17% |
| kNN, k=7, equal | `duration_s` eemaldatud | 83,20% | 75,32% | 74,70% |
| kNN, k=15, inverse | `show_speaker_count` eemaldatud | 82,79% | **75,37%** | **74,89%** |
| kNN, k=7, equal | kõik 8 tunnust | 82,38% | 74,19% | 73,54% |
| Linear SVM | kõik 8 tunnust | 81,56% | 69,77% | 69,06% |
| Boosted Trees | kõik 8 tunnust | 81,35% | 72,60% | 72,19% |
| RUSBoosted Trees | kõik 8 tunnust | 81,76% | 72,41% | 72,26% |

Täielik MATLABi Test1 katseplaan ja mõõdikud on failis
[test1_matlab.md](test1_matlab.md). Toorväljundid on katse väljundkaustas
failides `models_test1.csv`, `perclass_test1.csv`, `confusion_test1.csv` ja
`predictions_test1.csv`.

## MATLABi ja GNU Octave'i Test1 teostusvõrdlus

2026-10-19–20 korrati sama 498 variandi Test1 plaan GNU Octave 11.1.0 ja
Octave Statistics 2.0.1 abil. Kõik 498/498 varianti lõpetasid `OK`-ga.
Kuue standardse `templateSVM` mudeli tolerants on `1e-3`, kasutatava
LIBSVM-i dokumenteeritud tavaväärtus; nii ei esinenud lõplikus seadistuses
iteratsioonipiiri hoiatusi.

| Võrdlusnäitaja | Tulemus |
|---|---:|
| Mõlema katse ennustusread | 243 024 |
| Tegeliku klassi erinevusi | 0 |
| Täielikult samade ennustustega variandid | 450 / 498 (90,4%) |
| Erinevad ennustusread | 2 722 / 243 024 (1,12%) |
| Täielikult kattuvad kNN-i variandid | 359 / 363 |
| MATLABiga täielikult kattuvad standardsed SVM-id | 53 / 54 |

Peamised erinevused koondusid `SVM Kernel`i, `Logistic Regression Kernel`i,
Bagged Treesi ja RUSBoosted Treesi eri teostustesse. Standardsete SVM-ide
tulemused kattusid MATLABiga praktiliselt täielikult; ainult Cubic SVM-i
täistunnuste variandil erineb üks ennustus. Edasises kordusõpetuses ja
testimises kasutatakse GNU Octave'it. Tehniline käivitusjuhis on failis
[test1_octave.md](test1_octave.md).
