# Test2: GNU Octave'i katse

Test2 kasutab muutmata `log/training_data_b.csv` treeningfaili ja fikseeritud
`log/test2_data_b.csv` testfaili. Test2 sisaldab 337 kandidaati 14 terviksaatest:
`33, 43, 79–80, 83, 89, 91, 94, 102–105, 107–108`. Klassijaotus on 62
`ACCEPTED`, 151 `MODIFIED` ja 124 `REJECTED`.

Katse on eraldi GNU Octave'i teostus. MATLABi Test2 katset ei tehta.
Kasutatakse Test1-ga sama 498 mudelivariandi plaani, samu kaheksat
atribuuti ning samu mõõdikuid. Enne käivitust tuleb Test2 CSV koostada:

```bash
python docs/kursusetoo/scripts/export_test2.py
```

Seejärel käivita projekti juurkataloogist:

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_b.csv','log/test2_data_b.csv');"
```

Olemasolev Octave'i skript on enne Test2 käivitamist üldistatud nii, et see
kontrollib CSV nime järgi Test1 või Test2 fikseeritud koosseisu ning kirjutab
Test2 väljundid eraldi `_test2_octave` kataloogi. Test1 käivitus ja selle
väljundid jäävad muutmata.

## Tulemus

Katse lõpetas 2026-10-20: **498/498** mudeli/tunnusevarianti said staatuse
`OK` ja vigu ei olnud. Väljundid asuvad kataloogis
`log/oct-rdhW8P_test2_octave`; käituslogi on `log/test2_octave_run.log`.
