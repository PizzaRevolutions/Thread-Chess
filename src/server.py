import socket
import threading
import flet as ft
import chess 

# Costanti di rete
INDIRIZZO_SERVER = "localhost"
PORTA_SERVER = 5000

# Liste globali per la gestione
client_connessi = []
# Struttura sessioni_gioco: [ (socket_g1, nick_g1), (socket_g2, nick_g2), scacchiera_oggetto ]
sessioni_gioco = [] 

def gestisci_client(socket_client, indirizzo_ip, pagina):
    nickname = "Sconosciuto"
    try:
        # 1. Ricezione Nickname
        nickname = socket_client.recv(1024).decode('utf-8').strip()
        print(f"[CONNESSO] {nickname} da {indirizzo_ip}")
        
        client_connessi.append((socket_client, nickname))
        pagina.add(ft.Text(f"{nickname} connesso. In attesa..."))
        pagina.update()

        # 2. Matchmaking (Creazione della partita)
        sessione_corrente = None
        indice_giocatore = -1 # 0 = Bianco, 1 = Nero

        for sessione in sessioni_gioco:
            # Se la sessione ha meno di 2 elementi, significa che c'è un solo giocatore e manca la scacchiera
            if len(sessione) < 2: 
                sessione.insert(1, (socket_client, nickname)) # Mi aggiungo come secondo giocatore
                sessione_corrente = sessione
                indice_giocatore = 1 # Sono il Nero
                
                # Ora siamo in 2: Creiamo la Scacchiera e Iniziamo!
                scacchiera = chess.Board()
                sessione.append(scacchiera) # La scacchiera diventa l'elemento indice 2
                
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
            
            # CONTROLLO 1: È il turno di questo socket?
            # scacchiera.turn è True per il Bianco, False per il Nero
            # indice_giocatore è 0 per il Bianco, 1 per il Nero
            e_turno_bianco = scacchiera.turn
            sono_il_bianco = (indice_giocatore == 0)
            
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
                        pagina.add(ft.Text(f"Partita finita: {risultato}"))
                        pagina.update()
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
        
        # Rimuovi l'intera sessione se uno dei due si disconnette
        if sessione_corrente and sessione_corrente in sessioni_gioco:
            sessioni_gioco.remove(sessione_corrente)
            pagina.add(ft.Text(f"Sessione chiusa per disconnessione di {nickname}"))
            pagina.update()
        
        socket_client.close()

def avvia_server(pagina):
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_server.bind((INDIRIZZO_SERVER, PORTA_SERVER))
    socket_server.listen()
    
    pagina.add(ft.Text(f"SERVER AUTOREVOLE AVVIATO SU {INDIRIZZO_SERVER}:{PORTA_SERVER}"))
    pagina.update()
    
    while True:
        client, indirizzo = socket_server.accept()
        threading.Thread(target=gestisci_client, args=(client, indirizzo, pagina), daemon=True).start()

def principale(pagina: ft.Page):
    pagina.title = "Server Scacchi (Autorevole)"
    # Avvia il server in un thread separato per non bloccare la GUI di Flet
    threading.Thread(target=avvia_server, args=(pagina,), daemon=True).start()

ft.app(target=main)