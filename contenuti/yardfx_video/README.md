# Kit video YardFX — procedura di montaggio

Kit grafico: `yardfx.py` (`import yardfx as Y`). Font in `fonts/` (tutti OFL). Candele di prova in `candele_esempio.json`.
Stile: `../GUIDA_STILE_YARDFX.md`. Libreria dei video modello: https://claude.ai/artifact/6yztDxv7dCxcrsRM5jqtHc

Quando Salvatore incolla un prompt del calendario, segui questi passi. Lui lavora e non risponde: non fermarti a chiedere.

## 1. Script
- Paragrafi brevi separati da una riga vuota. Ogni paragrafo diventa una scena.
- La prima frase è il gancio, con il dato o la frase più forte.
- Numeri scritti in lettere per la voce ("quattromila e cento").
- Nessuna previsione certa: usa "di solito".

## 2. Voce: la registra SEMPRE Salvatore con Enea
- Manda lo script in chat dentro un blocco da copiare, poi **fermati** e aspetta il suo MP3, registrato su ElevenLabs con la voce Enea.
- **Mai** generare la voce da solo e mai usare voci gratuite o altre voci, nemmeno come bozza.
- Quando arriva l'MP3, ricava i tempi parola per parola con `Y.words_from_whisper('voce.mp3')`. Ogni scena cambia sulla prima parola del suo paragrafo (`Y.find_word`).

## 3. Storyboard (scrivilo prima del codice)
Per ogni scena indica:
- il **mondo**;
- il capitolo (candeline n/tot + nome a mano);
- l'**elemento protagonista**;
- la parola della voce che lo fa comparire;
- le parole chiave dei sottotitoli.

### I 3 mondi: ogni video ne alterna almeno 2, di solito 3
| Mondo | Ispirato a | Fondo | Per cosa |
|---|---|---|---|
| **NOTTE** | video 1 + 4 | `night_bg` (blu notte, raggi, costellazione, griglia di particelle) | gancio, numeri grandi, settimana, chiusura |
| **TERMINALE** | video 2 + 5 + 6 | `term_bg` (grafite con griglia a punti) + `price_widget` fisso in alto a destra | dati, calendario economico, grafici, trade, setup |
| **QUADERNO** | r601 + video 3 | `grid_paper` (carta a quadretti) | spiegare il perché, regole, errori, mindset |

Extra da usare 1 volta al massimo:
- `yellow_bg` (blocco giallo) per il colpo di scena;
- `cream_bg` per un mindset.

Cambio di mondo: sempre con `circle_wipe` (0,4 s).

### Firme fisse, in tutti i mondi
- `chapter_candles` (al posto della barra del tempo).
- `captions` parola per parola con la parola chiave nel riquadro oro.
- `gold_candle` in apertura e/o chiusura.
- `disclaimer`.
- Mai: barra del tempo, pillola "YARDFX · XAUUSD", statuetta/pupazzo 3D, screenshot incollati, loghi, musiche o foto di altri creator.

### Catalogo degli elementi
| Elemento | Funzione | Mondo | Usalo per |
|---|---|---|---|
| Titolo misto corsivo + bastone | `mixed_title`, `serif_heading` | tutti | ganci, titoli dei capitoli |
| Numero luminoso / che conta / che rotola | `glow_text`, `big_counter`, `number_roll` | Notte | il dato, il totale pips, l'orario |
| Faretto + icona luminosa | `spotlight`, `glow_icon` | Notte | l'oggetto del video (orologio, banca, lingotto) |
| Linea del tempo a nodi | `timeline_nodes` | Notte | settimana, giorni dei dati |
| Settimana a schede | `week_strip` | Notte/Terminale | anteprime, recap per giorno |
| Scheda app in prospettiva + lente | `ui_card`, `perspective`, `map_point`, `zoom_callout` | Terminale | calendario economico, conto MT5 |
| Widget prezzo | `price_widget` | Terminale | sempre visibile nelle scene Terminale |
| Etichetta ✓/✕ | `chip` | Terminale | sopra/sotto le attese, giusto/sbagliato |
| Barre scenario | `prob_bars` | Terminale | due scenari (se alto / se basso) |
| Quadrante a segmenti | `dial` | Notte/Terminale | rischio, volatilità, % del conto |
| Grafico con zone e livelli | `candles_chart` | Terminale | livelli, setup, trade (candele vere) |
| Smartphone inclinato | `phone` | Terminale | mostrare un grafico o un'app "dal telefono" |
| Scheda trade | `trade_card` | Terminale | recap, journal |
| Curva cumulata | `equity_curve` | Notte/Terminale | pips della settimana/mese |
| Notifica | `notification` | Notte/Terminale | "Take profit raggiunto", "CPI uscito" |
| Banner risultato | `banner` | Terminale | TAKE PROFIT / STOP PRESO |
| Checklist | `checklist` | tutti | piano, regole, errori |
| Catena causa → effetto | `chain` (a mano) / `glow_icon` + `dashed_arrow` | Quaderno / Notte | perché l'oro si muove |
| Barrato → nuovo valore | `strike_swap` | Quaderno | prima/dopo, atteso/uscito |
| Timbro | `stamp` | tutti | verdetti |
| Cerchio, freccia, sottolineato, evidenziatore | `circle`, `arrow`, `dashed_arrow`, `underline`, `marker` | Quaderno | indicare |
| Scrittura a mano | `hand` | Quaderno (poco negli altri) | note, commenti |
| Citazione | `quote` | Quaderno/Notte | mindset |
| Meme a due metà + scossa | `split_meme`, `shake` | tutti | meme "io alle 14:29 / 14:31" |
| Sondaggio | `poll` | Notte | chiusura "sopra o sotto?" |
| Fumetto commento | `comment_cta` | tutti | "commenta GUIDA" |
| Scheda profilo | `follow_card` | Notte | chiusura alternativa a `outro` |

### Regole del mix
- Almeno **5 elementi diversi** del catalogo per video, mai lo stesso protagonista in due scene di fila.
- Prima di scegliere, guarda gli ultimi video fatti (cartelle della sessione o storico Zernio): **non ripetere la stessa sequenza**.
- Il primo fotogramma (t=0) mostra già il gancio in grande, senza fade da nero.
- Ogni scena ha un movimento: tratto che si disegna, scheda che entra, numero che conta, zoom. Niente fermo immagine oltre 2 s.
- I sottotitoli stanno a y=1585 (sotto la grafica); se la scena usa quell'area, spostali (`y=1720`).
- Grafici: candele vere, dai suoi screenshot o dai prezzi trovati sul web. Se illustrative: "esempio didattico".

## 3a. VOCE = SCHERMO (regola fissa)
- **Ogni parola scritta a schermo deve essere detta dalla voce**, e compare nel momento in cui viene detta (`Y.find_word`).
- Scrivi lo script partendo dalle scritte delle scene, poi controlla che non ci sia nessuna scritta che la voce non dice.
- Le uniche eccezioni sono il disclaimer piccolo e il widget del prezzo.
- I nomi dei capitoli accanto alle candeline vanno usati solo se la voce li dice, altrimenti lascia solo le candeline.
- **Sottotitoli** (`Y.captions_pop`) sempre visibili, grandi e chiari per tutto il video, per chi guarda senza audio.
- Si tolgono solo durante la chiusura con i 4 paletti (`Y.cta_four`), dove le scritte animate fanno già da sottotitolo: passa `end=` uguale al tempo della prima parola della chiusura.

## 3b. MOVIMENTO, MUSICA ED EFFETTI (obbligatori: un video fermo è da rifare)
Niente sta fermo. Questi movimenti vengono dai video modello (vedi la libreria):
- **Entrate con rimbalzo**: ogni oggetto va disegnato dentro `Y.sprite(img, fn, t, t0, enter=..., idle=...)`.
  - `enter`: pop, drop, rise, left, right, spin, stamp.
  - `idle`: float, breathe, wobble, sway. Dopo l'entrata l'oggetto galleggia, pulsa o oscilla **sempre**.
- **Testo sfocato → nitido**: `Y.blur_in` (video 7, r601). Testo che si scrive con il cursore: `Y.type_text` (video 2, 4). Numeri che contano: `Y.count_text`, `Y.big_counter`, `Y.number_roll` (video 5).
- **Sfondi vivi**:
  - `Y.dust` (polvere che sale);
  - `Y.light_beams` (fasci di luce, video 1);
  - `Y.light_sweep` (luce diagonale);
  - `Y.pulse_rings` (onde dietro l'oggetto, video 1 e 7);
  - `Y.clock_hands` (lancette che girano);
  - schede in 3D che entrano ruotando con `Y.card_flip_quad` (video 4).
- **Camera**: `Y.camera(img, t, inizio_scena, punches=[...], shakes=[...])` su ogni scena. Spinge sempre piano in avanti e deriva, dà un colpo di zoom sulle parole chiave e una scossa su timbri e numeri forti.
- **Lampi**: `Y.flash` (bianco) e `Y.color_flash` (oro, rosso o verde) sulla parola più forte di ogni scena (video 2).
- **Transizioni**, mai due uguali di fila:
  - `whip` e `whip_v`: strisciate con scia (video 4);
  - `blur_cross` (video 7);
  - `zoom_through`;
  - `circle_wipe`.
- **Sottotitoli**: `Y.captions_pop`. Le parole saltano dentro, la chiave arriva nel riquadro oro che si allarga.
- **Audio** (`suoni.py`, tutto generato da zero, senza copyright):
  - `S.music(...)` crea la base musicale. Mood: tensione (news negative), positivo (recap verdi), calmo (mindset).
  - `S.mix(out, durata, voce=MP3 di Salvatore, musica=..., eventi=[(t,'pop'), ...])` abbassa la musica sotto la voce (sidechain) e normalizza a −14 LUFS.
  - Ogni comparsa ha il suo effetto:

    | Cosa succede | Effetto |
    |---|---|
    | entrata | pop / pop_hi / bubble |
    | cambio scena | whoosh, swipe, swoosh_up |
    | timbro | stamp |
    | numero forte | boom (+ glitch) |
    | dato giusto, livello | ding / trin / coin |
    | notifica, chip ✕ | alert |
    | scrittura e numeri che contano | click / tick |
    | prima di una rivelazione | riser |

  - In un video da 40 s ci vogliono almeno 60 effetti.
- **Render**: usa `multiprocessing.Pool(4)` per i fotogrammi (vedi esempio in `esempi/cpi_animato.py`): il video muto, poi `S.mix` e l'unione.

## 3c. CALL TO ACTION: sempre i 4 paletti
Ogni video, carosello e didascalia chiude chiedendo di:
1. **SEGUIRE** il profilo;
2. lasciare un **MI PIACE**;
3. **COMMENTARE** con una parola o una domanda legata al video (es. "commenta STRATEGIA", "scrivi SOPRA o SOTTO");
4. **CONDIVIDERE** il video (con chi sta iniziando, con l'amico che fa trading…).

- Le parole cambiano da video a video, ma i 4 paletti ci sono sempre. Nella voce sono l'ultima frase.
- A schermo usa `Y.cta_four(img, t, [t_segui, t_mipiace, t_commenta, t_condividi], 'PAROLA')`: i 4 tempi sono le parole della voce. Effetti sonori: pop, pop_hi, bubble, swoosh_up, più coin sull'ultimo.
- Se c'è spazio, aggiungi "scrivimi in DM per entrare nella community".

## 3d. CHIUSURA FISSA: logo + Telegram
Dopo la call to action con i 4 paletti:
1. `Y.logo_reveal(img, t, t0, W//2, 700, 400)`: il logo di Salvatore (`logo_yardfx.png`, già senza sfondo), non in grande. Entra ruotando con rimbalzo, alone oro e riflesso di luce, poi galleggia.
2. `Y.telegram_cta(img, t, t0 + 1.15, 1150)`: l'aereo di carta di Telegram vola dentro con la scia, poi compaiono "CERCAMI SU TELEGRAM" e @yard.fx come un timbro.

- Effetti sonori: boom, whoosh, trin sul riflesso, whoosh sull'aereo, pop, stamp e coin.
- Allunga la durata di circa 4 s dopo la voce.
- Il logo va anche in piccolo sulla **copertina**, che deve essere diversa dal primo fotogramma.
- **Candeline dei capitoli**: non metterle, a meno che abbiano un senso preciso detto dalla voce (es. numero della puntata).
- Esempio completo: `esempi/strategia1_rsi.py`.

## 4. Ricette per formato (mondi in ordine)
| Formato | Sequenza dei mondi | Elementi suggeriti | Durata |
|---|---|---|---|
| Notizia / dato macro | Notte → Terminale → Quaderno → Notte | orario luminoso + timeline; calendario in prospettiva + lente + chip; catena del perché + timbro; poll o outro | 30-40 s |
| Reazione al dato | Notte → Terminale → Quaderno → Notte | number_roll del dato uscito; strike atteso → uscito + chip; grafico ricostruito con freccia e banner; cosa guardare adesso | 25-35 s |
| Anteprima settimana | Notte → Terminale → Notte | timeline/week_strip; ui_card dei dati della settimana; grafico con livelli; follow_card | 25-30 s |
| Recap / journal | Notte → Terminale → Quaderno → Notte | big_counter pips; trade_card (stop compresi) + notification; equity_curve; lezione in checklist o quote | 35-45 s |
| Strategia base / lezione | Quaderno → Terminale → Notte | serif_heading numerati; phone con grafico + zone; dial del rischio; checklist | 40-60 s |
| Mindset | Quaderno (o crema) → Notte | quote; strike_swap; checklist; gold_candle in chiusura; `music_pad` | 10-15 s |
| Meme | split_meme + shake | stamp, scrittura a mano, grafico che crolla; `music_pad` | 8-12 s |
| Carosello (slide 1080x1350) | alterna Quaderno e Notte, slide dati in Terminale | stessi elementi, candeline = numero della slide, comment_cta sull'ultima | 6 slide |

## 5. Controllo e render
1. Guarda `Y.contact_sheet` con un fotogramma per scena, più t=0 e la chiusura. Correggi testi sovrapposti, tagliati o in conflitto con i sottotitoli.
2. Fai il render con `Y.render(frame, durata_voce + 2.5, 'voce.mp3', 'video.mp4')`. Per mindset e meme usa `Y.music_pad(durata, 'base.m4a')` come audio.
3. Fai la copertina 1080x1920 con le scritte nella fascia centrale.
4. Manda tutti i file in chat e pubblica con Zernio, come chiede il prompt.
