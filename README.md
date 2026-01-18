# ♟️ Online Multiplayer Chess (Python + Flet) 🇬🇧

A comprehensive cross-platform application for playing multiplayer chess over a local area network (TCP/IP). The project implements a **Client-Server** architecture, utilizing **Flet** for a modern graphical interface and **Multithreading** for managing simultaneous connections.

## 📥 Download and Installation (Play Now!)

Don't want to install Python or configure an environment? Download the executable files for your operating system directly from the GitHub **Releases** section.

[👉 **GO TO DOWNLOADS (RELEASES)](https://github.com/PizzaRevolutions/Thread-Chess/releases)**

### What to download:

* **🖥️ Windows:** Download the `.exe` file and run it on your device.
* **📱 Android:** Download the `.apk` file and install it on your device.

---

## 🚀 Key Features

* **Cross-Platform:** Play on Windows, Android, macOS, and Linux thanks to Flet.
* **Client-Server Architecture:** Uses TCP Sockets for real-time communication.
* **Graphical User Interface (GUI):** Modern and responsive, supporting **Drag and Drop** for pieces.
* **Multithreading:**
* The **Server** handles each client in a separate thread.
* The **Client** listens for opponent moves in the background without freezing the UI.


* **Chess Rules:** Full support (Castling, En Passant, Promotion) validated by the `python-chess` library.

---

## ▶️ How to Start (Using Executables)

If you downloaded the files from the Releases section:

1. **Launch the Server:** Open the `Server.exe` file. You will see a window or terminal indicating it is waiting for connections.
2. **Launch the Clients:**
* Run the application on two different devices or in two separate windows.
* Enter a Nickname and connect.


3. **Play:** Once two players are connected, the game starts automatically with random color assignment.

> **Note for Android/Local Network:** Ensure the Client knows the IP address of the PC where the Server is running if you are playing on different devices (the server listens on `localhost` by default).

---

## 🛠️ Development & Running from Source

If you are a developer or want to modify the code, follow this procedure.

### 1. Prerequisites

* Python 3.7 or higher.
* Git (optional, to clone the repo).

### 2. Installation

Clone the repository and create a virtual environment:

```bash
# Clone the repo (or download the zip)
git clone https://github.com/your-username/your-repo.git
cd your-repo

# Create Virtual Environment
python -m venv .venv

# Activate Virtual Environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

### 3. Launch (Development Mode)

Open **three** separate terminals within the `src` folder:

**Terminal 1 (Server):**

```bash
flet run server.py

```

*You should see: "SERVER STARTED AT..."*

**Terminal 2 (Player A):**

```bash
flet run

```

**Terminal 3 (Player B):**

```bash
flet run

```

---

## 🧠 Technical Details

### Socket Management and Threading

The system uses blocking sockets managed via threading to keep the GUI fluid:

* **Server:** Uses `threading.Thread` for every `accept()` call, allowing multiple simultaneous connections and independent game management.
* **Client:** Runs a `daemon` thread (`network_loop`) continuously listening with `socket.recv()`. Upon receiving a packet, it updates the board state via Flet's `page.update()`.

### Server-Authoritative Logic

To prevent cheating and desynchronization, the logic follows an authoritative model:

1. **Client A** sends a move (e.g., "e2e4").
2. **Server** receives and validates it via `python-chess` on its own board instance.
3. **If valid:** Updates the state and broadcasts the move to **Client B**.
4. **If invalid:** Rejects the move and forces a rollback on **Client A**.

---

*This project was created for educational purposes to study Python, Socket Programming, and GUI Development.*

# ♟️ Scacchi Online Multiplayer (Python + Flet) 🇮🇹

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
