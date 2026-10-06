# Lähteülesanne: ERR/Jupiteri saadete transkriptsioon ja kõnelejate eristamine

## Eesmärk

Luua Ubuntu serveris töötav lahendus, mis võtab sisendiks ERR-i või Jupiteri videoartikli/saate URL-i ning toodab struktureeritud transkriptsiooni. Igal tekstilõigul peavad olema ajavahemik ja kõneleja tunnus.

Lahenduse esmavaliku väljund ei ole sisuanalüüs, vaid usaldusväärne fail „kes ütles mida“. Hiljem kasutatakse neid transkriptsioone AI-agentide sisendina, näiteks saadete võrdlemiseks, faktiväidete eraldamiseks ja argumentatsiooni analüüsimiseks.

Kõik projekti loodavad tekstifailid, lähtekood ning väljundfailid peavad kasutama **UTF-8** märgistikku. Eestikeelne tekst peab säilima korrektselt; ERR-i VTT võimalik mojibake/valedekodeering tuleb töötluses parandada.

## Esimene MVP: CLI-prototüüp

MVP on väike konteineris töötav CLI-tööriist, ilma veebiliidese, autentimise, andmebaasi, RAG-i või AI-sisuanalüüsita. MVP 1.2 lisab sellele piiratud kvaliteedikontrolli tööriista; see ei ole veel teenusekiht ega RAG.

Esimestes versioonides keskendub tööriist ainult ERR-i ökosüsteemile: vähemalt `err.ee`, `jupiter.err.ee` ja `arhiiv.err.ee` URL-idele ning nende seotud ERR-i meediadomeenidele. See ei ole esialgu YouTube’i ega suvalise veebilehe videote üldine transkribeerija.

Näidiskäsk:

```bash
python process.py "<ERR-i URL>"
```

### Sisend ja töövoog

1. Kasutaja annab ERR-i/Jupiteri saate või videoartikli URL-i.
2. Tööriist tuvastab URL-i tüübi ning leiab automaatselt video, audio ja automaatsubtiitrite allikad. Toetatud peavad olema vähemalt ERR-i artikli-URL ja Jupiteri saate/video URL; otsene VOD manifesti või VTT URL on lubatud ainult tehnilise veaotsingu sisendina, mitte kasutajale nõutava vormina. Kasutada võib `yt-dlp`-d koos UglyERR pluginaga.
3. Laetakse ERR-i VTT toorbaidid ning säilitatakse need muutmata kujul `original.vtt`-na.
4. Toorbaidid dekodeeritakse eksplitsiitselt UTF-8-na ja kirjutatakse eraldi failina `normalized.vtt`. Mojibake-parandus on lubatud ainult tuvastatud valedekodeeringu korral; see ei tohi muuta juba korrektset teksti.
5. Hangitakse audio ning teisendatakse `ffmpeg`-iga diarization’i jaoks sobivaks mono, 16 kHz WAV-failiks.
6. Käivitatakse CPU-l speaker diarization, esialgu `pyannote.audio` abil.
7. Diarization’i ajavahemikud ühendatakse VTT subtiitrite ajavahemikega, eelistatult ajalise kattuvuse põhjal.
8. Mõõdetakse diarization’i ja kogu töötluse kestus.

### CLI leping

Põhikäsk on:

```bash
python process.py "<ERR-i URL>" --output-dir "<kataloog>"
```

MVP1 CLI peab vähemalt toetama järgmisi valikuid:

- `--video-index N` — artiklilt leitud mitmest meediaelemendist ühe valimine;
- `--output-dir KATALOOG` — tööpõhise väljundkataloogi määramine;
- `--speakers-map FAIL` või eraldi `apply-names` alamkäsk — käsitsi nimede kaardi rakendamine olemasolevatele väljunditele;
- `--time-offset SEKUNDID` — dokumenteeritud ajakorrektsiooni käsitsi määramine;
- `--min-speakers N` ja `--max-speakers N` — diarization’i kõnelejate arvu vihjed;
- `--no-cache` — cache’i teadlik eiramine uue diarization-jooksu jaoks;
- hilisemaks veaotsinguks reserveeritud `--keep-audio` — ajutise WAV-i säilitamine;
- `whisper-review --output-dir KATALOOG` — juba lõpetatud transkriptsioonijooksu kahtlaste lõikude kontrollimine Whisperiga; käsk ei tohi muuta põhitulemust automaatselt;
- `whisper-review --candidate-file FAIL` — valikuline käsitsi koostatud kandidaatide JSON, näiteks varem tehtud analüüsi osutatud ajavahemike lisamiseks automaatsete kandidaatide kõrvale.
- `alignment-review --output-dir KATALOOG --case-file FAIL` — inimese märgitud VTT segalõikude forced-alignmenti kontroll; käsk ei tohi muuta põhiartefakte automaatselt.
- `sentence-boundary-review --output-dir KATALOOG --case-file FAIL` — mudelivaba võrdlustest: olemasoleva VTT kirjavahemärkide ja `speakers.json` Pyannote'i piiride järgi pakutud cue-sisene poolitus; käsk ei tohi muuta põhiartefakte automaatselt.

CLI väljumiskood ja masina-loetav veateave peavad eristama vähemalt vigu `UNSUPPORTED_URL`, `ARTICLE_WITHOUT_MEDIA`, `MEDIA_NOT_FOUND`, `DRM_PROTECTED`, `DOWNLOAD_FAILED`, `DIARIZATION_FAILED`, `MERGE_FAILED` ja `INVALID_SPEAKERS_MAP`. Edukas töö kirjutab `run_metadata.json` faili ning prindib väljundkataloogi asukoha.

### Väljundid

Iga töötluse kohta peab tekkima vähemalt:

- `original.vtt` — ERR-ist saadud muutmata toorbaidid; see on auditeerimise erand üldisest UTF-8 väljundinõudest;
- `normalized.vtt` — töötluses kasutatav kontrollitult UTF-8 dekodeeritud VTT;
- `resolver.json` — algne URL, URL-i tüüp, leitud `media_items`, valitud meedia, kasutatud VTT/audio URL-id ning resolveri versioon;
- `speakers.json` — diarization’i kõnelejate ajavahemikud;
- `speaker_review.json` — anonüümsete kõnelejate käsitsi nimede ülevaatuse materjal;
- `transcript.json` — struktureeritud, kõneleja sildiga transkriptsioon;
- `<meedia-slug>-transcript.md` — inimesele loetav UTF-8 Markdown-transkriptsioon; see on näidisnimetus, mitte fikseeritud failinimi.
- `run_metadata.json` — töötluse mudeli-, tööriista- ja liitmisversioonid, parameetrid, kontrollsummad, ajakorrektsioon, kestused, ressursimõõdikud ja töö tulemus.

Whisperi kvaliteedikontroll on sama transkriptsioonijooksu lisamaterjal, mitte teine lõpptranskriptsioon. Selle püsivad tulemused paiknevad:

```text
<output-dir>/review/whisper/
├── whisper_review.json
└── whisper_review.md
```

Ajutine allalaaditud audio ja sellest lõigatud WAV-klipid paiknevad ainult `<runtime-root>/work/whisper-review/` all ning kustutatakse pärast õnnestunud või nurjunud kontrolljooksu. Review-fail viitab algse ERR-i URL-ile ja ajavahemikele; WAV-klippe ei säilitata vaikimisi. Inimese koostatud kandidaatide JSON-failid paiknevad `<runtime-root>/review-inputs/` all, et neid ei kirjutataks üle review-väljundi loomisel.

`transcript.json` peab toetama suvalist arvu kõnelejaid, näiteks:

```json
{
  "schema_version": "1.0",
  "source_url": "https://www.err.ee/...",
  "media_id": "...",
  "language": "et",
  "pipeline": {
    "diarization_model": "...",
    "model_revision": "...",
    "pipeline_version": "..."
  },
  "title": "...",
  "segments": [
    {
      "id": "seg_0001",
      "start": 49.2,
      "end": 55.0,
      "speaker_id": "SPEAKER_00",
      "speaker_name": "UNKNOWN",
      "speaker_name_source": "unknown",
      "attribution_status": "assigned",
      "vtt_cue_ids": ["cue_12"],
      "overlap_ratio": 0.96,
      "attribution_confidence": "high",
      "split_estimated": false,
      "text": "..."
    }
  ],
  "turns": []
}
```

`segments` säilitab VTT-lõigu taseme ja `turns` ühendab järjestikused sama kõneleja lõigud AI-agentidele sobivamaks kõnevooruks. Speaker diarization määrab anonüümsed sildid (`SPEAKER_00`, `SPEAKER_01`, jne), mitte isiku nime. Esimeses katses peab olema võimalik sildid käsitsi nimedega siduda.

Kõneleja nimi ja kõneleja omistuse kindlus on kaks eri asja:

- `speaker_id: "SPEAKER_00"`, `speaker_name: "UNKNOWN"`, `attribution_status: "assigned"` tähendab, et lõik on omistatud kindlale anonüümsele kõnelejale, kuid inimene pole veel nime saanud;
- `speaker_id: null`, `speaker_name: null`, `attribution_status: "unassigned"` tähendab, et lõiku ei saa piisava kindlusega ühelegi diarization’i kõnelejale omistada.

Nimede sidumine toimub eraldi `speakers_map.json` faili kaudu ning peab olema uuesti rakendatav ilma audio hankimist või diarization’it kordamata. Eraldi `merge`/`apply-names` käsk kasutab salvestatud `normalized.vtt` ja `speakers.json` faile uue JSON- ja Markdown-väljundi loomiseks.

### Kõnelejate nimede käsitsi ülevaatuse töövoog

Pärast diarization’it loob süsteem `speaker_review.json` või samaväärse Markdown-ülevaate. Iga anonüümse `SPEAKER_nn` kohta sisaldab see vähemalt kogukõneaega, 3–5 pikimat võimalikku mittekattuvat ja kõrge omistuskindlusega ajavahemikku, nendes lõikudes olevat VTT teksti ning viidet algsele ERR-i meediale ja ajamärgile. Helifaili säilitamine pole selleks vajalik: kasutaja saab ERR-i originaalvideost kuulata ülevaates toodud lühikesi ajavahemikke.

Artikli või saate metadata võib anda kandidaatnimed (näiteks saatejuht ja külaline), kuid süsteem näitab neid vaid abimaterjalina ega seo neid automaatselt häälega. Kasutaja kontrollib näiteid ning täidab näiteks järgmise kaardi:

```json
{
  "SPEAKER_00": {
    "name": "Mirko Ojakivi",
    "source": "manual",
    "confidence": "confirmed"
  },
  "SPEAKER_01": {
    "name": "Urmas Reinsalu",
    "source": "manual",
    "confidence": "confirmed"
  }
}
```

`speakers_map.json` peab sisaldama `diarization_run_id` või `speakers.json` kontrollsummat. `apply-names` keeldub nimede lisamisest, kui kaart ei vasta kasutatavale diarization-jooksule. Kui kasutaja ei ole kindel, jääb `speaker_name` väärtuseks `UNKNOWN`. Kõneleja ID on püsiv ainult selle konkreetse diarization-jooksu sees; seda ei käsitleta veel eri saadete vahelise püsiva hääletuvastusena.

### Esimene testjuhtum ja edukriteerium

Esimene test on ERR-i artikkel/saade:

<https://www.err.ee/1610154019/reinsalu-isamaa-eesmark-on-poorata-2027-aasta-kevadel-uus-lehekulg>

Saates on saatejuht Mirko Ojakivi ja külaline Urmas Reinsalu. Teadaolev VOD-identifikaator on `b4eb8107755029f5c6e92f8cfcf14911`; lõplik tööriist ei tohi siiski eeldada, et kasutaja seda käsitsi sisestab.

Edu ei tähenda ilusat rakendust. Edu tähendab, et 4 CPU-ga GPU-ta serveris tekib selle saate kohta kontrollitava kvaliteediga „kes ütles mida” fail ning on mõõdetud selle saavutamiseks kulunud aeg. Mõõdetavad läviväärtused ning kontrolllõikude märgendus tuleb lukustada enne võrdlustesti käivitamist, mitte tulemuse nägemise järel.

Serveri teadaolevad lähteandmed:

- 4 ARM Neoverse-N1 CPU tuuma;
- 23 GiB RAM;
- GPU puudub;
- rakendus peab töötama konteineris.

Kuna ERR annab juba automaatse VTT, ei transkribeerita esimeses MVP-s kogu saadet Whisperiga uuesti. Whisper/WhisperX võivad jääda hilisemaks kontroll- või varuvariandiks.

## Etapiline teekaart

### MVP — CLI-tehnilise tuuma tõestus

MVP on eespool kirjeldatud konteineris töötav CLI-prototüüp. Selle ainus eesmärk on tõestada testsaatega, et ERR URL → ERR VTT + audio → diarization → speaker-attributed transcript on sellel 4 CPU-ga serveril tehniliselt ja kvaliteedi mõttes kasutatav.

MVP ei sisalda veebivormi, avalikku API-t, autentimist, Oracle’i skeemi, kasutajalogimist, RAG-i ega AI-sisuanalüüsi. MVP lõpus on otsus: kas diarization’i kvaliteet ja töötlusaeg õigustavad teenusekihi ehitamist.

MVP sisaldab siiski failipõhist kahetasemelist cache’i, sest sama saate korduv diarization katsete ajal on kulukas. Resolveri/allalaadimise cache’i võti sisaldab vähemalt meedia/VOD-ID-d ning manifesti või muu allika versiooni/ETag-i. Diarization’i cache’i võti seob leitud meedia versiooni, pipeline’i versiooni, mudeli revisjoni ja parameetrid olemasoleva `speakers.json` väljundiga. Audio kontrollsumma salvestatakse pärast allalaadimist tervikluse kontrolliks, kuid seda ei kasutata esmase cache’i kontrollimiseks, sest audio allalaadimine nulliks cache’i ajasäästu. Liitmine ja nimede lisamine on odavad ning neid cache’itakse eraldi ainult vajaduse korral.

### MVP 1.2 — valikuline Whisperi kvaliteedikontroll

MVP 1.2 eesmärk on hinnata, kas kahtlaste VTT–diarization’i omistuste juures aitab Whisper vähendada inimese kuulamistööd. Whisper ei ole speaker identification mudel ega tohi isiku nime või anonüümset `SPEAKER_nn` silti iseseisvalt ümber määrata. Ta annab teise tekstituvastuse ja sõnatasandi ajad, mida võrreldakse olemasoleva VTT teksti ning Pyannote’i ajavahemikega.

MVP 1.2 sisend on lõpetatud MVP 1 transkriptsioonijooksu `transcript.json`, `speakers.json` ja `resolver.json`. Süsteem valib kontrollikandidaadid järgmiste läbipaistvate reeglite järgi:

- `attribution_confidence` on `medium`, `low` või `unknown`, või `attribution_status` on `unassigned`;
- sama VTT lõigu sees paikneb vähemalt kahe eri anonüümse kõneleja Pyannote’i ajavahemik;
- lühike lõik asub kahe teise kõneleja lõigu vahel (`short_speaker_flip`);
- kasutaja lisab ajavahemiku käsitsi kandidaatide JSON-failiga, näiteks varem tehtud analüüsi tähelepaneku alusel.

Käsitsi kandidaatide faili minimaalne vorm on:

```json
{
  "candidates": [
    {"segment_id": "seg_0038", "reason": "claude_review"},
    {"start": 61.2, "end": 66.8, "reason": "claude_review"}
  ]
}
```

Iga kandidaat töödeldakse koos `.env`-is määratud kontekstiajaga enne ja pärast kahtlast ajavahemikku. `whisper_review.json` peab sisaldama vähemalt algset VTT teksti, seniseid speaker-ID-sid, valikupõhjuseid, klipi ajavahemikku, Whisperi samale kandidaadivahemikule jäävat teksti, eraldi kontekstiteksti, sõnaajastusi, iga sõna kattuvat Pyannote’i speaker-ID-d ning VTT/Whisperi tekstisarnasust. `whisper_review.md` on inimesele loetav kontrollvaade. Mõlema tulemus on alati `human_review_required`; automaatset kõneleja ümberomistamist ega põhi-`transcript.json` muutmist MVP 1.2 ei tehta.

Whisperi tööline on eraldi Compose’i teenus ja Docker image (`whisper-review`), kuid kasutab sama Python-projekti ja sama välist runtime-kataloogi kui põhitööriist. Review-worker sisaldab `ffmpeg`-it ja sama pin’itud `yt-dlp` versiooni, sest ta hangib resolveri salvestatud kanonilise meedia-URL-i põhjal ainult ajutise audio. Ta ei vaja UglyERR pluginat ega Pyannote’i sõltuvusi: ERR-i artikli resolver on põhitöötluses juba varem teinud URL → kanoniline meedia-URL teisenduse. Põhi-image ei tohi saada Whisperi sõltuvusi. See valmistab ette hilisema arhitektuuri, kus API saadab eraldi töölistesse diarization’i, Whisperi kontrolli ja RAG-i indekseerimise töid.

Review-workeri audio hankimise vea vastus sisaldab lisaks `DOWNLOAD_FAILED` koodile `yt-dlp` lühendatud stderr-väljundit. Nii on puuduva binaari, võrgutõrke või ERR-i meedia vea põhjus nähtav ilma konteinerisse käsitsi sisenemata; tokenit ega muid `.env` saladusi veateatesse ei kirjutata. Muu ootamatu Whisperi töötlusviga annab `WHISPER_REVIEW_FAILED` vastuses erandi tüübi ja lühikese sõnumi, kuid mitte stack trace'i ega keskkonnamuutujate sisu. Nii saab järgmise vea põhjal teha konkreetse paranduse.

Whisperi mudel ja kõik avalikudki seadistusväärtused on `.env` failis. MVP 1.2 lähtekonfiguratsioon on:

- `.env`-is määratud `FASTER_WHISPER_VERSION=1.2.1`;
- `.env`-is määratud `PYAV_VERSION=18.0.0`; `faster-whisper` 1.2.1 ei ühildu PyAV 19-ga, sest kasutab eemaldatud `metadata_errors` argumenti;
- `.env`-is määratud `YTDLP_VERSION=2025.1.15`, mida kasutavad mõlemad image'id heli hankimiseks;
- mitmekeelne `medium` mudel, Hugging Face’i identifikaatoriga `Systran/faster-whisper-medium`;
- mudeli revisjon `08e178d48790749d25932bbc082711ddcfdfbc4f`;
- `device=cpu`, `compute_type=int8`, `language=et`, `cpu_threads=3`, `num_workers=1`, `word_timestamps=true` ja `.env`-is määratud `ERR2TEXT_WORKER_CPUS=3.0`;
- sama olemasolev Hugging Face’i cache `<runtime-root>/models/huggingface/`; pärast esimest allalaadimist tekib sinna mudeli standardne `models--Systran--faster-whisper-medium` cache-kataloog.

Whisperi mudel on avalik ega vaja uut Hugging Face’i tokenit, kuid worker pärib olemasoleva `HF_TOKEN` ja Hugging Face’i cache’i seadistuse samast `.env` failist. Konteineritele ei seata kunstlikku mälulage. Raskeid Pyannote’i ja Whisperi töid ei käivitata samal ajal; piirang on tööde järjestamisel ja CPU-lõimede arvus, mitte RAM-i juhuslikus ülempiiris.

Kõik runtime-andmed asuvad hostis `/srv/err2text/` all ning peavad kuuluma `.env` failis määratud hosti `ERR2TEXT_UID:ERR2TEXT_GID` kasutajale (praegusel serveril `ubuntu`). Mõlemad worker-konteinerid käivituvad selle UID/GID-ga. Image'i ehituse ajal võivad `/app` lähtekoodifailid kuuluda root'ile, sest worker loeb neid ainult; runtime-konteiner ei tohi kirjutada projekti checkout'i ega luua `/srv/err2text` alla root-omanikuga faile. Vajalikud hostikataloogid (`outputs`, `work`, `models/huggingface`, `cache`, `home`, `maps`, `review-inputs`) tuleb enne esimest käivitust luua õige omaniku ja kirjutusõigusega. Kood ei kasuta `sudo`, `chown` ega privileegide tõstmist; õiguste viga peab lõppema selge veaga, mitte vaikse root-kirjutusega.

MVP 1.2 ei tõsta olemasolevaid ühe jooksu väljundkatalooge ümber. Mitme töötlusjooksu püsiv paigutus võetakse kasutusele teenusekihi etapil kujul `<source-slug>/runs/<UTC-run-id>/`; iga jooks sisaldab oma põhiartefakte ja võimalikku `review/whisper/` alamkataloogi. Seega ei kasutata tulevikus ebaselgeid nimesid nagu `reinsalu-isamaa-1` ja `reinsalu-isamaa-2`.

MVP 1.2 esimene kontrolljuhtum on juba käsitsi nimedega kinnitatud Reinsalu intervjuu. Claude’i analüüsis nimetatud kohad lähevad käsitsi kandidaatide faili ning neid käsitletakse hüpoteesidena, mitte tõestatud vigadena. Võrdluses hinnatakse vähemalt: kandidaatide arv, inimese poolt tegelikult valeks tunnistatud omistuste arv, Whisperi poolt nähtavaks tehtud põhjendatud kõnelejapiirid ning kontrolliks kulunud aeg. Esmakordse image’i ehituse ja esimese kontrolljooksu teeb projekti kasutaja käsurealt; arendaja ei käivita neid selle muudatuse osana.

#### MVP 1.2 otsus

Reinsalu kontrolljooks tõestas, et `whisper-review` worker töötab tehniliselt, kuid lükkas tagasi selle kasutamise meetodina. ERR-i olemasolev VTT on eesti keeles üldiselt täpsem kui CPU-põhise Whisper `medium` mudeli uuesti loodud tekst. Whisper ei tuvasta isikut ega sõltumatut speaker-ID-d; review JSON-is olevad speaker-ID-d pärinevad ikka samast Pyannote’i tulemusest. Seetõttu ei saa Whisperi uus ASR-tekst parandada Pyannote’i vale või nihkes speaker-piiri ning see lisab teksti-, aja- ja CPU-kulu veaallika.

MVP 1.2 `whisper-review` artefaktid jäävad katse ja diagnostika tõendiks, kuid Whisperi taastranskribeerimise haru ei ole järgmise arenduse alus. Seda ei tohi kasutada põhi-VTT parandamiseks ega kõneleja automaatseks ümberomistamiseks. Katse konkreetsed tulemused, vead ja viited on failis `lessons_learned.md`.

### MVP 1.3 — olemasoleva VTT forced-alignmenti spike

MVP 1.3 eesmärk on kontrollida kitsalt A-tüüpi segalõikude parandatavust: üks ERR-i VTT cue sisaldab mitme kõneleja teksti, kuid VTT-l puuduvad sõnatasandi ajad. Katse ei tee uut transkriptsiooni. Ta joondab olemasoleva VTT teksti audioga ning seob joondatud sõnad Pyannote’i juba olemasolevate ajavahemikega.

Sisend on lõpetatud MVP 1 jooksu `transcript.json`, `speakers.json`, `resolver.json`, algne VTT ning inimese lugemise põhjal koostatud kontrollfail. Inimene ei pea esimeses etapis saadet tervikuna kuulama: ta loeb nimedega Markdown-transkriptsiooni, märgib segalõigu ning paneb `|` märgiga kirja tekstilise kõnelejavahetuse. Audiost täpset sekundipiiri selles etapis ei oletata. Kontrollfaili üks kirje sisaldab vähemalt:

```json
{
  "segment_id": "seg_0134",
  "review_method": "read_context",
  "verdict": "mixed_cue",
  "before_separator_speaker": "saatejuht",
  "after_separator_speaker": "Urmas Reinsalu",
  "separator_after_text": "vaates.",
  "note": "Saatejuhi küsimuse lõpp, seejärel Reinsalu vastus."
}
```

Reinsalu esimese spike’i lugemiskontekstiga märgitud kontrollnäited on kuus VTT cue’d ajavahemikega `00:02:20.620–00:02:22.400`, `00:04:21.400–00:04:23.660`, `00:07:26.300–00:07:28.040`, `00:07:54.040–00:07:58.040`, `00:09:06.120–00:09:08.400` ja `00:10:07.980–00:10:11.260`. Need ei ole veel audioga kinnitatud tõde, vaid tehnilise spike’i kontrollsisend.

Katse worker on Whisperist eraldi `alignment-review` image ja Compose’i teenus. See paigaldab ainult valitud CTC/forced-alignmenti mudeli ning vajalikud audio-sõltuvused; põhi-image ja aegunud `whisper-review` image ei tohi saada selle sõltuvusi. Mudelivaliku spike valis CC-BY-4.0 litsentsiga TalTechi üldotstarbelise eesti CTC-mudeli `TalTechNLP/xls-r-300m-et`, revisjoniga `a1a327b54c3ecbb4750ce8c75aa7ee996030753f`. Mudel on treenitud muu hulgas saadete ja intervjuude kõnel ning on VTT teksti joondamiseks sobivam lähtepunkt kui Whisperi uus ASR-tekst. Mudeli ja joondaja kõik versioonid ning avalikud seadistusväärtused paiknevad `.env` failis; mudelid kasutavad olemasolevat välist Hugging Face’i cache’i.

Worker töötleb inimese märgitud kahte liiki hindamisjuhtumeid: `mixed_cue`, kus üks cue sisaldab tekstilise `|`-märgi järgi kahte kõnelejat, ning `clean_transition`, kus kõnelejamuutus on õigesti kahe terve cue vahel. Teine liik mõõdab valepositiivseid cue-siseseid poolitusi. Iga juhtum joondatakse `±3` sekundi audioaknas koos sellele ajaliselt jäävate naaber-VTT cue’de tekstiga, sest ERR-i cue-ajad võivad olla mõne sekundi võrra nihkes. Enne CTC-sse andmist normaliseeritakse VTT tekst mudeli märgistikule: väiketähed, kirjavahemärgid eemaldatakse ning VTT sidekriipsu- ja tundmatute märgi artefaktid ei lähe target-järjendisse. Sõna speaker-ID määratakse sõna ja Pyannote’i spanide suurima ajalise kattuvuse järgi; olematu või liiga lühike kattuvus jääb määramata.

Forced-alignmenti tulemuse kõrvale tehakse eraldi, sellest sõltumatu `sentence-boundary-review` võrdlustest. See ei tohi laadida audiot ega CTC-mudelit ega kasutada joondatud sõnaaegu, CTC-kindlust, inimese märgitud kõnelejajärjestust ega `separator_after_text` väärtust ennustuse tegemisel. Ta kasutab ainult muutmata cue-teksti, cue algus- ja lõppaega ning `speakers.json` Pyannote'i spane. Algoritm arvestab ainult cue sees olevat täpselt üht Pyannote'i speaker-vahetust, mille aeg jääb vähemalt `0,5` sekundit kummastki cue servast eemale. Lause lõpu (`.`, `?`, `!`) aeg hinnatakse cue kestuse ja leksikaalsete sõnade järjekorra lineaarsel suhtel; lähim lõpp valitakse ainult siis, kui selle hinnanguline aeg jääb Pyannote'i piirist kuni `±2,0` sekundi kaugusele. See on teadlikult jäme tekstireegel, mitte väide tegeliku sõnaaja kohta. Inimese märgendust kasutatakse alles pärast ennustust täpsuse mõõtmiseks. Puhtas kontrollcue's loetakse valepositiivseks ainult selline pakutud sisemine poolitus; cue servast kuni `0,5` sekundi kaugusel olevat üleminekut ei loeta valepositiivseks. Sama cue kordumist mitmes kontrollpaaris arvestatakse üks kord.

Mõlemad review-käsud kirjutavad iga eraldi case-faili jooksu oma välisesse kataloogi:

```text
<output-dir>/review/alignment/<review-id>/
├── alignment_review.json
└── alignment_review.md

<output-dir>/review/sentence-boundary/<review-id>/
├── sentence_boundary_review.json
└── sentence_boundary_review.md
```

Iga tulemuskirje sisaldab muutmata VTT cue’d, inimese tekstilist poolitusmärget või puhta ülemineku kirjeldust, joondatud sõnu algus-/lõpuaja ja joonduskindlusega, iga sõna Pyannote’i kattuva speaker-ID-d, pakutud sõnapiiri ning vastuolu/ebakindluse põhjust. Joonduskindlus on CTC valitud märgi lokaalne suhteline tõenäosus võrreldes samal kaadril parima märgiga (`0…1`), mitte kalibreeritud väide sõna või kõneleja tõesuse kohta. `alignment_review.md` peab olema inimesele loetav: inimese märgendus nimetatakse `Lugemiskonteksti märgenduseks (audiot pole kontrollitud)`, tabelis tähistab `◀` pakutud speaker-piiri ning kuvatakse eelmise sõna lõpust tekkinud paus. Põhi-`transcript.json`, `speakers.json` ja transkriptsiooni Markdown ei muutu automaatselt.

Katse on edukas ainult siis, kui valitud mudel joondab piisava kindlusega olemasolevad VTT sõnad ning Pyannote’i sõnahaaval omistus taastab inimese märgitud kõnelejate järjestuse ning ületab või põhjendatult täiendab sõltumatut tekstipõhist võrdlustesti. Esimeses hindamiskomplektis on inimese lugemiskonteksti põhjal 18 `mixed_cue` kandidaati, 20 `clean_transition` kontrolli ning kolm terviklikult vale speaker-sildiga diagnostikajuhtu. Need ei ole audioga kinnitatud „teadaolevad vead”. Hindamine raporteerib A/B/C/D tüübi kaupa sõnapõhise variandi ja sõltumatu lauselõpu-variandi õigeid tulemusi, valepositiivseid poolitusi, määramata sõnu ning tööaega. Esialgse kuue cue’ hulgas on `00:04:21.400–00:04:23.660` D-tüübi diagnostikajuht: kui joondatud Reinsalu sõnad jäävad enne Pyannote’i vahetust `00:04:21.000`, on VTT ajamärk hiline; kui mitte, on Pyannote’i piir tõenäoliselt vale ning MVP 1.3 seda ei paranda. Enne automaatset laiemat kasutamist tuleb lukustada numbriline lävi, näiteks vähemalt 80% selgetest A-juhtudest õigesti poolitatud ning kuni üks vale muutus 20 puhta kontrolllõigu kohta, koos joonduskindluse miinimumi ja CPU-tööajaga. Kui joondus ei ületa sõltumatut baseline'i, kui eesti keeles on joondus ebausaldusväärne või kui Pyannote’i piir ise on vale, jääb tulemus `human_review_required` ning seda haru ei laiendata.

MVP 1.3 ei lahenda B-, C- ega D-tüüpi vigu: Pyannote’i kõikumist või nihkes piiri, puuduva lühikese kõnevooru ega küsimust „kes inimene on?”. Speaker embedding’uid ei salvestata; nende kasutamise vajadus otsustatakse alles pärast joondusspike’i ning nõuab enne eraldi lähteülesande muudatust.

### MVP2 — teenuse tuum, asünkroonsed tööd ja veebiliides

MVP2 algab ainult siis, kui MVP tehniline tuum on testsaate põhjal piisavalt toimiv. Eesmärk on muuta CLI-tuum hallatavaks teenuseks ning anda sellele sama töövoogu kasutav veebiliides. Veebiliides ei ole CLI-st eraldi töötlustee: nii brauser kui hilisemad AI-agendid kasutavad sama API-d, tööjärjekorda, Oracle’i metadata mudelit ja väliseid väljundfaile.

MVP2 skoobis on:

- FastAPI-põhine API transkriptsioonitöö esitamiseks;
- eraldi worker-konteiner CPU-raske audio hankimise, diarization’i ja liitmise käivitamiseks; FastAPI protsess ei tee diarization’it ise;
- tööde olekud `QUEUED`, `RESOLVING`, `DOWNLOADING`, `DIARIZING`, `MERGING`, `SUCCEEDED`, `FAILED`, `CANCELLED` ning tulemuse, vea ja edenemise pärimine;
- töö ajalõpp, katkestamine ja restarti järel kinnijäänud `RUNNING` töö tuvastamine/taastamine;
- API kaudu väljundpaketi (`original.vtt`, `normalized.vtt`, `speakers.json`, `speaker_review.json`, `transcript.json`, `<meedia-slug>-transcript.md`) allalaadimine;
- Oracle Database 26ai andmebaasis sellele rakendusele rangelt eraldi schema;
- transkriptsioonitööde, allikate, väljundite metaandmete ja failiviidete säilitamine;
- juba digitaliseeritud saadete korduvkasutuse tuvastamine, et sama URL-i ei töödelda põhjendamatult uuesti;
- veebiliides aadressil `https://err2text.fun-o.eu`, kus kasutaja sisestab ERR-i URL-i, valib mitme leitud meediaelemendi korral sobiva elemendi, käivitab töö, näeb olekut/veateadet ja avab või laadib alla tulemused;
- veebivaade põhi-Markdownile ning struktureeritud transkriptsioonile koos algse saate lingi, pealkirja, kuupäeva, töötlusversiooni ja töö oleku metadata'ga.

MVP2 veebiliides on esmalt piiratud töövahend. Selles etapis ei tehta veel kõnelejapiiride ega teksti parandamist brauseris; veebivaade peab siiski säilitama piisava konteksti, et MVP2.2 saaks kasutada samu töö-, allika- ja transkriptsiooniandmeid. MVP2 ei sisalda RAG-i, Google autentimist ega kasutajapõhiseid API-võtmeid. Serveri piiratud CPU tõttu on algne poliitika käitada korraga maksimaalselt üht diarization-tööd.

### MVP2.1 — autentimiseta veebikasutus

MVP2.1 avab MVP2 veebiliidese ilma autentimiseta kasutamiseks aadressil `https://err2text.fun-o.eu`. Anonüümne kasutaja saab esitada ERR-i URL-i, jälgida oma töö olekut ning avada tulemused. Kuna diarization on CPU-mahukas, on MVP2.1 algne samaaegsuse piir konfiguratsioonist määratav ning vaikimisi üks diarization-töö korraga. MVP2.1 ei rakenda veel IP-põhist päringusageduse piirangut; see kuulub hilisemasse autentimise ja kasutuspiirangute etappi. Anonüümsele kasutajale ei lubata vaikimisi teiste kasutajate tööandmete vaatamist.

### MVP2.2 — kõnelejapiiride kasutaja–süsteemi ülevaatus

MVP2.2 jätkab MVP1.3 poolituste probleemi veebiliideses. Eesmärk ei ole lasta süsteemil vaikimisi muuta transkriptsiooni, vaid teha inimese ja süsteemi tööjaotus läbipaistvaks ning salvestada kontrollitav otsus.

Skoobis on:

- süsteemi poolt leitud kahtlaste cue’de ja võimalike speaker-piiride esitamine koos põhjusega (näiteks cue-sisene Pyannote'i üleminek, madal omistuskindlus või review-katse tulemus);
- samas vaates originaal-VTT tekst, praegune speaker-silt, Pyannote'i ajavahemikud, võimalik tehniline kandidaat ja link/taasesitus algsele ERR-i meediale;
- kasutaja otsus: kinnita süsteemi pakutud poolitus, lükka see tagasi, märgi speaker/piir käsitsi või jäta `needs_review` olekusse;
- kasutaja viimase kinnituse või paranduse salvestamine vastava ülevaatuskandidaadi juurde; eraldi ülevaatusotsuste versiooniajalugu ei looda;
- kasutaja otsusest tuletatud inimesele loetav parandatud transkriptsioon ning masinloetav ülekatte-/parandusfail; `original.vtt`, algne `speakers.json` ja automaatne põhi-`transcript.json` säilivad muutmata.

MVP2.2 ei õpeta veel automaatselt uusi Pyannote'i või speaker-embeddingu mudeleid kasutaja otsustest ega kasuta neid otsuseid vaikiva automaatparandusena. Eesmärk on esmalt koguda veebis mugavalt tehtud kinnitused ja parandused, mille põhjal saab hiljem mõõta, kas lauselõpu-reegel, forced alignment või speaker-embedding annab päriselt lisaväärtust. Ühte transkriptsiooni töötleb korraga üks kasutaja; mitme kasutaja samaaegne muutmine ja konfliktihaldus ei kuulu MVP2.2 skoopi.

MVP2.2 transkriptsiooniversioonide tööpõhimõte on järgmine:

- `AUTOMATIC_DRAFT` on muutumatu automaatselt loodud transkriptsioon;
- `REVIEWED_DRAFT` on ühe kasutaja jooksvalt salvestatav tööversioon, mida veebiliidese tegevus „Salvesta muudatused” uuendab;
- `review_candidates` hoiab iga kahtlase koha viimast olekut ja kasutaja viimast otsust, näiteks `PENDING`, `ACCEPTED`, `REJECTED` või `MODIFIED`; eraldi otsuste ajalugu ei looda;
- parandatud tekst, poolitus ja kõnelejaseosed salvestatakse `REVIEWED_DRAFT` transkriptsioonisegmentidesse ja nende kõnelejaseostesse, mitte eraldi kohustuslike ajapiiriväljadena ülevaatuskandidaadi kirjesse;
- kui kõik nõutud kandidaadid on käsitletud, luuakse `REVIEWED_DRAFT` põhjal muutumatu `FINAL` versioon;
- `original.vtt`, algne `speakers.json`, `AUTOMATIC_DRAFT` ja varasem `FINAL` versioon säilivad muutmata.

### MVP3 — säilitatud korpus ja RAG

MVP3 lisab juba edukalt digitaliseeritud saadete säilitamise, versioonimise ja semantilise otsingu/RAG-i. See algab alles siis, kui transkriptide kvaliteet, JSON-skeem, töötlusversioonide tähendus ja korduvkasutuse reeglid on kinnitatud.

RAG ei ole CLI- ega teenuse-tuuma sõltuvus. `Double_Check_AI` projekti ingest/retrieval põhimõtteid võib kasutada eeskujuna, kuid embedding-mudel otsustatakse selle etapi alguses. Vektorid, transkriptsioonilõigud ja metadata salvestatakse Oracle Database 26ai AI Vector Searchi peale; PostgreSQL-i ega eraldi vektorandmebaasi ei lisata.

### MVP2.3 — autentimine, kasutajad ja API võtmed

Kui MVP2.1 anonüümne kasutus ja MVP2.2 ülevaatus on stabiilsed, lisatakse autentimine olemasolevale veebiliidesele ja API-le. Veebivorm kasutab jätkuvalt sama tööde- ja väljundmudelit nagu API-kliendid; eraldi paralleelset töövoogu ei looda.

Autentimise eelistatud suund on Google’i abil autentimine. Eraldi kasutajanime/parooli süsteemi ei tehta. Autenditud kasutajale saab rakendada eraldi kvoote, näidata tema tööajalugu ning lubada talle MVP2.2 ülevaatusotsuste loomist ja muutmist.

Autenditud kasutaja saab luua unikaalse API-võtme. Võtme toorväärtust näidatakse ainult loomisel; andmebaasis säilitatakse ainult selle turvaline räsi. Võtit peab saama tühistada ning hiljem lisada aegumise, õiguste ulatuse ja viimase kasutuse info.

MVP2.3 skoobis on ka kasutajategevuse audit: kes, mida, millal ja kas veebist või API kaudu töö algatas. Enne autentimisega etappi tuleb kinnitada ERR-i sisu ja tuletatud transkriptide kasutusõigus, privaatsustingimused ning teenuse kasutustingimused.

### Ühised andme- ja juurutuspõhimõtted alates MVP2-st

Uut andmebaasi ei lisata. Kasutatakse serveris juba olevat Oracle Database 26ai Always Free andmebaasi, kuid sellele rakendusele luuakse rangelt eraldi schema. Oracle’i skeemis hoitakse kasutajaid, transkriptsioonitöid, allikaid, väljundite metaandmeid, tegevuslogi ja API-võtmete räsi. Mahukaid audio-, VTT- ja JSON-faile ei salvestata andmebaasi; andmebaasis hoitakse nende viiteid, kontrollsummasid ja metaandmeid. Hilisemas RAG-etapis kasutatakse sama Oracle’i AI Vector Searchi nii embeddingute kui relatsioonilise metadata hübriidotsinguks.

#### Aja autoriteetsus ja ajavööndid

- Oracle’i andmebaasi autoriteetne aeg on UTC.
- Andmebaasi loodud ja API kaudu loetavad ajatemplid käsitletakse UTC-ajadena.
- API edastab ajad üheselt UTC-na, kasutades ISO 8601 vormingut ja `Z`-tähist.
- Brauser teisendab kuvatavad ajad kasutaja lokaalsesse ajavööndisse.
- Äriloogika ja ajalised võrdlused lähtuvad UTC-ajateljest.

Oracle’i kasutamine ORDS REST-vahekihi kaudu ei ole nõue. FastAPI ja worker võivad kasutada eraldi skeemiga Oracle’i otse `python-oracledb` abil; ORDS on ainult võimalik alternatiiv. Valitud lahendus peab kasutama ühenduste pooli, `.env`-põhiseid saladusi, migratsioone ning väikseimate õiguste põhimõtet. Andmebaas ei ole kunagi brauserile avalik.

## Tehniline lähtekoht ja põhjendused

### ERR-i olemasolevad allikad

ERR-i videod kasutavad MPEG-DASH voogusid. Esimese testsaate puhul on teada järgmised näited:

- VOD-identifikaator: `b4eb8107755029f5c6e92f8cfcf14911`;
- DASH manifest: <https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/manifest.mpd>;
- ERR-i automaatsubtiitrid: <https://vod.err.ee/dash/vod/b4eb8107755029f5c6e92f8cfcf14911/2/v/sub-f4.vtt>.

VTT annab juba ERR-i „Heli tekstiks” transkriptsiooni ja ajamärgid, kuid ei sisalda kõneleja infot. Seetõttu on MVP põhimõte kasutada olemasolevat VTT-d põhitekstina ning teha audio põhjal ainult kõnelejate diarization. See säästab GPU-ta serveris oluliselt ressursse võrreldes terve saate Whisperiga uuesti transkribeerimisega.

Lõppkasutajalt ei tohi nõuda VOD-identifikaatori, manifesti ega VTT URL-i otsimist. Need on siin dokumenteeritud vaid testimise ja veaotsingu lähteandmetena. URL-ist allikate automaatseks leidmiseks on eelistatud esimene kandidaat [`yt-dlp UglyERR`](https://github.com/smarbaa/yt-dlp-ugly-err) plugin koos `yt-dlp`-ga. Plugin toetab Jupiteri, Jupiter Plussi ja ERR-i portaali URL-e ning oskab hankida audio-, video- ja subtiitrivooge.

ERR-i URL-id ei ole tehniliselt ühesugused. Näiteks esimene test-URL `www.err.ee/1610154019/...` on uudise/artikli leht, mille tekstis viidatakse saatele „Esimene stuudio”; see ei ole otsene audio-, video-, DASH manifesti ega VTT URL. Video seos ja mängija andmed võivad olla lehe kliendipoolses JavaScriptis või ERR-i taustapäringus, mistõttu üldotstarbeline URL-transkribeerija võib lehelt meediat mitte leida. STT.ai katse andis just sellise vea: „Could not find any audio or video to download at that address.” See tõendab vajadust teha ERR-i artiklile eraldi resolver, mitte ei tõenda, et saates video puuduks.

MVP resolver peab töötama kaheastmeliselt:

1. klassifitseerima sisendi vähemalt `ERR_ARTICLE`, `JUPITER_MEDIA`, `ERR_ARCHIVE_MEDIA` või `DIRECT_TECHNICAL_URL` tüübiks;
2. artikli puhul leidma ERR-i lehe või selle taustapäringu metadata seest seotud meedia identifikaatori/URL-i ning alles siis andma selle `yt-dlp`/UglyERR-ile või kontrollitud DASH/VTT allikate hankijale.

Resolver peab koos töö tulemusega salvestama algse kasutaja URL-i, leitud kanonilise meedia URL-i/VOD-identifikaatori ja kasutatud VTT/audio URL-id. Vea korral peab API/CLI eristama vähemalt olukordi `UNSUPPORTED_URL`, `ARTICLE_WITHOUT_MEDIA`, `MEDIA_NOT_FOUND`, `DRM_PROTECTED` ja `DOWNLOAD_FAILED`; kasutajat ei tohi suunata käsitsi DevToolsi avama või otsemeedia URL-i otsima.

Esimese testsaate edukriteerium hõlmab seetõttu ka artikli resolverit: kasutaja sisestab algse `www.err.ee` artikli-URL-i ning tööriist leiab sealt automaatselt õige seotud saate meedia. Testides tuleb hiljem lisada eraldi Jupiteri video-URL ja ERR-i arhiivi URL, et artikli resolveri loogikat ei aetakse segi meedia-URL-i tavapärase allalaadimisega.

### Mitme videoga ERR-i artikkel

Artiklil võib olla null, üks või mitu seotud video- või audiomeedia elementi. Resolver ei tohi vaikimisi võtta lihtsalt lehel esimest meediaelementi, sest see võib olla artikli põhimaterjali asemel kõrvalklipp, eelvaade või muu seotud sisu.

Resolveri tulemuseks peab olema `media_items` nimekiri, milles igal elemendil on vähemalt:

- artikli sisene järjekorranumber;
- inimesele loetav pealkiri, kui ERR-i metadata selle annab;
- seotud ERR-i kanoniline meedia-URL ja/või VOD-identifikaator;
- võimalusel kestus, tüüp (video/audio) ja artiklis kuvamise järjekord.

CLI-MVP käitumine:

- kui seotud meediaelemente ei leita, lõpetab töö selge teatega;
- kui leitakse täpselt üks element, jätkub töötlus automaatselt;
- kui leitakse mitu elementi, ei alustata kallist audio- ja diarization-töötlust automaatselt. CLI kuvab inimloetava nummerdatud nimekirja ning kasutaja valib näiteks `--video-index 2`.

Kasutaja ei pea mitte üheski olukorras ise artiklist tehnilist video-URL-i, VOD-identifikaatorit ega manifesti otsima. Valik käib süsteemi avastatud pealkirja või järjekorranumbri alusel.

Hilisemas veebivormis näidatakse sama `media_items` nimekirja valitavate elementidena. Kui ERR-i metadata võimaldab põhimaterjali usaldusväärselt määrata, võib see olla vaikimisi valitud; muul juhul ei eeldata vaikivat automaatset valikut. Hiljem võib lisada ka teadliku „töötle kõik” valiku, kuid see peab kasutajale näitama eeldatavat töömahtu ning käivitama iga meediaelemendi eraldi transkriptsioonitööna.

ERR-i VTT puhul on täheldatud valedekodeeringut/mojibake’i, näiteks `Järgnevale` asemel vigane `JÃ¤rgnevale`. Tööriist peab esmalt säilitama algse VTT muutmata kujul ning seejärel looma dekodeeritud tööversiooni. Parandus peab olema deterministlik ja testitav, mitte teksti sisu muutva keelemudeli parandamine.

MVP1 sisaldab VTT parseri fiksuurteste vähemalt järgmiste juhtumitega: UTF-8 BOM, CRLF ja LF reavahetused, mitmerealised lõigud, inline-tag’id, `NOTE` plokid, tühjad tekstilõigud ja korduvad/veerevad subtiitrid. Testides peab säilima õige ajavahemik ja tekst ning juba korrektne eestikeelne UTF-8 tekst ei tohi normaliseerimisel muutuda.

### Kõnelejate diarization ja VTT ühendamine

Speaker diarization vastab küsimusele „kes rääkis millal?”, mitte „mis on inimese nimi?”. Selle väljund on näiteks:

```text
00:12:38–00:12:51  SPEAKER_00
00:12:51–00:12:52  SPEAKER_01
```

Seega ei tohi andmemudel eeldada kahte kõnelejat. Tulevastes valimisstuudiotes võivad olla saatejuhid, külalised, reporterid, salvestatud lõigud ning kattuv kõne.

Esimene mudelivalik on `pyannote.audio` speaker diarization. Uuem `pyannote/speaker-diarization-community-1` pakub ka *exclusive diarization* väljundit, kus korraga on üks kõige tõenäolisem kõneleja. See on olemasolevate VTT ajavahemikega sidumiseks praktilisem kui kattuva kõne täielik esitus, kuid kattuva kõne info tuleb võimaluse korral säilitada eraldi. Mudeli kasutamine eeldab üldjuhul Hugging Face’i kontot, mudeli kasutustingimustega nõustumist ja serverisse antavat lugemistokenit; token peab jääma `.env` faili või muusse salajaste seadistuste hoidlasse, mitte Git-i ega väljundfailidesse.

VTT ja diarization’i ühendamise algne reegel on määrata igale VTT lõigule selle ajavahemikuga suurima kattuvusega `speaker_id`. See on ainult lähtepunkt, mitte piisav kvaliteedireegel; tuleb arvestada järgmiste eranditega:

- üks VTT lõik võib sisaldada mitut lühikest kõnevooru;
- lühikesed nõustumis- ja vahelehüüdeid võivad saada vale sildi;
- inimesed võivad rääkida üksteise peale;
- VTT ja audio ajamärgid võivad olla nihkes eelsegmentide, perioodide, jinglite või muu meedia tõttu.

Seetõttu ei tohi liitmine anda ebakindlale tekstile vaikimisi kindlat inimese silti. VTT lõik säilib ühe tervikliku tekstilõiguna ja saab suurima ajalise kattuvusega anonüümse speaker-ID; seda ei poolitata Pyannote'i piiril, sest muidu võib sama VTT tekst korduda. Kui sama lõigu sees on eri kõnelejate Pyannote'i ajavahemikud, märgitakse see MVP 1.2 Whisperi ülevaatuse kandidaadiks. Kui piisavat kattuvust ei ole, jäävad `speaker_id` ja `speaker_name` väärtuseks `null` ning `attribution_status` väärtuseks `unassigned`. Igal segmendil peab olema `overlap_ratio` ja kvaliteediklass `high`, `medium`, `low` või `unknown`.

Enne liitmist tehakse ajatelje diagnostika: võrreldakse VTT esimest ja viimast kõnet sisaldavat ajavahemikku audio kõneaktiivsusega ning salvestatakse tuvastatud nihe. Liitmisprotsess peab toetama dokumenteeritud `time_offset_seconds` parameetrit; seletamatu suur nihe annab hoiatuse või lõpetab töö veaolekuga, mitte ei väljasta vaikselt ebausaldusväärset omistust.

Väljundites säilivad algsed ajavahemikud, diarization’i toorandmed ja liitmisparameetrid, et sama audioanalüüsi saaks hiljem odavalt uuesti liita. Isikunimede automaatne tuvastus ei kuulu MVP-sse ning speaker embedding’uid ei salvestata. Esimese saate puhul võib kaart olla käsitsi määratud, näiteks `SPEAKER_00 → Mirko Ojakivi` ja `SPEAKER_01 → Urmas Reinsalu`, kuid tegelik sildijärjekord tuleb kontrollida väljundi põhjal, mitte ette eeldada.

WhisperX oskab ühendada enda loodud transkriptsiooni pyannote’i diarization’iga, kuid MVP-s ei ole see põhikomponent, sest ERR-i VTT väldib ASR-i kordust. MVP 1.2 kasutab eraldi `faster-whisper` workerit ainult kahtlaste lõikude kvaliteedikontrolliks; WhisperX-i ei lisata, sest see dubleeriks praegust diarization’i kihti.

### Serveri võimekus ja sõltuvused

Kontrollitud serveri keskkond:

- arhitektuur: ARM64 (`aarch64`), 4 × ARM Neoverse-N1 tuuma;
- mälu: 23 GiB, millest kontrolli ajal oli umbes 22 GiB saadaval;
- vaba kettaruum: umbes 92 GiB;
- GPU: puudub;
- Python: 3.12.3.

Selline server on piisav ühe CPU-põhise diarization-töö eksperimendiks. RAM ja kettaruum ei ole eeldatavasti esimene piirang; peamine mõõdetav piirang on diarization’i tegelik kestus ja kvaliteet. Enne testsaate läbimist ei lubata kindlat töötluskiirust ega kõnelejate eristamise täpsust.

Kontrolli ajal ei olnud `torch`, `pyannote.audio`, `yt-dlp` ega `ffmpeg` veel projekti keskkonda paigaldatud. Kuna server kasutab ARM64 arhitektuuri ja Python 3.12-t, tuleb esimeses tehnilises töös eraldi tõestada, et vajalikud PyTorch/pyannote’i paketid paigaldatakse ning käivituvad selles konteineris. See on teostus- ja sõltuvusrisk, mitte põhjus lahendust mitte teha.

Enne täissaate testi tehakse kuni 5-minutilise heliga tehniline spike: konteineri ehitus, mudeli allalaadimine/lokaalne cache ning tegelik CPU- ja RAM-kasutus. Spike tõestab ainult, et lahendus käivitub; lõplik töötlusaja kordaja ja mäluvajadus mõõdetakse täispikal saatel. Mudeli identifikaator ja revisjon kinnitatakse (`pin`) ning salvestatakse iga väljundi metaandmetesse. Kui pyannote ei paigalda või ei tööta ARM64 keskkonnas piisavalt hästi, võrreldakse vähemalt üht CPU-/ONNX-põhist või NeMo alternatiivi enne, kui tehakse otsus teenusekihi kohta.

Audio töötluse sihtvorming on mono 16 kHz WAV. Audio hangitakse ainult audiovoona ning WAV on ajutine tööfail: see kustutatakse vaikimisi pärast edukat või nurjunud töötlust, et hoida ruumi kokku ja mitte dubleerida ERR-is olemasolevat meediat. Säilitatakse piisavad resolveri- ja töömetaandmed, et audio saaks vajadusel ERR-ist uuesti hankida. Arenduse veaotsinguks võib hiljem lisada teadliku `--keep-audio` valiku. Konteineritele ei seata kunstlikku mälulage; jagatud serveri kaitse tuleb raskete tööde järjestamisest, diarization’i/Whisperi lõimede arvust ning vajadusel madalamast protsessorieelisusest (`nice`).

## Olemasolevate projektide analüüs ja taaskasutus

### `Double_Check_AI`

[`Double_Check_AI`](https://github.com/alarj/Double_Check_AI) on Pythonil põhinev AI Guardrail/RAG projekt. Seal kasutatakse Docker Compose’i, eraldi FastAPI API-t ja Streamliti liidest, Ollamat, Chroma püsivat vektorbaasi ning andmetöötlus- ja stabiilsusteste.

Projektist on hilisemates faasides kasutatavad järgmised põhimõtted:

- API ja kasutajaliidese eraldamine;
- konteineris käivitatavad mõõtmis-, jõudlus- ja stabiilsustestid;
- RAG-i ingest/retrieval töövoo üldine struktuur;
- selge püsiva vektorandmestiku ja algandmete eristamine.

MVP-s ei võeta sellest projektist sõltuvuseks Chroma, Ollamat, Streamlitit ega RAG-i. Need ei aita ERR-i VTT + diarization’i tuuma valideerida ning suurendaksid GPU-ta serveril tarbetult ressursikulu. Ka projekti praegune API HTTP Basic autentimine fikseeritud kasutaja/parooliga ei sobi tulevasse lahendusse.

### `fun_o`

[`fun_o`](https://github.com/alarj/fun_o) on asjakohane eeskuju hilisemaks veebirakenduseks. Selle arhitektuur kasutab nginx’i avaliku sisenemispunktina, FastAPI-t API ja sessioonikihina ning Oracle Autonomous Database’i ORDS REST-kihi kaudu. Rakendus käib Docker Compose’iga ning seadistused tulevad `.env` failist. Käesolev projekt kasutab sellest eeskätt konteinerduse, Google autentimise ja eraldi andmeskeemi põhimõtteid; ORDS-i kasutamine ei ole kohustuslik.

Projektis on Google ID-tokeni kontroll, kasutaja sidumine Oracle’i kasutajakirjega, signeeritud sessiooniküpsised, Oracle’i eraldi andmeskeem ning auditilogi muster. Need on taaskasutatavad arhitektuurilised põhimõtted, mitte kopeeritav võistlusrakenduse äriloogika.

`fun_o` ei sisalda selle rakenduse jaoks vajalikku API-võtmete süsteemi. See tuleb kavandada eraldi. `fun_o` dokumentatsioonis täheldatud ORDS-i võimalik pudelikael on üks põhjus hoida ERR2TEXT-i andmekiht sõltumatuna: FastAPI ja worker võivad kasutada Oracle’i otse `python-oracledb` kaudu.

## Planeeritav hilisem arhitektuur

```text
veebibrauser / AI-agent API-klient
                ↓
              nginx
                ↓
             FastAPI
          ↙       ↓       ↘
Google autent   tööde haldus  Oracle (otseühendus või ORDS)
                ↓              ↓
       eraldi worker-konteiner  eraldi ERR2TEXT schema
                ↓
        väljundfailide hallatud salvestus
```

FastAPI peab jääma õhukeseks API-, autentimis- ja tööhalduse kihiks. Diarization on pikaajaline CPU-töö ning käib eraldi worker-konteineris, mitte FastAPI protsessis. Kuna serveris on ainult neli CPU tuuma, peab samaaegsete tööde arv olema piiratud; algne poliitika on üks diarization-töö korraga.

Veebivorm ja API peavad kasutama sama töömudelit ning looma samasuguse väljundpaketi. Veebivormi avalik aadress on `https://err2text.fun-o.eu`. nginx lõpetab TLS-i, serveerib veebivormi ning suunab API päringud FastAPI konteinerisse. FastAPI ning diarization-töötlus ei pea olema internetist otse pordiga avaldatud.

Oracle’i eraldi skeem peab võimaldama vähemalt järgnevaid objekte:

- kasutajad ja Google’i identiteedi sidumine;
- transkriptsioonitööd koos allika URL-i, oleku, kestuse ja veateabega;
- saadete/metaandmete kirjed ning korduvkasutuse tuvastamine;
- väljundite metaandmed, versioonid ja failiviited;
- API-võtmete räsi, omanik, staatus, loomisaeg ja viimane kasutus;
- kasutajategevuse auditilogi.

Audio, VTT, WAV, JSON ja Markdown ei lähe Oracle’i BLOB-ideks esimeses lahenduses. Neid hoitakse hallatud failiruumis; Oracle’is on nende turvalised viited, kontrollsummad ja metaandmed.

## Riskid, eeldused ja kvaliteedikontroll

- ERR-i lehe-, VOD- või DASH-struktuur võib muutuda. Allikate leidmine peab andma arusaadava vea ning olema testitav eraldi ülejäänud torustikust.
- `yt-dlp` ja UglyERR on kolmanda osapoole sõltuvused. Nende versioonid tuleb pin’ida; resolverit testitakse salvestatud ERR-i metadata/HTTP vastuste näidetega, et üksustestid ei sõltuks alati ERR-i live-lehest.
- ERR-i sisu kasutamisel tuleb järgida ERR-i kasutustingimusi ning õigusi; tööriist peab käsitlema ainult õiguspäraselt kättesaadavaid DRM-vabu vooge. Enne avalikku veebivormi tuleb eraldi hinnata, kas transkriptide allalaadimise pakkumine tähendab tuletatud sisu levitamist ning kas selleks on vaja ERR-i nõusolekut või täiendavaid kasutustingimusi.
- Pyannote’i tulemus ei ole nimeline speaker identification ega garanteeri täiuslikku kõnelejate arvu. Kvaliteeti hinnatakse esimeses katses käsitsi kontrollitud kõnevoorude põhjal.
- Kattuv kõne, taustamüra, muusikakatked ja väga lühikesed kõnevoorud võivad põhjustada valesid silte.
- Mudelite allalaadimine ja kasutuseelne Hugging Face’i nõusolek on vajalik eeltingimus; tootmisrakenduses ei tohi token sattuda logidesse, Git-i ega API vastustesse.
- VTT toorbaidid tuleb alles hoida, et hiljem oleks võimalik eristada ERR-i ASR-i viga, dekodeerimisviga ja diarization’i viga.
- Avalik vorm peab aktsepteerima ainult ERR-i lubatud domeenide URL-e, kasutama maksimaalse kestuse/mahu piiranguid ja kasutajapõhiseid kvoote. See välistab suvaliste URL-ide allalaadimise ning tasuta kontrollimatu CPU-kasutuse.
- Iga MVP test peab salvestama vähemalt kasutatud mudeli revisjoni, pipeline’i versiooni ja parameetrid, töö algus- ja lõpuaja, audio kestuse, diarization’i kestuse, ressursinäitajad, ajakorrektsiooni ning võimaliku vea.

### MVP valideerimise etapid ja Definition of Done

MVP koosneb kahest eraldi riskispike’ist ja kvaliteedivalideerimisest:

1. **Spike A — diarization ja liitmine:** teadaoleva VOD/audio/VTT abil tõestada ARM64 konteineris audio teisendus, diarization, ajakorrektsioon ja VTT liitmine.
2. **Spike B — artikli resolver:** tõestada algse ERR-i artikli URL → seotud meedia ID/URL leidmine. Resolveri ja diarization’i riske ei tohi segi ajada.
3. **Kvaliteedivalideerimine:** pärast spike’e kontrollida vähemalt kolme profiili: kahe kõnelejaga stuudiointervjuu, mitme osalejaga paneel/debatt ning reportaaž või muusikaga lõik.

Spike A ja Spike B võib käivitada enne lõpliku kvaliteediplaani lukustamist. Enne punktis 3 kirjeldatud kvaliteedivalideerimist tuleb aga valida konkreetsed saated, märgendada kontrolllõigud, lukustada mõõdikud ja läviväärtused ning versioonida testiplaan. Projekti juures olev `testiplaan_mall.md` on Claude’i loodud ülevaatamist vajav mall, mitte veel kehtiv testiplaan.

Enne kvaliteedivalideerimise käivitamist lukustatakse eraldi testiplaanis järgmised mõõdikud ja läviväärtused:

- käsitsi märgendatud kontrolllõikude asukoht ja kogukestus igas testprofiilis;
- mitte-kattuva kõne kõneleja omistuse õigsuse miinimum;
- `UNKNOWN` või madala usaldusega märgitavate lõikude maksimaalne osakaal;
- vale kindla omistuse maksimaalne osakaal;
- maksimaalne töötlusaja kordaja võrreldes saate kestusega;
- maksimaalne CPU- ja mälukasutus ning mõju samas serveris töötavatele rakendustele.

MVP Definition of Done on täidetud ainult siis, kui kõik kolm testprofiili läbivad eelnevalt lukustatud läved, väljund sisaldab vajalikku päritolu- ja kindlusinfot ning töötab tööde järjestamise ja lõimepiirangutega. ERR-i VTT teksti ASR-vigu mõõdetakse ja raporteeritakse eraldi; speaker diarization ei paranda neid ning nende olemasolu ei tohi varjata.

Kvaliteediotsus peab olema tasemeline, mitte ainult binaarne. Kui kahe kõnelejaga stuudiointervjuu läbib läved, kuid paneel või reportaaž mitte, võib tulemus olla „kasutatav piiratud kasutusjuhul”: teenuse järgmist etappi võib arendada ainult selgelt kirjeldatud toetatud profiilile ning mittetoetatud profiilid jäävad käsitsi ülevaatuse nõudega. Täpsed tasemed ja otsusereeglid määratakse lukustatud testiplaanis.

## Analoogsed lahendused ja viited

Täpselt samasugust avalikku avatud lähtekoodiga lahendust — „anna ERR-i URL, kasuta ERR-i olemasolevat VTT-d, lisa kõneleja sildid ja väljasta struktureeritud fail” — ei ole leitud. Olemas on üks ERR Jupiterit toetav kommertsteenus ning mitu ERR-i meedia/subtiitrite hankimise tööriista. Samuti on olemas küpsed üldotstarbelised diarization- ja transkriptsioonikomponendid.

### ERR-i/Jupiteri jaoks loodud või ERR-i toetavad lahendused

- [STT.ai: „Transcribe ERR Jupiter to Text”](https://stt.ai/transcribe-from/err-jupiter/) — kommertsteenus, kuhu saab sisestada avaliku ERR Jupiteri URL-i. Teenuse enda kirjelduse kohaselt hangib see meedia, transkribeerib valitud ASR-mudeliga, lisab speaker diarization’i (`Speaker 1`, `Speaker 2`, jne), võimaldab sildid ümber nimetada ning ekspordib TXT-, SRT-, VTT- ja DOCX-vormingus. Teenus väidab toetavat ka REST API-t ja partiitöötlust. Seda tuleb käsitleda funktsionaalse võrdluspunktina, mitte tehnilise sõltuvusena: see ei ole kohalik, kontrollitav ERR-i VTT-põhine tööriist ning selle kvaliteedi-, hinna- ja privaatsusväiteid ei ole selles projektis eraldi valideeritud.
- [`smarbaa/yt-dlp-ugly-err`](https://github.com/smarbaa/yt-dlp-ugly-err) — avatud lähtekoodiga `yt-dlp` plugin ERR-i portaalide jaoks. See ei tee transkriptsiooni ega diarization’i, kuid katab kõige kriitilisema ERR-spetsiifilise osa: URL-ist DRM-vaba audio-, video- ja subtiitrivoo leidmise ning allalaadimise.
- [`ahti123/jw-downloader`](https://github.com/ahti123/jw-downloader) — Python-tööriist ERR Jupiteri HLS-meedia allalaadimiseks. Kirjeldab Jupiteri sisulehe `contentId` põhist ERR API päringut ning HLS URL-i lugemist vastusest. See on varu- ja veaotsingureferents juhul, kui `yt-dlp UglyERR` ei suuda konkreetset Jupiteri URL-i töödelda. See ei tee transkriptsiooni ega kõnelejate eristamist.
- [`yllar/plugin.video.jupiter.err.ee`](https://github.com/yllar/plugin.video.jupiter.err.ee) — Kodi Jupiteri lisamoodul. See ei ole transkriptsioonitööriist, kuid tõendab eraldi, et Jupiteri sisu ja voogude kasutamiseks on olemas avalik kliendipoolne integratsioon. Projekti eesmärk ja litsents erinevad käesolevast lahendusest; seda ei ole kavas sõltuvusena kasutada.

ERR-i arhiivi automaatsubtiitrite olemasolu on ka teaduskirjanduses käsitletud kui suurt potentsiaalset eestikeelset andmestikku. See toetab otsust kasutada ERR-i olemasolevat VTT-d esmase tekstiallikana, mitte luua sama transkriptsiooni nullist.

### ERR-i meedia ja subtiitrite allalaadimine

- [`smarbaa/yt-dlp-ugly-err`](https://github.com/smarbaa/yt-dlp-ugly-err) — `yt-dlp` extractor plugin ERR-i Jupiteri, Jupiter Plussi ning tele- ja raadioarhiivi jaoks. Toetab DRM-vabade audio-, video- ja subtiitrivoogude hankimist. See on soovitatud komponent URL-ist ERR-i allikate automaatseks leidmiseks.

### Kõnelejate diarization

- [`pyannote/pyannote-audio`](https://github.com/pyannote/pyannote-audio) — peamine avatud lähtekoodiga Python-tööriistakast kõneaktiivsuse, kõnelejate vahetuse, kattuva kõne ja speaker diarization’i jaoks.
- [pyannote `community-1` mudeli kirjeldus](https://www.pyannote.ai/blog/community-1) — dokumenteerib `exclusive_speaker_diarization` väljundi, mis on eriti sobiv olemasolevate transkriptsiooni ajamärkide ja speaker-ID-de ühendamiseks.
- [NVIDIA NeMo Speaker Diarization](https://docs.nvidia.com/nemo-framework/user-guide/24.12/nemotoolkit/asr/speaker_diarization/intro.html) — alternatiivne diarization’i tööriistakast. See ei ole esimese MVP eelistus, sest pyannote on väiksema integratsiooniriskiga ja algse plaani osa, kuid võib olla võrdlusvariant, kui pyannote’i kvaliteet või ARM64 sõltuvused osutuvad probleemiks.

### Transkriptsiooni ja kõnelejate liitmine

- [`WhisperX`](https://github.com/joelvaneenwyk/whisper-x) — levinud lahendus, mis ühendab Whisperi transkriptsiooni ja pyannote’i diarization’i ning loob speaker-ID-dega transkriptsiooni. Selle projekti puhul on oluline eeskätt ajaliselt ühendamise üldpõhimõte; WhisperX ei ole MVP põhikomponent, kuna ERR-i VTT on juba olemas.
- [`JLCodeSource/vtt-transcribe`](https://github.com/JLCodeSource/vtt-transcribe) — sisaldab võimalust rakendada pyannote’i diarization olemasolevale transkriptsioonile. Kontseptuaalselt lähedane, kuid ei lahenda ERR-i URL-i ega selle konkreetset väljundmudelit.
- [`mzagozda/Transcriber`](https://github.com/mzagozda/Transcriber) — näide pyannote’i ja ASR-i ühendamisest ning SRT/VTT väljundite loomisest. Kasulik referents speaker-segmentide liitmise ja ekspordi osas, kuid kasutab uut transkribeerimist.
- [`AndrewMoryakov/gigastt-pyannote-transcriber`](https://github.com/AndrewMoryakov/gigastt-pyannote-transcriber) — CPU-sõbraliku diarization + ajamärkidega transkriptsiooni ühendamise näide; rõhutab eraldi toor-diarization’i, speaker mapping’u ja renderdatud väljundite säilitamist. Keele- ja ASR-valik ei vasta ERR-i kasutusjuhule, kuid andmemudeli ning mõõtmise ideed on asjakohased.

### Järeldus analoogsete lahenduste põhjal

Projekt ei ehita uut ASR-i ega diarization-mudelit. Selle eripära ja arendatav osa on ERR-spetsiifiline ühenduskiht:

```text
ERR-i URL
  → yt-dlp + UglyERR
  → ERR-i VTT + audio
  → pyannote diarization
  → VTT ajavahemike ja speaker-ID-de ühendamine
  → UTF-8 JSON / TXT / Markdown väljund
```

Seega kasutatakse olemasolevaid, tõestatud komponente, kuid luuakse väike läbipaistev torustik, mis kasutab ERR-i juba olemasolevat eestikeelset transkriptsiooni ega kuluta CPU-aega selle tarbetule uuesti loomisele.
