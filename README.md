# ERR2TEXT MVP1

Containeris töötav CLI, mis seob ERR-i olemasoleva VTT teksti audio-põhise
kõnelejate diarization'iga. MVP1 ei tee uut automaatset kõnetuvastust ega
automaatselt hääle järgi inimeste nimede määramist.

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

## Sõltuvused

`yt-dlp` hangib meedia ja subtiitrid. UglyERR paigaldatakse Docker image'i
ehitamisel lukustatud commit'ilt ning selle lähtekoodi ei hoita selles
repoos. `ffmpeg` teeb WAV teisenduse. `pyannote.audio` on valikuline
diarization'i sõltuvus; selle mudel nõuab Hugging Face'i tokenit `.env` failis.

## Ohutus ja andmed

Ära salvesta `.env`, Hugging Face'i tokenit, WAV-faile, mudelikaale ega
kasutaja väljundeid projekti kataloogi. `original.vtt` on auditikoopia ning
võib olla mitte-UTF-8; kõik ülejäänud tekstiväljundid on UTF-8.
