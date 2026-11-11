# Test1: eraldi GNU Octave'i katse

## Eesmärk

`test_all_models_octave.m` kordab Test1 katseplaani GNU Octave 11.1.0 ja
Octave Statistics 2.0.1 abil. See kasutab samu fikseeritud sisendfaile,
protsessi-/kandidaadivalimit, mudeli kaheksat atribuuti, 498 mudelivarianti
ja mõõdikute valemeid nagu MATLABi Test1 katse.

See on **eraldi Octave'i teostuse katse**, mitte väide, et tulemused on
MATLABi tulemustega bititäpselt samad. Octave Statisticsi puu-, SVM-,
kernel- ja ansamblialgoritmid võivad MATLABist erineda. Tulemusi võrreldakse
seetõttu Octave'i katse sees ning MATLABiga mudelite järjestuse,
klassipõhiste mõõdikute ja ennustuste tasemel.

MATLABi olemasolevad Test1 tulemused jäävad muutmata.

## Käivitamine serveris

Käivita projekti juurkataloogist:

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_b.csv','log/test1_data_b.csv');"
```

Skript laadib ise `statistics` paketi. Kasutatakse samu sisendite kontrolli
reegleid: 1 006 treeningrida, 488 Test1 rida, fikseeritud protsessi- ja
kandidaadi-ID-d, klassijaotused ning saadete mittekattumine.

Üksnes nimetatud mitte-kNN mudelite uuesti käivitamiseks võib kolmanda
argumendina anda mudelinimede loendi. Näiteks kuue standardse SVM-i
kontrolliks pärast SVM-i parameetrimuudatust:

```bash
octave11 --eval "addpath('docs/kursusetoo/scripts'); test_all_models_octave('log/training_data_b.csv','log/test1_data_b.csv',{'Linear SVM','Quadratic SVM','Cubic SVM','Fine Gaussian SVM','Medium Gaussian SVM','Coarse Gaussian SVM'});"
```

See käivitab 54 varianti (kuus mudelit × üheksa tunnusevarianti) ega käivita
kNN-i ega ülejäänud mudeleid.

## Katseplaan

- 15 muud mudelit: kõik kaheksa tunnust ja iga tunnuse eraldi eemaldamine
  (135 varianti).
- 33 kNN-seadistust: k = 1, 3, 5, 7, 10, 15, 21, 31, 51, 75, 100 ning
  kaalud `equal`, `inverse`, `squaredinverse`; kõik tunnused, kaheksa üksikut
  eemaldamist, kaks kõnelejate loendurit koos ja neli uut tunnust koos
  (363 varianti).
- Kokku 498 varianti.

kNN-i numbrilised tunnused normaliseeritakse ainult treeningandmete keskmise
ja standardhälbega. `candidate_type` kodeeritakse ainult treeningandmetest
saadud one-hot veergudeks. Teiste mudelite puhul jääb `candidate_type`
Octave'i tabelis kategooriliseks tekstiveeruks, nagu Octave Statistics seda
tabeli sisendina käsitleb.

Kuue `templateSVM` mudeli lõpetamistolerants on `1e-3`, mis on kasutatava
LIBSVM-i dokumenteeritud tavaväärtus. Octave Statisticsi `ClassificationSVM`
vaikimisi `1e-6` on selle andmestiku puhul liiga range ning võib viia sisemise
iteratsioonipiiri hoiatuseni. Väärtus salvestatakse iga katse
`settings_test1_octave.mat` faili.

## Väljundid

Iga käivitus loob projekti `log/` kataloogi unikaalse `_test1_octave` lõpuga
tulemuste kausta. Konteineri `/tmp` kataloogi ei kasutata, seega tulemused
jäävad alles ka pärast konteineri lõppemist.

| Fail | Sisu |
|---|---|
| `models_test1_octave.csv` | Mudeli üldmõõdikud ja staatus |
| `perclass_test1_octave.csv` | Klassi TP, FP, TN, FN, precision, TPR, FPR, FNR, F1 ja specificity |
| `confusion_test1_octave.csv` | Segadusmaatriksi kõik lahtrid |
| `predictions_test1_octave.csv` | Kandidaadipõhised tegelikud ja ennustatud klassid |
| `errors_test1_octave.csv` | Ainult ebaõnnestunud variandid; katse jätkub järgmise variandiga |
| `settings_test1_octave.mat` | Katseplaan, sisendfailid, kodeering ja Octave'i versioon |
| `results_test1_octave.mat` | Väljundfailide asukohad ning edukate/ebaõnnestunud variantide arv |

CSV-failidesse kirjutatakse iga variandi tulemused kohe. Katkestuse korral
jäävad juba lõpetatud variandid alles, kuid automaatset jätkamist ei ole.

## Teadlikud erinevused MATLABi katsest

- MATLABi `table`, `writetable`, `height`, `strlength`, `getReport` ja Java
  kontrollsumma sõltuvust ei kasutata.
- Octave'is puudub MATLABi `permutationImportance`; seda Test1
  hindamisskript niigi ei kasuta.
- Sama mudelinimi, parameetrid ja seeme ei taga puude, SVM-ide, kernelmudelite
  ega ansamblite identseid otsuseid, sest Statistics 2.0.1 teostus erineb
  MATLABi omast.
