# Kit video YardFX — procedura di montaggio

Kit grafico: `yardfx.py` (font in `fonts/`, candele di prova in `candele_esempio.json`).
Stile e ricette: `../GUIDA_STILE_YARDFX.md`. Libreria dei video modello: https://claude.ai/artifact/6yztDxv7dCxcrsRM5jqtHc

Quando Salvatore incolla un prompt del calendario, segui questi passi. Lui lavora e non risponde: non fermarti a chiedere.

## 1. Script
- Paragrafi brevi separati da una riga vuota. Ogni paragrafo diventa una scena.
- La prima frase è il gancio, con il dato o la frase più forte.
- Numeri scritti in lettere per la voce ("quattromila e cento").
- Nessuna previsione certa: usa "di solito".
- Chiusura: domanda da commentare oppure "seguimi e scrivimi in DM". La chiusura fissa è `Y.outro`.

## 2. Voce e tempi parola per parola
- Se Salvatore carica un MP3: `Y.words_from_whisper('voce.mp3')`.
- Altrimenti: `Y.tts_elevenlabs(testo, 'voce.mp3')`. Enea richiede il piano a pagamento; con il piano gratuito usa George (default).
- Controlla le pause tra i paragrafi: ogni scena cambia sulla prima parola del paragrafo (`Y.find_word`).

## 3. Storyboard (scrivilo prima del codice)
Per ogni scena indica:
- fondo (scuro, carta o giallo);
- capitolo (candeline n/tot + nome a mano);
- 1 elemento protagonista;
- la parola della voce che lo fa comparire;
- le parole chiave nei sottotitoli.

Regole del mix:
- Almeno 4 elementi diversi del kit per video, mai lo stesso elemento in due scene di fila.
- Alterna i fondi seguendo la ricetta del formato. Usa la tendina circolare (`Y.circle_wipe`, 0,4 s) per i cambi di fondo.
- Il primo fotogramma (t=0) mostra già il gancio in grande: niente fade da nero.
- Ogni scena ha un movimento: tratto che si disegna, testo che entra, numero che conta. Niente schermate ferme per più di 2 s.
- I sottotitoli sono sempre attivi (`Y.captions`), con 1 parola chiave ogni 2-3 gruppi, e stanno sotto la grafica (y=1585): non sovrapporli.
- Grafici sempre ridisegnati con `Y.candles_chart`, mai screenshot. Usa candele vere: dai suoi screenshot, oppure dai dati di prezzo trovati sul web. Se le candele sono illustrative, scrivi "esempio didattico".

| Elemento | Funzione | Quando |
|---|---|---|
| Candela d'oro | `gold_candle` | apertura, chiusura |
| Numero luminoso / contatore | `glow_text`, `big_counter` | il dato o il totale |
| Catena causa → effetto | `chain` + `ICONS` | spiegare perché l'oro si muove |
| Barrato → nuovo valore | `strike_swap` | dato precedente vs attuale |
| Timbro | `stamp` | il verdetto ("SOPRA LE ATTESE", "STOP PRESO") |
| Riquadro oro | `key_box` | la parola/frase da ricordare |
| Cerchio, freccia, sottolineato, evidenziatore | `circle`, `arrow`, `underline`, `marker` | indicare un punto |
| Scrittura a mano | `hand` | commenti, note, sottotitoli di sezione |
| Settimana a schede | `week_strip` | anteprime, recap |
| Grafico con zone/livelli | `candles_chart` | livelli, setup, trade |
| Banner risultato | `banner` | TAKE PROFIT / STOP |
| Checklist | `checklist` | piano, regole, errori |

## 4. Controllo e render
1. Guarda `Y.contact_sheet` con un fotogramma per scena, più t=0 e la chiusura. Correggi testi sovrapposti, tagliati o in conflitto con i sottotitoli.
2. Fai il render con `Y.render(frame, durata_voce + 2.5, 'voce.mp3', 'video.mp4')`.
3. Fai la copertina 1080x1920 con le scritte nella fascia centrale (1080x1350 visibile nella griglia Instagram).
4. Manda tutti i file in chat (video, copertina, MP3) e pubblica con Zernio, come chiede il prompt.

## Per mindset e meme (senza voce)
- Musica: `Y.music_pad(durata, 'base.m4a')`.
- Testo grande in 2-3 battute.
- Durata 8-15 s.
