# FactMachine — Guida unica del VENDITORE

Tutto quello che ti serve per vendere il bot a licenza: un **unico exe** da dare
ai clienti (con il browser già incluso, doppio click e via) e un **server di
licenze** sulla tua VPS che controlli tu.

---

## Come funziona in 30 secondi

```
  CLIENTE: FactMachine.exe ──(chiave + impronta PC)──► TUA VPS: server licenze
                           ◄──(valida / scaduta / altro PC)──
```

- Il cliente riceve **un solo file**: `FactMachine.exe` (browser incluso).
- All'avvio il bot chiede la **chiave** (una volta sola, poi la ricorda) e la
  verifica col **tuo server**. Senza licenza valida **non parte**.
- La chiave si lega al **primo PC** (non è condivisibile) e dura quanto decidi tu
  (giorno / settimana / mese), a partire dalla **prima attivazione**.

---

## I file del progetto

**Lato tuo (restano a te):**
| File | A cosa serve |
|------|--------------|
| `license_server/server.py` | Il server licenze, gira **sulla VPS** |
| `license_server/admin.py` | Il tuo pannello: crea/elenca/revoca chiavi |
| `factmachine/COMPILA_EXE.bat` | Compila l'exe tutto-in-uno (lo lanci su Windows) |
| `factmachine/dashboard.py` | Il bot (sorgente che viene compilato) |
| `factmachine/license_client.py` | Il controllo licenza dentro il bot |

**Lato cliente (gli dai solo questo):**
| File | A cosa serve |
|------|--------------|
| `FactMachine.exe` | Il bot completo, browser incluso. **Un solo file.** |

> `login.py` **non serve più** al cliente: il login (numero + SMS) si fa dentro
> l'exe, nel browser che si apre al primo avvio.

---

## PARTE 1 — Server licenze sulla VPS (una volta sola)

1. Metti la cartella `license_server` sulla VPS.

2. Apri `license_server/server.py` con Blocco note e cambia **questi due valori**
   (scegli due stringhe lunghe e casuali tue):
   ```python
   ADMIN_TOKEN    = "..."   # password per creare/revocare chiavi (resta solo tua)
   SIGNING_SECRET = "..."   # segreto di firma (va messo UGUALE anche nel bot)
   ```

3. Avvia il server. Nella cartella `license_server`, apri il CMD e scrivi
   (copia → tasto destro per incollare → INVIO):
   ```
   python server.py
   ```
   Deve apparire `Server licenze FactMachine su http://0.0.0.0:8000`.
   Lascialo aperto (la tua VPS è sempre accesa, quindi lo avvii una volta e basta).

4. Apri la porta 8000 nel firewall. CMD **come amministratore**:
   ```
   netsh advfirewall firewall add rule name="FactMachine Licenze" dir=in action=allow protocol=TCP localport=8000
   ```

5. Segnati l'indirizzo del server: `http://IP-DELLA-VPS:8000`
   (l'IP pubblico della tua VPS).

---

## PARTE 2 — Preparare l'exe da dare ai clienti (una volta sola)

1. Apri `factmachine/license_client.py` con Blocco note e imposta:
   ```python
   SERVER_URL     = "http://IP-DELLA-VPS:8000"   # il tuo server (Parte 1, punto 5)
   SIGNING_SECRET = "..."                         # LO STESSO di server.py !
   ```
   > Il `SIGNING_SECRET` deve essere **identico** nei due file. L'`ADMIN_TOKEN`
   > invece **non** va nel bot (resta solo tuo).

2. Compila l'exe: entra nella cartella `factmachine` e fai **doppio click su
   `COMPILA_EXE.bat`**. Fa tutto da solo (installa gli strumenti, scarica il
   browser, compila). Alla fine trovi l'exe in:
   ```
   factmachine\dist\FactMachine.exe
   ```
   Questo è il file unico da dare ai clienti (browser già dentro).

> Nota: devi avere **Python installato** sul PC dove compili (vedi la guida nella
> cartella `factmachine`, README, sezione "Installare Python dal CMD").

---

## PARTE 3 — Creare e gestire le chiavi

Usa `license_server/admin.py` (sulla VPS, o dal tuo PC mettendo in cima
`SERVER_URL` e `ADMIN_TOKEN`). Comandi pronti:

```
python admin.py create --days 30 --note "cliente Mario"   # MENSILE
python admin.py create --days 7                            # SETTIMANALE
python admin.py create --days 1                            # GIORNALIERA
python admin.py create --days 30 --count 5                 # 5 chiavi insieme
python admin.py list                                       # elenco + stato
python admin.py revoke FM-ABCD-EFGH-JKLM                   # blocca subito
python admin.py reset  FM-ABCD-EFGH-JKLM                   # sblocca il PC (nuovo computer)
```

La chiave creata (es. `FM-ABCD-EFGH-JKLM`) è quella che mandi al cliente.

---

## PARTE 4 — Cosa fa il cliente

1. Riceve da te **`FactMachine.exe`** e la **chiave**.
2. **Doppio click** sull'exe (non serve installare niente).
3. Appare la finestra "Inserisci la chiave di licenza": incolla la chiave (una
   volta sola).
4. Si apre il browser: la **prima volta** fa il login con numero + SMS, poi
   resta ricordato.
5. Usa la dashboard. Le volte successive apre e basta, finché la licenza è
   valida.

Quando la licenza **scade** o tu la **revochi**, alla riapertura il bot avvisa e
**non parte** finché non gli dai una chiave nuova.

---

## Promemoria vendita

1. **Una volta:** server sulla VPS (Parte 1) → metti IP+segreto nel bot e compila
   l'exe (Parte 2).
2. **Per ogni cliente:** `admin.py create --days 30` → ottieni la chiave → mandi
   **exe + chiave**.
3. **Quando vuoi:** `list` per controllare, `revoke` per bloccare, `reset` se il
   cliente cambia PC.

> Sicurezza: non condividere mai `ADMIN_TOKEN` e `SIGNING_SECRET`. Il sistema usa
> blocco-per-PC, scadenza lato server e firma anti-manomissione. Per alzare
> ancora la protezione si può passare il server a **HTTPS** (serve un dominio):
> chiedi quando vuoi.
