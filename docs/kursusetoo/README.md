# Kursusetöö

See kataloog sisaldab kursusetöö dokumentatsiooni, fikseeritud andmevalimite
manifeste ja nende koostamise, analüüsi ning hindamise skripte. Need failid on
Gititavad. Andme-CSV-d, MATLABi/Octave'i käituste logid ja tulemuste kaustad
jäävad projekti juurkataloogi `log/` alla ning Git neid ei jälgi.

| Asukoht | Sisu |
|---|---|
| [`tulemused.md`](tulemused.md) | Katsete tulemused, järeldused ja edasine plaan |
| [`tulemused2.md`](tulemused2.md) | Binaarse inimsekkumise (0/1) katse tulemused ja valikureegel |
| [`mudelivariantide_koondtulemused.md`](mudelivariantide_koondtulemused.md) | Kõigi 498 mudelivariandi B1–D1 ja X1 mõõdikud |
| [`mudelivariantide_koondtulemused2.md`](mudelivariantide_koondtulemused2.md) | Kõigi 498 binaarse inimsekkumise mudelivariandi detailtulemused |
| [`matlab_eelkatsed.md`](matlab_eelkatsed.md) | Varasemad MATLABi eelkatsed ja MATLAB–Octave'i Test1 teostusvõrdlus |
| [`andmestik_b.md`](andmestik_b.md) | Mudeli kaheksa atribuudi päritolu ja arvutusreeglid |
| [`test1_matlab.md`](test1_matlab.md) | MATLABi Test1 katseplaan ja mõõdikud |
| [`test1_octave.md`](test1_octave.md) | GNU Octave'i Test1 katseplaan ja käivitus |
| [`test2_octave.md`](test2_octave.md) | GNU Octave'i Test2 katseplaan ja käivitus |
| [`c_d_octave.md`](c_d_octave.md) | C1 ja D1 ümberjaotuste metoodika, manifestid ja GNU Octave'i käivitus |
| [`x_octave.md`](x_octave.md) | X1 kandidaadipõhise juhujaotuse kontrollkatse ja GNU Octave'i käivitus |
| [`y_octave.md`](y_octave.md) | Y1 teine sõltumatu kandidaadipõhise juhujaotuse kontrollkatse ja GNU Octave'i käivitus |
| [`knn_tunnuste_analuus.md`](knn_tunnuste_analuus.md) | kNN-i tunnuste analüüsi metoodika |
| [`andmestik_ajalooline_test.md`](andmestik_ajalooline_test.md) | Varasema testandmestiku ajalooline kirjeldus |
| [`manifestid/`](manifestid/) | Fikseeritud B-, Test1- ja Test2-andmestiku päritolu ning kontrollsummad |
| [`scripts/`](scripts/) | Andmete eksportimise, mudelite analüüsi ja testimise skriptid |

Kursusetöö andmete kasutusluba ja protsesside koosseis on autoriteetselt
kirjas failis [`../evaluation_data.md`](../evaluation_data.md). Kõik
katsetes kasutatavad CSV-failid paiknevad `log/` kataloogis.

GNU Octave'i Test1 käivitus projekti juurkataloogist:

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_b.csv','log/test1_data_b.csv');"
```

Test2 ekspordi- ja Octave'i käivitusjuhis on failis
[`test2_octave.md`](test2_octave.md). MATLABi Test2 katset ei tehta.
