# Nota di spiegazione: interfaccia e algoritmo

Questa nota descrive in modo operativo come usare l'applicazione **Shadow Orography Studio** e come funziona il motore di calcolo delle intersezioni tra ombra dei rotori e area di interesse (AOI).

## 1) Interfaccia utente (GUI)

L'interfaccia principale è organizzata in due pannelli:

- **Pannello controlli (sinistra)**: caricamento dati, impostazioni, calcolo, esportazione.
- **Viewport grafica (destra)**: visualizzazione AOI, turbine, traiettoria dell'ombra e ombra corrente.

### Controlli principali

- **Year**: anno di simulazione.
- **Min solar elev (deg)**: soglia minima di elevazione solare per considerare una condizione valida (filtra alba/tramonto molto bassi).
- **Load AOI shapefile**: carica un poligono AOI da file `.shp`.
- **Load/Save project JSON**: apre/salva un progetto (turbine, path AOI, parametri).
- **Add demo turbines**: inserisce due turbine di esempio.
- **Compute intersections**: esegue il calcolo annuale.
- **Export CSV**: salva i risultati tabellari delle intersezioni.
- **Export WebM**: esporta una sequenza video dell'animazione giornaliera.
- **Day + timeline + Play/Speed**: selezione giorno e animazione frame-by-frame delle posizioni d'ombra.

### Logica di visualizzazione

- L'AOI viene disegnata come poligono verde.
- Le turbine sono punti rossi.
- Per il giorno selezionato, la timeline mostra:
  - la **traiettoria** dei centri delle ellissi d'ombra (linea ciano),
  - l'**ellisse corrente** (contorno blu) al frame corrente.

## 2) Algoritmo di calcolo

L'algoritmo calcola, su tutto l'anno, gli istanti in cui l'ombra di ciascuna turbina interseca il poligono AOI.

### Passo A — Campionamento temporale annuale

Viene creato un indice temporale timezone-aware con passo fisso (default 15 minuti) dal 1 gennaio al 31 dicembre dell'anno selezionato.

### Passo B — Posizione solare

Per ogni timestamp si calcolano almeno:

- **azimuth** del sole,
- **apparent_elevation**.

Il calcolo usa `pvlib`.

### Passo C — Filtro ore di luce

Si mantengono solo i timestamp con `apparent_elevation > min_solar_elevation_deg`.

### Passo D — Ellisse d'ombra per turbina e istante

Per ogni turbina e timestamp valido, si costruisce un'ellisse che rappresenta l'ombra “worst-case” del rotore su terreno piano:

- Distanza centro ombra dalla turbina:
  - `d = hub_height / tan(elevation)`
- Semiasse maggiore:
  - `a = rotor_radius / sin(elevation)`
- Semiasse minore:
  - `b = rotor_radius`
- Traslazione del centro secondo azimuth:
  - `dx = -d * sin(azimuth)`
  - `dy = -d * cos(azimuth)`
- Rotazione finale ellisse:
  - `rotation = 90° - azimuth`

### Passo E — Test di intersezione AOI

Per efficienza, il controllo avviene in due stadi:

1. **Bounds pre-check** (rettangoli min/max): scarta subito i casi certamente disgiunti.
2. **Intersezione geometrica** `aoi.intersects(ellipse)` con Shapely.

Se l'intersezione è vera, si registra una riga risultato con:

- ID turbina,
- timestamp locale ISO,
- data e ora locali,
- azimuth ed elevazione solare.

## 3) Risultati prodotti

- **DataFrame risultati**: eventi “turbina-ora” con intersezione positiva.
- **CSV esportabile**: serializzazione del DataFrame.
- **Animazione WebM**: rendering dei frame della scena Qt nel giorno selezionato.

## 4) Assunzioni e limiti principali

- Modello geometrico su **terreno piano** (non usa DEM/DTM).
- Ombra modellata come inviluppo ellittico “worst-case”, non come simulazione pale istantanea.
- Accuratezza dipendente da:
  - qualità coordinate AOI/turbine,
  - sistema di riferimento coerente,
  - passo temporale scelto (più fine = più accurato ma più lento).

## 5) Suggerimenti pratici

- Verificare che AOI e turbine siano nello stesso sistema metrico/proiettivo.
- Usare 15 minuti per analisi preliminare e 5 minuti per raffinamento locale.
- Impostare `min solar elev` a 3–8° per ridurre casi marginali vicino all'orizzonte.
