import socket
import threading
import flet as ft
import chess # Ora il server usa la libreria scacchi!

HOST = "localhost"
PORT = 5000
clients = []
# Struttura sessioni: [ (sock1, nick1), (sock2, nick2), chess.Board() ]
sessioni = [] 

def gestisciClient(client_socket, indirizzo, page):
    nickname = "Sconosciuto"
    try:
        # 1. Ricezione Nickname
        nickname = client_socket.recv(1024).decode('utf-8').strip()
        print(f"[CONNESSO] {nickname} da {indirizzo}")
        
        clients.append((client_socket, nickname))
        page.add(ft.Text(f"{nickname} connesso. In attesa..."))
        page.update()

        # 2. Matchmaking
        sessione_corrente = None
        player_index = -1 # 0 = Bianco, 1 = Nero

        for s in sessioni:
            if len(s) < 2: # Se c'è spazio (c'è solo 1 giocatore e manca la board)
                s.insert(1, (client_socket, nickname)) # Aggiungo come secondo giocatore
                sessione_corrente = s
                player_index = 1 # Sono il Nero
                
                # Ora siamo in 2: Creiamo la Scacchiera e Iniziamo!
                board = chess.Board()
                s.append(board) # La scacchiera è l'elemento indice 2
                
                p1_sock = s[0][0]
                p2_sock = s[1][0]
                
                print(f"START: {s[0][1]} vs {s[1][1]}")
                page.add(ft.Text(f"PARTITA: {s[0][1]} (W) vs {s[1][1]} (B)"))
                page.update()

                p1_sock.send("START|WHITE".encode())
                p2_sock.send("START|BLACK".encode())
                break
        
        if not sessione_corrente:
            # Creo nuova sessione con me come primo giocatore
            nuova_s = [(client_socket, nickname)] 
            sessioni.append(nuova_s)
            sessione_corrente = nuova_s
            player_index = 0 # Sono il Bianco

        # 3. Loop di Gioco (Server Authoritative)
        while True:
            msg = client_socket.recv(1024).decode()
            if not msg: break
            
            # Controllo se la partita è iniziata (ci sono 2 player e la board)
            if len(sessione_corrente) < 3:
                continue

            board = sessione_corrente[2] # Recupero l'oggetto chess.Board
            
            # CONTROLLO 1: È il turno di questo socket?
            # board.turn è True per White, False per Black
            # player_index è 0 per White, 1 per Black
            # Quindi: se (board.turn == True e player_index == 0) -> OK
            is_white_turn = board.turn
            am_i_white = (player_index == 0)
            
            if is_white_turn != am_i_white:
                print(f"Mossa rifiutata: non è il turno di {nickname}")
                client_socket.send("ERROR|Non è il tuo turno".encode())
                continue

            # CONTROLLO 2: La mossa è valida?
            try:
                move = chess.Move.from_uci(msg)
                if move in board.legal_moves:
                    # VALIDAZIONE OK: Eseguiamo la mossa sul Server
                    board.push(move)
                    print(f"Mossa valida {msg} da {nickname}. Inoltro...")
                    
                    # Inoltra la mossa all'AVVERSARIO
                    opponent_idx = 1 if player_index == 0 else 0
                    opponent_sock = sessione_corrente[opponent_idx][0]
                    opponent_sock.send(msg.encode())
                    
                    # Controlla fine partita
                    if board.is_game_over():
                        res = board.result()
                        page.add(ft.Text(f"Partita finita: {res}"))
                        page.update()
                else:
                    print(f"Mossa illegale tentata da {nickname}: {msg}")
                    client_socket.send("ERROR|Mossa illegale".encode())
            except ValueError:
                pass

    except Exception as e:
        print(f"Errore {nickname}: {e}")
    finally:
        # Pulizia sessione (semplificata)
        if (client_socket, nickname) in clients:
            clients.remove((client_socket, nickname))
        # Rimuovi l'intera sessione se qualcuno si disconnette
        if sessione_corrente and sessione_corrente in sessioni:
            sessioni.remove(sessione_corrente)
            page.add(ft.Text(f"Sessione chiusa per disconnessione di {nickname}"))
            page.update()
        client_socket.close()

def avvia_server(page):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    page.add(ft.Text(f"SERVER AUTOREVOLE AVVIATO SU {HOST}:{PORT}"))
    page.update()
    while True:
        client, addr = server.accept()
        threading.Thread(target=gestisciClient, args=(client, addr, page), daemon=True).start()

def main(page: ft.Page):
    page.title = "Server Scacchi (Authoritative)"
    threading.Thread(target=avvia_server, args=(page,), daemon=True).start()

ft.app(target=main)