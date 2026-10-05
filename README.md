# ERR2TEXT MVP1.3

Containeris töötav CLI, mis seob ERR-i olemasoleva VTT teksti audio-põhise
kõnelejate diarization'iga. MVP1 ei tee uut automaatset kõnetuvastust ega
automaatselt hääle järgi inimeste nimede määramist. MVP1.2 lisab eraldi
Whisperi kontrolltöölise, mis kuulab üle ainult kahtlased lõigud ega muuda
põhitranskriptsiooni automaatselt. MVP1.3 lisab sellest eraldi fixed-VTT
forced-alignmenti katse inimese märgitud segalõikudele.

## Käivitamine

```bash
python process.py "https://www.err.ee/..." --output-dir /srv/err2text/outputs/minu-toe
```

`--output-dir` peab asuma väljaspool projekti checkout'i. Käitusaegne cache,
mudelid ja ajutine audio paiknevad samuti `ERR2TEXT_RUNTIME_ROOT` all
(vaikimisi `/srv/err2text`).

`ERR2TEXT_UID` ja `ERR2TEXT_GID` peavad `.env` failis olema hosti kasutaja
arvulised UID ja GID (`id -u`, `id -g`). Konteiner kirjutab nende õigustega,
nii et hosti kasutaja saab väljundeid lugeda ja hallata.

Rakenda nimed pärast käsitsi kontrolli ilma audio- või diarization-etappi
käivitamata:

```bash
python process.py apply-names --output-dir /srv/err2text/outputs/minu-toe --speakers-map /srv/err2text/maps/nimed.json
```

## MVP1.2: Whisperi kontroll

`whisper-review` võtab sisendiks juba valminud `transcript.json`,
`speakers.json` ja `resolver.json` failid. Ta valib keskmise või madala usaldusega,
VTT-lõigu sees oleva diarization'i piiri või lühikese kõnelejavahetusega
lõigud, hangib ERR-ist ajutiselt audio ning kirjutab kontrollmaterjali samasse
väljundisse:

```text
/srv/err2text/outputs/<saate-slug>/review/whisper/
├── whisper_review.json
└── whisper_review.md
```

Käsk ei muuda `transcript.json`-i, Markdown-transkriptsiooni ega
`speakers.json`-i. Iga tulemus jääb inimese kinnitust ootavaks.

Claude'i või inimese poolt käsitsi osutatud kohad võib lisada eraldi faili
`/srv/err2text/review-inputs/<saate-slug>-candidates.json`:

```json
{
  "candidates": [
    {"segment_id": "seg_0038", "reason": "manual_review"},
    {"start": 61.2, "end": 66.8, "reason": "manual_review"}
  ]
}
```

Reinsalu esimese katse kontrollitud kandidaatide lähtefail on repoos
`examples/reinsalu-isamaa-claude-candidates.json`. Kopeeri see enne esimest
Whisperi jooksu välisesse runtime-kataloogi, et seda Gitist mitte lugeda ega
review-väljundiga segada:

```bash
cp examples/reinsalu-isamaa-claude-candidates.json \
  /srv/err2text/review-inputs/reinsalu-isamaa-candidates.json
```

Pärast seda käivitatakse eraldi teenus:

```bash
docker compose --profile whisper-review run --rm whisper-review whisper-review \
  --output-dir /runtime/outputs/reinsalu-isamaa \
  --candidate-file /runtime/review-inputs/reinsalu-isamaa-candidates.json
```

Esimese image'i ehituse ja esimese review-jooksu teeb projekti kasutaja.

## MVP1.3: VTT forced-alignmenti katse

Whisperi katse järeldus on dokumenteeritud failis
[`lessons_learned.md`](lessons_learned.md): uus ASR-tekst ei kontrolli
Pyannote'i speaker-piiri sõltumatult. Seetõttu joondab `alignment-review`
muutmata ERR-i VTT sõnad otse audioga ning seob iga sõna olemasoleva
Pyannote'i ajavahemikuga. See on ainult inimese kontrollmaterjal ega muuda
`transcript.json`-i, `speakers.json`-i ega Markdown-transkriptsiooni.

Reinsalu kuue inimese lugemise põhjal märgitud A-tüüpi segalõigu lähtefail on
repoos `examples/reinsalu-isamaa-alignment-spike.json`. Kopeeri see runtime'i:

```bash
cp examples/reinsalu-isamaa-alignment-spike.json \
  /srv/err2text/review-inputs/reinsalu-isamaa-alignment-spike.json
```

Ehita eraldi worker ja kontrolli esmalt käsurea lepingut:

```bash
docker compose --profile alignment-review build alignment-review
docker compose --profile alignment-review run --rm alignment-review alignment-review --help
```

Katse käsk on:

```bash
docker compose --profile alignment-review run --rm alignment-review alignment-review \
  --output-dir /runtime/outputs/reinsalu-isamaa \
  --case-file /runtime/review-inputs/reinsalu-isamaa-alignment-spike.json
```

Tulemus kirjutatakse ainult siia:

```text
/srv/err2text/outputs/reinsalu-isamaa/review/alignment/
├── alignment_review.json
└── alignment_review.md
```

Mudel `TalTechNLP/xls-r-300m-et` (CC-BY-4.0, revision
`a1a327b54c3ecbb4750ce8c75aa7ee996030753f`) on avalik; uut HF tokenit selle
jaoks vaja ei ole. Selle ja tööriistaversioonide väärtused on `.env` failis.

Pärast `.env` täiendamist ehitatakse tööline, mida päriselt kasutad:

```bash
docker compose build err2text
docker compose --profile whisper-review build whisper-review
docker compose --profile alignment-review build alignment-review
```

Enne pärisjooksu saab ainult käsurea lepingu kontrollida ilma meediat
allalaadimata:

```bash
docker compose --profile whisper-review run --rm whisper-review whisper-review --help
```

## `.env` ja hosti õigused

Kõik seadistusväärtused, ka avalikud mudeli- ja kataloogiväärtused, paiknevad
`.env` failis. Sellele tuleb lisada olemasolevaid `HF_TOKEN`, `UGLYERR_REF`,
`ERR2TEXT_UID`, `ERR2TEXT_GID` ja `ERR2TEXT_RUNTIME_ROOT` väärtusi muutmata:

```dotenv
ERR2TEXT_CONTAINER_RUNTIME_ROOT=/runtime
ERR2TEXT_WORKER_CPUS=3.0
ERR2TEXT_HOME=/runtime/home
ERR2TEXT_USER=err2text
ERR2TEXT_LOGNAME=err2text
ERR2TEXT_HF_HOME=/runtime/models/huggingface
ERR2TEXT_HF_HUB_CACHE=/runtime/models/huggingface/hub
ERR2TEXT_XDG_CACHE_HOME=/runtime/cache
ERR2TEXT_TORCHINDUCTOR_CACHE_DIR=/runtime/cache/torchinductor

WHISPER_MODEL=medium
WHISPER_MODEL_REVISION=08e178d48790749d25932bbc082711ddcfdfbc4f
FASTER_WHISPER_VERSION=1.2.1
PYAV_VERSION=18.0.0
YTDLP_VERSION=2025.1.15
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=et
WHISPER_CPU_THREADS=3
WHISPER_REVIEW_CONTEXT_SECONDS=10
WHISPER_REVIEW_SHORT_SEGMENT_SECONDS=2
WHISPER_REVIEW_MAX_CANDIDATES=50

TORCH_VERSION=2.11.0
TRANSFORMERS_VERSION=4.57.1
ALIGNMENT_MODEL=TalTechNLP/xls-r-300m-et
ALIGNMENT_MODEL_REVISION=a1a327b54c3ecbb4750ce8c75aa7ee996030753f
ALIGNMENT_DEVICE=cpu
ALIGNMENT_CPU_THREADS=3
ALIGNMENT_SAMPLE_RATE=16000
```

Whisperi mudel laaditakse esimesel review-jooksul samasse Hugging Face'i
cache'i kui Pyannote: `/srv/err2text/models/huggingface/hub/`. Mudel on avalik;
olemasolevat `HF_TOKEN` väärtust ei pea Whisperi tõttu muutma.

Konteinerid käivituvad `.env` faili `ERR2TEXT_UID:ERR2TEXT_GID` õigustes.
Enne Whisperi või alignment-workeri esimest jooksu peab hostis olema kasutaja omandis järgmine uus
kataloog:

```bash
sudo install -d -o "$(id -u)" -g "$(id -g)" -m 0750 \
  /srv/err2text/work/whisper-review /srv/err2text/work/alignment-review \
  /srv/err2text/review-inputs
```

Konteinerid ei kasuta `sudo` ega `chown`-i. Mudelite, tööfailide ja väljundite
omanik peab jääma hosti kasutajaks, mitte `root`-iks.

## Sõltuvused

`yt-dlp` hangib meedia ja subtiitrid. UglyERR paigaldatakse Docker image'i
ehitamisel lukustatud commit'ilt ning selle lähtekoodi ei hoita selles
repoos. `ffmpeg` teeb WAV teisenduse. `pyannote.audio` on valikuline
diarization'i sõltuvus; selle mudel nõuab Hugging Face'i tokenit `.env` failis.
`.env`-is lukustatud `FASTER_WHISPER_VERSION` on ainult `whisper-review`
image'i sõltuvus ning selle mitmekeelne `medium` mudel on lukustatud Hugging
Face'i revisjonile.

## Ohutus ja andmed

Ära salvesta `.env`, Hugging Face'i tokenit, WAV-faile, mudelikaale ega
kasutaja väljundeid projekti kataloogi. `original.vtt` on auditikoopia ning
võib olla mitte-UTF-8; kõik ülejäänud tekstiväljundid on UTF-8.
