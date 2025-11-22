import flet as ft
import socket
import threading
import chess

# Costanti di connessione
INDIRIZZO_SERVER = "localhost"
PORTA_SERVER = 5000

class ClientScacchi:
    def __init__(self, pagina: ft.Page):
        self.pagina = pagina
        self.pagina.title = "Client Scacchi"
        self.pagina.bgcolor = "#263238"
        self.pagina.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.pagina.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        self.socket_client = None
        self.scacchiera = chess.Board()
        self.mio_colore = None 
        self.mio_turno = False
        self.caselle_grafiche = {} # Dizionario per mappare le caselle UI

        # UI Login
        self.campo_nickname = ft.TextField(label="Nickname", width=200, text_align=ft.TextAlign.CENTER)
        self.etichetta_stato = ft.Text("", size=20, weight="bold")
        
        self.mostra_schermata_login()

    def mostra_schermata_login(self):
        self.pagina.clean()
        self.pagina.add(
            ft.Column([
                ft.Text("Scacchi Online", size=40, weight="bold"),
                self.campo_nickname,
                ft.ElevatedButton("Entra in Coda", on_click=self.connetti_al_server)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def mostra_schermata_attesa(self):
        self.pagina.clean()
        self.pagina.add(ft.Column([ft.ProgressRing(), ft.Text("In attesa dell'avversario...", size=20)], alignment=ft.MainAxisAlignment.CENTER))
        self.pagina.update()

    def connetti_al_server(self, evento):
        if not self.campo_nickname.value: return
        
        self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_client.connect((INDIRIZZO_SERVER, PORTA_SERVER))
        self.socket_client.send(self.campo_nickname.value.encode())
        
        self.mostra_schermata_attesa()
        # Avvia il thread per ascoltare il server
        threading.Thread(target=self.ciclo_ricezione_dati, daemon=True).start()

    def ciclo_ricezione_dati(self):
        while True:
            try:
                dati_ricevuti = self.socket_client.recv(1024).decode()
                if not dati_ricevuti: break
                
                if dati_ricevuti.startswith("START|"):
                    colore_assegnato = dati_ricevuti.split("|")[1]
                    self.mio_colore = chess.WHITE if colore_assegnato == "WHITE" else chess.BLACK
                    self.mio_turno = (self.mio_colore == chess.WHITE)
                    self.inizializza_scacchiera_grafica()
                
                elif dati_ricevuti.startswith("ERROR|"):
                    messaggio_errore = dati_ricevuti.split("|")[1]
                    print(f"ERRORE DAL SERVER: {messaggio_errore}")
                    
                else:
                    self.gestisci_mossa_avversario(dati_ricevuti)
                    
            except Exception as errore:
                print(f"Disconnesso: {errore}")
                break

    def inizializza_scacchiera_grafica(self):
        self.pagina.clean()
        immagine_scacchiera = ft.Image(src="board.png", width=400, height=400, fit=ft.ImageFit.FILL)
        colonna_griglia = ft.Column(spacing=0, width=400, height=400)
        
        # Orientamento scacchiera (Se sono bianco vedo 1 in basso, se nero vedo 8 in basso)
        righe = range(7, -1, -1) if self.mio_colore == chess.WHITE else range(8)
        colonne = range(8) if self.mio_colore == chess.WHITE else range(7, -1, -1)

        for riga_idx in righe:
            riga_componenti = []
            for colonna_idx in colonne:
                # Calcola il nome della casella (es. "e4")
                nome_casella = chess.square_name(chess.square(colonna_idx, riga_idx))
                
                contenitore = ft.Container(width=50, height=50, alignment=ft.alignment.center)
                
                # Zona di rilascio per il Drag & Drop
                bersaglio = ft.DragTarget(
                    group="scacchi", 
                    content=contenitore, 
                    on_accept=self.al_rilascio_pezzo, 
                    data=nome_casella
                )
                
                self.caselle_grafiche[nome_casella] = contenitore
                riga_componenti.append(bersaglio)
            
            colonna_griglia.controls.append(ft.Row(controls=riga_componenti, spacing=0))

        self.etichetta_stato.value = "Tocca a te!" if self.mio_turno else "Attendi avversario..."
        
        self.pagina.add(
            self.etichetta_stato,
            ft.Container(
                ft.Stack([immagine_scacchiera, colonna_griglia], width=400, height=400), 
                border=ft.border.all(2, "white")
            ),
            ft.Text(f"Tu sei: {'BIANCO' if self.mio_colore == chess.WHITE else 'NERO'}")
        )
        self.aggiorna_pezzi()
        self.pagina.update()

    def aggiorna_pezzi(self):
        mappa_pezzi = self.scacchiera.piece_map()
        
        for nome_casella, contenitore in self.caselle_grafiche.items():
            pezzo = mappa_pezzi.get(chess.parse_square(nome_casella))
            contenitore.content = None
            
            if pezzo:
                # Esempio nome file: wP.png (White Pawn) o bK.png (Black King)
                nome_file_img = f"{'w' if pezzo.color else 'b'}{pezzo.symbol().upper()}.png"
                immagine = ft.Image(src=nome_file_img, width=40, height=40)
                
                # Rendi il pezzo trascinabile solo se è del mio colore
                if pezzo.color == self.mio_colore:
                    contenitore.content = ft.Draggable(
                        group="scacchi", 
                        content=immagine, 
                        content_when_dragging=ft.Container(content=immagine, opacity=0.5), 
                        data=nome_casella
                    )
                else:
                    contenitore.content = immagine
        self.pagina.update()

    def al_rilascio_pezzo(self, evento: ft.DragTargetEvent):
        # 1. Controllo preliminare Client: è il mio turno?
        if not self.mio_turno: return
        
        casella_partenza = self.pagina.get_control(evento.src_id).data
        casella_arrivo = evento.control.data
        
        mossa = None
        try:
            # Logica gestione promozione semplificata (sempre Regina 'q')
            mossa = self.scacchiera.find_move(chess.parse_square(casella_partenza), chess.parse_square(casella_arrivo))
        except:
            try: 
                # Tentativo manuale con promozione
                mossa = chess.Move.from_uci(f"{casella_partenza}{casella_arrivo}q")
            except: 
                mossa = None

        # 2. Se la mossa è legale localmente, la inviamo al server
        if mossa and mossa in self.scacchiera.legal_moves:
            # Eseguiamo localmente "con fiducia" (Optimistic UI update)
            self.scacchiera.push(mossa)
            self.aggiorna_pezzi()
            self.mio_turno = False
            self.etichetta_stato.value = "Turno avversario..."
            self.pagina.update()
            
            # INVIO AL SERVER
            self.socket_client.send(mossa.uci().encode())
        else:
            self.aggiorna_pezzi() # Reset visuale in caso di mossa invalida (il pezzo torna indietro)

    def gestisci_mossa_avversario(self, mossa_uci):
        try:
            mossa = chess.Move.from_uci(mossa_uci)
            # Qui ci fidiamo del server (che ha già validato la mossa)
            self.scacchiera.push(mossa)
            self.mio_turno = True
            self.etichetta_stato.value = "TOCCA A TE!"
            self.aggiorna_pezzi()
        except:
            pass # Ignora errori di parsing se arrivano dati sporchi

def principale(pagina: ft.Page):
    ClientScacchi(pagina)

ft.app(target=main, assets_dir="assets")