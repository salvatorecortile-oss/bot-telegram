"""
Report giornaliero / settimanale / mensile e buongiorno (orari Europe/Rome).

- Buongiorno: lun-ven alle 06:00
- Giornaliero: lun-ven alle 23:00 (operazioni chiuse oggi)
- Settimanale: sabato alle 10:00 (operazioni chiuse da lunedi')
- Mensile: ultimo giorno del mese alle 23:00 (operazioni chiuse dal giorno 1)
"""
import calendar
from datetime import datetime, time, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    ITALY_TZ = ZoneInfo("Europe/Rome")
except Exception:  # Windows senza il pacchetto tzdata
    ITALY_TZ = None

import database as db
from messages import (
    DAILY_REPORT_TEMPLATE,
    MONTHLY_REPORT_TEMPLATE,
    WEEKLY_REPORT_TEMPLATE,
)

# Come gli altri bot: un'operazione chiusa a BE (o quasi a zero) non conta
# ne' come vincente ne' come persa, ma i suoi pips restano nel totale.
_MIN_PIPS_RESULT = 1.0

_MONTHS = {1: "GEN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAG", 6: "GIU",
           7: "LUG", 8: "AGO", 9: "SET", 10: "OTT", 11: "NOV", 12: "DIC"}

# Se il PC era spento all'orario previsto, il messaggio parte comunque
# entro questa finestra; oltre viene saltato (niente report "vecchi").
LATE_WINDOW = timedelta(hours=3)


def now_italy():
    return datetime.now(ITALY_TZ) if ITALY_TZ else datetime.now().astimezone()


def _local_midnight(day):
    naive = datetime.combine(day, time(0, 0))
    return naive.replace(tzinfo=ITALY_TZ) if ITALY_TZ else naive.astimezone()


def _fmt_day(day):
    return f"{day.day} {_MONTHS[day.month]}"


def _stats(rows):
    operations = len(rows)
    wins = sum(1 for r in rows if r["status"] != "CLOSED_BE" and r["pips"] > _MIN_PIPS_RESULT)
    losses = sum(1 for r in rows if r["status"] != "CLOSED_BE" and r["pips"] < -_MIN_PIPS_RESULT)
    return {
        "operations": operations,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / operations * 100.0) if operations else 0.0,
        "pips": sum(r["pips"] for r in rows),
        # Operazioni ancora aperte al momento del report.
        "open_operations": len(db.get_open_signals()),
    }


def _rows(start_day, end_day_exclusive):
    start = _local_midnight(start_day).astimezone(timezone.utc)
    end = _local_midnight(end_day_exclusive).astimezone(timezone.utc)
    return db.get_closed_between(start, end)


def daily_report_text(day):
    stats = _stats(_rows(day, day + timedelta(days=1)))
    return DAILY_REPORT_TEMPLATE.format(date=day.strftime("%d/%m/%Y"), **stats)


def weekly_report_text(day):
    """Settimana (lunedi'-venerdi') che contiene `day`; se e' weekend, quella appena finita."""
    monday = day - timedelta(days=day.weekday())
    friday = monday + timedelta(days=4)
    stats = _stats(_rows(monday, monday + timedelta(days=7)))
    return WEEKLY_REPORT_TEMPLATE.format(date_range=f"{_fmt_day(monday)} - {_fmt_day(friday)}", **stats)


def monthly_report_text(day):
    first = day.replace(day=1)
    last = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    stats = _stats(_rows(first, last + timedelta(days=1)))
    return MONTHLY_REPORT_TEMPLATE.format(date_range=f"{_fmt_day(first)} - {_fmt_day(last)}", **stats)


def due_messages(now):
    """
    Messaggi programmati da inviare adesso: lista di (chiave, tipo, giorno).
    La chiave serve a non inviarli mai due volte (anche dopo un riavvio).
    """
    today = now.date()
    weekday = today.weekday()  # 0 = lunedi'
    last_day = calendar.monthrange(today.year, today.month)[1]
    schedule = []
    if weekday < 5:
        schedule.append(("morning", time(6, 0)))
        schedule.append(("daily", time(23, 0)))
    if weekday == 5:
        schedule.append(("weekly", time(10, 0)))
    if today.day == last_day:
        schedule.append(("monthly", time(23, 0)))

    due = []
    for kind, at in schedule:
        target = datetime.combine(today, at, tzinfo=now.tzinfo)
        if target <= now < target + LATE_WINDOW:
            due.append((f"{kind}:{today.isoformat()}", kind, today))
    return due
