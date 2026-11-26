"""
Mostra i risultati del registro di verifica.

    python report.py            -> tutto lo storico
    python report.py --giorni 7 -> solo gli ultimi 7 giorni
"""
import argparse

from journal import Journal, format_stats

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--giorni", type=int, default=None)
    a = p.parse_args()
    title = f"Registro Kronos - ultimi {a.giorni} giorni" if a.giorni else "Registro Kronos - tutto"
    print(format_stats(Journal().stats(days=a.giorni), title))
