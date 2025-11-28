# ♟️ Scacchi Online Multiplayer (Python + Flet)

Un'applicazione completa cross-platform per giocare a scacchi in multiplayer via rete locale (TCP/IP). Il progetto implementa un'architettura **Client-Server**, utilizzando **Flet** per l'interfaccia grafica moderna e **Multithreading** per la gestione delle connessioni simultanee.

## 📥 Download e Installazione (Gioca Subito!)

Non vuoi installare Python o configurare l'ambiente? Scarica direttamente i file eseguibili per il tuo sistema operativo dalla sezione **Releases** di GitHub.

[👉 **VAI AI DOWNLOAD (RELEASES)**](https://github.com/PizzaRevolutions/Thread-Chess/releases)

### Cosa scaricare:
*   🖥️ **Windows:** Scarica il file `.exe` e eseguilo sul tuo dispositivo.
*   📱 **Android:** Scarica il file `.apk` e installalo sul tuo dispositivo.

---

## 🚀 Caratteristiche Principali

*   **Cross-Platform:** Gioca su Windows, Android, macOS e Linux grazie a Flet.
*   **Architettura Client-Server:** Utilizzo di Socket TCP per la comunicazione in tempo reale.
*   **Interfaccia Grafica (GUI):** Moderna e reattiva, supporta il **Drag and Drop** dei pezzi.
*   **Multithreading:**
    *   Il Server gestisce ogni client in un thread separato.
    *   Il Client ascolta le mosse dell'avversario in background senza bloccare la grafica.
*   **Regole Scacchistiche:** Supporto completo (Arrocco, En Passant, Promozione) validato da `python-chess`.

---

## ▶️ Come Avviare il Gioco (Dagli Eseguibili)

Se hai scaricato i file dalla sezione Releases:

1.  **Avvia il Server:** Apri il file `Server.exe`. Vedrai una finestra o un terminale che indica l'attesa di connessioni.
2.  **Avvia i Client:**
    *   Esegui l'applicazione su due dispositivi o finestre diverse.
    *   Inserisci un Nickname e connettiti.
3.  **Gioca:** Una volta connessi due giocatori, la partita inizia automaticamente con l'assegnazione casuale dei colori.

> **Nota per Android/Rete Locale:** Assicurati che il Client conosca l'indirizzo IP del PC dove gira il Server se giochi su dispositivi diversi (il server di default ascolta su `localhost`).

---

## 🛠️ Sviluppo & Esecuzione da Codice Sorgente

Se sei uno sviluppatore o vuoi modificare il codice, segui questa procedura.

### 1. Prerequisiti
*   Python 3.7 o superiore.
*   Git (opzionale, per clonare la repo).

### 2. Installazione
Clona la repository e crea un ambiente virtuale:

```bash
# Clona la repo (o scarica lo zip)
git clone https://github.com/tuo-username/tuo-repo.git
cd tuo-repo

# Crea Virtual Environment
python -m venv .venv

# Attiva Virtual Environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Installa dipendenze
pip install -r requirements.txt
```

### 3. Avvio (Development Mode)

Apri **tre** terminali separati all'interno della cartella `src`:

**Terminale 1 (Server):**
```bash
flet run server.py
```
*Dovresti vedere: "SERVER AVVIATO SU..."*

**Terminale 2 (Giocatore A):**
```bash
flet run
```

**Terminale 3 (Giocatore B):**
```bash
flet run
```

---

## 🧠 Dettagli Tecnici

### Gestione Socket e Threading
Il sistema utilizza socket bloccanti gestiti tramite threading per mantenere la GUI fluida:

*   **Server:** Utilizza `threading.Thread` per ogni chiamata `accept()`, permettendo connessioni multiple simultanee e gestione indipendente delle partite.
*   **Client:** Esegue un thread `daemon` (`network_loop`) in ascolto continuo con `socket.recv()`. Alla ricezione di un pacchetto, aggiorna lo stato della scacchiera tramite `page.update()` di Flet.

### Logica Server-Authoritative
Per prevenire cheating e desincronizzazioni, la logica segue un modello autoritativo:

1.  Client A invia mossa ("e2e4").
2.  Server riceve, valida tramite `python-chess` sulla propria istanza della scacchiera.
3.  **Se valida:** Aggiorna lo stato e trasmette la mossa al Client B.
4.  **Se invalida:** Rifiuta la mossa e forza il rollback sul Client A.

---

*Progetto realizzato a scopo didattico per lo studio di Python, Socket Programming e GUI Development.*
