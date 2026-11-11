# C1 ja D1: GNU Octave'i katsed

C ja D on kaks uut, reprodutseeritavat treeningu/testi ümberjaotust samast
juba fikseeritud 1 831 kandidaadi kogumist: B-treening, B1 (Test1) ja B2
(Test2). Nad ei muuda ega asenda B, B1 või B2 andmeid. Iga saate kõik
kandidaadid kuuluvad ühes C- või D-jaotuses ainult treeningusse või testi.

Jaotused koostas `scripts/create_c_d_splits.py` protsessitaseme juhuvalikuga.
Kasutati kahte eri fikseeritud seemet ning kummagi puhul hinnati 50 000
sõltumatut 70/30 Bernoulli-jaotust. Valiti madalaima tasakaaluskooriga
lubatud jaotus: mõlemas osas peab olema `ACCEPTED`, `MODIFIED` ja `REJECTED`
ning 2-, 3- ja 4+ osalejaga saated; testis olev `candidate_type` peab esinema
ka treeningus. Valiku eesmärk oli umbes 30% testiridu ja koguühendile lähedane
klassijaotus. Täpsed seemned, protsessid ja kontrollsummad on manifestides.

| Jaotus | Treening | Test | Testi osakaal | Treeningu protsesse | Testi protsesse |
|---|---:|---:|---:|---:|---:|
| C / C1 | 1 277 | 554 | 30,3% | 58 | 22 |
| D / D1 | 1 283 | 548 | 29,9% | 55 | 25 |

| Jaotus | Treening: A / M / R | Test: A / M / R | Seeme | Treeningu SHA-256 | Testi SHA-256 |
|---|---|---|---:|---|---|
| C / C1 | 421 / 497 / 359 | 182 / 215 / 157 | 485716290318 | `81c8fb6e9987634bcfdf181b5b5822154b610c556e18894d10cbdc7089a4b2ca` | `b8f6aaeab5b712fc9a12063203a7783f09cef11529295c65280f0cc5db222a4d` |
| D / D1 | 425 / 495 / 363 | 178 / 217 / 153 | 739184620557 | `99bf85f7a519520d1d56d420f567de866714501daf1baddee7d22fe4b76a9ad8` | `a24d939099c7ba2e1b068089a8264ab7290ac7e47344cc9343bcad1f6a847a26` |

Test C1 protsessid: `16, 20–21, 29, 31, 33, 35–36, 40, 50, 53–55, 65–66,
69, 78, 84–85, 91, 95, 101`.

Test D1 protsessid: `18, 24, 31–32, 34, 36, 38–39, 48, 58, 62, 69, 71–72,
76, 79, 83, 86, 89, 91, 93, 98, 101, 103, 107`.

Täielikud koosseisud on vastavalt
`manifestid/c_split_manifest.json` ja `manifestid/d_split_manifest.json`.

## Käivitus

C1:

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_c.csv','log/test_data_c1.csv');"
```

D1:

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_d.csv','log/test_data_d1.csv');"
```

Mõlemad kasutavad sama 498 mudelivariandi plaani, samu kaheksat
atribuuti ning kuue standardse `templateSVM` mudeli tolerantsi `1e-3`.
Väljundid kirjutatakse eraldi C1- või D1-nimelisse Octave'i tulemuste
kataloogi. C1 ja D1 käivitatakse üksteisest sõltumatute protsessidena.

## Tulemus

Mõlemad käivitused lõpetasid 2026-10-20: C1 ja D1 puhul sai **498/498**
varianti staatuse `OK`; vigu ei olnud. Täielik nelja katse B1/B2/C1/D1
võrdlus on failis `tulemused.md`.

## Tähistus

- **B1**: B-treeninguga hinnatud Test1.
- **B2**: B-treeninguga hinnatud Test2.
- **C1**: C-treeninguga hinnatud C-test.
- **D1**: D-treeninguga hinnatud D-test.
- **B3**, **C3**, **D3**: hiljem samal seni puutumata Test3-l hinnatavad
  B-, C- ja D-mudelid.

Test3 on ühine sõltumatu lõppvõrdlus. Finalistid fikseeritakse B1, B2, C1
ja D1 tulemuste põhjal enne B3/C3/D3 hindamist.
