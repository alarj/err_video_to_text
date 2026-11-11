# X1: kandidaadipõhise juhujaotuse GNU Octave'i kontrollkatse

X kasutab sama 1 831 kandidaadi kogumit nagu C ja D: B-treening, B1 ja B2.
Erinevalt B1/B2/C1/D1 katsetest ei ole X-s saatepiirangut. Sama saate eri
kandidaadid võivad olla nii X-treeningus kui X1 testis. Seega on X1 teadlik
võrdluskatse, mis mõõdab, kui palju annab tulemusele juurde samast saatest
tulenev treeningu/testi kattuv kontekst. Seda ei kasutata finalistide
valimise argumendina.

Valik tehti kandidaatide kaupa otsuseklassi stratifikatsiooniga 70/30
jaotuses. Juhuarvud pärinevad Python `secrets.SystemRandom`-ist, mida toetab
operatsioonisüsteemi krüptograafiliselt turvaline juhuarvugeneraator. Kuna
sellel pole kasutajaseemet, fikseerib katse täielikult manifestis olev
kandidaatide loetelu ja CSV-de kontrollsummad.

| Jaotus | Treening | Test | Testi osakaal | A / M / R |
|---|---:|---:|---:|---|
| X / X1 | 1 281 | 550 | 30,0% | treening 422 / 498 / 361; test 181 / 214 / 155 |

Treeningu SHA-256 on
`281be2ba5f8294ae68e2fb77886fbcb792874a32aebab82a798c5c8d758e06ff`;
testi SHA-256 on
`c9254d5c8f89339b943703dd6e5b22c21e5e62ee988f33a321ae7630806ec0a8`.
X-treeningu ja X1 testi vahel kattub 77 saadet. Täpne koosseis on failis
`manifestid/x_split_manifest.json`; andmete koostamise skript on
`scripts/create_x_split.py`.

## Käivitus

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_x.csv','log/test_data_x1.csv');"
```

Katse kasutab sama 498 mudelivariandi plaani, samu kaheksat
atribuuti ja kuue standardse `templateSVM` mudeli tolerantsi `1e-3`.

## Tähistus

- **X1**: X-treeninguga õpetatud mudelite hindamine kandidaadipõhisel
  juhutestil.
- **X3**: hiljem X-treeninguga õpetatud mudelite hindamine samal seni
  puutumata Test3-l nagu B3, C3 ja D3.

X1 lisatakse B1/B2/C1/D1 tulemustabelite kõrvale võrdlusmaterjalina.
