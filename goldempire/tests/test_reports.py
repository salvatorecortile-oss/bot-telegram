"""Test di orari e contenuto di report e buongiorno. Avvio: python tests/test_reports.py"""
import os
import sys
import tempfile
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db  # noqa: E402

db.set_db_path(os.path.join(tempfile.mkdtemp(), "r.db"))
db.init_database()

import reports  # noqa: E402

TZ = reports.ITALY_TZ


def at(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def kinds(now):
    return sorted(k for _, k, _ in reports.due_messages(now))


# --- Orari (ottobre 2026: venerdi' 16, sabato 17, sabato 31 = ultimo giorno) ---
assert kinds(at(2026, 10, 16, 5, 59)) == []
assert kinds(at(2026, 10, 16, 6, 0)) == ["morning"]
assert kinds(at(2026, 10, 16, 23, 0)) == ["daily"]
assert kinds(at(2026, 10, 17, 6, 0)) == []                 # sabato: niente buongiorno
assert kinds(at(2026, 10, 17, 10, 0)) == ["weekly"]
assert kinds(at(2026, 10, 17, 23, 0)) == []                # sabato: niente giornaliero
assert kinds(at(2026, 10, 31, 23, 0)) == ["monthly"]       # ultimo giorno (sabato)
assert kinds(at(2026, 9, 30, 23, 0)) == ["daily", "monthly"]  # ultimo giorno (mercoledi')
assert kinds(at(2026, 10, 16, 9, 30)) == []                # buongiorno troppo in ritardo: saltato
assert kinds(at(2026, 10, 16, 8, 30)) == ["morning"]       # PC acceso tardi: entro 3 ore parte

# --- Contenuto report ---
def add_closed(mid, status, pips, closed_local):
    db.insert_signal(mid, {"direction": "SELL", "entry": 1, "sl": 2, "tp": 0.5})
    db.mark_opened(mid, None, 1, 0.01, 2, 0.5)
    db.claim_close(mid, status, 1, pips)
    with db.get_connection() as conn:
        conn.execute("UPDATE signals SET closed_at = ? WHERE source_message_id = ?",
                     (closed_local.astimezone(reports.timezone.utc).isoformat(), mid))

add_closed(1, "CLOSED_TP", 352.4, at(2026, 10, 12, 11))      # lunedi'
add_closed(2, "CLOSED_SL", -241.6, at(2026, 10, 16, 8))      # venerdi'
add_closed(3, "CLOSED_MANUAL", 308.2, at(2026, 10, 16, 19))  # venerdi'
add_closed(4, "CLOSED_BE", 2.0, at(2026, 10, 16, 23, 30))    # venerdi' dopo il report
add_closed(5, "CLOSED_TP", 100.0, at(2026, 9, 30, 12))       # mese precedente

daily = reports.daily_report_text(date(2026, 10, 16))
assert "16/10/2026" in daily and "Operazioni chiuse: 3" in daily, daily
assert "Operazioni ancora aperte: 0" in daily, daily
db.insert_signal(99, {"direction": "BUY", "entry": 1, "sl": 0.5, "tp": 2})
db.mark_opened(99, None, 1, 0.01, 0.5, 2)
assert "Operazioni ancora aperte: 1" in reports.daily_report_text(date(2026, 10, 16))
assert "Operazioni ancora aperte: 1" in reports.weekly_report_text(date(2026, 10, 17))
assert "Operazioni ancora aperte: 1" in reports.monthly_report_text(date(2026, 10, 31))
assert "✅ Vincenti: 1" in daily and "❌ Perse: 1" in daily and "TOT +69 PIPS" in daily, daily

weekly = reports.weekly_report_text(date(2026, 10, 17))
assert "12 OTT - 16 OTT" in weekly and "Operazioni chiuse: 4" in weekly, weekly
assert "Win Rate: 50.0%" in weekly and "TOT +421 PIPS" in weekly, weekly

monthly = reports.monthly_report_text(date(2026, 10, 31))
assert "1 OTT - 31 OTT" in monthly and "Operazioni chiuse: 4" in monthly, monthly

assert not db.was_sent("daily:2026-10-16")
db.mark_sent("daily:2026-10-16")
assert db.was_sent("daily:2026-10-16")

print("OK - test report e orari superati.")
print(daily)
