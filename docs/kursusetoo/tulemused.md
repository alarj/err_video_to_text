# Kursusetöö tulemused

> **AI märkus:** dokument koondab praeguse kolmeklassilise `decision`-
> ülesande GNU Octave'i tulemused. See põhineb kasutaja juhistel, fikseeritud
> andmevalimitel ja katseväljunditel. Varasemad MATLABi eelkatsed on eraldi
> dokumendis [matlab_eelkatsed.md](matlab_eelkatsed.md).

## Sisukord

1. [Eesmärk ja märgend](#eesmärk-ja-märgend)
2. [Andmed ja katsete tähistused](#andmed-ja-katsete-tähistused)
3. [Mudelite, tunnusevariantide ja andmejaotuste võrdlus](#mudelite-tunnusevariantide-ja-andmejaotuste-võrdlus)
4. [Edasine katseplaan](#edasine-katseplaan)
5. [Versiooniajalugu](#versiooniajalugu)

## Eesmärk ja märgend

Praegune ülesanne ennustab inimese lõppotsust tunnusega `decision`:
`ACCEPTED`, `MODIFIED` või `REJECTED`. 498 fikseeritud mudelivarianti
kasutavad samu kaheksat atribuuti ning nende tulemused on GNU Octave'i
teostuse tulemused. Neile lisaks on dokumendis eraldi MATLABi `fitcnet`
Narrow Neural Networki katse samade kaheksa atribuudiga.

Mudelil on 8 atribuuti:

| Atribuut | Lühikirjeldus |
|---|---|
| `duration_s` | kandidaadilõigu kestus sekundites |
| `words` | kandidaadilõigu sõnade arv |
| `show_speaker_count` | saates tuvastatud eri kõnelejate arv |
| `candidate_type` | kandidaadi tüüp |
| `internal_speaker_change_count` | kandidaadilõigu sees olevate kõnelejavahetuste arv |
| `distinct_speaker_count` | kandidaadilõiku katvate eri kõnelejate arv |
| `dominant_speaker_coverage` | kõige enam lõiku katva kõneleja osakaal lõigu kestusest |
| `nearest_change_edge_ratio` | lähima sisemise kõnelejavahetuse kaugus lähimast lõiguservast, jagatuna lõigu kestusega |

### Toorkandidaatide tihedus osalejate arvu järgi

Kontroll hõlmab kõiki 109 aktiivset `AUTOMATIC_DRAFT` protsessi, kus on
aktiivseid diariseerimise kandidaate: kokku 3027 käsitsi parandamise eelset
toorkandidaati. Iga saate kohta on arvutatud kandidaatide tihedus viie minuti
kohta ning rühma keskmine annab igale saatele võrdse kaalu.

| Osalejate arv | Saateid | Min kandidaate 5 min saate kohta | Maks kandidaate 5 min saate kohta | Keskmine kandidaate 5 min saate kohta | Mediaan kandidaate 5 min saate kohta |
|---|---:|---:|---:|---:|---:|
| 2 | 73 | 0,639 | 12,313 | 4,801 | 4,457 |
| 3 | 15 | 1,889 | 8,378 | 4,216 | 3,868 |
| 4+ | 21 | 1,467 | 7,902 | 4,116 | 3,997 |
| **Kõik saated** | **109** | 0,639 | 12,313 | 4,589 | 4,150 |

Täielik arvutuskäik ja toorandmete definitsioon on failis
[diariseerimise_kandidaatide_tihedus.md](diariseerimise_kandidaatide_tihedus.md).

## Andmed ja katsete tähistused

Andmekasutus ja protsesside täpsed nimekirjad on autoriteetselt failis
[evaluation_data.md](../evaluation_data.md). C- ja D-jaotuse koostamise ning
manifestide üksikasjad on failis [c_d_octave.md](c_d_octave.md). X ja Y on
kaks sõltumatut kandidaadipõhist juhujaotust; nende metoodika on failides
[x_octave.md](x_octave.md) ja [y_octave.md](y_octave.md).

| Tähis | Õpetamine ja test | Treeningridu | Testiridu | Eesmärk |
|---|---|---:|---:|---|
| **B1** | Algse B-treeninguga õpetatud mudelid fikseeritud Test1-l | 1 006 | 488 | esimene terviksaadetel põhinev välistest |
| **B2** | Sama B-treeninguga õpetatud mudelid fikseeritud Test2-l | 1 006 | 337 | teine terviksaadetel põhinev välistest |
| **C1** | C 70/30 saadetepõhise ümberjaotuse treening ja testiosa | 1 277 | 554 | sõltumatu ümberjaotuse võrdlus |
| **D1** | D 70/30 saadetepõhise ümberjaotuse treening ja testiosa | 1 283 | 548 | teine sõltumatu ümberjaotuse võrdlus |
| **X1** | X kandidaadipõhise 70/30 juhujaotuse treening ja testiosa | 1 281 | 550 | esimene kandidaadipõhine 70/30 juhujaotus |
| **Y1** | Y kandidaadipõhise 70/30 juhujaotuse treening ja testiosa | 1 281 | 550 | X-ist sõltumatu kandidaadipõhine 70/30 juhujaotus; 498/498 Octave'i varianti edukad |

C ja D on kaks eri, osaliselt kattuvat saadetepõhist 70/30 ümberjaotust
B-treeningu, Test1 ja Test2 ühendist. Iga C- või D-katse sees kuulub terve
saade ainult treeningusse või testi. B1, B2, C1 ja D1 tulemusi kasutatakse
finalistide eelvalikuks. Pärast eelvaliku fikseerimist hinnatakse finalistid
seni puutumata Test3-l tähistega B3, C3 ja D3.


### Mõõdikute tähendus

Klassipõhistes tabelites tähendab `TP` (*true positive*) selle klassi
kandidaati, mille mudel ennustas õigesti samasse klassi; `FN` (*false
negative*) on selle klassi kandidaat, mille mudel ennustas mõnda teise
klassi. `FP` (*false positive*) on mõne muu klassi kandidaat, mille mudel
ennustas ekslikult vaadeldavasse klassi, ning `TN` (*true negative*) on muu
klassi kandidaat, mille mudel jättis õigesti vaadeldavasse klassi määramata.

- **Recall / TPR** = `TP / (TP + FN)`: kui suure osa tegelikult sellesse
  klassi kuuluvatest kandidaatidest mudel leiab. TPR ja recall on sama
  näitaja eri nimetused.
- **FNR** = `FN / (TP + FN)` = `1 − recall`: kui suur osa tegelikust klassist
  jääb mudelil leidmata.
- **Precision** = `TP / (TP + FP)`: kui suur osa selle klassi ennustustest on
  õiged.
- **F1** = precision'i ja recall'i harmooniline keskmine:
  `2 × precision × recall / (precision + recall)`. See on kõrge vaid siis,
  kui mudel nii leiab klassi üles kui ka ei ennusta seda põhjendamatult.
- **FPR** = `FP / (FP + TN)`: kui suur osa teistesse klassidesse kuuluvatest
  kandidaatidest liigitatakse ekslikult vaadeldavasse klassi.
- **Specificity / TNR** = `TN / (FP + TN)` = `1 − FPR`: kui hästi mudel jätab
  õigesti välja kandidaadid, mis sellesse klassi ei kuulu.

Üldmõõdikud kasutavad neid klassipõhiseid näitajaid:

- **Accuracy** ehk üldtäpsus on õigete ennustuste osakaal kõigist testirea-
  dest: `õiged ennustused / kõik ennustused`. See on lihtne üldnäitaja, kuid
  suurema klassi ülekaal võib selle kõrgeks teha ka siis, kui väiksemaid
  klasse tuvastatakse nõrgalt.
- **Macro-F1** on kolme otsuseklassi (`ACCEPTED`, `MODIFIED`, `REJECTED`)
  ülal kirjeldatud F1 näitajate lihtne aritmeetiline keskmine. Kõik klassid kaaluvad võrdselt,
  sõltumata sellest, mitu kandidaati neis testis oli. Seetõttu on see hea
  näitaja, kui iga otsusetüüp on sisuliselt oluline.
- **Balanced accuracy** on kolme klassi recall'i ehk TPR-i aritmeetiline
  keskmine. See vastab küsimusele, kui suure osa igast tegelikust klassist
  mudel keskmiselt üles leiab; iga klass annab tulemusse võrdse panuse.
- **Weighted F1** on klasside F1 näitajate keskmine, kus iga klassi kaaluks on
  selle kandidaatide arv testis. See kirjeldab paremini testi tegelikku
  üldmahtu, kuid suurem klass mõjutab tulemust rohkem.

Kuna B1, B2, C1, D1, X1 ja Y1 klassijaotused on erinevad, tuleb üldtäpsust vaadata
koos macro-F1 ja balanced accuracy'ga. Weighted F1 on nende kõrval kasulik
lisavaade, sest see arvestab iga testi tegelikku klassijaotust.


## Mudelite, tunnusevariantide ja andmejaotuste võrdlus

Kõigil B1, B2, C1, D1, X1 ja Y1 komplektidel hinnati sama muutmata 498
mudeli/tunnusevarianti. Igas katses lõpetasid kõik **498/498** varianti
staatusega `OK`; vigu ei olnud. B2 sisaldab 337 kandidaati 14 terviksaatest:
62 `ACCEPTED` (18,4%), 151 `MODIFIED` (44,8%) ja 124 `REJECTED` (36,8%).
C1 sisaldab 554 ning D1 548 kandidaati 1 831-realise B/B1/B2 ühendist.
X1 ja Y1 on mõlemad samast ühendist tehtud sõltumatud kandidaadipõhised 70/30
juhujaotused: kummaski on treeningus 1 281 ja testis 550 kandidaati ning ühe
saate read võivad paikneda nii treeningus kui testis. Mõlemas testis on 181
`ACCEPTED`, 214 `MODIFIED` ja 155 `REJECTED` kandidaati. Y1
testivalimil on X1-ga ühiseid 167 kandidaati (Jaccard 17,90%); täpne Y1
lähteandmete kirjeldus on failis [y_octave.md](y_octave.md).
Katsete klassijaotused erinevad, mistõttu ei võrrelda ainult accuracy't.

Katsetati järgmisi mudeliperekondi: otsustuspuud (`Fine`, `Medium`, `Coarse`),
lineaarne, kvadraatne ja kuup-SVM, Gaussian SVM-id (`Fine`, `Medium`,
`Coarse`), SVM-kernel, ansamblid (`Boosted Trees`, `Bagged Trees`,
`RUSBoosted Trees`), Kernel Naive Bayes, Logistic Regression Kernel ning
kNN. kNN-is kasutati naabrite arve `1`, `3`, `5`, `7`, `10`, `15`, `21`,
`31`, `51`, `75` ja `100` ning kauguskaale `equal`, `inverse` ja
`squaredinverse`. Iga sobiva mudeli puhul katsetati kõiki kaheksat atribuuti
ning variante, kus üks atribuut on eemaldatud; see moodustab kokku 498
mudeli/tunnusevarianti.

Test1 võrdlustabelis kasutatakse uuema käituse 54 standardse SVM-i tulemust
(`log/oct-TmAUoK_test1_octave`); ülejäänud 444 varianti
pärinevad täielikust Test1 käitusest (`log/oct-HlIJvh_test1_octave`).
B2 tulemused on kataloogis `log/oct-rdhW8P_test2_octave`, C1 tulemused
`log/oct-yxbe3l_c1_octave`, D1 tulemused `log/oct-3bqqzd_d1_octave` ning
X1 tulemused `log/oct-bshFjj_x1_octave` ja Y1 tulemused
`log/oct-OKMtsB_y1_octave`.

| Mõõdik, kõigi 498 variandi keskmine | B1 | B2 | C1 | D1 | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|
| Testiridu | 488 | 337 | 554 | 548 | 550 | 550 |
| Accuracy | 76,07% | 65,17% | 66,93% | 69,45% | 68,67% | **69,65%** |
| Macro-F1 | 66,38% | 66,99% | 65,82% | 68,20% | 67,55% | **68,53%** |
| Balanced accuracy | 66,92% | 69,18% | 66,55% | 69,06% | 68,59% | **69,24%** |
| Weighted F1 | 75,97% | 64,06% | 65,98% | 68,45% | 67,69% | **68,85%** |

Täielik 498 mudelivariandi tabel koos iga variandi kõigi B1–D1, X1 ja Y1 mõõdikutega
on failis [mudelivariantide_koondtulemused.md](mudelivariantide_koondtulemused.md).

Järgmised tabelid on selle täieliku tabeli lühendatud vaated. Põhiosas on
kuni kümme kõrgeima B1–D1 aritmeetilise keskmisega varianti: keskmist
kasutatakse ainult tabeli lugemisjärjestuseks, mitte mudelivaliku reegliks.
Punktiirjoone all on lisaks kõik põhikümnest puudunud mudelivariandid, mis
olid mõnes B1, B2, C1, D1, X1 või Y1 katses vastava mõõdiku absoluutselt parimad või
viimased. **Paks kiri** tähistab alati selle katse parimat ning ***paks
kursiiv*** alati selle katse viimast tulemust kõigi 498 variandi seas.

<!-- OVERALL_MODEL_TABLES_START -->

### Parimad mudelid Accuracy järgi

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Quadratic SVM, `show_speaker_count` eemaldatud | 82,17% | **72,70%** | 73,47% | 72,26% | 75,15% | 71,27% | 71,09% |
| Medium Gaussian SVM, `show_speaker_count` eemaldatud | 82,58% | 70,33% | **74,19%** | 73,18% | 75,07% | 73,45% | 73,82% |
| KNN k=51 squaredinverse, `show_speaker_count` eemaldatud | 82,38% | 71,51% | 71,84% | 74,27% | 75,00% | 70,73% | 72,00% |
| KNN k=75 squaredinverse, `show_speaker_count` eemaldatud | 81,35% | 71,81% | 72,02% | 74,45% | 74,91% | 70,91% | 72,36% |
| Medium Gaussian SVM, kõik 8 tunnust | 81,15% | 71,81% | 72,38% | 74,09% | 74,86% | 73,82% | 73,82% |
| Medium Gaussian SVM, `distinct_speaker_count` eemaldatud | 80,94% | **72,70%** | 72,74% | 72,99% | 74,84% | **74,36%** | 73,27% |
| KNN k=75 inverse, `show_speaker_count` eemaldatud | 81,76% | 72,11% | 70,76% | 74,45% | 74,77% | 71,82% | 72,55% |
| KNN k=51 inverse, `show_speaker_count` eemaldatud | 81,97% | 70,62% | 71,12% | 74,27% | 74,49% | 71,64% | 73,09% |
| KNN k=21 equal, `duration_s` eemaldatud | **83,61%** | 68,55% | 72,38% | 73,36% | 74,47% | 71,82% | 74,18% |
| SVM Kernel, `duration_s` eemaldatud | 82,38% | 71,51% | 70,22% | 73,72% | 74,46% | 73,82% | 74,18% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| KNN k=10 equal, `duration_s` eemaldatud | **83,61%** | 69,44% | 70,76% | 72,99% | 74,20% | 73,27% | **76,00%** |
| KNN k=10 equal, `distinct_speaker_count` eemaldatud | 81,97% | 68,55% | 70,22% | **75,55%** | 74,07% | 72,18% | 74,00% |
| KNN k=10 equal, kõik 8 tunnust | 82,38% | 67,36% | 70,40% | **75,55%** | 73,92% | 71,09% | 73,82% |
| KNN k=15 equal, `dominant_speaker_coverage` eemaldatud | 80,94% | 65,58% | 66,97% | **75,55%** | 72,26% | 72,73% | 74,18% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 66,80% | ***28,78%*** | ***39,89%*** | ***40,15%*** | 43,91% | ***41,82%*** | ***42,36%*** |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***21,31%*** | 39,76% | 50,72% | 51,64% | 40,86% | 51,45% | 51,27% |

### Parimad mudelid Macro-F1 järgi

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| SVM Kernel, `duration_s` eemaldatud | 75,02% | 74,18% | 69,63% | 73,30% | 73,03% | 73,24% | 73,46% |
| KNN k=51 squaredinverse, `show_speaker_count` eemaldatud | 74,31% | 72,78% | 70,90% | 73,28% | 72,82% | 69,85% | 71,09% |
| KNN k=7 inverse, `show_speaker_count` eemaldatud | 74,34% | 72,66% | 70,57% | 72,70% | 72,57% | 69,41% | 70,93% |
| KNN k=7 equal, `duration_s` eemaldatud | 75,32% | 73,50% | 69,12% | 72,27% | 72,55% | 71,86% | 73,65% |
| KNN k=75 squaredinverse, `show_speaker_count` eemaldatud | 72,64% | 72,93% | 71,02% | 73,42% | 72,50% | 70,00% | 71,39% |
| KNN k=21 squaredinverse, kõik 8 tunnust | 73,17% | 72,94% | 70,07% | 73,80% | 72,49% | 71,34% | 73,91% |
| KNN k=10 inverse, `duration_s` eemaldatud | 74,52% | 73,00% | 71,02% | 71,43% | 72,49% | 69,95% | **75,14%** |
| KNN k=10 inverse, `show_speaker_count` eemaldatud | 72,22% | 72,03% | 70,98% | 74,66% | 72,47% | 70,52% | 72,68% |
| KNN k=15 inverse, `show_speaker_count` eemaldatud | **75,37%** | 71,54% | 69,01% | 73,93% | 72,46% | 70,96% | 72,74% |
| Medium Gaussian SVM, `show_speaker_count` eemaldatud | 73,10% | 71,69% | **73,16%** | 71,81% | 72,44% | 72,71% | 72,70% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Medium Gaussian SVM, `distinct_speaker_count` eemaldatud | 69,82% | **74,89%** | 71,91% | 71,70% | 72,08% | **73,68%** | 72,48% |
| KNN k=15 inverse, `dominant_speaker_coverage` eemaldatud | 71,51% | 69,53% | 67,16% | **74,96%** | 70,79% | 72,23% | 72,62% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***16,94%*** | 25,75% | 50,81% | 51,81% | 36,33% | 51,53% | 51,39% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 42,69% | ***23,40%*** | ***29,11%*** | ***28,11%*** | 30,83% | ***29,93%*** | ***30,88%*** |

### Parimad mudelid Balanced accuracy järgi

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| KNN k=51 squaredinverse, `show_speaker_count` eemaldatud | 73,77% | 74,97% | 71,75% | 73,93% | 73,61% | 70,87% | 71,87% |
| SVM Kernel, `duration_s` eemaldatud | 74,72% | 75,11% | 70,24% | 73,88% | 73,49% | 74,02% | 73,77% |
| KNN k=15 inverse, `show_speaker_count` eemaldatud | 74,89% | 73,65% | 70,08% | 74,72% | 73,34% | 72,18% | 73,53% |
| KNN k=7 inverse, `show_speaker_count` eemaldatud | 74,50% | 73,92% | 71,50% | 73,39% | 73,32% | 70,63% | 71,68% |
| KNN k=10 inverse, `show_speaker_count` eemaldatud | 72,10% | 73,48% | 71,92% | **75,50%** | 73,25% | 71,71% | 73,29% |
| KNN k=7 equal, `show_speaker_count` eemaldatud | **74,99%** | 72,72% | 71,81% | 73,42% | 73,23% | 71,19% | 72,39% |
| KNN k=75 squaredinverse, `show_speaker_count` eemaldatud | 72,19% | 74,83% | 71,85% | 73,99% | 73,21% | 70,96% | 72,12% |
| KNN k=7 equal, `duration_s` eemaldatud | 74,70% | 75,28% | 69,90% | 72,92% | 73,20% | 73,01% | 74,39% |
| KNN k=5 equal, `show_speaker_count` eemaldatud | 72,27% | 74,65% | 72,13% | 73,70% | 73,19% | 71,47% | 70,57% |
| KNN k=15 squaredinverse, `show_speaker_count` eemaldatud | 72,71% | 74,58% | 71,32% | 74,01% | 73,16% | 71,59% | 71,97% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Medium Gaussian SVM, `show_speaker_count` eemaldatud | 72,26% | 73,63% | **73,91%** | 72,66% | 73,11% | 73,82% | 73,42% |
| KNN k=10 inverse, `duration_s` eemaldatud | 74,15% | 74,35% | 71,74% | 72,12% | 73,09% | 70,95% | **75,70%** |
| Medium Gaussian SVM, `distinct_speaker_count` eemaldatud | 69,22% | **76,65%** | 72,53% | 72,08% | 72,62% | **74,57%** | 72,93% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***36,68%*** | ***35,84%*** | 51,92% | 53,46% | 44,47% | 52,97% | 52,98% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 45,92% | 40,11% | ***38,87%*** | ***39,72%*** | 41,16% | ***40,91%*** | ***41,26%*** |

### Parimad mudelid Weighted F1 järgi

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Quadratic SVM, `show_speaker_count` eemaldatud | 81,55% | 71,85% | 72,58% | 71,22% | 74,30% | 70,39% | 70,04% |
| KNN k=51 squaredinverse, `show_speaker_count` eemaldatud | 82,28% | 70,57% | 70,90% | 73,44% | 74,30% | 69,89% | 71,27% |
| Medium Gaussian SVM, `show_speaker_count` eemaldatud | 82,12% | 69,30% | **73,24%** | 72,10% | 74,19% | 72,61% | 72,98% |
| KNN k=75 squaredinverse, `show_speaker_count` eemaldatud | 81,23% | 70,83% | 71,06% | 73,62% | 74,18% | 70,07% | 71,63% |
| SVM Kernel, `duration_s` eemaldatud | 82,47% | 71,34% | 69,58% | 73,28% | 74,17% | 73,18% | 73,69% |
| Medium Gaussian SVM, kõik 8 tunnust | 80,47% | 71,31% | 71,57% | 73,20% | 74,14% | 73,06% | 73,24% |
| Medium Gaussian SVM, `distinct_speaker_count` eemaldatud | 80,23% | **72,21%** | 71,98% | 72,07% | 74,12% | **73,63%** | 72,71% |
| KNN k=10 inverse, `show_speaker_count` eemaldatud | 80,30% | 69,88% | 70,91% | 74,58% | 73,92% | 70,31% | 72,87% |
| KNN k=21 inverse, `distinct_speaker_count` eemaldatud | 81,18% | 70,43% | 70,68% | 73,37% | 73,91% | 71,56% | 73,65% |
| KNN k=21 equal, `duration_s` eemaldatud | 83,01% | 67,96% | 71,90% | 72,68% | 73,89% | 70,95% | 73,37% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| KNN k=10 inverse, `duration_s` eemaldatud | 82,32% | 70,37% | 70,95% | 71,26% | 73,73% | 69,85% | **75,30%** |
| KNN k=10 equal, `duration_s` eemaldatud | **83,15%** | 68,70% | 69,88% | 72,31% | 73,51% | 72,40% | 75,12% |
| KNN k=10 equal, `distinct_speaker_count` eemaldatud | 81,41% | 67,87% | 69,52% | **74,94%** | 73,44% | 71,32% | 73,02% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***10,76%*** | 28,63% | 50,45% | 51,27% | 35,28% | 51,25% | 50,79% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 58,19% | ***21,96%*** | ***30,73%*** | ***29,57%*** | 35,11% | ***31,65%*** | ***32,76%*** |
<!-- OVERALL_MODEL_TABLES_END -->

Kõrge B1 accuracy tuleneb eelkõige selle `ACCEPTED`-rohkusest. D1 on B1–D1
nelja katse keskmise macro-F1, accuracy ja weighted F1 järgi tugevaim; balanced
accuracy on väga lähedane B2 omale (69,06% vs 69,18%). C1 on neist neljast
raskem keskmine proov: selle macro-F1 ja balanced accuracy on madalaimad.

Ükski variant ei ole kõigis neljas B1–D1 katses esimene. Kõige ühtlasem tugev
kandidaat jääb `SVM Kernel` ilma `duration_s`-ita: macro-F1 on B1-s 75,02%,
B2-s 74,18%, C1-s 69,63% ja D1-s 73,30%. B2 ja C1 parimad variandid on
Medium Gaussian SVM-id, D1 parimad aga kNN-i seadistused. X1 ja Y1 on kaks
sõltumatut kandidaadipõhist juhujaotust. Nende tulemused on eraldi
finalistitabelites ning neid käsitletakse B1–D1 tulemustega samaväärsete
võrdlusandmetena.

### X1 ja Y1 võrdlus

Y1 kinnitab X1-ga sama üldpilti. Kõigi 498 variandi keskmistes on Y1 X1-st
0,98 protsendipunkti kõrgem nii accuracy kui macro-F1 järgi, 0,65 punkti
kõrgem balanced accuracy ning 1,16 punkti kõrgem weighted F1 järgi. Erinevus
on väike võrreldes B1–D1 katsete vahega; seega ei anna teine sõltumatu,
saatepiiranguta 70/30 jaotus põhjust arvata, et X1 tulemus oli juhuslik erand.
Kandidaadipõhine ja saadetepõhine jaotus on mõlemad mudelivaliku
võrdlusandmed; kumbki jaotustüüp ei ole praeguste andmete põhjal teise ees
eelistatud.

Järgmised tabelid sisaldavad klassipõhiste mõõdikute 498 variandi
aritmeetilisi keskmisi. Eri katsete klasside mahud on erinevad, mistõttu on
tabelites võrreldavad ainult protsendimõõdikud, mitte keskmised kandidaatide
arvud.

### Klassipõhised koondmõõdikud

#### `ACCEPTED`

| Mõõdik | B1 | B2 | C1 | D1 | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|
| Tegelikke kandidaate | 290 | 62 | 182 | 178 | 181 | 181 |
| Precision | **92,77%** | 76,11% | 78,24% | 81,02% | 80,60% | 82,96% |
| Recall / TPR | 89,68% | 90,21% | 89,49% | 93,19% | **93,63%** | 92,50% |
| F1 | 90,81% | 81,94% | 83,33% | 86,50% | 86,49% | **87,30%** |
| FPR | 10,02% | **7,25%** | 12,53% | 11,06% | 11,40% | 9,76% |
| FNR | 10,32% | 9,79% | 10,51% | 6,81% | **6,37%** | 7,50% |
| Specificity / TNR | 89,98% | **92,75%** | 87,47% | 88,94% | 88,60% | 90,24% |

#### `MODIFIED`

| Mõõdik | B1 | B2 | C1 | D1 | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|
| Tegelikke kandidaate | 107 | 151 | 215 | 217 | 214 | 214 |
| Precision | 49,81% | 63,58% | 59,87% | 64,02% | 63,29% | **64,11%** |
| Recall / TPR | 62,77% | **67,41%** | 60,27% | 63,02% | 58,29% | 62,83% |
| F1 | 55,00% | **64,86%** | 59,79% | 63,26% | 60,49% | 63,26% |
| FPR | **18,44%** | 31,54% | 25,89% | 23,35% | 21,68% | 22,53% |
| FNR | 37,23% | **32,59%** | 39,73% | 36,98% | 41,71% | 37,17% |
| Specificity / TNR | **81,56%** | 68,46% | 74,11% | 76,65% | 78,32% | 77,47% |

#### `REJECTED`

| Mõõdik | B1 | B2 | C1 | D1 | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|
| Tegelikke kandidaate | 91 | 124 | 157 | 153 | 155 | 155 |
| Precision | **63,78%** | 62,46% | 62,27% | 61,99% | 59,74% | 59,94% |
| Recall / TPR | 48,32% | 49,92% | 49,87% | 50,96% | **53,85%** | 52,40% |
| F1 | 53,34% | 54,15% | 54,34% | 54,83% | **55,67%** | 55,02% |
| FPR | **6,72%** | 18,20% | 12,30% | 12,44% | 14,53% | 13,97% |
| FNR | 51,68% | 50,08% | 50,13% | 49,04% | **46,15%** | 47,60% |
| Specificity / TNR | **93,28%** | 81,80% | 87,70% | 87,56% | 85,47% | 86,03% |

<!-- CLASS_MODEL_TABLES_START -->

Iga järgmine tabel sisaldab vähemalt viis B1–D1 keskmise järgi parimat mudelivarianti. Kui järgmise variandi keskmine on viiendal kohal olevaga sama pärast ümardamist kahe komakohani, kuulub ka see põhiossa. Punktiirjoone all on kõik tabeli põhiosast puudunud variandid, mis olid vähemalt ühes B1, B2, C1, D1, X1 või Y1 katses vastava mõõdiku sisuliselt parimad või halvimad. Precisioni, recalli, F1 ja specificity puhul on suurem parem; FPR-i ja FNR-i puhul väiksem parem. **Paks** tähistab parimat ning ***paks kursiiv*** halvimat tulemust.

#### Parimad mudelid klassis `ACCEPTED`

##### precision

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fine Gaussian SVM, `words` eemaldatud | 96,51% | 89,29% | 84,78% | 86,41% | 89,25% | 84,29% | 88,04% |
| Fine Gaussian SVM, `dominant_speaker_coverage` eemaldatud | 96,28% | 86,21% | **85,00%** | 86,89% | 88,59% | 86,08% | 89,14% |
| Fine Gaussian SVM, `duration_s` eemaldatud | 95,31% | 85,94% | 84,92% | 87,50% | 88,42% | 86,24% | 89,13% |
| Fine Gaussian SVM, `distinct_speaker_count` eemaldatud | 96,55% | 85,71% | 84,24% | 87,13% | 88,41% | 86,13% | 90,30% |
| Fine Gaussian SVM, `internal_speaker_change_count` eemaldatud | 95,79% | 85,96% | 84,21% | **87,64%** | 88,40% | 85,25% | 89,60% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Fine Gaussian SVM, kõik 8 tunnust | 96,71% | 85,71% | 83,93% | 86,86% | 88,30% | **86,44%** | **90,53%** |
| Kernel Naive Bayes, `candidate_type` eemaldatud | **100,00%** | **100,00%** | 65,81% | 66,94% | 83,19% | 70,64% | 67,50% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | ***68,19%*** | ***22,18%*** | ***37,53%*** | ***36,82%*** | 41,18% | ***37,84%*** | ***38,29%*** |

##### recall / TPR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coarse Gaussian SVM, `distinct_speaker_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Gaussian SVM, `dominant_speaker_coverage` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Gaussian SVM, `duration_s` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Gaussian SVM, kõik 8 tunnust | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Gaussian SVM, `internal_speaker_change_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Gaussian SVM, `nearest_change_edge_ratio` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Gaussian SVM, `show_speaker_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Gaussian SVM, `words` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Coarse Tree, `dominant_speaker_coverage` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | 98,90% | 97,24% |
| Linear SVM, `distinct_speaker_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Linear SVM, `dominant_speaker_coverage` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Linear SVM, `duration_s` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Linear SVM, kõik 8 tunnust | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Linear SVM, `internal_speaker_change_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Linear SVM, `nearest_change_edge_ratio` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Linear SVM, `show_speaker_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Linear SVM, `words` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Boosted Trees, `internal_speaker_change_count` eemaldatud | 95,17% | 93,55% | **100,00%** | 97,19% | 96,48% | 98,34% | 96,69% |
| Boosted Trees, `show_speaker_count` eemaldatud | 95,17% | 93,55% | 98,35% | **100,00%** | 96,77% | 97,79% | 97,24% |
| Coarse Tree, `distinct_speaker_count` eemaldatud | 96,55% | 95,16% | **100,00%** | **100,00%** | 97,93% | **100,00%** | **100,00%** |
| Coarse Tree, `duration_s` eemaldatud | 96,55% | 95,16% | **100,00%** | **100,00%** | 97,93% | **100,00%** | **100,00%** |
| Coarse Tree, kõik 8 tunnust | 96,55% | 95,16% | **100,00%** | **100,00%** | 97,93% | **100,00%** | **100,00%** |
| Coarse Tree, `internal_speaker_change_count` eemaldatud | 96,55% | 95,16% | **100,00%** | **100,00%** | 97,93% | **100,00%** | **100,00%** |
| Coarse Tree, `nearest_change_edge_ratio` eemaldatud | 96,55% | 95,16% | **100,00%** | **100,00%** | 97,93% | **100,00%** | **100,00%** |
| Coarse Tree, `show_speaker_count` eemaldatud | 96,55% | 95,16% | **100,00%** | **100,00%** | 97,93% | **100,00%** | **100,00%** |
| Coarse Tree, `words` eemaldatud | 96,55% | 95,16% | **100,00%** | **100,00%** | 97,93% | **100,00%** | 97,24% |
| KNN k=10 equal, `duration_s` eemaldatud | 97,93% | 93,55% | 94,51% | 96,07% | 95,51% | 98,34% | **100,00%** |
| KNN k=15 equal, `all_four_new_features` eemaldatud | 97,24% | **100,00%** | 91,21% | 98,31% | 96,69% | 95,58% | 97,24% |
| KNN k=21 equal, `all_four_new_features` eemaldatud | 97,59% | **100,00%** | 91,21% | 98,88% | 96,92% | 97,24% | 97,79% |
| KNN k=21 inverse, `all_four_new_features` eemaldatud | 92,76% | **100,00%** | 87,36% | 96,63% | 94,19% | 93,92% | 92,82% |
| KNN k=31 equal, `all_four_new_features` eemaldatud | 98,28% | **100,00%** | 89,56% | 98,88% | 96,68% | 97,79% | 96,69% |
| KNN k=31 inverse, `all_four_new_features` eemaldatud | 94,83% | **100,00%** | 86,81% | 97,19% | 94,71% | 93,37% | 92,27% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***1,03%*** | ***3,23%*** | ***42,31%*** | ***46,63%*** | 23,30% | ***42,54%*** | ***44,75%*** |
| Logistic Regression Kernel, `distinct_speaker_count` eemaldatud | 99,66% | 98,39% | 98,90% | **100,00%** | 99,24% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `dominant_speaker_coverage` eemaldatud | 99,66% | 98,39% | 98,90% | **100,00%** | 99,24% | 99,45% | 98,90% |
| Logistic Regression Kernel, `duration_s` eemaldatud | **100,00%** | 98,39% | 98,90% | 98,31% | 98,90% | 98,34% | **100,00%** |
| Logistic Regression Kernel, kõik 8 tunnust | **100,00%** | **100,00%** | 98,90% | 98,88% | 99,44% | **100,00%** | 99,45% |
| Logistic Regression Kernel, `internal_speaker_change_count` eemaldatud | **100,00%** | **100,00%** | 99,45% | **100,00%** | 99,86% | **100,00%** | 99,45% |
| Logistic Regression Kernel, `show_speaker_count` eemaldatud | 98,97% | 95,16% | 98,90% | **100,00%** | 98,26% | 99,45% | 99,45% |
| Medium Gaussian SVM, `duration_s` eemaldatud | 99,66% | **100,00%** | 98,35% | 96,07% | 98,52% | 99,45% | 98,90% |
| Medium Gaussian SVM, `show_speaker_count` eemaldatud | 98,28% | 93,55% | 99,45% | **100,00%** | 97,82% | 98,90% | 98,90% |
| Medium Tree, `show_speaker_count` eemaldatud | 88,62% | 91,94% | 98,35% | **100,00%** | 94,73% | 97,79% | 97,24% |
| Quadratic SVM, `duration_s` eemaldatud | 83,79% | **100,00%** | 99,45% | 97,19% | 95,11% | 99,45% | 99,45% |
| Quadratic SVM, `internal_speaker_change_count` eemaldatud | 84,14% | **100,00%** | 95,05% | 95,51% | 93,67% | 98,90% | **100,00%** |
| RUSBoosted Trees, `distinct_speaker_count` eemaldatud | 97,24% | **100,00%** | 97,80% | 97,19% | 98,06% | 98,90% | 97,79% |
| RUSBoosted Trees, `dominant_speaker_coverage` eemaldatud | 97,93% | **100,00%** | 97,80% | 96,63% | 98,09% | 98,34% | 96,69% |
| RUSBoosted Trees, kõik 8 tunnust | 97,24% | **100,00%** | 97,80% | 97,19% | 98,06% | 98,90% | 97,79% |
| RUSBoosted Trees, `internal_speaker_change_count` eemaldatud | 97,24% | **100,00%** | **100,00%** | 97,19% | 98,61% | 98,90% | 97,24% |
| RUSBoosted Trees, `nearest_change_edge_ratio` eemaldatud | 97,59% | **100,00%** | 97,25% | 98,31% | 98,29% | 98,34% | 97,24% |

##### F1

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Quadratic SVM, `show_speaker_count` eemaldatud | 96,47% | 87,77% | 89,05% | 90,96% | 91,06% | 90,13% | 91,60% |
| Medium Gaussian SVM, `duration_s` eemaldatud | 96,82% | 88,57% | 89,28% | 89,53% | 91,05% | 90,68% | 92,03% |
| RUSBoosted Trees, `internal_speaker_change_count` eemaldatud | 95,43% | 87,32% | 89,88% | 91,05% | 90,92% | 90,86% | 91,67% |
| KNN k=15 equal, `words` eemaldatud | 96,63% | 88,89% | 88,04% | 90,10% | 90,92% | 90,08% | 90,72% |
| Medium Gaussian SVM, `words` eemaldatud | 95,95% | 88,24% | 89,62% | 89,76% | 90,89% | 90,13% | 90,62% |
| Coarse Gaussian SVM, `distinct_speaker_count` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Gaussian SVM, `dominant_speaker_coverage` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Gaussian SVM, `duration_s` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Gaussian SVM, kõik 8 tunnust | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Gaussian SVM, `internal_speaker_change_count` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Gaussian SVM, `nearest_change_edge_ratio` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Gaussian SVM, `show_speaker_count` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Gaussian SVM, `words` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Coarse Tree, `dominant_speaker_coverage` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 91,33% | 92,39% |
| Linear SVM, `distinct_speaker_count` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Linear SVM, `dominant_speaker_coverage` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Linear SVM, `duration_s` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Linear SVM, kõik 8 tunnust | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Linear SVM, `internal_speaker_change_count` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Linear SVM, `nearest_change_edge_ratio` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Linear SVM, `show_speaker_count` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| Linear SVM, `words` eemaldatud | **96,83%** | 86,71% | 89,43% | 90,59% | 90,89% | 90,50% | 91,41% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Boosted Trees, `duration_s` eemaldatud | 94,86% | 88,06% | 89,72% | 90,57% | 90,80% | 91,09% | **93,23%** |
| KNN k=100 squaredinverse, `dominant_speaker_coverage` eemaldatud | 95,40% | **90,91%** | 81,08% | 89,01% | 89,10% | 89,74% | 90,43% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***2,05%*** | ***6,25%*** | ***51,51%*** | 54,97% | 28,69% | ***53,10%*** | ***53,82%*** |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 80,28% | 35,98% | 52,99% | ***53,66%*** | 55,73% | 54,74% | 54,86% |
| Medium Tree, `duration_s` eemaldatud | 87,78% | 86,13% | **90,50%** | 90,37% | 88,70% | **91,75%** | 92,43% |
| RUSBoosted Trees, `duration_s` eemaldatud | 95,25% | 86,52% | 89,22% | **91,29%** | 90,57% | 90,86% | 91,84% |

##### FPR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fine Gaussian SVM, `distinct_speaker_count` eemaldatud | 3,54% | 2,91% | **6,99%** | **5,95%** | 4,84% | **6,50%** | **4,34%** |
| Fine Gaussian SVM, kõik 8 tunnust | 3,54% | 2,91% | 7,26% | 6,22% | 4,98% | **6,50%** | **4,34%** |
| Fine Gaussian SVM, `words` eemaldatud | 4,04% | 2,18% | 7,53% | 6,76% | 5,13% | 8,13% | 5,96% |
| Fine Gaussian SVM, `internal_speaker_change_count` eemaldatud | 4,55% | 2,91% | 7,26% | **5,95%** | 5,16% | 7,32% | 4,88% |
| Fine Gaussian SVM, `dominant_speaker_coverage` eemaldatud | 4,55% | 2,91% | 7,26% | 6,49% | 5,30% | 7,32% | 5,15% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Kernel Naive Bayes, `candidate_type` eemaldatud | **0,00%** | **0,00%** | 10,75% | 11,08% | 5,46% | 8,67% | 10,57% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | ***66,67%*** | ***75,27%*** | ***73,39%*** | ***81,62%*** | 74,24% | ***79,67%*** | ***76,42%*** |

##### FNR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coarse Gaussian SVM, `distinct_speaker_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Gaussian SVM, `dominant_speaker_coverage` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Gaussian SVM, `duration_s` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Gaussian SVM, kõik 8 tunnust | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Gaussian SVM, `internal_speaker_change_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Gaussian SVM, `nearest_change_edge_ratio` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Gaussian SVM, `show_speaker_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Gaussian SVM, `words` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Coarse Tree, `dominant_speaker_coverage` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | 1,10% | 2,76% |
| Linear SVM, `distinct_speaker_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Linear SVM, `dominant_speaker_coverage` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Linear SVM, `duration_s` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Linear SVM, kõik 8 tunnust | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Linear SVM, `internal_speaker_change_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Linear SVM, `nearest_change_edge_ratio` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Linear SVM, `show_speaker_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Linear SVM, `words` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Boosted Trees, `internal_speaker_change_count` eemaldatud | 4,83% | 6,45% | **0,00%** | 2,81% | 3,52% | 1,66% | 3,31% |
| Boosted Trees, `show_speaker_count` eemaldatud | 4,83% | 6,45% | 1,65% | **0,00%** | 3,23% | 2,21% | 2,76% |
| Coarse Tree, `distinct_speaker_count` eemaldatud | 3,45% | 4,84% | **0,00%** | **0,00%** | 2,07% | **0,00%** | **0,00%** |
| Coarse Tree, `duration_s` eemaldatud | 3,45% | 4,84% | **0,00%** | **0,00%** | 2,07% | **0,00%** | **0,00%** |
| Coarse Tree, kõik 8 tunnust | 3,45% | 4,84% | **0,00%** | **0,00%** | 2,07% | **0,00%** | **0,00%** |
| Coarse Tree, `internal_speaker_change_count` eemaldatud | 3,45% | 4,84% | **0,00%** | **0,00%** | 2,07% | **0,00%** | **0,00%** |
| Coarse Tree, `nearest_change_edge_ratio` eemaldatud | 3,45% | 4,84% | **0,00%** | **0,00%** | 2,07% | **0,00%** | **0,00%** |
| Coarse Tree, `show_speaker_count` eemaldatud | 3,45% | 4,84% | **0,00%** | **0,00%** | 2,07% | **0,00%** | **0,00%** |
| Coarse Tree, `words` eemaldatud | 3,45% | 4,84% | **0,00%** | **0,00%** | 2,07% | **0,00%** | 2,76% |
| KNN k=10 equal, `duration_s` eemaldatud | 2,07% | 6,45% | 5,49% | 3,93% | 4,49% | 1,66% | **0,00%** |
| KNN k=15 equal, `all_four_new_features` eemaldatud | 2,76% | **0,00%** | 8,79% | 1,69% | 3,31% | 4,42% | 2,76% |
| KNN k=21 equal, `all_four_new_features` eemaldatud | 2,41% | **0,00%** | 8,79% | 1,12% | 3,08% | 2,76% | 2,21% |
| KNN k=21 inverse, `all_four_new_features` eemaldatud | 7,24% | **0,00%** | 12,64% | 3,37% | 5,81% | 6,08% | 7,18% |
| KNN k=31 equal, `all_four_new_features` eemaldatud | 1,72% | **0,00%** | 10,44% | 1,12% | 3,32% | 2,21% | 3,31% |
| KNN k=31 inverse, `all_four_new_features` eemaldatud | 5,17% | **0,00%** | 13,19% | 2,81% | 5,29% | 6,63% | 7,73% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***98,97%*** | ***96,77%*** | ***57,69%*** | ***53,37%*** | 76,70% | ***57,46%*** | ***55,25%*** |
| Logistic Regression Kernel, `distinct_speaker_count` eemaldatud | 0,34% | 1,61% | 1,10% | **0,00%** | 0,76% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `dominant_speaker_coverage` eemaldatud | 0,34% | 1,61% | 1,10% | **0,00%** | 0,76% | 0,55% | 1,10% |
| Logistic Regression Kernel, `duration_s` eemaldatud | **0,00%** | 1,61% | 1,10% | 1,69% | 1,10% | 1,66% | **0,00%** |
| Logistic Regression Kernel, kõik 8 tunnust | **0,00%** | **0,00%** | 1,10% | 1,12% | 0,56% | **0,00%** | 0,55% |
| Logistic Regression Kernel, `internal_speaker_change_count` eemaldatud | **0,00%** | **0,00%** | 0,55% | **0,00%** | 0,14% | **0,00%** | 0,55% |
| Logistic Regression Kernel, `show_speaker_count` eemaldatud | 1,03% | 4,84% | 1,10% | **0,00%** | 1,74% | 0,55% | 0,55% |
| Medium Gaussian SVM, `duration_s` eemaldatud | 0,34% | **0,00%** | 1,65% | 3,93% | 1,48% | 0,55% | 1,10% |
| Medium Gaussian SVM, `show_speaker_count` eemaldatud | 1,72% | 6,45% | 0,55% | **0,00%** | 2,18% | 1,10% | 1,10% |
| Medium Tree, `show_speaker_count` eemaldatud | 11,38% | 8,06% | 1,65% | **0,00%** | 5,27% | 2,21% | 2,76% |
| Quadratic SVM, `duration_s` eemaldatud | 16,21% | **0,00%** | 0,55% | 2,81% | 4,89% | 0,55% | 0,55% |
| Quadratic SVM, `internal_speaker_change_count` eemaldatud | 15,86% | **0,00%** | 4,95% | 4,49% | 6,33% | 1,10% | **0,00%** |
| RUSBoosted Trees, `distinct_speaker_count` eemaldatud | 2,76% | **0,00%** | 2,20% | 2,81% | 1,94% | 1,10% | 2,21% |
| RUSBoosted Trees, `dominant_speaker_coverage` eemaldatud | 2,07% | **0,00%** | 2,20% | 3,37% | 1,91% | 1,66% | 3,31% |
| RUSBoosted Trees, kõik 8 tunnust | 2,76% | **0,00%** | 2,20% | 2,81% | 1,94% | 1,10% | 2,21% |
| RUSBoosted Trees, `internal_speaker_change_count` eemaldatud | 2,76% | **0,00%** | **0,00%** | 2,81% | 1,39% | 1,10% | 2,76% |
| RUSBoosted Trees, `nearest_change_edge_ratio` eemaldatud | 2,41% | **0,00%** | 2,75% | 1,69% | 1,71% | 1,66% | 2,76% |

##### specificity / TNR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fine Gaussian SVM, `distinct_speaker_count` eemaldatud | 96,46% | 97,09% | **93,01%** | **94,05%** | 95,16% | **93,50%** | **95,66%** |
| Fine Gaussian SVM, kõik 8 tunnust | 96,46% | 97,09% | 92,74% | 93,78% | 95,02% | **93,50%** | **95,66%** |
| Fine Gaussian SVM, `words` eemaldatud | 95,96% | 97,82% | 92,47% | 93,24% | 94,87% | 91,87% | 94,04% |
| Fine Gaussian SVM, `internal_speaker_change_count` eemaldatud | 95,45% | 97,09% | 92,74% | **94,05%** | 94,84% | 92,68% | 95,12% |
| Fine Gaussian SVM, `dominant_speaker_coverage` eemaldatud | 95,45% | 97,09% | 92,74% | 93,51% | 94,70% | 92,68% | 94,85% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Kernel Naive Bayes, `candidate_type` eemaldatud | **100,00%** | **100,00%** | 89,25% | 88,92% | 94,54% | 91,33% | 89,43% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | ***33,33%*** | ***24,73%*** | ***26,61%*** | ***18,38%*** | 25,76% | ***20,33%*** | ***23,58%*** |

#### Parimad mudelid klassis `MODIFIED`

##### precision

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| RUSBoosted Trees, `duration_s` eemaldatud | 57,45% | **73,08%** | 69,09% | 71,71% | 67,83% | 66,10% | 65,56% |
| RUSBoosted Trees, `dominant_speaker_coverage` eemaldatud | 59,76% | 70,00% | 67,57% | 69,46% | 66,70% | 72,12% | 65,95% |
| RUSBoosted Trees, kõik 8 tunnust | 57,47% | 70,09% | 67,31% | 70,95% | 66,45% | 65,57% | 66,85% |
| RUSBoosted Trees, `nearest_change_edge_ratio` eemaldatud | 57,14% | 72,81% | 66,27% | 68,48% | 66,17% | 66,47% | 68,39% |
| RUSBoosted Trees, `distinct_speaker_count` eemaldatud | 56,47% | 70,34% | 67,09% | 70,29% | 66,05% | 65,57% | 66,85% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| KNN k=1 equal, `candidate_type` eemaldatud | 31,28% | 57,02% | ***48,28%*** | 55,08% | 47,92% | 55,96% | 50,70% |
| KNN k=1 inverse, `candidate_type` eemaldatud | 31,28% | 57,02% | ***48,28%*** | 55,08% | 47,92% | 55,96% | 50,70% |
| KNN k=1 squaredinverse, `candidate_type` eemaldatud | 31,28% | 57,02% | ***48,28%*** | 55,08% | 47,92% | 55,96% | 50,70% |
| KNN k=21 equal, `duration_s` eemaldatud | **62,28%** | 67,09% | 65,58% | 68,60% | 65,89% | 65,84% | 68,75% |
| KNN k=3 squaredinverse, `candidate_type` eemaldatud | 34,46% | 60,32% | 51,77% | 57,75% | 51,08% | ***53,23%*** | 53,30% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***17,91%*** | 57,69% | 49,74% | ***53,01%*** | 44,59% | 54,07% | ***49,71%*** |
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | 45,00% | 55,56% | 63,31% | 71,30% | 58,79% | **74,77%** | 67,20% |
| Kernel Naive Bayes, `show_speaker_count` eemaldatud | 44,83% | 64,96% | 65,62% | **72,73%** | 62,03% | 70,73% | **71,79%** |
| Kernel Naive Bayes, `words` eemaldatud | 22,50% | ***44,12%*** | 56,36% | 64,60% | 46,90% | 63,11% | 62,89% |
| RUSBoosted Trees, `internal_speaker_change_count` eemaldatud | 54,12% | 71,17% | **69,68%** | 67,38% | 65,59% | 65,00% | 65,56% |

##### recall / TPR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coarse Gaussian SVM, `words` eemaldatud | 83,18% | 92,72% | **81,86%** | **85,25%** | 85,75% | **84,11%** | **87,38%** |
| Coarse Gaussian SVM, `candidate_type` eemaldatud | **96,26%** | **98,68%** | 61,40% | 58,99% | 78,83% | 60,28% | 61,21% |
| KNN k=100 equal, `words` eemaldatud | 74,77% | 86,75% | 74,42% | 76,50% | 78,11% | 73,83% | 76,17% |
| Fine Gaussian SVM, `distinct_speaker_count` eemaldatud | 83,18% | 82,12% | 71,63% | 75,12% | 78,01% | 75,70% | 80,37% |
| Fine Gaussian SVM, kõik 8 tunnust | 82,24% | 80,79% | 70,70% | 74,65% | 77,10% | 73,83% | 79,44% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Kernel Naive Bayes, `candidate_type` eemaldatud | 11,21% | ***9,93%*** | 44,65% | 40,55% | 26,59% | 43,46% | 40,65% |
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | 8,41% | ***9,93%*** | 40,93% | 35,48% | 23,69% | 38,79% | 39,25% |
| Kernel Naive Bayes, `internal_speaker_change_count` eemaldatud | ***6,54%*** | 11,92% | 40,93% | 37,79% | 24,30% | 38,32% | 38,79% |
| Kernel Naive Bayes, `words` eemaldatud | 8,41% | ***9,93%*** | 28,84% | 33,64% | 20,21% | 35,98% | 28,50% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 40,19% | 25,17% | ***26,51%*** | ***20,28%*** | 28,04% | ***23,83%*** | ***27,10%*** |

##### F1

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| KNN k=75 inverse, `show_speaker_count` eemaldatud | 62,71% | **74,40%** | 63,38% | 69,70% | 67,55% | 63,24% | 65,38% |
| KNN k=75 squaredinverse, `show_speaker_count` eemaldatud | 62,76% | 73,56% | 64,11% | 68,98% | 67,35% | 62,22% | 65,70% |
| KNN k=51 squaredinverse, `show_speaker_count` eemaldatud | 64,10% | 73,07% | 63,46% | 68,22% | 67,21% | 61,69% | 64,72% |
| Medium Gaussian SVM, `show_speaker_count` eemaldatud | 61,82% | 71,73% | 66,98% | 66,98% | 66,88% | 64,14% | 67,30% |
| Coarse Gaussian SVM, `nearest_change_edge_ratio` eemaldatud | 63,04% | 70,06% | 66,67% | 67,67% | 66,86% | 67,43% | 68,61% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Boosted Trees, `internal_speaker_change_count` eemaldatud | 63,11% | 68,69% | **67,28%** | 65,92% | 66,25% | 62,35% | 62,32% |
| Coarse Gaussian SVM, kõik 8 tunnust | 62,36% | 70,49% | 65,67% | 67,81% | 66,58% | **67,71%** | 68,70% |
| KNN k=10 equal, `duration_s` eemaldatud | **65,80%** | 70,22% | 64,07% | 66,67% | 66,69% | 66,51% | **70,67%** |
| KNN k=10 equal, kõik 8 tunnust | 62,56% | 67,51% | 64,41% | **69,91%** | 66,10% | 63,66% | 68,79% |
| Kernel Naive Bayes, `internal_speaker_change_count` eemaldatud | ***10,69%*** | 19,25% | 50,00% | 49,10% | 32,26% | 50,31% | 49,55% |
| Kernel Naive Bayes, `words` eemaldatud | 12,24% | ***16,22%*** | 38,15% | 44,24% | 27,71% | 45,83% | 39,23% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 47,78% | 34,23% | ***34,34%*** | ***30,66%*** | 36,75% | ***35,05%*** | ***37,79%*** |

##### FPR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | **2,89%** | 6,45% | 15,04% | 9,37% | 8,44% | 8,33% | 12,20% |
| Kernel Naive Bayes, `nearest_change_edge_ratio` eemaldatud | 3,67% | **5,91%** | 14,75% | 10,57% | 8,73% | 11,01% | 12,50% |
| Kernel Naive Bayes, `internal_speaker_change_count` eemaldatud | 4,46% | 9,68% | 14,45% | 10,57% | 9,79% | 8,93% | 11,31% |
| Kernel Naive Bayes, `duration_s` eemaldatud | 7,35% | 8,60% | 15,34% | 12,99% | 11,07% | 10,12% | 12,20% |
| Kernel Naive Bayes, kõik 8 tunnust | 6,82% | 10,22% | 15,93% | 11,48% | 11,11% | 11,61% | 12,50% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Coarse Gaussian SVM, `candidate_type` eemaldatud | ***93,18%*** | ***94,09%*** | 33,92% | 26,28% | 61,87% | 26,19% | 26,79% |
| Coarse Gaussian SVM, `words` eemaldatud | 23,62% | 62,37% | ***45,13%*** | ***44,71%*** | 43,96% | ***44,94%*** | ***44,05%*** |
| Coarse Tree, `distinct_speaker_count` eemaldatud | 13,91% | 24,73% | **12,09%** | 19,03% | 17,44% | 19,35% | 19,05% |
| Coarse Tree, `duration_s` eemaldatud | 13,91% | 24,73% | **12,09%** | 19,03% | 17,44% | 19,35% | 19,05% |
| Coarse Tree, kõik 8 tunnust | 13,91% | 24,73% | **12,09%** | 19,03% | 17,44% | 19,35% | 19,05% |
| Coarse Tree, `internal_speaker_change_count` eemaldatud | 13,91% | 24,73% | **12,09%** | 19,03% | 17,44% | 19,35% | 19,05% |
| Coarse Tree, `nearest_change_edge_ratio` eemaldatud | 13,91% | 24,73% | **12,09%** | 19,03% | 17,44% | 19,35% | 19,05% |
| Coarse Tree, `show_speaker_count` eemaldatud | 13,91% | 24,73% | **12,09%** | 19,03% | 17,44% | 19,35% | 19,05% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | 14,44% | **5,91%** | 28,61% | 23,56% | 18,13% | 23,51% | 26,19% |
| Kernel Naive Bayes, `show_speaker_count` eemaldatud | 12,60% | 22,04% | 12,98% | 9,97% | 14,40% | 10,71% | **9,82%** |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 7,87% | 17,74% | 17,70% | **7,85%** | 12,79% | **7,74%** | 10,42% |

##### FNR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coarse Gaussian SVM, `words` eemaldatud | 16,82% | 7,28% | **18,14%** | **14,75%** | 14,25% | **15,89%** | **12,62%** |
| Coarse Gaussian SVM, `candidate_type` eemaldatud | **3,74%** | **1,32%** | 38,60% | 41,01% | 21,17% | 39,72% | 38,79% |
| KNN k=100 equal, `words` eemaldatud | 25,23% | 13,25% | 25,58% | 23,50% | 21,89% | 26,17% | 23,83% |
| Fine Gaussian SVM, `distinct_speaker_count` eemaldatud | 16,82% | 17,88% | 28,37% | 24,88% | 21,99% | 24,30% | 19,63% |
| Fine Gaussian SVM, kõik 8 tunnust | 17,76% | 19,21% | 29,30% | 25,35% | 22,90% | 26,17% | 20,56% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Kernel Naive Bayes, `candidate_type` eemaldatud | 88,79% | ***90,07%*** | 55,35% | 59,45% | 73,41% | 56,54% | 59,35% |
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | 91,59% | ***90,07%*** | 59,07% | 64,52% | 76,31% | 61,21% | 60,75% |
| Kernel Naive Bayes, `internal_speaker_change_count` eemaldatud | ***93,46%*** | 88,08% | 59,07% | 62,21% | 75,70% | 61,68% | 61,21% |
| Kernel Naive Bayes, `words` eemaldatud | 91,59% | ***90,07%*** | 71,16% | 66,36% | 79,79% | 64,02% | 71,50% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 59,81% | 74,83% | ***73,49%*** | ***79,72%*** | 71,96% | ***76,17%*** | ***72,90%*** |

##### specificity / TNR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | **97,11%** | 93,55% | 84,96% | 90,63% | 91,56% | 91,67% | 87,80% |
| Kernel Naive Bayes, `nearest_change_edge_ratio` eemaldatud | 96,33% | **94,09%** | 85,25% | 89,43% | 91,27% | 88,99% | 87,50% |
| Kernel Naive Bayes, `internal_speaker_change_count` eemaldatud | 95,54% | 90,32% | 85,55% | 89,43% | 90,21% | 91,07% | 88,69% |
| Kernel Naive Bayes, `duration_s` eemaldatud | 92,65% | 91,40% | 84,66% | 87,01% | 88,93% | 89,88% | 87,80% |
| Kernel Naive Bayes, kõik 8 tunnust | 93,18% | 89,78% | 84,07% | 88,52% | 88,89% | 88,39% | 87,50% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Coarse Gaussian SVM, `candidate_type` eemaldatud | ***6,82%*** | ***5,91%*** | 66,08% | 73,72% | 38,13% | 73,81% | 73,21% |
| Coarse Gaussian SVM, `words` eemaldatud | 76,38% | 37,63% | ***54,87%*** | ***55,29%*** | 56,04% | ***55,06%*** | ***55,95%*** |
| Coarse Tree, `distinct_speaker_count` eemaldatud | 86,09% | 75,27% | **87,91%** | 80,97% | 82,56% | 80,65% | 80,95% |
| Coarse Tree, `duration_s` eemaldatud | 86,09% | 75,27% | **87,91%** | 80,97% | 82,56% | 80,65% | 80,95% |
| Coarse Tree, kõik 8 tunnust | 86,09% | 75,27% | **87,91%** | 80,97% | 82,56% | 80,65% | 80,95% |
| Coarse Tree, `internal_speaker_change_count` eemaldatud | 86,09% | 75,27% | **87,91%** | 80,97% | 82,56% | 80,65% | 80,95% |
| Coarse Tree, `nearest_change_edge_ratio` eemaldatud | 86,09% | 75,27% | **87,91%** | 80,97% | 82,56% | 80,65% | 80,95% |
| Coarse Tree, `show_speaker_count` eemaldatud | 86,09% | 75,27% | **87,91%** | 80,97% | 82,56% | 80,65% | 80,95% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | 85,56% | **94,09%** | 71,39% | 76,44% | 81,87% | 76,49% | 73,81% |
| Kernel Naive Bayes, `show_speaker_count` eemaldatud | 87,40% | 77,96% | 87,02% | 90,03% | 85,60% | 89,29% | **90,18%** |
| Logistic Regression Kernel, `candidate_type` eemaldatud | 92,13% | 82,26% | 82,30% | **92,15%** | 87,21% | **92,26%** | 89,58% |

#### Parimad mudelid klassis `REJECTED`

##### precision

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| KNN k=75 inverse, `show_speaker_count` eemaldatud | 72,88% | **79,22%** | 66,67% | 72,48% | 72,81% | 63,97% | 63,43% |
| KNN k=100 inverse, `show_speaker_count` eemaldatud | 73,47% | 75,71% | 71,30% | 68,87% | 72,34% | 64,34% | 66,40% |
| KNN k=100 equal, `show_speaker_count` eemaldatud | 71,43% | 75,44% | **75,82%** | 66,33% | 72,25% | 65,83% | 66,67% |
| KNN k=75 equal, `show_speaker_count` eemaldatud | 72,22% | 76,06% | 69,81% | 69,90% | 72,00% | 64,39% | 64,89% |
| KNN k=75 squaredinverse, `show_speaker_count` eemaldatud | 73,44% | 75,00% | 67,97% | 70,25% | 71,66% | 60,69% | 62,59% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Coarse Gaussian SVM, `candidate_type` eemaldatud | **80,00%** | 66,67% | 68,33% | 62,50% | 69,38% | 66,23% | 62,50% |
| Coarse Tree, `words` eemaldatud | 57,69% | 60,00% | 59,02% | 62,39% | 59,78% | **75,00%** | 53,03% |
| Fine Gaussian SVM, `duration_s` eemaldatud | 75,34% | 69,66% | 62,30% | 63,78% | 67,77% | 64,66% | **70,37%** |
| KNN k=100 inverse, kõik 8 tunnust | 69,23% | 64,94% | 72,92% | **72,53%** | 69,90% | 66,09% | 66,97% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***21,29%*** | ***37,86%*** | ***44,26%*** | ***43,41%*** | 36,71% | ***42,01%*** | ***44,71%*** |

##### recall / TPR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | 95,60% | 87,90% | **74,52%** | **81,70%** | 84,93% | **82,58%** | 73,55% |
| Kernel Naive Bayes, `internal_speaker_change_count` eemaldatud | 96,70% | 87,10% | **74,52%** | 79,74% | 84,52% | 80,00% | 76,77% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | **97,80%** | **94,35%** | 68,79% | 73,20% | 83,54% | 72,90% | 73,55% |
| Kernel Naive Bayes, `words` eemaldatud | 95,60% | 87,10% | **74,52%** | 75,82% | 83,26% | 70,97% | **79,35%** |
| Kernel Naive Bayes, `nearest_change_edge_ratio` eemaldatud | 92,31% | 87,10% | 72,61% | 77,78% | 82,45% | 76,77% | 74,84% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Coarse Gaussian SVM, `words` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `candidate_type` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `distinct_speaker_count` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `dominant_speaker_coverage` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `duration_s` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, kõik 8 tunnust | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `internal_speaker_change_count` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `nearest_change_edge_ratio` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `show_speaker_count` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `words` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |

##### F1

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| KNN k=10 inverse, `show_speaker_count` eemaldatud | 66,29% | 62,83% | 61,90% | 65,78% | 64,20% | 62,26% | 60,87% |
| KNN k=5 equal, `show_speaker_count` eemaldatud | 67,40% | 64,38% | 62,16% | 62,84% | 64,20% | 62,42% | 58,09% |
| KNN k=10 squaredinverse, `show_speaker_count` eemaldatud | 66,30% | 64,07% | 60,54% | 65,55% | 64,12% | 61,54% | 58,86% |
| KNN k=5 inverse, `show_speaker_count` eemaldatud | 67,03% | 64,71% | 60,81% | 63,70% | 64,06% | 62,46% | 57,42% |
| RUSBoosted Trees, `duration_s` eemaldatud | 63,78% | 64,03% | **64,44%** | 63,79% | 64,01% | 59,05% | 56,05% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Coarse Gaussian SVM, `words` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Cubic SVM, `duration_s` eemaldatud | 60,98% | **65,13%** | 58,82% | 59,53% | 61,12% | 61,69% | 63,06% |
| KNN k=15 inverse, `dominant_speaker_coverage` eemaldatud | 58,75% | 55,46% | 54,23% | **66,67%** | 58,78% | 62,54% | 60,59% |
| KNN k=15 squaredinverse, `duration_s` eemaldatud | 67,05% | 63,87% | 60,07% | 62,58% | 63,39% | 58,33% | **63,84%** |
| KNN k=7 equal, `show_speaker_count` eemaldatud | **70,72%** | 61,61% | 60,90% | 61,64% | 63,72% | 61,20% | 60,47% |
| KNN k=7 inverse, `show_speaker_count` eemaldatud | **70,72%** | 61,61% | 60,75% | 62,33% | 63,85% | 60,62% | 59,67% |
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | 65,17% | 60,06% | 63,41% | 64,43% | 63,27% | **66,67%** | 60,48% |
| Logistic Regression Kernel, `candidate_type` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `distinct_speaker_count` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `dominant_speaker_coverage` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `duration_s` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, kõik 8 tunnust | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `internal_speaker_change_count` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `nearest_change_edge_ratio` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `show_speaker_count` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |
| Logistic Regression Kernel, `words` eemaldatud | ***0,00%*** | ***0,00%*** | ***0,00%*** | ***0,00%*** | 0,00% | ***0,00%*** | ***0,00%*** |

##### FPR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coarse Gaussian SVM, `words` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `candidate_type` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `distinct_speaker_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `dominant_speaker_coverage` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `duration_s` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, kõik 8 tunnust | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `internal_speaker_change_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `nearest_change_edge_ratio` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `show_speaker_count` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| Logistic Regression Kernel, `words` eemaldatud | **0,00%** | **0,00%** | **0,00%** | **0,00%** | 0,00% | **0,00%** | **0,00%** |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***82,87%*** | ***90,14%*** | ***34,26%*** | ***36,96%*** | 61,06% | ***39,49%*** | ***35,70%*** |

##### FNR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kernel Naive Bayes, `dominant_speaker_coverage` eemaldatud | 4,40% | 12,10% | **25,48%** | **18,30%** | 15,07% | **17,42%** | 26,45% |
| Kernel Naive Bayes, `internal_speaker_change_count` eemaldatud | 3,30% | 12,90% | **25,48%** | 20,26% | 15,48% | 20,00% | 23,23% |
| Kernel Naive Bayes, `candidate_type` eemaldatud | **2,20%** | **5,65%** | 31,21% | 26,80% | 16,46% | 27,10% | 26,45% |
| Kernel Naive Bayes, `words` eemaldatud | 4,40% | 12,90% | **25,48%** | 24,18% | 16,74% | 29,03% | **20,65%** |
| Kernel Naive Bayes, `nearest_change_edge_ratio` eemaldatud | 7,69% | 12,90% | 27,39% | 22,22% | 17,55% | 23,23% | 25,16% |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Coarse Gaussian SVM, `words` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `candidate_type` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `distinct_speaker_count` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `dominant_speaker_coverage` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `duration_s` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, kõik 8 tunnust | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `internal_speaker_change_count` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `nearest_change_edge_ratio` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `show_speaker_count` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |
| Logistic Regression Kernel, `words` eemaldatud | ***100,00%*** | ***100,00%*** | ***100,00%*** | ***100,00%*** | 100,00% | ***100,00%*** | ***100,00%*** |

##### specificity / TNR

| Variant | B1 | B2 | C1 | D1 | B1–D1 keskmine | X1 | Y1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Coarse Gaussian SVM, `words` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `candidate_type` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `distinct_speaker_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `dominant_speaker_coverage` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `duration_s` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, kõik 8 tunnust | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `internal_speaker_change_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `nearest_change_edge_ratio` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `show_speaker_count` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| Logistic Regression Kernel, `words` eemaldatud | **100,00%** | **100,00%** | **100,00%** | **100,00%** | 100,00% | **100,00%** | **100,00%** |
| · · · | · · · | · · · | · · · | · · · | · · · | · · · | · · · |
| Kernel Naive Bayes, `candidate_type` eemaldatud | ***17,13%*** | ***9,86%*** | ***65,74%*** | ***63,04%*** | 38,94% | ***60,51%*** | ***64,30%*** |

<!-- CLASS_MODEL_TABLES_END -->

<!-- FINALIST_SELECTION_START -->

### Fikseeritud finalistide valikureegel

See finalistitabel on B1–D1 saadetepõhiste katsete rakendus sama valikureegliga. X1–Y1 kandidaadipõhise jaotuse rakendus on allpool ning seda käsitletakse samaväärse võrdlusandmena. Kõigepealt rakendatakse kõigile kolmele klassile ja igale B1–D1 katsele kaks kohustuslikku tingimust: `F1 ≥ 50%` ning `recall / TPR ≥ 55%`. Selle filtri läbis **51/498** varianti.

Allesjäänud variante võrreldakse protsentiilsete asetuste abil kõigi 498 variandi seas. Üldine koondskoor on 50% üldtoimivus (`25%` macro-F1, `15%` balanced accuracy, `7%` weighted F1, `3%` accuracy), 40% kolme klassi F1 võrdne keskmine ja 10% kolme klassi recall'i võrdne keskmine. Klassipõhistes top-5 tabelites kasutatakse sama üldtoimivuse 50% osa, kuid ülejäänud 50% tuleb vastava klassi F1-st (40%) ja recall'ist (10%).

#### Üldine top-10

| Koht | Variant | Koondskoor | Macro-F1, B1–D1 | Balanced accuracy, B1–D1 | Weighted F1, B1–D1 | Macro-F1, X1 | Macro-F1, Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | SVM Kernel, `duration_s` eemaldatud | 93,25 | 73,03% | 73,49% | 74,17% | 73,24% | 73,46% |
| 2 | KNN k=7 equal, `duration_s` eemaldatud | 91,77 | 72,55% | 73,20% | 73,80% | 71,86% | 73,65% |
| 3 | KNN k=7 inverse, `show_speaker_count` eemaldatud | 90,32 | 72,57% | 73,32% | 73,72% | 69,41% | 70,93% |
| 4 | KNN k=7 equal, `show_speaker_count` eemaldatud | 88,84 | 72,44% | 73,23% | 73,70% | 69,84% | 71,50% |
| 5 | KNN k=10 inverse, `duration_s` eemaldatud | 88,22 | 72,49% | 73,09% | 73,73% | 69,95% | 75,14% |
| 6 | KNN k=10 inverse, kõik 8 tunnust | 87,85 | 72,27% | 72,85% | 73,43% | 70,21% | 74,00% |
| 7 | KNN k=10 inverse, `show_speaker_count` eemaldatud | 87,82 | 72,47% | 73,25% | 73,92% | 70,52% | 72,68% |
| 8 | KNN k=5 equal, `show_speaker_count` eemaldatud | 87,01 | 72,34% | 73,19% | 73,78% | 70,34% | 69,79% |
| 9 | KNN k=15 inverse, `duration_s` eemaldatud | 86,74 | 72,34% | 72,96% | 73,52% | 69,58% | 74,58% |
| 10 | KNN k=21 inverse, `duration_s` eemaldatud | 85,93 | 72,26% | 72,72% | 73,58% | 70,38% | 74,88% |

#### Klass `ACCEPTED` – top-5

| Koht | Variant | Klassiskoor | F1, B1–D1 | Recall / TPR, B1–D1 | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | KNN k=7 equal, `duration_s` eemaldatud | 91,17 | 89,71% | 95,48% | 90,36% | 98,34% | 91,75% | 98,34% |
| 2 | SVM Kernel, `duration_s` eemaldatud | 88,49 | 89,47% | 93,38% | 89,51% | 96,69% | 90,29% | 95,03% |
| 3 | KNN k=7 inverse, `show_speaker_count` eemaldatud | 86,77 | 89,21% | 94,70% | 88,49% | 95,58% | 89,41% | 95,58% |
| 4 | KNN k=10 inverse, kõik 8 tunnust | 85,75 | 89,28% | 94,33% | 90,03% | 97,24% | 91,38% | 96,69% |
| 5 | KNN k=7 equal, kõik 8 tunnust | 84,89 | 89,30% | 95,00% | 90,08% | 97,79% | 90,96% | 97,24% |

#### Klass `MODIFIED` – top-5

| Koht | Variant | Klassiskoor | F1, B1–D1 | Recall / TPR, B1–D1 | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | SVM Kernel, `duration_s` eemaldatud | 92,72 | 65,80% | 66,10% | 65,52% | 62,15% | 68,22% | 68,22% |
| 2 | KNN k=7 equal, `duration_s` eemaldatud | 88,03 | 65,06% | 64,57% | 62,60% | 57,48% | 66,50% | 63,55% |
| 3 | KNN k=21 inverse, `duration_s` eemaldatud | 87,45 | 65,19% | 64,95% | 62,62% | 60,28% | 69,38% | 67,76% |
| 4 | KNN k=7 inverse, `show_speaker_count` eemaldatud | 86,03 | 64,64% | 64,74% | 59,13% | 53,74% | 63,73% | 60,75% |
| 5 | KNN k=7 equal, `show_speaker_count` eemaldatud | 85,80 | 64,72% | 63,90% | 59,43% | 53,74% | 64,69% | 61,21% |

#### Klass `REJECTED` – top-5

| Koht | Variant | Klassiskoor | F1, B1–D1 | Recall / TPR, B1–D1 | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | KNN k=10 inverse, `show_speaker_count` eemaldatud | 98,72 | 64,20% | 60,92% | 62,26% | 63,87% | 60,87% | 58,71% |
| 2 | SVM Kernel, `duration_s` eemaldatud | 98,55 | 63,82% | 60,98% | 64,69% | 63,23% | 61,86% | 58,06% |
| 3 | KNN k=5 equal, `show_speaker_count` eemaldatud | 98,31 | 64,20% | 61,72% | 62,42% | 63,23% | 58,09% | 56,77% |
| 4 | KNN k=10 inverse, `duration_s` eemaldatud | 98,19 | 63,99% | 62,16% | 59,87% | 60,65% | 63,79% | 61,94% |
| 5 | KNN k=7 inverse, `show_speaker_count` eemaldatud | 98,16 | 63,85% | 60,53% | 60,62% | 62,58% | 59,67% | 58,71% |

#### Klassitop-5-st üldisest top-10-st välja jäänud variandid

| Variant | Jõudis klassi top-5 hulka | Üldine koondskoor |
|---|---|---:|
| KNN k=7 equal, kõik 8 tunnust | `ACCEPTED` | 84,99 |

### X1–Y1 kandidaadipõhine finalistivalik

See on X1–Y1 kandidaadipõhise jaotuse rakendus sama valikureegliga. Kasutatud on sama filtrit (`F1 ≥ 50%` ja `recall / TPR ≥ 55%` igas klassis mõlemas katses) ning sama protsentiilset kaalutud skoori. Filtri läbis **144/498** varianti.

#### Üldine top-10

| Koht | Variant | Koondskoor | Macro-F1, X1 | Macro-F1, Y1 | Macro-F1, X1–Y1 | Balanced accuracy, X1–Y1 | Weighted F1, X1–Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Medium Gaussian SVM, `duration_s` eemaldatud | 97,54 | 72,81% | 74,49% | 73,65% | 74,44% | 73,78% |
| 2 | Medium Gaussian SVM, kõik 8 tunnust | 93,18 | 73,11% | 73,01% | 73,06% | 73,77% | 73,15% |
| 3 | KNN k=15 equal, `dominant_speaker_coverage` eemaldatud | 92,76 | 72,00% | 73,39% | 72,69% | 73,53% | 72,76% |
| 4 | Medium Gaussian SVM, `distinct_speaker_count` eemaldatud | 92,65 | 73,68% | 72,48% | 73,08% | 73,75% | 73,17% |
| 5 | KNN k=21 squaredinverse, `distinct_speaker_count` eemaldatud | 92,16 | 71,35% | 74,07% | 72,71% | 73,39% | 72,80% |
| 6 | KNN k=7 equal, `duration_s` eemaldatud | 91,89 | 71,86% | 73,65% | 72,76% | 73,70% | 72,74% |
| 7 | KNN k=10 inverse, `duration_s` eemaldatud | 91,24 | 69,95% | 75,14% | 72,55% | 73,33% | 72,58% |
| 8 | KNN k=21 inverse, `duration_s` eemaldatud | 91,12 | 70,38% | 74,88% | 72,63% | 73,25% | 72,77% |
| 9 | Medium Gaussian SVM, `show_speaker_count` eemaldatud | 90,93 | 72,71% | 72,70% | 72,71% | 73,62% | 72,79% |
| 10 | KNN k=21 squaredinverse, kõik 8 tunnust | 90,83 | 71,34% | 73,91% | 72,62% | 73,32% | 72,70% |

#### Klass `ACCEPTED` – top-5

| Koht | Variant | Klassiskoor | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 | F1, X1–Y1 | Recall / TPR, X1–Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Medium Gaussian SVM, `duration_s` eemaldatud | 98,54 | 90,68% | 99,45% | 92,03% | 98,90% | 91,36% | 99,17% |
| 2 | Quadratic SVM, `duration_s` eemaldatud | 96,63 | 91,37% | 99,45% | 91,60% | 99,45% | 91,49% | 99,45% |
| 3 | KNN k=7 equal, `duration_s` eemaldatud | 95,30 | 90,36% | 98,34% | 91,75% | 98,34% | 91,05% | 98,34% |
| 4 | KNN k=15 equal, `dominant_speaker_coverage` eemaldatud | 95,15 | 89,57% | 97,24% | 92,54% | 99,45% | 91,06% | 98,34% |
| 5 | KNN k=10 inverse, `duration_s` eemaldatud | 94,50 | 89,69% | 96,13% | 92,71% | 98,34% | 91,20% | 97,24% |

#### Klass `MODIFIED` – top-5

| Koht | Variant | Klassiskoor | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 | F1, X1–Y1 | Recall / TPR, X1–Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Medium Gaussian SVM, `duration_s` eemaldatud | 96,65 | 64,84% | 60,75% | 69,36% | 68,22% | 67,10% | 64,49% |
| 2 | SVM Kernel, `duration_s` eemaldatud | 96,35 | 65,52% | 62,15% | 68,22% | 68,22% | 66,87% | 65,19% |
| 3 | KNN k=21 inverse, kõik 8 tunnust | 94,33 | 64,06% | 61,21% | 68,69% | 68,69% | 66,38% | 64,95% |
| 4 | Medium Gaussian SVM, `distinct_speaker_count` eemaldatud | 94,24 | 66,00% | 62,15% | 66,51% | 65,89% | 66,26% | 64,02% |
| 5 | Medium Gaussian SVM, kõik 8 tunnust | 93,59 | 65,17% | 61,21% | 67,14% | 66,36% | 66,16% | 63,79% |

#### Klass `REJECTED` – top-5

| Koht | Variant | Klassiskoor | F1, X1 | Recall / TPR, X1 | F1, Y1 | Recall / TPR, Y1 | F1, X1–Y1 | Recall / TPR, X1–Y1 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | KNN k=21 inverse, `show_speaker_count` eemaldatud | 98,89 | 65,18% | 65,81% | 61,90% | 58,71% | 63,54% | 62,26% |
| 2 | KNN k=21 equal, `show_speaker_count` eemaldatud | 98,77 | 65,18% | 65,81% | 62,07% | 58,06% | 63,62% | 61,94% |
| 3 | KNN k=7 equal, `duration_s` eemaldatud | 98,15 | 62,62% | 63,23% | 62,71% | 61,29% | 62,66% | 62,26% |
| 4 | SVM Kernel, `duration_s` eemaldatud | 98,11 | 64,69% | 63,23% | 61,86% | 58,06% | 63,27% | 60,65% |
| 5 | Medium Gaussian SVM, `duration_s` eemaldatud | 97,43 | 62,91% | 61,29% | 62,07% | 58,06% | 62,49% | 59,68% |

#### Klassitop-5-st üldisest top-10-st välja jäänud variandid

| Variant | Jõudis klassi top-5 hulka | Üldine koondskoor |
|---|---|---:|
| KNN k=21 inverse, `show_speaker_count` eemaldatud | `REJECTED` | 90,71 |
| SVM Kernel, `duration_s` eemaldatud | `MODIFIED, REJECTED` | 90,67 |
| Quadratic SVM, `duration_s` eemaldatud | `ACCEPTED` | 90,03 |
| KNN k=21 inverse, kõik 8 tunnust | `MODIFIED` | 89,88 |
| KNN k=21 equal, `show_speaker_count` eemaldatud | `REJECTED` | 89,51 |

<!-- FINALIST_SELECTION_END -->

Variantide järjestus ei ole kõigis neljas saadetepõhises katses sama, kuid macro-F1
korrelatsioonid jäävad vahemikku 0,829–0,923 ning balanced accuracy omad
0,859–0,900. Kõige lähedasemad paarid on C1/D1 (macro-F1 0,923; balanced
accuracy 0,900) ja B2/D1 (vastavalt 0,902 ning 0,878). See toetab B1, B2,
C1 ja D1 ühist kasutamist finalistide eelvalikuks. Lõplik valik jääb siiski
Test3-eelselt fikseeritavaks.

### Täiendav mudel: Narrow Neural Network (MATLAB)

Lisamudel on MATLAB R2026b Statistics and Machine Learning Toolboxi
`fitcnet`-põhine närvivõrk: üks 10-neuroni ja ReLU aktiveerimisega peitkiht,
standarditud arvulised atribuudid ning kolm `decision`-klassi. Iga B-, C-, D-,
X- ja Y-treeningu kohta tehti kümme sõltumatut õpetamisjooksu seemnetega
1–10. Viiekordse valideerimise jaotus oli sama treeningu kõigi kümne jooksu
jaoks fikseeritud; jooksud erinevad võrgu juhusliku algseisu ja optimeerimise
tee poolest.

Allpool on kümne jooksu aritmeetilised keskmised. Sulgudes on accuracy
minimaalne ja maksimaalne väärtus kümne jooksu seas. Kõik 50 õpetamist ja
110 hindamistulemust lõpetasid staatusega `OK`; veafailis kirjeid ei olnud.

| Mudel ja test | Accuracy | Macro-F1 | Balanced accuracy | Weighted F1 |
|---|---:|---:|---:|---:|
| B1 | 78,69% (77,25–80,33%) | 70,39% | 70,51% | 79,08% |
| B2 | 69,41% (66,17–71,22%) | 71,63% | 72,38% | 69,15% |
| C1 | 70,52% (68,77–71,84%) | 69,98% | 70,48% | 69,97% |
| D1 | 72,30% (69,16–73,91%) | 71,77% | 72,25% | 71,85% |
| X1 | 72,25% (70,55–73,64%) | 71,71% | 72,80% | 71,57% |
| Y1 | 73,24% (70,91–75,09%) | 72,52% | 72,84% | 72,78% |

| Test | Recall / TPR: ACCEPTED | Recall / TPR: MODIFIED | Recall / TPR: REJECTED |
|---|---:|---:|---:|
| B1 | 91,38% | 60,47% | 59,67% |
| B2 | 87,42% | 69,80% | 59,92% |
| C1 | 92,58% | 61,35% | 57,52% |
| D1 | 94,16% | 64,15% | 58,43% |
| X1 | 96,85% | 57,15% | 64,39% |
| Y1 | 95,03% | 66,73% | 56,77% |

Sama finalistireegliga läbib Narrow Neural Network kohustusliku klassipõhise
filtri. B1–D1 järjestuses on see 52 filtri läbinud mudeli seas 34. kohal ning
X1–Y1 järjestuses 145 filtri läbinud mudeli seas 28. kohal. Seega ei muuda
see kummagi järjestuse top-10 koosseisu.

## Edasine katseplaan

1. Koostada Test3 seni kõigist treening- ja testandmetest välja jäänud
   kõlblikest kandidaatidest ning hinnata sellel finalistid, Narrow Neural
   Network ja võimalikud ansamblid.
2. Vajaduse korral koostada uus, umbes 1 500 kandidaadiga treeninghulk ja
   õpetada uued mudelid. Vana ning uus treeninghulk võrreldakse samal enne
   õpetamist fikseeritud Test3-l.

## Versiooniajalugu

| Kuupäev | Versioon | Muudatus |
|---|---|---|
| 15.10.2026 | 1.0 | Asendatud varasemad tulemused praeguse `human_action_required` märgendi, 5-fold valideerimise ja välise testi mudelivõrdlusega. Valitud mudel: Quadratic SVM. |
| 15.10.2026 | 1.1 | Lisatud kuue tunnusega kolmeklassilise `decision`-mudeli 5-fold valideerimise ja välise testi tulemused. Kolmeklassilise mudeli kandidaat: Boosted Trees (Model 6). |
| 19.10.2026 | 2.0 | Lisatud kaheksa atribuudiga Test1 katse: 488 kandidaati, 498 varianti, 0 viga. Lõplikku mudelit ega ansamblit pole veel valitud; Test2/Test3 ja uue treeninghulga võrdluse plaan fikseeritud. |
| 20.10.2026 | 2.1 | Lisatud GNU Octave'i Test1 katse ja MATLABi võrdlus: 498/498 edukat varianti, 450 täielikult kattuvat varianti, kNN-i tulemuste sisuline kattuvus ning iteratsioonipiiri hoiatuseta SVM-i seadistus. |
| 20.10.2026 | 2.2 | Fikseeritud Test2: 337 kandidaati 14 terviksaatest, samade atribuutidega CSV ja manifest; tulemusi pole veel arvutatud. Test2 on ette nähtud üksnes GNU Octave'i katses. |
| 20.10.2026 | 2.3 | Lisatud GNU Octave'i Test2 katse ja Test1–Test2 võrdlus. Kõik 498 Test2 varianti lõpetasid vigadeta; Test1 SVM-i osas kasutatakse uuemat 54 katse tulemust. |
| 20.10.2026 | 2.4 | Lisatud C1 ja D1 70/30 saadetepõhise ümberjaotuse tulemused: mõlemas 498/498 edukat varianti, 0 viga; B1/B2/C1/D1 ühine mõõdikute ja klasside võrdlus. |
| 20.10.2026 | 2.5 | Põhidokument koondati praegusele kolmeklassilisele B1/B2/C1/D1/X1 katseraamile; varasemad MATLABi eelkatsed ja MATLAB–Octave'i Test1 teostusvõrdlus tõsteti faili `matlab_eelkatsed.md`. |
| 20.10.2026 | 2.6 | Lisatud põhidokumenti nelja testmõõdiku top-tabelid ning eraldi täielik 498 mudelivariandi B1–D1 koondtabel. Tabelites on lisaks top-10-le iga katse absoluutne parim ja viimane variant. |
| 20.10.2026 | 2.7 | Lisatud X1 kandidaadipõhise juhujaotuse tulemused: 498/498 edukat varianti, 550 testirida ning X1 veerg põhidokumendi ja täielikus koondtabelis. |
| 20.10.2026 | 2.8 | Lisatud iga otsuseklassi kuus parimate mudelite tabelit. Need kasutavad B1–D1 keskmise järgi top-5 järjestust ning näitavad eraldi ka iga katse sisuliselt parimaid ja halvimaid variante. |
| 20.10.2026 | 2.9 | Fikseeritud finalistide valikureegel: klassipõhine 50% F1 ja 55% recall'i filter, kaalutud üldine top-10, kolme klassi top-5 ning üldisest top-10-st välja jäänud klassifinalistid. |
| 20.10.2026 | 3.0 | Lisatud Y1 sõltumatu kandidaadipõhise 70/30 jaotuse tulemused: 498/498 edukat varianti, 550 testirida, X1–Y1 võrdlus ning Y1 veerg üld-, klassi- ja detailtabelites. |
| 20.10.2026 | 3.1 | Lisatud X1–Y1 kandidaadipõhine finalistivalik: sama klassipõhine filter ja sama protsentiilne kaalutud algoritm nagu B1–D1 valikul; tulemus on eraldi võrdlusvaade. |
| 20.10.2026 | 3.2 | Lisatud kõigi kandidaatidega saadete toorkandidaatide tihedus osalejate arvu järgi ning fikseeritud, et saadetepõhine ja kandidaadipõhine jaotus on praegu samaväärsed võrdlusandmed. |
| 21.10.2026 | 3.3 | Lisatud MATLABi Narrow Neural Networki katse: üks 10-neuroni ReLU peitkihiga `fitcnet`-mudel, kümme sõltumatut jooksu iga B/C/D/X/Y treeningu kohta, kokku 50 edukat õpetamist ja 110 hindamistulemust. |

