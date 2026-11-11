# kNN tunnuste analüüs

Käivita projekti juurkataloogist; skript asub
`docs/kursusetoo/scripts/` ja täielik treening-CSV `log/` kataloogis:

```matlab
addpath("docs/kursusetoo/scripts");
outputs_knn = analyze_feature_value_knn("log/training_data_b.csv");
```

Nõuab Statistics and Machine Learning Toolboxi. Testfaili ei loeta.
33 varianti: k = 1, 3, 5, 7, 10, 15, 21, 31, 51, 75, 100 ning
DistanceWeight = equal, inverse, squaredinverse. Kaugus on Euclidean.
Parameetrid: https://www.mathworks.com/help/stats/fitcknn.html

Viis saatepõhist foldi luuakse sama algoritmi ja seemnega (20261017) nagu
`analyze_feature_value.m`. Sama järjestusega algfail annab sama jaotuse.
Process ja muud ID-d ei sisene mudelisse. Skaleerimise keskmised ja
standardhälbed arvutatakse iga foldi treeningosast. Konstantse tunnuse
standardhälbe asemel kasutatakse 1. Kategooriad õpitakse treeningosast;
candidate_type kodeeritakse skaleerimata 0/1 indikaatoriteks, tundmatul
kategoorial on eraldi indikaator. Numbrilise skaala erinevused eemaldatakse,
kuid harvaesinevaid kategooriaid ei võimendata dispersiooniga skaleerides.
Kodeerimisvalik on selle katse fikseeritud eeldus.

Permutation importance mõõdetakse täielikel treeningandmetel 30 segamisega.
See mõõdab mudeli sõltuvust tunnusest; eriti k=1 puhul ei tõesta kõrge
treeningtäpsus ega olulisus üldistumisvõimet. Candidate_type indikaatorid
segatakse ühe grupina sama reavahetusega. Mõõdik on treeningtäpsuse langus.
Sama segamiste jada kasutatakse kõigil 33 konfiguratsioonil.

Eemaldamiskatses treenitakse igas foldis uus mudel, säilitades k, kaalumise,
kauguse ning ülejäänud tunnuste kodeerimise ja skaleerimise. Eemaldatakse
iga tunnus eraldi, kaks loendust koos ning kõik neli uut tunnust koos.
Viimane võrdlus jätab alles neli ühist atribuuti; see EI ole vana kuue
tunnusega A-komplekt. AccuracyDrop = täiskomplekti CVAccuracy miinus
eemaldatud tunnusega CVAccuracy. Negatiivne väärtus tähendab paranemist.
MacroF1Drop töötab samal põhimõttel. Muutuste mõju ei ole liidetav.
Üks jaotus ei anna statistilise kindluse hinnangut; eri k väärtused pole
sõltumatud korduskatsed.

Iga käivitus loob CSV kõrvale uue `_knn` lõpuga tulemuste kausta. Põhifailid:

- model_validation_results_knn.csv
- permutation_importance_all_models_knn.csv
- feature_ablation_all_models_knn.csv
- feature_value_summary_knn.csv

Lisaks errors_knn.csv (tühjana vigu pole), validation_folds_knn.csv,
settings_knn.mat ja feature_value_results_knn.mat. Edukad tulemused
salvestatakse iga konfiguratsiooni järel; vead säilivad eraldi ja ei
tekita samast katsest vasturääkivaid OK/FAILED ridu.

Kõik täpsused, recall'id, F1-d ja erinevused on skaalal 0–1.
0.01 täpsuse muutust tähendab üht protsendipunkti.
Koondi ModelsUsingPredictor loendab positiivse keskmise olulisusega
konfiguratsioone, mitte statistiliselt tõestatud kasulikkust.

Skript on staatiliselt üle vaadatud; selles serveris MATLAB puudub,
seega MATLABi käivitust siin kontrollida ei saanud.
