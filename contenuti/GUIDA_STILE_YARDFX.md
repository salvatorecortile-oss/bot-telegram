# Guida di stile video YardFX (@yard.fx)

Libreria completa con le schede dei video modello: https://claude.ai/artifact/6yztDxv7dCxcrsRM5jqtHc
Kit grafico e procedura di montaggio passo passo: `contenuti/yardfx_video/` (leggi `README.md`).

Ogni nuovo video di riferimento va scomposto (fondo, testo, grafica, passaggi, ritmo, chiusura), aggiunto alla libreria
e, se ha una tecnica utile, rifatto da zero in stile YardFX. Mai copiare loghi, musiche, foto o grafiche di altri creator.

## VIDEO MODELLO (qualità da raggiungere sempre)
**Strategia base #1: RSI**, programmato per l'11 novembre 2026 alle 10:00. Codice: `yardfx_video/esempi/strategia1_rsi.py`.

Paletti fissi presi da questo video:
1. **Sincronizzazione perfetta**: `Y.words_aligned(mp3, script)`. Ogni scena inizia sulla prima parola del suo paragrafo e resta finché la voce non l'ha finito. Ogni scritta compare sulla sua parola.
2. **Montaggio** animato e dinamico: una scena per paragrafo, transizioni sempre diverse, camera viva, lampi.
3. **Audio**: la voce «salvatore» di Speechify (dal 18/11), una musica che si abbassa sotto la voce e circa 100 effetti sonori al minuto.
4. **Sottotitoli** sempre visibili fino alla chiusura.
5. **Chiusura**: i 4 paletti detti e animati, poi il logo animato e "CERCAMI SU TELEGRAM @yard_fx".
6. **Copertina** diversa dal primo fotogramma, con il logo piccolo.
7. **Revisione**: video e copertina vanno a Salvatore prima di pubblicare o programmare.

## Il principio: 3 mondi + firme fisse
Ogni video alterna almeno 2 dei 3 mondi (di solito 3), scelti scena per scena in base a cosa si dice:
- **NOTTE** (video 1 + 4): blu notte, raggi, costellazione, faretto, icone luminose, numeri giganti con alone, linea del tempo a nodi. Per ganci, numeri e chiusure.
- **TERMINALE** (video 2 + 5 + 6): grafite, schede di app in prospettiva con lente, widget del prezzo fisso, chip ✓/✕, barre scenario, grafici con zone, schede trade, notifiche. Per dati, livelli e trade.
- **QUADERNO** (r601 + video 3): carta a quadretti, titoli numerati in corsivo elegante, disegni a mano, frecce tratteggiate, timbri, barrati. Per spiegare il perché.

Firme fisse in tutti i mondi:
- sottotitoli parola per parola con la parola chiave nel riquadro oro;
- chiusura con logo YardFX animato + Telegram @yard_fx (candeline in alto solo se hanno un senso detto dalla voce);
- disclaimer piccolo.

Cambio di mondo con tendina circolare.

## Palette e font
- Oro #d6a63a.
- Notte: #080b16, con un tocco di azzurro ghiaccio #96beff.
- Terminale: #0c0d10, con schede #18191e.
- Quaderno: #f4f2ec, con quadretti #d6dade.
- Verde #46c878, rosso #e0483e.

Font:
- titoli: Anton;
- corsivo elegante: Instrument Serif Italic;
- sottotitoli: Barlow Condensed;
- dati e app: JetBrains Mono e Inter;
- note a mano: Caveat, solo nel Quaderno.

## Sempre / mai
- Sempre: @yard.fx (col punto) in chiusura; "Contenuto informativo. Il trading comporta rischi." piccolo in basso.
- Sempre: voce «salvatore» di Speechify generata da Claude (`Y.voice_speechify`, README sezione 2). Ogni tanto, senza strafare, cambia qualcosina prendendo spunto dalla libreria (README sezione 6): lo stile attuale piace.
- Sempre, chiarezza prima di tutto (richiesta di Salvatore del 18/11, dopo la Strategia #5 «che non spiega nulla»): voce e scritte precise e complete, così chi guarda può provarlo subito sul grafico.
  - Termini tecnici giusti (time frame H1/M15, time frame operativo, EMA 50, trend rialzista/ribassista, massimi e minimi crescenti/decrescenti, ritracciamento, tocco, rifiuto con lo spike, chiusura della candela, buy, sell, stop loss, take profit, laterale), spiegati in parole semplici la prima volta.
  - Nelle strategie, passo per passo: time frame della direzione e time frame dell'entrata (e perché sono collegati); come si riconosce il trend; cosa deve fare il prezzo esattamente per entrare (es. la candela M15 tocca l'EMA 50 e la rifiuta con lo spike senza chiudere oltre); BUY e SELL ognuno con condizioni, stop loss e take profit; quando NON si opera.
  - Mai frasi vaghe («guardo l'ora» → «guardo il time frame H1»). Strategie di circa 50-65 secondi: meglio chiaro che corto.
- Sempre, appena un contenuto è pubblicato o programmato: segnalo come FATTO nel calendario del mese (artifact «Calendario YardFX», `done:true` sul giorno, poi ripubblica). Il giorno appare barrato con l'etichetta «✓ FATTO».
- Sempre, quando un contenuto è preparato il giorno prima: scrivilo e montalo come se fosse il giorno di uscita indicato nel prompt (date, «oggi», «domani», «ieri», news, orari e prezzi riferiti a quel giorno) e programmalo per quel giorno.
- Sempre, nei contenuti di strategia:
  - spiega l'ACQUISTO e poi rispiega la VENDITA con le sue condizioni, il suo stop e il suo obiettivo (mai solo "per vendere, il contrario");
  - quando mostri la trappola, spiega anche come evitarla con una regola pratica. Dettagli in `yardfx_video/README.md`, sezione 3f.
- Mai:
  - barra del tempo in alto;
  - pillola "YARDFX · XAUUSD";
  - statuetta 3D;
  - screenshot incollati;
  - loghi, musiche o foto di altri creator;
  - la frase sulla "prima candela" ripetuta ogni volta.

## Catalogo elementi e ricette per formato
Sono in `yardfx_video/README.md`. I formati coperti sono: news, reazione, anteprima, recap/journal, lezione, mindset, meme e carosello.

## Video modello analizzati (9 nov 2026)
r601 quaderno disegnato · v1 icone cinematografiche · v2 interfacce e timbri · v3 capitoli numerati e tendina circolare ·
v4 numeri luminosi e linea del tempo · v5 contatori e capitoli · v6 trading educativo con zone e banner · v7 pulito editoriale.
