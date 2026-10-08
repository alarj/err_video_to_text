# Hiljem lahendamist vajavad probleemid

## 2026-10-08 — kõnelejaseoste ajaväärtuste võrdlus

- **Probleem:** `transcript_segment_speakers` olemasolevat seost otsitakse
  praegu ajaväärtuste tolerantsiga. See väldib `float`-teisenduse tõttu tekkivat
  vale duplikaat-INSERT-i, kuid ei kasuta kanonilist normaliseeritud
  kümnendväärtust.
- **Mõju:** poolituse salvestamine võib sõltuda valitud tolerantsist ning
  erineva täpsusega ajaväärtuste korral võib tekkida liiga lai või liiga kitsas
  vaste.
- **Koht koodis:**
  `backend/app/api/routes.py`, funktsioon `save_review_candidate()`, sisemine
  funktsioon `restore_or_insert_speaker()`.
- **Võimalik lahendus:** määrata ajaväärtuste kanoniline täpsus andmemudeli ja
  pipeline'i põhjal, teisendada väärtused `Decimal`-iks ning võrrelda mõlemat
  väärtust sama normaliseeritud kümnendtäpsusega (näiteks millisekunditeni).
  SQL-i võrdlus peab kasutama sama normaliseerimist, mitte suvalist tolerantsi.
- **Leitud:** 2026-10-08
- **Lahendatud:** 2026-10-08 — ajaväärtused normaliseeritakse `NUMBER(12,3)` täpsusele enne võrdlust, deduplikatsiooni ja INSERT-i; kandidaadi 219 unikaalsuskonflikt ei tohiks enam tekkida.
