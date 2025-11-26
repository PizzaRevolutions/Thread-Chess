import socket
import threading
import time
import flet as ft
import chess 

# Costanti di rete
INDIRIZZO_SERVER = "localhost"
PORTA_SERVER = 5000
DURATA_TIMER = 600  # secondi (10 minuti)

# Liste globali per la gestione
client_connessi = []

# Struttura sessioni_gioco:
# [
#   (socket_g1, nick_g1),
#   (socket_g2, nick_g2) opzionale finché non si accoppia,
#   scacchiera_oggetto (chess.Board),
#   timer_info (dict) - opzionale finché non parte la partita
# ]
sessioni_gioco = [] 

def notifica_fine_partita(sessione, risultato, pagina):
    """
    Invia ai giocatori un messaggio di fine partita in base al risultato.
    risultato: stringa restituita da chess.Board().result() -> "1-0", "0-1", "1/2-1/2"
    """
    if len(sessione) < 2:
        return

    socket_g1, nick_g1 = sessione[0]
    socket_g2, nick_g2 = sessione[1]

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


def gestisci_client(socket_client, indirizzo_ip, pagina):
    nickname = "Sconosciuto"
    indice_giocatore = -1  # 0 = Bianco, 1 = Nero
    sessione_corrente = None

    try:
        # 1. Ricezione Nickname
        nickname = socket_client.recv(1024).decode('utf-8').strip()
        print(f"[CONNESSO] {nickname} da {indirizzo_ip}")
        
        client_connessi.append((socket_client, nickname))
        pagina.add(ft.Text(f"{nickname} connesso. In attesa..."))
        pagina.update()

        # 2. Matchmaking (Creazione della partita)
        for sessione in sessioni_gioco:
            # Se la sessione ha meno di 2 elementi, significa che c'è un solo giocatore e manca la scacchiera
            if len(sessione) < 2: 
                sessione.insert(1, (socket_client, nickname)) # Mi aggiungo come secondo giocatore
                sessione_corrente = sessione
                indice_giocatore = 1 # Sono il Nero
                
                # Ora siamo in 2: Creiamo la Scacchiera e Iniziamo!
                scacchiera = chess.Board()
                sessione.append(scacchiera) # La scacchiera diventa l'elemento indice 2
                timer_info = {
                    "white_time": DURATA_TIMER,
                    "black_time": DURATA_TIMER,
                    "ultimo_tick": time.time()
                }
                sessione.append(timer_info)  # Timer info diventa elemento indice 3
                
                socket_g1 = sessione[0][0]
                socket_g2 = sessione[1][0]
                nick_g1 = sessione[0][1]
                nick_g2 = sessione[1][1]
                
                print(f"START: {nick_g1} vs {nick_g2}")
                pagina.add(ft.Text(f"PARTITA: {nick_g1} (Bianco) vs {nick_g2} (Nero)"))
                pagina.update()

                # Invio segnale di start e assegnazione colori
                socket_g1.send("START|WHITE".encode())
                socket_g2.send("START|BLACK".encode())
                invia_tempo_ai_giocatori(sessione)
                threading.Thread(
                    target=loop_timer_sessione, args=(sessione, pagina), daemon=True
                ).start()
                break
        
        if not sessione_corrente:
            # Se non ho trovato partite aperte, creo una nuova sessione con me come primo giocatore
            nuova_sessione = [(socket_client, nickname)] 
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
        if (socket_client, nickname) in client_connessi:
            client_connessi.remove((socket_client, nickname))
        
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

            pagina.add(ft.Text(f"Sessione chiusa per disconnessione di {nickname}"))
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
    messaggio_timeout = f"TIMEOUT|{colore_scaduto}"
    descrizione = "Bianco" if colore_scaduto == "WHITE" else "Nero"
    pagina.add(ft.Text(f"Tempo scaduto per {descrizione}"))
    pagina.update()
    for giocatore in sessione[:2]:
        try:
            giocatore[0].send(messaggio_timeout.encode())
        except:
            pass
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
    
    pagina.add(ft.Text(f"SERVER AUTOREVOLE AVVIATO SU {INDIRIZZO_SERVER}:{PORTA_SERVER}"))
    pagina.update()
    
    while True:
        client, indirizzo = socket_server.accept()
        threading.Thread(target=gestisci_client, args=(client, indirizzo, pagina), daemon=True).start()

def main(pagina: ft.Page):
    pagina.title = "Server Scacchi (Autorevole)"
    # Avvia il server in un thread separato per non bloccare la GUI di Flet
    threading.Thread(target=avvia_server, args=(pagina,), daemon=True).start()

ft.app(target=main)