"""
Esempio: come un altro bot (o una sala segnali) chiede la previsione
al servizio Kronos. Usa solo librerie standard di Python.

    python client_example.py
"""
import json
import urllib.request

KRONOS_URL = "http://127.0.0.1:8765"


def get_forecast(symbol="XAUUSD", timeframe="M15", timeout=120):
    url = f"{KRONOS_URL}/forecast?symbol={symbol}&timeframe={timeframe}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    r = get_forecast()
    print(f"{r['symbol']} {r['timeframe']}: {r['bias']} "
          f"(rialzo {r['upside_probability'] * 100:.0f}%, "
          f"prezzo medio previsto {r['mean_final_close']})")
