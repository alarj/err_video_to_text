# MVP4 videoga transkriptsioonivaade

## Nõuded

- Transkriptsiooni olemasolul kuvatakse töö juures nupp „Vaade”.
- Vaade avab TTÜ projektiga sama kujundusmustriga modaali: üleval video, all
  sünkroonitud transkriptsioon ja versioonivalik.
- Avamisel on video nähtav, kuid ei käivitu. Esitus käivitub ainult kasutaja
  Play-nupust või ajamärgi klõpsust.
- Ajamärk otsib video õigesse kohta, käivitab esituse ja taastab teksti
  jälgimise. Kasutaja kerimise järel taastab „Jälgi teksti” automaatse jälgimise.
- Brauser jätab saate viimase vaatamiskoha meelde. Video tuleb otse ERR-i või
  Jupiteri voost; videofaili ei laadita alla ega salvestata.

## Lahendus

- API tagastab protsessi aktiivsed transkriptsiooniversioonid ja valitud versiooni
  ajastatud segmendid.
- Brauser valib vaikimisi viimase versiooni, ehitab segmentidest klõpsatavad
  ajamärgid ning hoiab aktiivset segmenti video `timeupdate` sündmusega kooskõlas.
- Esituskoht on `localStorage`-is protsessi kaupa. Vaate sulgemine peatab voo.
