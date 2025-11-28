import socket
import threading
import time
import flet as ft
import chess
import re
import pathlib
import functools

# Costanti di rete
INDIRIZZO_SERVER = "localhost"
PORTA_SERVER = 5000

# Valori consentiti per la durata del timer (in secondi)
MODALITA_CONSENTITE = {0, 60, 180, 300, 600, 1200}

# Liste globali per la gestione
client_connessi = []

# Struttura sessioni_gioco:
# [
#   (socket_g1, nick_g1, durata_timer),
#   (socket_g2, nick_g2, durata_timer) opzionale finché non si accoppia,
#   scacchiera_oggetto (chess.Board),
#   timer_info (dict) - opzionale finché non parte la partita (solo se durata_timer > 0)
# ]
sessioni_gioco = []

# Riferimenti UI per il pannello di amministrazione
contenitore_sessioni = None  # ft.Column che contiene tutte le session card
ui_sessioni = {}  # mappa id(sessione) -> dict con controlli UI (card, lista mosse, ecc.)

# Percorso del file con le parole vietate (stessa cartella di questo file)
BAD_WORDS_FILE = pathlib.Path(__file__).with_name("bad_words.txt")


@functools.lru_cache(maxsize=1)
def carica_parole_vietate():
    """
    Legge il file bad_words.txt (una parola per riga, minuscolo).
    Se il file non esiste o non è leggibile, ritorna una piccola lista di default.
    """
    try:
        if BAD_WORDS_FILE.exists():
            parole = []
            with BAD_WORDS_FILE.open("r", encoding="utf-8") as f:
                for riga in f:
                    riga = riga.strip().lower()
                    # Salta righe vuote o commenti
                    if not riga or riga.startswith("#"):
                        continue
                    parole.append(riga)
            if parole:
                return parole
    except Exception:
        pass

    # Fallback minimale se il file manca o è vuoto
    return [
        "cazzo",
        "merda",
        "stronzo",
        "vaffanculo",
    ]


def nickname_valido(nickname: str) -> bool:
    """
    Valida il nickname lato server: lunghezza, caratteri e parolacce.
    Deve essere coerente (o più restrittivo) rispetto al controllo lato client.
    """
    if not nickname:
        return False

    nickname = nickname.strip()

    # Lunghezza massima
    if len(nickname) > 16:
        return False

    # Solo lettere, numeri e underscore
    if not re.fullmatch(r"[A-Za-z0-9_]+", nickname):
        return False

    # Lista di parole vietate caricata dal file (o fallback)
    parole_vietate = carica_parole_vietate()

    nick_lower = nickname.lower()
    for parola in parole_vietate:
        if parola in nick_lower:
            return False

    return True

def notifica_fine_partita(sessione, risultato, pagina):
    """
    Invia ai giocatori un messaggio di fine partita in base al risultato.
    risultato: stringa restituita da chess.Board().result() -> "1-0", "0-1", "1/2-1/2"
    """
    if len(sessione) < 2:
        return

    # Gli elementi dei giocatori sono tuple (socket, nickname, durata_timer)
    socket_g1, nick_g1, _ = sessione[0]
    socket_g2, nick_g2, _ = sessione[1]

    if risultato == "1-0":
        # Bianco vince
        messaggio_bianco = "GAMEOVER|WIN"
        messaggio_nero = "GAMEOVER|LOSE"
    elif risultato == "0-1":
        # Nero vince
        messaggio_bianco = "GAMEOVER|LOSE"
        messaggio_nero = "GAMEOVER|WIN"
    else:
        # Patta (es: "1/2-1/2" o altri risultati equivalenti)
        messaggio_bianco = "GAMEOVER|DRAW"
        messaggio_nero = "GAMEOVER|DRAW"

    try:
        socket_g1.send(messaggio_bianco.encode())
    except:
        pass
    try:
        socket_g2.send(messaggio_nero.encode())
    except:
        pass

    pagina.add(ft.Text(f"Partita finita: {risultato}"))
    pagina.update()


def avvisa_avversario_abbandono(sessione, indice_giocatore_che_abbandona):
    """
    Avvisa l'avversario che il giocatore si è disconnesso/ha abbandonato.
    """
    try:
        indice_avversario = 1 if indice_giocatore_che_abbandona == 0 else 0
        if len(sessione) > indice_avversario:
            socket_avversario = sessione[indice_avversario][0]
            try:
                socket_avversario.send("GAMEOVER|OPPONENT_LEFT".encode())
            except:
                pass
            try:
                socket_avversario.close()
            except:
                pass
    except:
        pass


def crea_ui_sessione(sessione, durata_sessione, pagina):
    """
    Crea una scheda grafica per una nuova sessione.
    """
    global contenitore_sessioni, ui_sessioni
    if contenitore_sessioni is None:
        return

    sid = id(sessione)
    socket_g1, nick_g1, _ = sessione[0]
    socket_g2, nick_g2, _ = sessione[1]

    descr_timer = "No time" if durata_sessione == 0 else f"{int(durata_sessione // 60)}' per lato"

    titolo = ft.Text(
        f"Sessione #{sid} - {nick_g1} (Bianco) vs {nick_g2} (Nero) - {descr_timer}",
        weight="bold",
    )

    # UI Mosse
    lista_mosse = ft.ListView(expand=1, spacing=2, padding=5, auto_scroll=True, height=100)
    # UI Chat (NUOVO)
    lista_chat = ft.ListView(expand=1, spacing=2, padding=5, auto_scroll=True, height=100)
    
    testo_stato = ft.Text("In corso", color="green")

    def chiudi_sessione_admin(e):
        chiudi_sessione_da_admin(sessione, motivo="Chiusura manuale (patta)", esito_forzato="DRAW", pagina=pagina)

    def banna_bianco(e):
        banna_giocatore(sessione, indice_bannato=0, pagina=pagina)

    def banna_nero(e):
        banna_giocatore(sessione, indice_bannato=1, pagina=pagina)

    pulsanti = ft.Row(
        [
            ft.ElevatedButton("Chiudi sessione", on_click=chiudi_sessione_admin),
            ft.TextButton("Banna Bianco", on_click=banna_bianco),
            ft.TextButton("Banna Nero", on_click=banna_nero),
        ],
        spacing=10,
    )

    card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    titolo,
                    pulsanti,
                    ft.Text("Mosse:", weight="bold"),
                    ft.Container(content=lista_mosse, border=ft.border.all(1, "grey"), border_radius=5, height=100),
                    ft.Text("Chat:", weight="bold"),
                    ft.Container(content=lista_chat, border=ft.border.all(1, "grey"), border_radius=5, height=100),
                    testo_stato,
                ],
                spacing=5,
            ),
            padding=10,
        )
    )

    ui_sessioni[sid] = {
        "card": card,
        "lista_mosse": lista_mosse,
        "lista_chat": lista_chat, # Salviamo il riferimento
        "testo_stato": testo_stato,
    }

    contenitore_sessioni.controls.append(card)
    pagina.update()


def log_chat_sessione(sessione, mittente, messaggio, pagina):
    """Aggiunge un messaggio alla chat della UI admin"""
    global ui_sessioni
    sid = id(sessione)
    ui = ui_sessioni.get(sid)
    if not ui:
        return
    testo = ft.Text(f"[{mittente}]: {messaggio}", size=12)
    ui["lista_chat"].controls.append(testo)
    pagina.update()


def marca_sessione_chiusa(sessione, testo, colore="red", pagina=None):
    """Aggiorna lo stato visivo di una sessione quando viene chiusa."""
    global ui_sessioni, contenitore_sessioni
    sid = id(sessione)
    ui = ui_sessioni.get(sid)
    if not ui:
        return
    ui["testo_stato"].value = testo
    ui["testo_stato"].color = colore
    if pagina:
        pagina.update()


def chiudi_sessione_da_admin(sessione, motivo, esito_forzato, pagina):
    """
    Chiusura anticipata della sessione da parte dell'admin.
    esito_forzato: "DRAW" per patta amministrativa.
    """
    if len(sessione) < 2:
        return

    try:
        socket_g1, nick_g1, _ = sessione[0]
        socket_g2, nick_g2, _ = sessione[1]

        if esito_forzato == "DRAW":
            mess1 = "GAMEOVER|DRAW"
            mess2 = "GAMEOVER|DRAW"
        else:
            mess1 = "GAMEOVER|DRAW"
            mess2 = "GAMEOVER|DRAW"

        try:
            socket_g1.send(mess1.encode())
        except:
            pass
        try:
            socket_g2.send(mess2.encode())
        except:
            pass

        try:
            socket_g1.close()
        except:
            pass
        try:
            socket_g2.close()
        except:
            pass
    finally:
        if sessione in sessioni_gioco:
            sessioni_gioco.remove(sessione)
        marca_sessione_chiusa(sessione, f"Chiusa: {motivo}", pagina=pagina)


def banna_giocatore(sessione, indice_bannato, pagina):
    """
    Banna un giocatore:
    - il bannato perde
    - l'altro vince
    - la sessione viene chiusa
    """
    if len(sessione) < 2:
        return

    vincitore = 1 - indice_bannato
    try:
        socket_bannato, nick_bannato, _ = sessione[indice_bannato]
        socket_vincitore, nick_vincitore, _ = sessione[vincitore]

        try:
            socket_bannato.send("GAMEOVER|LOSE".encode())
        except:
            pass
        try:
            socket_vincitore.send("GAMEOVER|WIN".encode())
        except:
            pass

        try:
            socket_bannato.close()
        except:
            pass
        try:
            socket_vincitore.close()
        except:
            pass
    finally:
        if sessione in sessioni_gioco:
            sessioni_gioco.remove(sessione)
        marca_sessione_chiusa(
            sessione,
            f"Chiusura: {nick_bannato} bannato, vittoria a {nick_vincitore}",
            pagina=pagina,
        )


def gestisci_client(socket_client, indirizzo_ip, pagina):
    nickname = "Sconosciuto"
    indice_giocatore = -1  # 0 = Bianco, 1 = Nero
    sessione_corrente = None
    durata_timer_richiesta = 600  # default di sicurezza

    try:
        # 1. Ricezione Nickname + durata timer (formato: "nickname|secondi")
        prima_risposta = socket_client.recv(1024).decode('utf-8').strip()
        parti = prima_risposta.split("|")
        nickname = (parti[0] if parti else "").strip()

        durata_timer_richiesta = 600
        if len(parti) >= 2:
            try:
                durata_parsata = int(float(parti[1]))
                if durata_parsata in MODALITA_CONSENTITE:
                    durata_timer_richiesta = durata_parsata
            except ValueError:
                pass

        # Validazione nickname lato server (sicurezza)
        if not nickname_valido(nickname):
            try:
                socket_client.send("ERROR|Nickname non valido".encode())
            except:
                pass
            try:
                socket_client.close()
            except:
                pass
            pagina.add(ft.Text(f"Connessione rifiutata da {indirizzo_ip}: nickname non valido ({nickname!r})"))
            pagina.update()
            return

        print(f"[CONNESSO] {nickname} da {indirizzo_ip} (timer: {durata_timer_richiesta}s)")
        
        client_connessi.append((socket_client, nickname, durata_timer_richiesta))
        pagina.update()

        # 2. Matchmaking (Creazione della partita)
        for sessione in sessioni_gioco:
            # Se la sessione ha meno di 2 elementi, significa che c'è un solo giocatore e manca la scacchiera
            # e la durata del timer deve coincidere
            if len(sessione) < 2:
                durata_sessione = sessione[0][2]
                if durata_sessione != durata_timer_richiesta:
                    continue

                sessione.insert(1, (socket_client, nickname, durata_timer_richiesta)) # Mi aggiungo come secondo giocatore
                sessione_corrente = sessione
                indice_giocatore = 1 # Sono il Nero
                
                # Ora siamo in 2: Creiamo la Scacchiera e Iniziamo!
                scacchiera = chess.Board()
                sessione.append(scacchiera) # La scacchiera diventa l'elemento indice 2

                if durata_sessione > 0:
                    timer_info = {
                        "white_time": durata_sessione,
                        "black_time": durata_sessione,
                        "ultimo_tick": time.time()
                    }
                    sessione.append(timer_info)  # Timer info diventa elemento indice 3
                
                socket_g1 = sessione[0][0]
                socket_g2 = sessione[1][0]
                nick_g1 = sessione[0][1]
                nick_g2 = sessione[1][1]
                
                print(f"START: {nick_g1} vs {nick_g2} (timer: {durata_sessione}s)")
                pagina.update()

                # Crea la scheda grafica per questa nuova sessione
                crea_ui_sessione(sessione, durata_sessione, pagina)

                # Invio segnale di start e assegnazione colori
                socket_g1.send("START|WHITE".encode())
                socket_g2.send("START|BLACK".encode())

                if durata_sessione > 0:
                    invia_tempo_ai_giocatori(sessione)
                    threading.Thread(
                        target=loop_timer_sessione, args=(sessione, pagina), daemon=True
                    ).start()
                break
        
        if not sessione_corrente:
            # Se non ho trovato partite aperte con la stessa durata, creo una nuova sessione con me come primo giocatore
            nuova_sessione = [(socket_client, nickname, durata_timer_richiesta)] 
            sessioni_gioco.append(nuova_sessione)
            sessione_corrente = nuova_sessione
            indice_giocatore = 0 # Sono il Bianco

        # 3. Ciclo di Gioco (Logica Autorevole del Server)
        while True:
            messaggio = socket_client.recv(1024).decode()
            if not messaggio: break
            
            # Controllo se la partita è effettivamente iniziata (ci sono 2 player e la scacchiera)
            if len(sessione_corrente) < 3:
                continue

            scacchiera = sessione_corrente[2] # Recupero l'oggetto chess.Board
            timer_info_presente = len(sessione_corrente) >= 4
            
            if timer_info_presente:
                colore_scaduto = aggiorna_timer(sessione_corrente)
                if colore_scaduto:
                    gestisci_timeout(sessione_corrente, colore_scaduto, pagina)
                    break
            
            # CONTROLLO 1: È il turno di questo socket?
            # scacchiera.turn è True per il Bianco, False per il Nero
            # indice_giocatore è 0 per il Bianco, 1 per il Nero
            e_turno_bianco = scacchiera.turn
            sono_il_bianco = (indice_giocatore == 0)
            # Gestione CHAT
            if messaggio.startswith("CHAT|"):
                try:
                    # Dividiamo solo alla prima pipe, così il messaggio può contenere pipe
                    _, contenuto_chat = messaggio.split("|", 1)
                    contenuto_chat = contenuto_chat.strip()
                    
                    if contenuto_chat:
                        # Costruiamo il pacchetto da inviare ai client
                        msg_out = f"CHAT|{nickname}|{contenuto_chat}"
                        
                        # Invio a entrambi i giocatori
                        for g in sessione_corrente[:2]: # g è (socket, nick, timer)
                            try:
                                g[0].send(msg_out.encode())
                            except:
                                pass
                        
                        # Log lato admin
                        log_chat_sessione(sessione_corrente, nickname, contenuto_chat, pagina)
                except Exception as e:
                    print(f"Errore chat: {e}")
                continue # Passa al prossimo ciclo
            # Gestione richiesta mosse valide
            if messaggio.startswith("MOVES|"):
                if e_turno_bianco != sono_il_bianco:
                    socket_client.send("MOVES|".encode())  # Nessuna mossa valida se non è il tuo turno
                    continue
                
                try:
                    casella_richiesta = messaggio.split("|")[1]
                    square = chess.parse_square(casella_richiesta)
                    pezzo = scacchiera.piece_at(square)
                    
                    # Verifica che ci sia un pezzo e che sia del colore del giocatore
                    if pezzo and pezzo.color == (chess.WHITE if sono_il_bianco else chess.BLACK):
                        # Trova tutte le mosse legali da questa casella
                        mosse_valide = [m for m in scacchiera.legal_moves if m.from_square == square]
                        caselle_valide = [chess.square_name(m.to_square) for m in mosse_valide]
                        risposta = f"MOVES|{','.join(caselle_valide)}"
                        socket_client.send(risposta.encode())
                    else:
                        socket_client.send("MOVES|".encode())  # Nessuna mossa valida
                except:
                    socket_client.send("MOVES|".encode())  # Errore nel parsing
                continue
            
            if e_turno_bianco != sono_il_bianco:
                print(f"Mossa rifiutata: non è il turno di {nickname}")
                socket_client.send("ERROR|Non è il tuo turno".encode())
                continue

            # CONTROLLO 2: La mossa è valida secondo le regole degli scacchi?
            try:
                mossa = chess.Move.from_uci(messaggio)
                if mossa in scacchiera.legal_moves:
                    # VALIDAZIONE OK: Eseguiamo la mossa sulla scacchiera del Server
                    scacchiera.push(mossa)
                    print(f"Mossa valida {messaggio} da {nickname}. Inoltro...")
                    # Log grafico della mossa
                    log_mossa_sessione(sessione_corrente, nickname, messaggio, pagina)
                    
                    # Inoltra la mossa all'AVVERSARIO
                    indice_avversario = 1 if indice_giocatore == 0 else 0
                    socket_avversario = sessione_corrente[indice_avversario][0]
                    socket_avversario.send(messaggio.encode())
                    
                    # Controlla fine partita (Scacco matto, stallo, ecc.)
                    if scacchiera.is_game_over():
                        risultato = scacchiera.result()
                        notifica_fine_partita(sessione_corrente, risultato, pagina)
                        # Chiudo la sessione e le connessioni
                        if sessione_corrente in sessioni_gioco:
                            sessioni_gioco.remove(sessione_corrente)
                        for giocatore in sessione_corrente[:2]:
                            try:
                                giocatore[0].close()
                            except:
                                pass
                        break
                    if timer_info_presente:
                        invia_tempo_ai_giocatori(sessione_corrente)
                else:
                    print(f"Mossa illegale tentata da {nickname}: {messaggio}")
                    socket_client.send("ERROR|Mossa illegale".encode())
            except ValueError:
                pass # Formato mossa non valido

    except Exception as errore:
        print(f"Errore {nickname}: {errore}")
    finally:
        # Pulizia sessione in caso di disconnessione
        # Rimuovi qualunque entry con questo socket, ignorando la durata
        for entry in list(client_connessi):
            if entry[0] is socket_client:
                client_connessi.remove(entry)
        
        # Se esiste una sessione associata, avvisa l'avversario che questo giocatore ha abbandonato
        if sessione_corrente and sessione_corrente in sessioni_gioco:
            # Calcola l'indice locale del giocatore che sta abbandonando, se non noto lo deduciamo
            if indice_giocatore not in (0, 1):
                try:
                    if sessione_corrente[0][0] is socket_client:
                        indice_giocatore = 0
                    elif len(sessione_corrente) > 1 and sessione_corrente[1][0] is socket_client:
                        indice_giocatore = 1
                except:
                    indice_giocatore = -1

            if indice_giocatore in (0, 1):
                avvisa_avversario_abbandono(sessione_corrente, indice_giocatore)

            if sessione_corrente in sessioni_gioco:
                sessioni_gioco.remove(sessione_corrente)

            pagina.update()
        
        socket_client.close()

def invia_tempo_ai_giocatori(sessione):
    if len(sessione) < 4:
        return
    timer_info = sessione[3]
    tempo_bianco = max(0, int(timer_info["white_time"]))
    tempo_nero = max(0, int(timer_info["black_time"]))
    messaggio = f"TIME|{tempo_bianco}|{tempo_nero}"
    for giocatore in sessione[:2]:
        try:
            giocatore[0].send(messaggio.encode())
        except:
            pass

def aggiorna_timer(sessione):
    if len(sessione) < 4:
        return None
    timer_info = sessione[3]
    scacchiera = sessione[2]
    ora_attuale = time.time()
    trascorso = ora_attuale - timer_info["ultimo_tick"]
    if trascorso <= 0:
        return None
    timer_info["ultimo_tick"] = ora_attuale
    chiave_colore = "white_time" if scacchiera.turn else "black_time"
    timer_info[chiave_colore] -= trascorso
    if timer_info[chiave_colore] <= 0:
        timer_info[chiave_colore] = 0
        return "WHITE" if chiave_colore == "white_time" else "BLACK"
    return None

def gestisci_timeout(sessione, colore_scaduto, pagina):
    """
    Gestisce la fine della partita per tempo, applicando le regole:
    - Chi va a zero perde, SE l'avversario ha materiale sufficiente per dare matto in teoria.
    - Se entrambi i tempi sono a zero -> patta.
    - Se il giocatore che ha ancora tempo NON ha materiale sufficiente per dare matto -> patta.
    """
    if len(sessione) < 4:
        return

    scacchiera = sessione[2]
    timer_info = sessione[3]

    # Valori di tempo normalizzati (non negativi)
    white_time = max(0, float(timer_info.get("white_time", 0)))
    black_time = max(0, float(timer_info.get("black_time", 0)))

    # Caso: entrambi i tempi a zero → patta
    if white_time <= 0 and black_time <= 0:
        pagina.add(ft.Text("Tempo scaduto per entrambi: partita patta (tempo)."))
        pagina.update()
        notifica_fine_partita(sessione, "1/2-1/2", pagina)
    else:
        # Determina chi ha finito il tempo e chi è l'avversario
        if colore_scaduto == "WHITE":
            losing_color = chess.WHITE
            winning_color = chess.BLACK
            descrizione = "Bianco"
        else:
            losing_color = chess.BLACK
            winning_color = chess.WHITE
            descrizione = "Nero"

        pagina.add(ft.Text(f"Tempo scaduto per {descrizione}"))
        pagina.update()

        # Controllo materiale sufficiente: usiamo la logica di python-chess.
        # Se la funzione dice che la posizione è a "materiale insufficiente" complessivo
        # (nessuna delle due parti può dare matto in teoria), allora la partita è patta,
        # indipendentemente da chi è andato a zero.
        if scacchiera.is_insufficient_material():
            risultato = "1/2-1/2"
        else:
            # Vittoria al tempo per il colore che ha ancora tempo.
            risultato = "0-1" if losing_color == chess.WHITE else "1-0"

        notifica_fine_partita(sessione, risultato, pagina)

    # In ogni caso notifichiamo comunque il tipo di timeout esplicito (per compatibilità client)
    messaggio_timeout = f"TIMEOUT|{colore_scaduto}"
    for giocatore in sessione[:2]:
        try:
            giocatore[0].send(messaggio_timeout.encode())
        except:
            pass

    # Chiudiamo la sessione e le connessioni
    if sessione in sessioni_gioco:
        sessioni_gioco.remove(sessione)
    for giocatore in sessione[:2]:
        try:
            giocatore[0].close()
        except:
            pass

def loop_timer_sessione(sessione, pagina):
    while True:
        if sessione not in sessioni_gioco:
            break
        if len(sessione) < 4:
            time.sleep(0.5)
            continue
        colore_scaduto = aggiorna_timer(sessione)
        invia_tempo_ai_giocatori(sessione)
        if colore_scaduto:
            gestisci_timeout(sessione, colore_scaduto, pagina)
            break
        time.sleep(1)

def avvia_server(pagina):
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_server.bind((INDIRIZZO_SERVER, PORTA_SERVER))
    socket_server.listen()
    
    pagina.update()
    
    while True:
        client, indirizzo = socket_server.accept()
        threading.Thread(target=gestisci_client, args=(client, indirizzo, pagina), daemon=True).start()

def main(pagina: ft.Page):
    global contenitore_sessioni
    pagina.title = f"Server Scacchi ({INDIRIZZO_SERVER}:{PORTA_SERVER})"    

    # Pannello superiore di info generali
    intestazione = ft.Column(
        [
            ft.Text(f"Server Scacchi ({INDIRIZZO_SERVER}:{PORTA_SERVER})", size=24, weight="bold"),
            ft.Text("Sessioni attive e strumenti di moderazione:", size=16),
        ],
        spacing=5,
    )

    contenitore_sessioni = ft.Column(spacing=10, expand=1)

    pagina.add(
        intestazione,
        ft.Divider(),
        contenitore_sessioni,
    )
    pagina.update()

    # Avvia il server in un thread separato per non bloccare la GUI di Flet
    threading.Thread(target=avvia_server, args=(pagina,), daemon=True).start()

ft.app(target=main)