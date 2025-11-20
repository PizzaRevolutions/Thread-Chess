# ♟️ Scacchi Online Multiplayer (Python + Flet)

Un'applicazione completa per giocare a scacchi in multiplayer via rete locale (TCP/IP). Il progetto implementa un'architettura **Client-Server**, utilizzando **Flet** per l'interfaccia grafica moderna e **Multithreading** per la gestione delle connessioni simultanee.

## 🚀 Caratteristiche Principali

* **Architettura Client-Server:** Utilizzo di Socket TCP per la comunicazione in tempo reale.
* **Interfaccia Grafica (GUI):** Realizzata con **Flet**, supporta il **Drag and Drop** dei pezzi.
* **Multithreading:**
  * Il Server gestisce ogni client in un thread separato.
  * Il Client utilizza un thread secondario per ascoltare le mosse dell'avversario senza bloccare l'interfaccia.
* **Regole Scacchistiche:** Supporto completo (Arrocco, En Passant, Promozione) grazie a `python-chess`.

## 🛠️ Installazione

1. **Prerequisiti:** Assicurati di avere Python installato (versione 3.7 o superiore).
2. **Crea un Virtual Environment (opzionale ma consigliato):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Su Mac/Linux
   # .venv\Scripts\activate   # Su Windows
   ```
3. **Installa le dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```

## ▶️ Come Avviare il Gioco

Per giocare, devi avviare prima il server e poi due client (uno per giocatore).

### 1. Avviare il Server

Apri un terminale, entra nella cartella `src` ed esegui:

```bash
flet run server.py
```

*Vedrai il messaggio "SERVER AVVIATO SU localhost:5000".*

### 2. Avviare il Primo Giocatore (Client)

Apri un **secondo** terminale, entra in `src` ed esegui:

```bash
flet run
```

* Inserisci un Nickname e clicca su "Entra in Coda".
* Vedrai una schermata di attesa.

### 3. Avviare il Secondo Giocatore

Apri un **terzo** terminale ed esegui di nuovo il client:

```bash
flet run
```

* Inserisci un altro Nickname e connettiti.
* **La partita inizierà automaticamente!** Il server assegnerà casualmente il Bianco e il Nero.

## 🧠 Dettagli Tecnici

### Gestione Socket e Threading

Il sistema utilizza i socket bloccanti. Per evitare che l'interfaccia grafica (GUI) si blocchi in attesa di un messaggio di rete:

* **Server:** Usa `threading.Thread` per ogni connessione `accept()`, permettendo a più client di connettersi contemporaneamente.
* **Client:** Lancia un thread `daemon` (`network_loop`) che esegue un ciclo infinito di `socket.recv()`. Quando arriva un messaggio, aggiorna la GUI chiamando `page.update()`.

### Logica Server-Authoritative

A differenza di sistemi peer-to-peer semplici, qui i client non si fidano ciecamente l'uno dell'altro.

1. Il Client A invia una mossa ("e2e4").
2. Il Server riceve "e2e4", controlla se è legale sulla sua copia della scacchiera interna.
3. Se valida: il Server aggiorna il suo stato e inoltra la mossa al Client B.
4. Se invalida: il Server risponde con un errore e la mossa viene annullata.

## 📋 Requisiti (requirements.txt)

```text
flet
python-chess
```

---

*Progetto realizzato a scopo didattico per lo studio di Python, Socket Programming e GUI Development.*
