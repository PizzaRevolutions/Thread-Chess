# Per avviare: source .venv/bin/activate, poi python main.py
import socket
import threading
import flet as ft
clients = []
sessioni = []

def gestisciClient(client_socket, indirizzo, page):
    def smistamentoClient(client):
        i = 0
        while sessioni[i].lenght == 2:
            i = i + 1
        sessioni[i].append(client)
        if sessioni[i].lenght == 2:
            avvioPartita(sessioni[i])
    def avvioPartita(sessione):
        # Avvio partita
        print("Sostituiscimi")
    # Ricezione del nickname
    nickname = client_socket.recv(1024).decode('utf-8').strip()
    clients.append((client_socket, nickname))
    print(f"[CONNESSO] {nickname} da {indirizzo}")
    page.add(ft.Text(f"{nickname} sta attendendo di essere connesso.", client_socket))
    smistamentoClient(clients[::1])
    # Rimozione del client
    clients.remove((client_socket, nickname))
    client_socket.close()

def main(page: ft.Page):
    page.title = "Server"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Configurazione parametri
    def btn_click(e):
        if not txt_server_ip.value:
            txt_server_ip.error_text = "Inserisci un ip"
            page.update()
        elif not txt_server_port.value:
            txt_server_port.error_text = "Inserisci una porta"
            page.update()
        else:
            server_ip = txt_server_ip.value
            server_port = int(txt_server_port.value)
            avvioServer(server_ip, server_port)

    txt_server_ip = ft.TextField(label="Inserisci l'ip del server")
    txt_server_port = ft.TextField(label="Inserisci la porta del server")
    page.add(txt_server_ip, txt_server_port, ft.ElevatedButton("Avvia server!", on_click=btn_click))

    # Avvio del server
    def avvioServer(server_ip, server_port):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((server_ip, server_port))
        server.listen()
        page.clean()
        page.add(ft.Text(f"Server in ascolto su {server_ip}:{server_port}!"))
        while True:
            client_socket, addr = server.accept()
            thread = threading.Thread(target=gestisciClient, args=(client_socket, addr, page))
            thread.start()
ft.app(main)