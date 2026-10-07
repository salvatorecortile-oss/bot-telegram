"""
Redattore AI (Claude).

Il filtro a parole chiave fa una prima scrematura (gratis). Le notizie che
passano vengono mandate a Claude, che per ognuna:
- dà un voto di importanza da 1 a 10 per la community (oro, macro, geopolitica)
- scrive titolo e breve testo in italiano
- se è chiaro, indica il possibile impatto sull'oro
- segnala i doppioni di notizie già pubblicate

Serve una chiave API di Anthropic (console.anthropic.com) nel file .env.
"""
import json
import logging

import anthropic

import config

log = logging.getLogger("news_bot")

SYSTEM_PROMPT = """Sei il redattore delle notizie del canale Telegram "YardFX Community", \
una community italiana di trader che opera soprattutto sull'oro (XAUUSD).

Ricevi una lista di titoli di notizie appena uscite (in inglese, da agenzie e testate \
internazionali). Per ognuna decidi quanto è importante per la community e scrivila in italiano.

Voto di importanza (1-10):
- 9-10: eventi che muovono subito i mercati o sono di portata mondiale. Esempi: decisione \
della Fed o della BCE sui tassi, dato CPI o payrolls USA molto diverso dalle attese, oro a \
record storico o movimento violento dell'oro, inizio o forte escalation di una guerra, \
attacchi tra potenze (USA, Russia, Cina, Iran, Israele, NATO), golpe, crolli bancari, \
nuovi dazi pesanti di USA o Cina.
- 7-8: notizie importanti ma non urgenti (dichiarazioni rilevanti di Powell/Lagarde, \
sviluppi significativi di conflitti in corso, dati macro importanti in linea con le attese).
- 1-6: tutto il resto. Dai voti bassi a: articoli "in attesa di..." (preview), commenti e \
analisi, opinioni, spiegoni, notizie locali, risultati di singole aziende, banche centrali \
minori, cronaca, notizie vecchie o di contorno.

Sii severo: nella maggior parte dei casi il voto deve essere 6 o meno. \
Solo poche notizie al giorno meritano 9-10.

Per ogni notizia scrivi:
- titolo: titolo in italiano, chiaro e breve (massimo 15 parole), senza clickbait
- testo: 1-2 frasi in italiano che spiegano la notizia. Usa solo le informazioni presenti \
nel titolo e nel riassunto: non inventare numeri, nomi o dettagli
- impatto_oro: una frase breve sul possibile effetto sull'oro, solo se è ragionevolmente \
chiaro (es. "Possibile spinta al rialzo: aumenta la domanda di beni rifugio"). \
Altrimenti stringa vuota. Non dare consigli di trading
- categoria: "oro", "macro", "geopolitica" oppure "mondo"
- doppione: true se racconta lo stesso fatto di una notizia nella lista "già pubblicate"
"""

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "importanza": {"type": "integer"},
        "categoria": {"type": "string", "enum": ["oro", "macro", "geopolitica", "mondo"]},
        "titolo": {"type": "string"},
        "testo": {"type": "string"},
        "impatto_oro": {"type": "string"},
        "doppione": {"type": "boolean"},
    },
    "required": ["id", "importanza", "categoria", "titolo", "testo", "impatto_oro", "doppione"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"notizie": {"type": "array", "items": ITEM_SCHEMA}},
    "required": ["notizie"],
    "additionalProperties": False,
}


class AIEditor:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=3)

    def evaluate(self, infos, already_sent_titles):
        """
        infos: lista di storie (dict di NewsEngine.story_info).
        Ritorna {story_id: risultato} oppure None se la chiamata non riesce.
        """
        if not infos:
            return {}
        notizie = [
            {
                "id": info["story_id"],
                "titolo": info["title"],
                "riassunto": info["summary"] or "",
                "fonte": info["source"],
                "numero_fonti": info["num_sources"],
            }
            for info in infos
        ]
        user_content = (
            "Già pubblicate nelle ultime 12 ore:\n"
            + json.dumps(already_sent_titles, ensure_ascii=False)
            + "\n\nNotizie da valutare:\n"
            + json.dumps(notizie, ensure_ascii=False)
        )
        try:
            response = self.client.beta.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={
                    "effort": config.CLAUDE_EFFORT,
                    "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
                },
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.AuthenticationError:
            log.error("Chiave ANTHROPIC_API_KEY non valida.")
            return None
        except anthropic.APIStatusError as exc:
            log.error("Errore API Claude (%s): %s", exc.status_code, exc.message)
            return None
        except anthropic.APIConnectionError:
            log.error("Claude non raggiungibile (problema di rete).")
            return None

        if response.stop_reason in ("refusal", "max_tokens"):
            log.warning("Claude non ha completato la valutazione (%s).", response.stop_reason)
            return None
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.error("Risposta di Claude non leggibile.")
            return None

        usage = response.usage
        log.info("Claude ha valutato %d notizie (token: %d in, %d out).",
                 len(infos), usage.input_tokens, usage.output_tokens)
        valid_ids = {info["story_id"] for info in infos}
        return {
            item["id"]: item for item in data.get("notizie", []) if item.get("id") in valid_ids
        }
