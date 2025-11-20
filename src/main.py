# Per avviare: source .venv/bin/activate, poi python main.py
import socket
import threading
import flet as ft

HOST = "localhost"
clients = []
sessioni = []

def gestisciClient(client_socket, indirizzo, page):
    def smistamentoClient(client):
        # Prova a trovare una sessione libera (con meno di 2 client)
        for sessione in sessioni:
            if len(sessione) < 2:
                sessione.append(client)
                if len(sessione) == 2:
                    avvioPartita(sessione)
                return
        # Nessuna sessione libera, ne creo una nuova
        nuova_sessione = [client]
        sessioni.append(nuova_sessione)
    def avvioPartita(sessione):
        # Avvio partita
        print("Sostituiscimi")
    # Ricezione del nickname
    nickname = client_socket.recv(1024).decode('utf-8').strip()
    clients.append((client_socket, nickname))
    print(f"[CONNESSO] {nickname} da {indirizzo}")
    page.add(ft.Text(f"{nickname} sta attendendo di essere connesso.", client_socket))
    smistamentoClient((client_socket, nickname))
    # Rimozione del client
    clients.remove((client_socket, nickname))
    client_socket.close()

def main(page: ft.Page):
    page.title = "Server"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Crea un widget immagine usando il file dalla cartella 'assets'
    img = ft.Image(
        src="chess.png",  # NON serve scrivere "assets/flet_logo.png"
        width=100,
        height=100,
        fit=ft.ImageFit.CONTAIN, # Adatta l'immagine mantenendo le proporzioni
    )
    page.add(img)
        
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, 5000))
    server.listen()
    page.clean()
    page.add(ft.Text(f"Server in ascolto su {HOST}:5000!"))
    while True:
        client_socket, addr = server.accept()
        thread = threading.Thread(target=gestisciClient, args=(client_socket, addr, page))
        thread.start()
ft.app(target=main, assets_dir="assets")