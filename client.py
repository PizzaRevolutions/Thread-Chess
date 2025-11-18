# Client per progetto di Scacchi con socket TCP multithread in cui si connettono due client 
# e si gioca un gioco di scacchi.

import socket
import threading

ip_server = input("In che server vuoi connetterti? (Inserisci ip): ")
port_server = input("In che porta vuoi connetterti? (Inserisci porta): ")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((ip_server, port_server))
print(f"Connesso al server {ip_server} sulla porta {port_server}")

# while True:
    # Ricezione: 1. Partite disponibili