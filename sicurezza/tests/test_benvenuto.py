"""Test del messaggio di benvenuto. Avvio: python tests/test_benvenuto.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import benvenuto  # noqa: E402

cartella = tempfile.mkdtemp()
file = os.path.join(cartella, "benvenuto.txt")

# File mancante -> nessun messaggio
assert benvenuto.testo_benvenuto(file) is None

# File vuoto o solo note (#) -> nessun messaggio
open(file, "w", encoding="utf-8").write("# solo una nota\n\n   \n")
assert benvenuto.testo_benvenuto(file) is None

# Testo con segnaposto, a capo, emoji e note
open(file, "w", encoding="utf-8").write(
    "# nota da non mandare\nCiao {nome}, benvenuto in {chat}! 🔥\n\nScrivimi: @mionome\n")
assert benvenuto.testo_benvenuto(file, "Mario", "YardFX | COMMUNITY 🔥") == \
    "Ciao Mario, benvenuto in YardFX | COMMUNITY 🔥! 🔥\n\nScrivimi: @mionome"

# Nome mancante -> segnaposto vuoto, altre graffe lasciate come sono
open(file, "w", encoding="utf-8").write("Ciao {nome}! {altro}")
assert benvenuto.testo_benvenuto(file) == "Ciao ! {altro}"

# File salvato dal Blocco note con BOM
open(file, "w", encoding="utf-8-sig").write("Benvenuto!")
assert benvenuto.testo_benvenuto(file) == "Benvenuto!"

# Il file di esempio funziona
esempio = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benvenuto.esempio.txt")
t = benvenuto.testo_benvenuto(esempio, "Mario", "Community")
assert t.startswith("Ciao Mario, benvenuto in Community!") and "#" not in t

print("test_benvenuto: OK")
