# Test1: andmed ja kõigi mudelite testimine

GNU Octave'i eraldi korduskatse juhend ja käivitus on failis
[`test1_octave.md`](test1_octave.md). See ei asenda käesoleva
MATLABi katse tulemusi ega eelda nendega täpset arvulist kokkulangevust.

## Käivitamine MATLABis

Käivita projekti juurkataloogist. Andme-CSV-d jäävad `log/` kataloogi ja
skript asub `docs/kursusetoo/scripts/` kataloogis.

```matlab
addpath("docs/kursusetoo/scripts");
outputs_test1 = test_all_models("log/training_data_b.csv", "log/test1_data_b.csv");
```

Vajalik on Statistics and Machine Learning Toolbox. Java ei ole vajalik.
Kasuta sama MATLABi versiooni nagu treenimisel (R2026b). Siinses keskkonnas
MATLABi pole; skripti pole siin MATLABiga käivitatud.

## Andmed

Test1 sisaldab registris `docs/evaluation_data.md` fikseeritud 488 kandidaati
15 protsessist: 14–16 ja 18–29. Klassid: ACCEPTED 290, MODIFIED 107,
REJECTED 91. Teadaolevalt vigased sildid on välistatud.

Kaheksa atribuudi nimed, järjekord ja arvutusreeglid on samad kui treeningus.
ID-d ja `decision` ei ole atribuudid. CSV-s pole vanu kasutamata
`spans`, `speakers`, `max_confidence` ega vastusest tuletatud
`human_action_required` veerge. Fail sisaldab nelja ID/viiteveeru, kaheksat
sisendit ja vastuseveergu `decision`.

Tunnused pärinevad automaatsest mustandist ja selle algsetest artefaktidest;
inimese otsus on ainult vastus. Ühiste kandidaatide kõik kaheksa tunnust
võrreldi varasema B-testfailiga. Puuduvaid väärtusi ei täidetud ja ridu ei
eemaldatud. Päritolu ning failide SHA-256 on
[`manifestid/test1_manifest.json`](manifestid/test1_manifest.json) failis.
Eksport: [`scripts/export_test1.py`](scripts/export_test1.py) kasutab olemasolevat geomeetriafunktsiooni ja
Oracle'i `SET TRANSACTION READ ONLY` ühendust.

## Mudelid ja tingimused

Varasemad analüüsiskriptid ei salvestanud sobitatud mudeliobjekte.
Seetõttu sobitab skript mudelid uuesti kogu muutmata treeningfailil;
Test1 kasutatakse ainult ennustamiseks ja hindamiseks. See ei ole uus
ristvalideerimine ega hüperparameetrite otsing. CV alamvalimite mudelite asemel
kasutatakse väliseks testiks kogu treeninghulgal sobitatud mudeleid.

- 15 muud mudelit: kõik 8 tunnust ning iga tunnuse eraldi eemaldamine
  (9 varianti, kokku 135).
- 33 kNN-seadistust: k = 1, 3, 5, 7, 10, 15, 21, 31, 51, 75, 100;
  kaalud equal, inverse, squaredinverse. Kõik tunnused, kaheksa üksikut
  eemaldamist, mõlemad kõnelejate loendurid koos ning neli uut tunnust koos
  (11 varianti, kokku 363).
- Kokku 498 eelnevalt määratud mudeli/tunnusekomplekti kombinatsiooni.
  Tunnuste eemaldamise variantide täisandmetel mudelid sobitatakse nüüd;
  varasemates katsetes hinnati neid CV kaudu.
- Mudelite loomise ja kNN-kodeeringu funktsioonid on muutmata koopiad
  analüüsiskriptidest. Gaussian SVM-i skaala sõltub allesjäänud tunnuste arvust
  täpselt nagu varasemal tunnuste eemaldamise katsel.
- Muude mudelite täistreeningu juhuseeme on 100000 + mudeli järjekorranumber,
  nagu algses skriptis; seda kasutatakse ka eemaldamisvariantidel.
- kNN-i numbriliste tunnuste keskmine ja standardhälve ning kategooriate
  one-hot-kodeering õpitakse ainult treeningandmetest. Kategooriaid ei skaleerita.
  Tunnuse eemaldamisel eemaldatakse kogu vastav kodeeritud veeruplokk.
- Enne treenimist kontrollitakse Java-vabalt nõutud veerge, ridade arvu,
  protsesside ja kandidaatide koosseisu, klassijaotusi ning saadete
  mittekattumist. SHA-256 kontrollsummad on manifestides väliseks kontrolliks;
  skript neid käivitamisel ei arvuta.

## Väljundid

Iga käivitus loob uue `_test1` lõpuga kausta ega kirjuta varasemaid tulemusi üle.

| Fail | Sisu |
|---|---|
| `models_test1.csv` | TrainingAccuracy, Accuracy, MacroF1, BalancedAccuracy, WeightedF1 ja staatus iga variandi kohta |
| `perclass_test1.csv` | Iga klassi Support, TP, FP, TN, FN, Precision, Recall/TPR, F1, FPR, FNR, Specificity/TNR |
| `confusion_test1.csv` | Kõik 9 segadusmaatriksi lahtrit iga variandi kohta; read tegelik, veerud ennustatud klass |
| `predictions_test1.csv` | Iga kandidaadi tegelik ja ennustatud klass, protsessi ja kandidaadi ID-ga |
| `errors_test1.csv` | Ebaõnnestunud variandid ja veateated; ülejäänud jätkavad |
| `settings_test1.mat` | Fikseeritud katseplaan, andmed, eeltöötlus, MATLABi ja toolboxide versioonid |
| `models/model_NNN.mat` | Sobitatud mudel, tunnused, variant ja eeltöötlus |
| `results_test1.mat` | Koondtulemused |

Mõõdikud on osakaalud 0–1, mitte protsendid. FPR = FP/(FP+TN),
FNR = FN/(FN+TP); klassipõhised mõõdikud kasutavad one-vs-rest põhimõtet.
BalancedAccuracy on kolme klassi recall'i keskmine. MacroF1 on klasside
F1 aritmeetiline keskmine, WeightedF1 kaalub klasside tegelike suurustega.
Nullnimetajaga mõõdik on NaN, mitte eksitav null.

CSV-d salvestatakse iga variandi järel. Katkestatud käivituse lõpetatud mudelid
ja tulemused jäävad alles; automaatset poolelijäänud käivituse jätkamist pole.
Testitulemuste järgi skript tunnuseid ega parameetreid ei muuda.
