# Analüüsi- ja õppeandmete register

## Eesmärk

Register määrab, milliseid inimese lõpetatud tehniliste kandidaatide otsuseid
võib kasutada ICM0035 kursusetöö analüüsis ja mudelkatsetes. See ei ole
tootmismudeli õppeandmete register.

Kursusetöö jaoks on analüüsiks lubatud iga allolevas tabelis nimetatud
kandidaadivahemik. Protsessi olek või `FINAL` versiooni olemasolu ei ole
selle valiku kriteerium. Tootmismudeli õpetamine eeldaks eraldi valideeritud
`FINAL` versiooni; käesolevas tabelis on selle veerg seetõttu kõikjal `Ei`.

Analüüsiloa tingimus on, et kandidaadil on inimese lõpetatud ja omavahel
kooskõlaline `status`, `decision` ning `decision_at`:
`ACCEPTED`, `MODIFIED` või `REJECTED`. `PENDING` kandidaate ei kasutata.

## Välistatud andmed

| Protsess või vahemik | Analüüsiks | Põhjus |
|---|---|---|
| `#13` | Ei | Kõik 34 otsust salvestati vana UI tõttu `MODIFIED`-na; tegelikku otsuseliiki ei saa taastada. |
| `#17` | Ei | Kõik 46 otsust salvestati vana UI tõttu `MODIFIED`-na; tegelikku otsuseliiki ei saa taastada. |
| `#15`, kandidaadid `171–178` | Ei | Otsused salvestati enne otsuseliikide parandust `MODIFIED`-na. |

2026-10-17 kasutaja kinnitatud erand: B-tunnustega ajaloolises testfailis
`log/test_data_b.csv` säilitatakse varasema 341-realise CSV täpne koosseis,
sealhulgas protsessi 15 kandidaadid 171–178 ja nende senised sildid.
Erand võimaldab võrrelda sama valimi tulemusi; nende kaheksa sildi teadaolev
ebausaldusväärsus säilib. Erand ei laiene treeningule ega uutele testvalimitele.

## Andmehulkade jaotus

| Andmehulk | Protsessid | Staatus ja kasutus |
|---|---|---|
| Treeningandmed | `31–32, 34–42, 44, 47–50, 53–55, 57–59, 61–67, 69, 71–72, 75–78, 81–82, 84–86, 88, 90, 93, 95–101` | Praegune 1 006-realine treeningandmestik |
| Testandmestik 1 | `14–16, 18–29` | 2026-10-19 fikseeritud 488 kandidaati 15 protsessist; CSV `log/test1_data_b.csv`. Sellel hinnati 498 eelnevalt fikseeritud mudeli/tunnusevarianti. |
| Testandmestik 2 | `33, 43, 79–80, 83, 89, 91, 94, 102–105, 107–108` | 2026-10-20 fikseeritud 337 kandidaati 14 terviksaatest; CSV `log/test2_data_b.csv`. Hinnatud eraldi GNU Octave'i katses: 498/498 varianti, 0 viga. |
| Testandmestik 3 (võimalik) | Treeningust ja Test1–Test2-st väljas olevad `109+` protsessid | Täpne koosseis ja maht pole veel määratud. Protsessid 100 ja 101 kuuluvad praegusesse treeningusse ning 102–108 Test2-sse. |

### Fikseeritud koosseis, 2026-10-19 ja 2026-10-20

Treeningu aluseks on muutmata `log/training_data_b.csv`: 1 006 kandidaati
51 protsessist. Täpsed kandidaadivahemikud on allolevas registris treeningu
protsesside ridadel; uued otsused neisse automaatselt ei lisandu.
Faili SHA-256: `4a7e4dbbbf8c760e10ae49f9cc2b0d77de96fa0ee517731053486d64328c9095`.

| Andmehulk | Kandidaate | ACCEPTED | MODIFIED | REJECTED |
|---|---:|---:|---:|---:|
| Treening | 1 006 | 251 | 454 | 301 |
| Test1 | 488 | 290 | 107 | 91 |
| Test2 | 337 | 62 | 151 | 124 |

Test1 sisaldab protsesside 14–29 kõiki kontrolli hetkeks lõpetatud,
kooskõlalisi ja kvaliteedipiirangutele vastavaid otsuseid. 542 lõpetatud
otsusest on välja jäetud protsess 17 (46 kandidaati) ning protsessi 15
kandidaadid 171–178 (8 kandidaati). Protsessist 25 kuulub komplekti
24 ülevaadatud kandidaati; 38 ülevaatamata kandidaati jäävad välja.
Varasem 341-realine `log/test_data_b.csv` jääb ajalooliseks failiks ega
esinda uut Test1 koosseisu.

Test1 fail: `log/test1_data_b.csv`, SHA-256
`de55ad11a8236782ef286e2876c0ba32d1cf9a145377ea3afe0c7d1e0ff08c7e`.
Päritolu on `docs/kursusetoo/manifestid/test1_manifest.json` failis. Kõigi fikseeritud mudelite ja
tunnusevariantide testimisskript on `docs/kursusetoo/scripts/test_all_models.m`; käivitusjuhend
ja mõõdikud on `docs/kursusetoo/test1_matlab.md` failis. Test käivitati MATLABis
2026-10-19: 498/498 varianti lõpetasid, vigu oli 0. Tulemuste kokkuvõte on
`docs/kursusetoo/tulemused.md` failis.

Sama fikseeritud Test1 katseplaan on realiseeritud ka eraldi GNU Octave'i
katsena failis `docs/kursusetoo/scripts/test_all_models_octave.m`. See kasutab samu sisendfaile
ja mõõdikuid, kuid on Octave'i teostuse katse; selle arvusid ei käsitleta
MATLABi tulemuste täpse kordusena. Käivitus- ja võrdlusreeglid on
`docs/kursusetoo/test1_octave.md` failis.

Serveri Octave'i paigalduse ja `octave11` käivitaja juhend ei kuulu
repositoriooriumi: `/home/ubuntu/.local/share/octave-runtime/octave-ubuntu-setup.md`.

Test2 fail: `log/test2_data_b.csv`, SHA-256
`f96dd98818797d8523cf87c4c4d658c989b7b0e91287f91fbfa82214a04bc183`.
Päritolu on `docs/kursusetoo/manifestid/test2_manifest.json` failis ja
ekspordiskript on `docs/kursusetoo/scripts/export_test2.py`. Test2 hinnati
üksnes GNU Octave'i katses; käivitusjuhend ja tulemus on failis
`docs/kursusetoo/test2_octave.md`.

Test2 on 2026-10-20 seisuga fikseeritud vahemiku 30–108 protsessidest, mis
ei esine tegelikus treeningfailis ning mille kõik aktiivsed automaatse mustandi
kandidaadid on lõpetatud ja kooskõlaliste otsustega. Koosseisu kuuluvad
`33, 43, 79–80, 83, 89, 91, 94, 102–105, 107–108`: 337 kandidaati, neist
62 `ACCEPTED`, 151 `MODIFIED` ja 124 `REJECTED`. Protsess 106 jääb välja,
sest kõik selle 30 kandidaati on `PENDING`. Test2 CSV ja manifest kasutavad
samu B-tunnuseid nagu treening- ja Test1-fail; Test2 hinnati ainult GNU
Octave'i eraldi katses.

### Edasine katseplaan, fikseeritud 2026-10-19

1. Test2 koosseis on fikseeritud 14 terviksaatega. Sellel hinnati muutmata
   498 mudeli/tunnusevariandi plaan GNU Octave'is; kõik variandid lõpetasid
   vigadeta. Test2 eel ei muudetud mudeleid, parameetreid ega tunnusekomplekte.
2. Test1 ja Test2 võrdlusest selgub, kas mudelite järjestus ja klassipõhised
   TPR/FPR/FNR-id püsivad. Test1 on pärast variantide võrdlust
   arendus-/valikukomplekt; Test2 tulemust kasutatakse samuti finalistide
   valikuks, mitte lõpliku sõltumatu tõestusena.
3. Pärast finalistide, sealhulgas võimalike mudeliansamblite, fikseerimist
   koostatakse Test3. See sisaldab seni puutumata terviksaateid, tõenäoliselt
   protsessidest 109+. Test3 on lõplik sõltumatu võrdluskomplekt.
4. Seejärel võib koostada uue, umbes 1 500 kandidaadiga treeninghulga ning
   õpetada sellel uued mudelid. Praeguse 1 006-realise ja uue treeninghulga
   võrdlus toimub samal enne õpetamist fikseeritud Test3-l. Nii ei tulene
   erinevus eri raskusega testvalimitest.

Uue treeningu- ja testijaotuse koosseis ning tulemused fikseeritakse eraldi;
senist jaotust ega tulemusi ei kirjutata ümber. Varasemates katsetes kasutatud
andmete ajalugu säilib, et neid ei käsitletaks seni puutumata testina.

### C ja D ümberjaotused, fikseeritud 2026-10-20

C ja D kasutavad ainult praeguste B-treeningu, Test1 ja Test2 failide ühendit:
kokku 1 831 kandidaati 80 terviksaatest. Mõlemas jaotuses kuulub iga saade
tervikuna kas treeningusse või testi. Need on kaks eri, osaliselt kattuvat
reprodutseeritavat 70/30 juhujaotust, mitte Test3 asendajad. Täpne koosseis,
seemned ja kontrollsummad on failides
`docs/kursusetoo/manifestid/c_split_manifest.json` ja
`docs/kursusetoo/manifestid/d_split_manifest.json`; metoodika ning tähistus
B1/B2/C1/D1/B3/C3/D3 on failis `docs/kursusetoo/c_d_octave.md`.

### X kandidaadipõhine kontrolljaotus, fikseeritud 2026-10-20

X kasutab sama 1 831 kandidaadi ja 80 saate ühendit kui C ja D, kuid jagab
read otsuseklassi järgi stratifikatsiooniga juhuslikult treeninguks ja testiks;
ühest saatest võivad kandidaadid olla mõlemas pooles. X1 on võrdlusmaterjal
saatepiirangu mõju hindamiseks, mitte finalistide valikukriteerium. Täpne
kandidaatide loetelu, OS-i CSPRNG kasutuse kirjeldus ja kontrollsummad on
failis `docs/kursusetoo/manifestid/x_split_manifest.json`; käivitusjuhend on
`docs/kursusetoo/x_octave.md`. X3 hinnatakse hiljem samal seni puutumata
Test3-l nagu B3, C3 ja D3.

### Y kandidaadipõhine kontrolljaotus, fikseeritud 2026-10-20

Y on X-ist sõltumatu kandidaatide kaupa stratified 70/30 juhujaotus samast
1 831 kandidaadi ja 80 saate ühendist. Saatepiirangut ei rakendata; ühe saate
kandidaadid võivad olla nii Y-treeningus kui Y1 testis. Y1 kordab X1
kontrolli teise juhujaotusega. Täpne kandidaatide loetelu, X1 testiosaga
kattuvus, CSPRNG kasutus ja kontrollsummad on failis
`docs/kursusetoo/manifestid/y_split_manifest.json`; käivitusjuhend on
`docs/kursusetoo/y_octave.md`.

## Analüüsiks lubatud kandidaatide register

Treeningu kandidaadivahemikud pärinevad 2026-10-14 registrist ja vastavad
fikseeritud treeningfailile. Test1 read kontrolliti 2026-10-19 ning Test2
read 2026-10-20 andmebaasi lugemispäringuga. Loendus hõlmab aktiivse
`AUTOMATIC_DRAFT` versiooni aktiivseid segmente ja kandidaate; `status`
peab võrduma `decision`-iga ning `decision_at` peab olema täidetud.
Tabeli otsuste jaotus on `ACCEPTED / MODIFIED / REJECTED`.

| Protsess | Kandidaadid | Analüüsiks | Õpetamiseks | Otsuseid | Jaotus | Põhjus |
|---:|---|---|---|---:|---|---|
| 14 | `130–170` | Jah | Ei | 41 | 17 / 16 / 8 | Kooskõlalised inimese otsused |
| 15 | `179–221` | Jah | Ei | 43 | 23 / 10 / 10 | Kooskõlalised inimese otsused |
| 16 | `222–249` | Jah | Ei | 28 | 12 / 8 / 8 | Kooskõlalised inimese otsused |
| 18 | `296–334` | Jah | Ei | 39 | 10 / 14 / 15 | Kooskõlalised inimese otsused |
| 19 | `335–373` | Jah | Ei | 39 | 28 / 7 / 4 | Kooskõlalised inimese otsused |
| 20 | `374–395` | Jah | Ei | 22 | 18 / 2 / 2 | Kooskõlalised inimese otsused |
| 21 | `396–406` | Jah | Ei | 11 | 5 / 1 / 5 | Kooskõlalised inimese otsused |
| 22 | `407–444` | Jah | Ei | 38 | 32 / 4 / 2 | Kooskõlalised inimese otsused |
| 23 | `445–462` | Jah | Ei | 18 | 10 / 3 / 5 | Kooskõlalised inimese otsused |
| 24 | `463–504` | Jah | Ei | 42 | 34 / 4 / 4 | Kooskõlalised inimese otsused |
| 25 | `505–528` | Jah | Ei | 24 | 14 / 8 / 2 | Kooskõlalised inimese otsused |
| 26 | `567–611` | Jah | Ei | 45 | 27 / 15 / 3 | Kooskõlalised inimese otsused |
| 27 | `612–649` | Jah | Ei | 38 | 24 / 5 / 9 | Kooskõlalised inimese otsused |
| 28 | `650–671` | Jah | Ei | 22 | 19 / 2 / 1 | Kooskõlalised inimese otsused |
| 29 | `672–709` | Jah | Ei | 38 | 17 / 8 / 13 | Kooskõlalised inimese otsused |
| 31 | `710–735` | Jah | Ei | 26 | 18 / 5 / 3 | Kooskõlalised inimese otsused |
| 32 | `736–792` | Jah | Ei | 57 | 27 / 20 / 10 | Kooskõlalised inimese otsused |
| 33 | `793–844` | Jah | Ei | 52 | 32 / 9 / 11 | Test2; kõik kandidaadid üle vaadatud |
| 34 | `845–848` | Jah | Ei | 4 | 3 / 0 / 1 | Kooskõlalised inimese otsused |
| 35 | `890–980` | Jah | Ei | 91 | 31 / 35 / 25 | Kooskõlalised inimese otsused |
| 36 | `981–1004` | Jah | Ei | 24 | 20 / 2 / 2 | Kooskõlalised inimese otsused |
| 37 | `1005–1009, 1019` | Jah | Ei | 6 | 4 / 1 / 1 | Kooskõlalised inimese otsused |
| 38 | `1032–1047` | Jah | Ei | 16 | 12 / 3 / 1 | Kooskõlalised inimese otsused |
| 39 | `1098–1129` | Jah | Ei | 32 | 26 / 1 / 5 | Kooskõlalised inimese otsused |
| 40 | `1136–1137` | Jah | Ei | 2 | 1 / 1 / 0 | Kooskõlalised inimese otsused |
| 41 | `1169–1175` | Jah | Ei | 7 | 7 / 0 / 0 | Kooskõlalised inimese otsused |
| 42 | `1197–1239` | Jah | Ei | 43 | 29 / 9 / 5 | Kooskõlalised inimese otsused |
| 43 | `1240–1259` | Jah | Ei | 20 | 15 / 0 / 5 | Test2; kõik kandidaadid üle vaadatud |
| 44 | `1260–1261` | Jah | Ei | 2 | 1 / 1 / 0 | Kooskõlalised inimese otsused |
| 47 | `1370–1372, 1389, 1392–1395` | Jah | Ei | 8 | 6 / 1 / 1 | Kooskõlalised inimese otsused |
| 48 | `1396–1398, 1412–1416` | Jah | Ei | 8 | 6 / 1 / 1 | Kooskõlalised inimese otsused |
| 49 | `1417–1427` | Jah | Ei | 11 | 3 / 5 / 3 | Kooskõlalised inimese otsused |
| 50 | `1456–1491` | Jah | Ei | 36 | 18 / 10 / 8 | Kooskõlalised inimese otsused |
| 53 | `1571–1592` | Jah | Ei | 22 | 2 / 11 / 9 | Kooskõlalised inimese otsused |
| 54 | `1593–1619` | Jah | Ei | 27 | 1 / 16 / 10 | Kooskõlalised inimese otsused |
| 55 | `1620–1624` | Jah | Ei | 5 | 0 / 3 / 2 | Kooskõlalised inimese otsused |
| 57 | `1625–1635` | Jah | Ei | 11 | 0 / 7 / 4 | Kooskõlalised inimese otsused |
| 58 | `1636–1654` | Jah | Ei | 19 | 4 / 13 / 2 | Kooskõlalised inimese otsused |
| 59 | `1655–1700` | Jah | Ei | 46 | 3 / 21 / 22 | Kooskõlalised inimese otsused |
| 61 | `1732–1744` | Jah | Ei | 13 | 0 / 8 / 5 | Kooskõlalised inimese otsused |
| 62 | `1745–1753` | Jah | Ei | 9 | 1 / 7 / 1 | Kooskõlalised inimese otsused |
| 63 | `1754–1779` | Jah | Ei | 26 | 1 / 16 / 9 | Kooskõlalised inimese otsused |
| 64 | `1780–1784` | Jah | Ei | 5 | 0 / 3 / 2 | Kooskõlalised inimese otsused |
| 65 | `1785–1816` | Jah | Ei | 32 | 0 / 26 / 6 | Kooskõlalised inimese otsused |
| 66 | `1817–1823` | Jah | Ei | 7 | 1 / 3 / 3 | Kooskõlalised inimese otsused |
| 67 | `1824–1837` | Jah | Ei | 14 | 0 / 7 / 7 | Kooskõlalised inimese otsused |
| 69 | `1855–1863` | Jah | Ei | 9 | 1 / 5 / 3 | Kooskõlalised inimese otsused |
| 71 | `1927–1960` | Jah | Ei | 34 | 1 / 25 / 8 | Kooskõlalised inimese otsused |
| 72 | `1984–1999` | Jah | Ei | 16 | 0 / 9 / 7 | Kooskõlalised inimese otsused |
| 75 | `2048–2062` | Jah | Ei | 15 | 4 / 6 / 5 | Kooskõlalised inimese otsused |
| 76 | `2063–2081` | Jah | Ei | 19 | 0 / 10 / 9 | Kooskõlalised inimese otsused |
| 77 | `2082–2106` | Jah | Ei | 25 | 0 / 19 / 6 | Kooskõlalised inimese otsused |
| 78 | `2107–2125` | Jah | Ei | 19 | 1 / 14 / 4 | Kooskõlalised inimese otsused |
| 79 | `2126–2151` | Jah | Ei | 26 | 2 / 13 / 11 | Test2; kõik kandidaadid üle vaadatud |
| 80 | `2152–2228` | Jah | Ei | 77 | 2 / 49 / 26 | Test2; kõik kandidaadid üle vaadatud |
| 81 | `2229–2243` | Jah | Ei | 15 | 1 / 10 / 4 | Kooskõlalised inimese otsused |
| 82 | `2244–2254` | Jah | Ei | 11 | 0 / 7 / 4 | Kooskõlalised inimese otsused |
| 83 | `2255–2298` | Jah | Ei | 44 | 2 / 26 / 16 | Test2; kõik kandidaadid üle vaadatud |
| 84 | `2299–2309` | Jah | Ei | 11 | 0 / 9 / 2 | Kooskõlalised inimese otsused |
| 85 | `2310–2339` | Jah | Ei | 30 | 1 / 13 / 16 | Kooskõlalised inimese otsused |
| 86 | `2340–2346` | Jah | Ei | 7 | 1 / 2 / 4 | Kooskõlalised inimese otsused |
| 88 | `2410–2417` | Jah | Ei | 8 | 3 / 4 / 1 | Kooskõlalised inimese otsused |
| 89 | `2418–2442` | Jah | Ei | 25 | 2 / 11 / 12 | Test2; kõik kandidaadid üle vaadatud |
| 90 | `2443–2471` | Jah | Ei | 29 | 2 / 13 / 14 | Kooskõlalised inimese otsused |
| 91 | `2472–2482` | Jah | Ei | 11 | 2 / 7 / 2 | Test2; kõik kandidaadid üle vaadatud |
| 93 | `2535–2552` | Jah | Ei | 18 | 0 / 8 / 10 | Kooskõlalised inimese otsused |
| 94 | `2553–2562` | Jah | Ei | 10 | 0 / 3 / 7 | Test2; kõik kandidaadid üle vaadatud |
| 95 | `2563–2585` | Jah | Ei | 23 | 0 / 13 / 10 | Kooskõlalised inimese otsused |
| 96 | `2586–2588` | Jah | Ei | 3 | 0 / 2 / 1 | Kooskõlalised inimese otsused |
| 97 | `2589–2610` | Jah | Ei | 22 | 2 / 5 / 15 | Kooskõlalised inimese otsused |
| 98 | `2611–2625` | Jah | Ei | 15 | 2 / 9 / 4 | Kooskõlalised inimese otsused |
| 99 | `2626–2647` | Jah | Ei | 22 | 3 / 12 / 7 | Kooskõlalised inimese otsused |
| 100 | `2648–2665` | Jah | Ei | 18 | 3 / 9 / 6 | Kooskõlalised inimese otsused |
| 101 | `2666–2693` | Jah | Ei | 28 | 1 / 14 / 13 | Kooskõlalised inimese otsused |
| 102 | `2694–2715` | Jah | Ei | 22 | 0 / 12 / 10 | Test2; kõik kandidaadid üle vaadatud |
| 103 | `2716–2720` | Jah | Ei | 5 | 0 / 2 / 3 | Test2; kõik kandidaadid üle vaadatud |
| 104 | `2721–2727` | Jah | Ei | 7 | 0 / 3 / 4 | Test2; kõik kandidaadid üle vaadatud |
| 105 | `2728–2739` | Jah | Ei | 12 | 2 / 3 / 7 | Test2; kõik kandidaadid üle vaadatud |
| 107 | `2770–2784` | Jah | Ei | 15 | 3 / 6 / 6 | Test2; kõik kandidaadid üle vaadatud |
| 108 | `2785–2795` | Jah | Ei | 11 | 0 / 7 / 4 | Test2; kõik kandidaadid üle vaadatud |

## Kasutuspiirangud

- Kursusetöö mudelkatse kasutab ainult tabeli `Analüüsiks: Jah` ridu.
- Sama saate segmendid peavad jääma ühte andmehulka: kas treeningusse,
  valideerimisse või testi.
- Uued lõpetatud kandidaadid lisatakse registrisse alles pärast nende
  `status`, `decision` ja `decision_at` kooskõla kontrolli.
