# Õppetunnid ja otsused

See fail on Gitiga versioonitav teadmiste register: kinnitatud järeldused,
otsused ja kõrvale jäetud lahendused. Üksikasjalik käituslogi on ignoreeritud
failis [`log/build_and_run_log.md`](../log/build_and_run_log.md).

## Katsete ülevaade

| Etapp | Tulemus | Otsus |
|---|---|---|
| MVP 1.1: ERR URL → VTT + diarization + transkript | Toimib | Jääb tuumaks |
| MVP 1.1: cue poolitamine Pyannote'i piiril | Tekst dubleerus | Cue säilib tervikuna |
| MVP 1.2: Whisperi uus ASR kahtlastel kohtadel | Tehniliselt toimib, sisuliselt ebapiisav | Ei arendata speaker-kontrollina edasi |
| MVP 1.3: olemasoleva VTT forced alignment | 13/18 lugemiskontekstiga märgitud cue-järjestust sobis, kuid ei parandanud Pyannote'i vigu | Jääb diagnostikaks, mitte automaatseks paranduseks |
| MVP 1.3: mudelivaba lauselõpu-võrdlustest | 12/18 kandidaati, kõik 12 kattusid märgitud tekstipiiriga; 0 valepositiivi 39 unikaalses kontrollcue's | Odav reegel katab ainult osa juhtumeid; automaatset poolitust ei lülitata veel sisse |

## MVP 1.1 — CLI tuum

### Kinnitatud otsused

1. ERR-i automaatsubtiitrid on põhiline tekstiallikas. Audio-põhine töötlus
   lisab kõnelejate anonüümsed ajavahemikud, mitte uut põhiteksti.
2. ERR-i artikli URL ei ole tingimata meedia URL. Resolver leiab artikli
   yt-dlp metadata seest seotud VOD-meedia URL-i enne audio hankimist.
3. Runtime-andmed asuvad alati väljaspool Git checkout'i kataloogis
   `/srv/err2text/`; checkout ei sisalda väljundeid, mudeleid, cache'i,
   audiofaile ega `.env` faili.
4. Konteinerid kirjutavad hosti kasutaja UID:GID õigustes. Nii ei teki
   root-omanikuga väljundeid.
5. Pyannote'i `SPEAKER_nn` ei ole inimese nimi. Isikunimed lisatakse alles
   inimese kinnitatud speaker-kaardi kaudu.

### Parandatud VTT dubleerimise viga

Esialgne liitmine poolitas cue Pyannote'i speaker-piiril. Mõlemad poolikud
pärisid sama cue teksti ning Markdownis kordusid laused. Nüüd säilib cue
tervikliku tekstina ning cue sees olev speaker-piir on ebakindluse signaal.

Põhitranskriptsiooni Markdown vorm on
`**kõneleja** (*ajavahemik*): tekst`. Masinloetav allikas on
`transcript.json` ja diarization'i toorandmed on `speakers.json`.

Kontrollitud Reinsalu põhiartefaktid:

```text
/srv/err2text/outputs/reinsalu-isamaa/
├── transcript.json
├── speakers.json
├── resolver.json
└── reinsalu-isamaa-eesm-rk-on-p-rata-2027-aasta-kevadel-uus-lehek-lg-transcript.md
```

## MVP 1.2 — Whisperi kvaliteedikontroll

Katse hüpoteeside lähtefail on
[`examples/reinsalu-isamaa-claude-candidates.json`](examples/reinsalu-isamaa-claude-candidates.json).
Tulemused asuvad:

```text
/srv/err2text/outputs/reinsalu-isamaa/review/whisper/
├── whisper_review.json
└── whisper_review.md
```

Kontrolljooks töötles 50 kandidaati, millest 19 tulid käsitsi koostatud
hüpoteeside loendist. Töö kestus oli 1391,349 sekundit ehk umbes 23 minutit.
Kasutati `faster-whisper==1.2.1`, `medium` mudelit, CPU `int8` režiimi ja
kolme CPU-lõime.

### Tehnilised õppetunnid

1. Eraldi review-worker, välised runtime-kataloogid ja Hugging Face'i jagatud
   cache töötavad.
2. RAM ei olnud piirang: kasutus oli ligikaudu 1,3–1,5 GiB ja swap'i ei
   kasutatud. CPU oli piirang: `medium` kasutas ligikaudu 2,5–3 CPU-tuuma.
3. `faster-whisper==1.2.1` ei ühildu PyAV 19-ga, sest PyAV 19 eemaldas
   `metadata_errors` argumendi. Worker lukustab `PYAV_VERSION=18.0.0`.

### Sisuline järeldus

Whisperi uuesti loodud tekst ei ole ERR-i VTT parandaja. Kontrollitud näites
`00:07:54.040–00:07:58.040` oli tulemus:

```text
ERR VTT:  vaates. Miks, kui tagurpidi õnnestus see teha,
Whisper:  lühigises vaatas. Miks? Kui tagur pidi õnestusse teha,
```

Whisper ei tee speaker identification'it. Review JSON-i
`diarization_speaker_id` väärtused tulevad Whisperi sõnaaja kattumisest
olemasoleva Pyannote'i tulemusega, mitte Whisperi sõltumatust hinnangust.
Meetod ei paranda Pyannote'i valet või nihkes speaker-piiri.

`whisper_review.md` ei olnud piisav kõnelejaotsuse tegemiseks. Sõnatasandi
speaker-ID-d olid JSON-is olemas, kuid mitte Markdownis samas loetavas vaates.
Tulevased inimese review-artefaktid peavad näitama tekstilist piiri, ajapiiri
ja olemasolevat speaker-ID-d koos.

Otsus: Whisperi taastranskribeerimise haru jääb katse tõendina alles, kuid
seda ei kasutata ERR-i VTT muutmiseks ega kõneleja automaatseks
ümberomistamiseks.

## MVP 1.3 — olemasoleva VTT forced alignment

MVP 1.3 lähteülesanne on failis [`task_to_solve.md`](task_to_solve.md).
Siht on joondada ERR-i olemasolevad sõnad audioga ja seostada need
sõnahaaval Pyannote'i speaker-vahemikega; uut teksti ei looda.

Reinsalu esimese spike'i lugemiskontekstiga märgitud A-tüüpi segacue'd:

```text
00:02:20.620–00:02:22.400  Urmas Reinsalu | saatejuht
00:04:21.400–00:04:23.660  Urmas Reinsalu | saatejuht
00:07:26.300–00:07:28.040  Urmas Reinsalu | saatejuht
00:07:54.040–00:07:58.040  saatejuht | Urmas Reinsalu
00:09:06.120–00:09:08.400  saatejuht | Urmas Reinsalu
00:10:07.980–00:10:11.260  Urmas Reinsalu | saatejuht
```

Need on lugemiskonteksti põhised kontrollnäited, mitte audioga sekunditäpselt
kinnitatud tõde. Spike'i väljund on eraldi:

```text
<output-dir>/review/alignment/
├── alignment_review.json
└── alignment_review.md
```

Kui joondaja ei leia eesti keeles usaldusväärseid sõnaaegu või Pyannote'i piir
on ise vale, jääb tulemus `human_review_required`. B-, C- ja D-tüüpi vigu
MVP 1.3 ei lahenda.

### Esimene käivitatud katse

Katse käivitati kuue ülaltoodud cue'ga TalTechi mudelil
`TalTechNLP/xls-r-300m-et` revisjoniga
`a1a327b54c3ecbb4750ce8c75aa7ee996030753f`. Töö kestus oli 86,157 sekundit
ning tekitas järgmised välised artefaktid:

```text
/srv/err2text/outputs/reinsalu-isamaa/review/alignment/
├── alignment_review.json
└── alignment_review.md
```

Esimese jooksu sõnaajad näisid mõistlikud, kuid selle CTC-kindlused olid
peaaegu null. Põhjus oli konkreetselt vale normaliseerimine: joondaja muutis
teksti suurtähtedeks, kuid TalTechi vocab'i põhitähed on väiketähed. See
diagnostikajooks on säilitatud kataloogis
`/srv/err2text/outputs/reinsalu-isamaa/review/alignment-attempt-1/`.

Pärast väiketähenormaliseerimise parandust kestis sama kuue cue'ga jooks
45,679 sekundit. `alignment_review.md` näitab nüüd enamiku sõnade lokaalset
CTC-kindlust vahemikus 0,94–1,00 ning tulemus on sisuliselt tõlgendatav:

1. `02:20`, `07:26`, `09:06` ja `10:07` — Pyannote'i sõnahaaval omistus
   järgib inimese loetud speaker-järjestust. See on tehniline tõend, et VTT
   sõnaaegade puudumine on vähemalt osa A-tüüpi vigade praktiliselt lahendatav
   osa.
2. `04:21` — joondatud sõnad „et sellisel kujul ei realiseeruks” jäid
   Pyannote'i järgi saatejuhile, mitte Reinsalule. See on D-tüübi
   Pyannote'i-piiriviga, mitte VTT ajamärgi hilinemine; forced alignment seda
   üksi ei paranda.
3. `07:54` — joondaja asetab „Miks” veel saatejuhile ning vahetuse esimese
   sõna „kui” juurde. Inimese tekstimärgendus pani piiri juba pärast
   „vaates.” Seda ühesõnalist erinevust ei muudeta automaatselt.

Kehtiv tulemus on
`/srv/err2text/outputs/reinsalu-isamaa/review/alignment/`. Teine säilitatud
diagnostikajooks (`alignment-attempt-2`) kasutas õiget märgistikku, kuid vana
toortõenäosuse kuvamist; kehtiv jooks kasutab lokaalset suhtelist CTC-kindlust.

Joondus kasutab kolmesekundilist konteksti mõlemal pool cue'd ja naabercue’de
VTT teksti.

### Laiendatud hindamine ja sõltumatu baseline

Hindamiskomplektis on 18 inimese lugemiskontekstiga märgitud `mixed_cue`
juhtu ja 20 `clean_transition` kontrollüleminekut. Need on kõik jätkuvalt
lugemiskonteksti märgendused, mitte audioga kinnitatud vead või õiged piirid.
Kolm terviklikult vale speaker-sildiga cue'd jäävad sellest mõõtmisest välja,
sest forced alignment ja lauselõpu-reegel ei saa tervikliku cue speakerit
sõltumatult kindlaks teha.

Forced-alignmenti täisjooks kestis 338,589 sekundit ning taastatud
Pyannote'i sõnajärjestus sobis 13 juhul 18-st. Varem review-failis olnud
`punctuation_baseline` ei olnud siiski sõltumatu võrdlus: see kasutas
alignmenti sõnaaegadest tuletatud Pyannote'i sõnasilte ning `±1,5` sekundi
akent. Seega ei saa selle põhjal väita, et CTC joondus ületas või ei ületanud
lihtsat reeglit.

Selle puuduse kõrvaldamiseks lisati eraldi `sentence-boundary-review`. See ei
laadi audiofaili ega CTC-mudelit ja ei kasuta ennustuse tegemisel inimese
speaker-järjestust või tekstilist poolitusmärget. Sisend on ainult
`transcript.json` cue-tekst ja aeg ning `speakers.json` Pyannote'i spanid.
Reegel:

1. arvestab täpselt üht cue-sisest speaker-muutust, mis jääb vähemalt 0,5 s
   cue kummastki servast eemale;
2. leiab cue tekstist lauselõpu ning hindab selle aja lineaarselt sõnade
   järjekorra ja cue kestuse järgi;
3. pakub poolitust vaid siis, kui hinnanguline lauselõpp asub Pyannote'i
   piirist kuni 2,0 s kaugusel;
4. võrdleb inimese `separator_after_text` märgendusega alles pärast pakkumise
   moodustamist.

Reinsalu hindamise tulemus on välises artefaktis:

```text
/srv/err2text/outputs/reinsalu-isamaa/review/sentence-boundary/
└── reinsalu-isamaa-alignment-evaluation-1/
    ├── sentence_boundary_review.json
    └── sentence_boundary_review.md
```

Tulemus oli 12 kandidaati 18 segacue'st ja kõik 12 kandidaati kattusid inimese
märgitud tekstipiiriga. Kuuel juhul reegel ettepanekut ei teinud, sest cue's
polnud täpselt üht piisavalt sisemist Pyannote'i speaker-piiri. 20 puhta
kontrollülemineku 39 unikaalses cue's ei olnud ühtki valepositiivset
poolitusettepanekut. See on hea katvus-kvaliteedi signaal, kuid ei ole veel
alus automaatseks parandamiseks: lugemiskonteksti märgendus vajab olulistel
juhtudel audioga kinnitamist ning kuus katmata ja terviklikult vale sildiga
juhtu jäävad lahendamata.

### Claude'i retsensioonist rakendatud õppetunnid

Claude'i retsensioon rõhutas õigesti nelja kontrollpunkti, mis lisati
lähteülesandesse ja katsesse:

1. Whisperi uus ASR ei ole sobiv vahend olemasoleva ERR-i VTT kõneleja
   omistuse parandamiseks, sest ta loob nõrgema uue teksti ega tuvasta
   kõnelejat.
2. Forced alignment annab sõnaajastuse, kuid pärib speaker-omistuse ikkagi
   Pyannote'ilt; seetõttu ei lahenda ta Pyannote'i vale või nihkes piiri ega
   terviklikult valet cue-silti.
3. Võrdlus peab olema tegelikult mudelist sõltumatu, kasutama enne hindamist
   vaid süsteemi lähteandmeid ning määratlema cue-serva üleminekute ja
   korduvate kontrollcue'de arvestuse.
4. Inimese kuulamine on vajalik vaid lõpliku tõe loomiseks; käsitsi failide
   põhjal tehtav review ei ole piisavalt mugav. Sellepärast viiakse
   kasutaja–süsteemi poolitusotsus edasi MVP2.2 veebiliidesesse.

Otsus: MVP1.3 forced alignment jääb säilitatavaks diagnostikakatseks ja
lauselõpu-reegel säilib mõõdetud kandidaadivalikuna. Kumbagi ei rakendata
praegu automaatselt põhi-`transcript.json` või Markdown-transkriptsiooni
muutmiseks. Järgmine arendus on MVP2 teenus ja veebiliides; MVP2.2-s kogutakse
auditeeritavad inimese otsused, mille põhjal saab meetodeid ausalt võrrelda.

## Muutmise põhimõte

Iga uus järeldus lisatakse siia koos viitega kontrollitud lähte- või
väljundfailile. Funktsionaalseid nõudeid muudetakse enne koodi failis
[`task_to_solve.md`](task_to_solve.md). Käitusandmeid, audiofaile, mudeleid
ja saladusi sellesse faili ei kirjutata.
