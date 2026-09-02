# Förtidsröster – dashboard

Statisk dashboard som visar mottagna förtidsröster i riksdagsvalet 2026. Data hämtas automatiskt från Valmyndighetens öppna CSV-fil.

## Automatisk uppdatering

**Du behöver inte göra något manuellt efter att sidan är publicerad.**

1. Pusha repot till GitHub och aktivera **GitHub Pages** (mappen `/docs`).
2. Se till att **Actions** är tillåtna i repot (Settings → Actions → Allow all actions).
3. Klart. Workflowen körs schemalagt **ca 06:30 och 14:30** svensk tid (GitHub Actions kan försenas). Trigga manuellt via **Actions → Uppdatera förtidsröster → Run workflow** om du vill ha in data direkt.

Du kan också trigga en uppdatering manuellt under **Actions → Uppdatera förtidsröster → Run workflow**.

Valmyndighetens CSV uppdateras kl 06 och 14:
`https://data.val.se/filer/val2026/rostmottagning/mottagna-fortidsroster-val2026.csv`

## Grafer

1. **Andel av röstberättigade** – kumulativa förtidsröster / antal röstberättigade det aktuella året.
2. **Andel av förväntade röster** – kumulativa förtidsröster / förväntat antal röster om valdeltagandet blir 84,21 % (som 2022).

Jämförelsekurvor för 2010, 2014, 2018 och 2022 hämtas från Valmyndighetens historiska filer (raden `summa`/`SUMMA`). Tidigare version halverade dessa felaktigt.

## Publicera på GitHub Pages

1. Skapa ett nytt repo (eller använd en undermapp i ett befintligt repo).
2. Kopiera innehållet i `fortidsroster-dashboard/`.
3. Gå till **Settings → Pages** och välj **Deploy from branch**, mappen **`/docs`**.
4. Aktivera **Actions** i repot så att workflowen kan committa uppdateringar.

Efter någon minut finns sidan på `https://<användare>.github.io/<repo>/`.

## Köra lokalt

```bash
python scripts/update_data.py
cd docs
python -m http.server 8080
```

Öppna http://localhost:8080

## Manuellt alternativ (Excel)

Om du inte vill ha GitHub Pages räcker det att ladda ner Valmyndighetens CSV och summera kolumnen `TOTAL` (eller summera datumkolumnerna). Excel-mallen på Valcentralen gör samma sak per kommun. Automatisering är enklare om du vill ha grafer som uppdateras själva.

## Källa

Data: [Valmyndigheten – rådata val 2026](https://www.val.se/valresultat-och-statistik/statistik-och-data/radata-val-2026)
