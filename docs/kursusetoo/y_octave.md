# Y1: teine kandidaadipõhise juhujaotuse GNU Octave'i kontrollkatse

Y kasutab sama 1 831 kandidaadi kogumit kui X, C ja D: B-treening, B1 ja B2.
See on X-ist sõltumatu kandidaatide kaupa tehtud 70/30 jaotus; saatepiirangut
ei rakendata ning sama saate kandidaadid võivad olla nii Y-treeningus kui Y1
testis. Y1 kontrollib, kas X1 tulemus on stabiilne ka teise juhujaotuse korral.

Valik on otsuseklassi järgi stratified ning kasutab Python
`secrets.SystemRandom`-it ehk operatsioonisüsteemi CSPRNG-d. Y testijaotus ei
ole X1-ga sama: 550 testikandidaadist kattub X1-ga 167 (Jaccardi indeks
17,90%). Manifestis olev kandidaatide loetelu ja kontrollsummad muudavad
tegelikult valitud Y-jaotuse täielikult auditeeritavaks.

| Jaotus | Treening | Test | Testi osakaal | A / M / R |
|---|---:|---:|---:|---|
| Y / Y1 | 1 281 | 550 | 30,0% | treening 422 / 498 / 361; test 181 / 214 / 155 |

Treeningu SHA-256 on
`94ba65adfa3532f7d4b90216a2d293b96b8dbd46f6ac9c341c4107932e22c0a0`;
testi SHA-256 on
`2842a3d6830b2ed7d3821c64f4ac2452d82c7f221a901d1668d66d0b836e2394`.
Treeningu ja testi vahel kattub 77 saadet. Täpne koosseis on failis
`manifestid/y_split_manifest.json`; andmete koostamise skript on
`scripts/create_y_split.py`.

## Käivitus

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_y.csv','log/test_data_y1.csv');"
```

Katse kasutab sama 498 mudelivariandi plaani, samu kaheksat
atribuuti ja kuue standardse `templateSVM` mudeli tolerantsi `1e-3` nagu
X1. Tulemuste kaust luuakse `log/` alla ning nime lõpus on `_y1_octave`.

## Tähistus

- **Y1**: Y-treeninguga õpetatud mudelite hindamine teisel sõltumatul
  kandidaadipõhisel juhutestil.
- **Y3**: hiljem Y-treeninguga õpetatud mudelite hindamine samal seni
  puutumata Test3-l nagu B3, C3, D3 ja X3.

Y1 tulemusi võrreldakse esmalt X1 ning B1–D1 tulemustega. Kui X1 ja Y1
annavad samalaadse pildi, kasutatakse X1/Y1 eraldi kontrollvaatena;
saadetepõhine B1–D1 valikureegel jääb eraldi alles.
