"""Test del captcha. Avvio: python tests/test_captcha.py"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import captcha  # noqa: E402

rng = random.Random(1)

# Sfida: 6 pulsanti diversi, quello giusto e' tra loro
s = captcha.nuova_sfida(1000, 180, 2, rng)
assert len(s.opzioni) == 6 and len(set(s.opzioni)) == 6
assert 0 <= s.corretta < 6 and s.scadenza == 1180
etichette = captcha.etichette_pulsanti(s)
assert etichette[s.corretta] == s.oggetto[0]

# La domanda contiene la PAROLA (it + en), non l'emoji da cercare
testo = captcha.testo_domanda(s, "Sala Elite", 180)
assert s.oggetto[1] in testo and s.oggetto[2] in testo
assert s.oggetto[0] not in testo
assert "Sala Elite" in testo and "3 minuti" in testo
assert "Hai 60 secondi" in captcha.testo_domanda(s, "", 60)
assert "Hai 90 secondi" in captcha.testo_domanda(s, "", 90)

# Risposta giusta
assert captcha.rispondi(s, s.corretta, 1010) == "ok"

# Sbagliata: prima 'sbagliato' (puo' riprovare), poi 'fallito'
s = captcha.nuova_sfida(1000, 180, 2, rng)
sbagliato = (s.corretta + 1) % 6
assert captcha.rispondi(s, sbagliato, 1010) == "sbagliato"
assert captcha.rispondi(s, sbagliato, 1020) == "fallito"

# Un solo tentativo
s = captcha.nuova_sfida(1000, 180, 1, rng)
assert captcha.rispondi(s, (s.corretta + 1) % 6, 1010) == "fallito"

# Tempo scaduto: anche la risposta giusta non vale
s = captcha.nuova_sfida(1000, 180, 2, rng)
assert captcha.rispondi(s, s.corretta, 1181) == "scaduto"

# Elenco delle sfide scadute
sfide = {(1, -100): captcha.nuova_sfida(1000, 60, 2, rng), (2, -100): captcha.nuova_sfida(1000, 600, 2, rng)}
assert captcha.scadute(sfide, 1100) == [(1, -100)]
assert captcha.scadute(sfide, 1000) == []

# Nomi univoci (nessuna parola uguale per due emoji)
assert len({o[1] for o in captcha.OGGETTI}) == len(captcha.OGGETTI)
assert len({o[0] for o in captcha.OGGETTI}) == len(captcha.OGGETTI)

print("test_captcha: OK")
