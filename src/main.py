import socket
import threading
import flet as ft

HOST = "localhost"
PORT = 5000
clients = []
sessioni = []

def gestisciClient(client_socket, indirizzo, page):
    nickname = "Sconosciuto"
    try:
        # 1. Ricezione Nickname
        nickname = client_socket.recv(1024).decode('utf-8').strip()
        print(f"[CONNESSO] {nickname} da {indirizzo}")
        
        # Aggiungiamo alla lista e aggiorniamo la GUI del server
        clients.append((client_socket, nickname))
        page.add(ft.Text(f"{nickname} connesso. In attesa di avversario..."))
        page.update()

        # 2. Logica di Matchmaking
        trovato = False
        for sessione in sessioni:
            if len(sessione) < 2:
                sessione.append((client_socket, nickname))
                if len(sessione) == 2:
                    # ABBIAMO UNA COPPIA! AVVIAMO LA PARTITA
                    p1_sock, p1_nick = sessione[0]
                    p2_sock, p2_nick = sessione[1]
                    
                    print(f"Avvio partita: {p1_nick} (Bianco) vs {p2_nick} (Nero)")
                    page.add(ft.Text(f"MATCH: {p1_nick} vs {p2_nick}"))
                    page.update()

                    # Invio segnale di START e COLORE
                    p1_sock.send("START|WHITE".encode())
                    p2_sock.send("START|BLACK".encode())
                trovato = True
                break
        
        if not trovato:
            # Creo nuova sessione
            sessioni.append([(client_socket, nickname)])

        # 3. Ciclo di gioco (Relay dei messaggi)
        while True:
            msg = client_socket.recv(1024)
            if not msg: break
            
            # Trova l'avversario nella sessione
            mio_avversario = None
            for s in sessioni:
                if (client_socket, nickname) in s:
                    for c_sock, c_nick in s:
                        if c_sock != client_socket:
                            mio_avversario = c_sock
                            break
            
            # Inoltra la mossa
            if mio_avversario:
                mio_avversario.send(msg)

    except Exception as e:
        print(f"Errore con {nickname}: {e}")
    finally:
        if (client_socket, nickname) in clients:
            clients.remove((client_socket, nickname))
        client_socket.close()

def avvia_server(page):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    page.add(ft.Text(f"Server avviato su {HOST}:{PORT}"))
    page.update()
    while True:
        client, addr = server.accept()
        threading.Thread(target=gestisciClient, args=(client, addr, page), daemon=True).start()

def main(page: ft.Page):
    page.title = "Server Scacchi"
    threading.Thread(target=avvia_server, args=(page,), daemon=True).start()

ft.app(target=main) # Non servono assets qui, solo log