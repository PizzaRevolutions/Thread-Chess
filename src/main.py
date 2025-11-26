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
        self.mioColore = None 
        self.mioTurno = False
        self.caselleGrafica = {} # Dizionario per mappare le caselle UI
        self.casellaSelezionata = None # Casella del pezzo selezionato
        self.mosseValideEvidenziate = [] # Lista delle caselle con mosse valide evidenziate
        self.durataTimer = 600
        self.tempo_bianco = self.durataTimer
        self.tempo_nero = self.durataTimer
        self.testoTempoBianco = None
        self.testoTempoNero = None
        self.partitaTerminata = False

        # UI Login
        self.campoNickname = ft.TextField(label="Nickname", width=200, text_align=ft.TextAlign.CENTER)
        self.etichettaStatoAttuale = ft.Text("", size=20, weight="bold")
        
        self.schermataLogin()

    def schermataLogin(self):
        self.pagina.clean()
        self.pagina.add(
            ft.Column([
                ft.Text("Scacchi Online", size=40, weight="bold"),
                self.campoNickname,
                ft.ElevatedButton("Entra in Coda", on_click=self.connetti_al_server)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def mostra_schermata_attesa(self):
        self.pagina.clean()
        self.pagina.add(ft.Column([ft.ProgressRing(), ft.Text("In attesa dell'avversario...", size=20)],alignment=ft.MainAxisAlignment.CENTER))
        self.pagina.update()

    def connetti_al_server(self, evento):
        if not self.campoNickname.value: return
        
        try:
            self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_client.connect((INDIRIZZO_SERVER, PORTA_SERVER))
            self.socket_client.send(self.campoNickname.value.encode())
            
            self.mostra_schermata_attesa()
            # Avvia il thread per ascoltare il server
            threading.Thread(target=self.cicloRicezione, daemon=True).start()
        except Exception as e:
            print(f"Errore nella connessione: {e}")
            self.etichettaStatoAttuale.value = f"Errore di connessione: {e}"
            self.pagina.update()
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None

    def gestisci_disconnessione(self):
        """Gestisce la disconnessione dal server"""
        # Se la partita è già terminata e abbiamo già mostrato la schermata finale,
        # non sovrascriviamo l'interfaccia con il messaggio di disconnessione.
        if self.partitaTerminata:
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None
            return

        # Se la connessione cade ma, secondo la nostra scacchiera locale,
        # la partita risulta già finita, deduciamo il risultato e mostriamo
        # la schermata finale invece del messaggio generico.
        try:
            if self.scacchiera.is_game_over() and self.mioColore is not None:
                risultato = self.scacchiera.result()  # "1-0", "0-1", "1/2-1/2", ecc.
                if risultato == "1-0":
                    messaggio = "Hai vinto!" if self.mioColore == chess.WHITE else "Hai perso!"
                elif risultato == "0-1":
                    messaggio = "Hai vinto!" if self.mioColore == chess.BLACK else "Hai perso!"
                else:
                    messaggio = "Patta!"
                self.mostra_schermata_fine_partita(messaggio)
            else:
                self.mioTurno = False
                self.etichettaStatoAttuale.value = "Disconnesso dal server. Ricarica la pagina."
                self.pagina.update()
        except Exception:
            # In caso di problemi usiamo il messaggio di fallback.
            self.mioTurno = False
            self.etichettaStatoAttuale.value = "Disconnesso dal server. Ricarica la pagina."
            self.pagina.update()

        if self.socket_client:
            try:
                self.socket_client.close()
            except:
                pass
            self.socket_client = None

    def cicloRicezione(self):
        while True:
            try:
                if not self.socket_client:
                    break
                datoRicevuto = self.socket_client.recv(1024).decode()
                if not datoRicevuto: 
                    break

                if datoRicevuto.startswith("START|"):
                    coloreAssegnato = datoRicevuto.split("|")[1]
                    self.mioColore = chess.WHITE if coloreAssegnato == "WHITE" else chess.BLACK
                    self.mioTurno = (self.mioColore == chess.WHITE)
                    self.schermataScacchiera()
                elif datoRicevuto.startswith("ERROR|"):
                    messaggioErrore = datoRicevuto.split("|")[1]
                    print(f"ERRORE DAL SERVER: {messaggioErrore}")
                elif datoRicevuto.startswith("MOVES|"):
                    # Formato: MOVES|e4,e5,e6 (lista di caselle separate da virgola)
                    caselle_valide = datoRicevuto.split("|")[1].split(",") if len(datoRicevuto.split("|")) > 1 and datoRicevuto.split("|")[1] else []
                    self.mosseValideEvidenziate = caselle_valide
                    self.aggiornaPezzi()
                elif datoRicevuto.startswith("TIME|"):
                    parti = datoRicevuto.split("|")
                    if len(parti) >= 3:
                        try:
                            tempo_bianco = int(float(parti[1]))
                            tempo_nero = int(float(parti[2]))
                            self.aggiorna_timer_ui(tempo_bianco, tempo_nero)
                        except ValueError:
                            pass
                elif datoRicevuto.startswith("TIMEOUT|"):
                    parti = datoRicevuto.split("|")
                    if len(parti) >= 2:
                        colore_scaduto = parti[1]
                        if self.mioColore is not None:
                            if (self.mioColore == chess.WHITE and colore_scaduto == "WHITE") or (
                                self.mioColore == chess.BLACK and colore_scaduto == "BLACK"
                            ):
                                messaggio = "Hai perso per tempo!"
                            else:
                                messaggio = "Hai vinto per tempo!"
                        else:
                            messaggio = "Tempo scaduto."
                        self.mostra_schermata_fine_partita(messaggio)
                        break
                elif datoRicevuto.startswith("GAMEOVER|"):
                    parti = datoRicevuto.split("|")
                    esito = parti[1] if len(parti) > 1 else ""
                    if esito == "WIN":
                        messaggio = "Hai vinto!"
                    elif esito == "LOSE":
                        messaggio = "Hai perso!"
                    elif esito == "DRAW":
                        messaggio = "Patta!"
                    elif esito == "OPPONENT_LEFT":
                        messaggio = "Il tuo avversario ha abbandonato!"
                    else:
                        messaggio = "Partita terminata."
                    self.mostra_schermata_fine_partita(messaggio)
                    break
                else:
                    self.mossaAvversario(datoRicevuto)
                    
            except (ConnectionResetError, OSError, BrokenPipeError) as errore:
                print(f"Disconnesso: {errore}")
                # Se non siamo già arrivati a una schermata di fine partita,
                # gestiamo la disconnessione in modo generico.
                if self.socket_client is not None and not self.partitaTerminata:
                    self.gestisci_disconnessione()
                break
            except Exception as errore:
                print(f"Errore nella ricezione: {errore}")
                break
        # Alla fine chiudiamo il socket se è ancora aperto
        if self.socket_client:
            try:
                self.socket_client.close()
            except:
                pass
            self.socket_client = None

    def mostra_schermata_fine_partita(self, messaggio):
        """Pulisce la pagina e mostra il risultato della partita con possibilità di nuova partita."""
        # Segna che la partita è conclusa per evitare messaggi di disconnessione sovrascrittivi
        self.partitaTerminata = True
        # Reset stato interno
        self.mioTurno = False
        self.casellaSelezionata = None
        self.mosseValideEvidenziate = []
        self.scacchiera = chess.Board()
        self.caselleGrafica = {}

        self.pagina.clean()
        titolo = ft.Text(messaggio, size=40, weight="bold")
        bottone_nuova = ft.ElevatedButton(
            "Gioca un'altra partita",
            on_click=self.riavvia_partita
        )
        bottone_home = ft.TextButton(
            "Torna al menu principale",
            on_click=lambda e: self.schermataLogin()
        )
        self.pagina.add(
            ft.Column(
                [
                    titolo,
                    ft.Row(
                        [bottone_nuova, bottone_home],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        self.pagina.update()

    def riavvia_partita(self, evento):
        """Ricrea una nuova connessione e rimette il giocatore in coda con lo stesso nickname."""
        # Mantieni il nickname già inserito, se presente
        if not self.campoNickname.value:
            # Se per qualche motivo è vuoto, torna al menu standard
            self.schermataLogin()
            return
        # Reimposta timer
        self.tempo_bianco = self.durataTimer
        self.tempo_nero = self.durataTimer
        # Connetti nuovamente al server
        self.connetti_al_server(evento)

    def schermataScacchiera(self):
        self.pagina.clean()
        self.tempo_bianco = self.durataTimer
        self.tempo_nero = self.durataTimer
        immagineScacchiera = ft.Image(src="board.png", width=400, height=400, fit=ft.ImageFit.FILL)
        colonnaGriglia = ft.Column(spacing=0, width=400, height=400)
        
        # Orientamento scacchiera (Se sono bianco vedo 1 in basso, se nero vedo 8 in basso)
        righe = range(7, -1, -1) if self.mioColore == chess.WHITE else range(8)
        colonne = range(8) if self.mioColore == chess.WHITE else range(7, -1, -1)

        for riga_idx in righe:
            rigaComponenti = []
            for colonna_idx in colonne:
                # Calcola il nome della casella (es. "e4")
                nomeCasella = chess.square_name(chess.square(colonna_idx, riga_idx))
                
                contenitore = ft.Container(width=50, height=50, alignment=ft.alignment.center)
                
                # Zona di rilascio per il Drag & Drop e click
                bersaglio = ft.GestureDetector(
                    content=ft.DragTarget(
                        group="scacchi", 
                        content=contenitore, 
                        on_accept=self.rilascioPezzo, 
                        data=nomeCasella
                    ),
                    on_tap=lambda e, casella=nomeCasella: self.clickSuCasella(e, casella)
                )
                
                self.caselleGrafica[nomeCasella] = contenitore
                rigaComponenti.append(bersaglio)
            
            colonnaGriglia.controls.append(ft.Row(controls=rigaComponenti, spacing=0))

        self.etichettaStatoAttuale.value = "Tocca a te!" if self.mioTurno else "Attendi avversario..."
        self.testoTempoBianco = ft.Text("", size=18, weight="bold", color="white")
        self.testoTempoNero = ft.Text("", size=18, weight="bold", color="white")
        
        self.pagina.add(
            self.etichettaStatoAttuale,
            ft.Row(
                [
                    self.testoTempoBianco,
                    self.testoTempoNero
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                width=400
            ),
            ft.Container(
                ft.Stack([immagineScacchiera, colonnaGriglia], width=400, height=400), 
                border=ft.border.all(2, "white")
            ),
            ft.Text(f"Tu sei: {'BIANCO' if self.mioColore == chess.WHITE else 'NERO'}")
        )
        self.aggiorna_timer_ui(self.tempo_bianco, self.tempo_nero)
        self.aggiornaPezzi()
        self.pagina.update()

    def aggiornaPezzi(self):
        mappaPezzi = self.scacchiera.piece_map()
        
        for nomeCasella, contenitore in self.caselleGrafica.items():
            pezzo = mappaPezzi.get(chess.parse_square(nomeCasella))
            
            # Determina il colore di sfondo della casella
            bgcolor = None
            border = None
            
            # Evidenzia la casella selezionata
            if nomeCasella == self.casellaSelezionata:
                bgcolor = "#4CAF50"  # Verde per la casella selezionata
                border = ft.border.all(3, "#2E7D32")
            # Evidenzia le caselle con mosse valide
            elif nomeCasella in self.mosseValideEvidenziate:
                bgcolor = "#81C784"  # Verde chiaro per mosse valide
                border = ft.border.all(2, "#66BB6A")
            
            # Aggiorna lo sfondo del contenitore
            contenitore.bgcolor = bgcolor
            contenitore.border = border
            
            contenitore.content = None
            
            if pezzo:
                # Esempio nome file: wP.png (White Pawn) o bK.png (Black King)
                nomeImgPezzo = f"{'w' if pezzo.color else 'b'}{pezzo.symbol().upper()}.png"
                immaginePezzo = ft.Image(src=nomeImgPezzo, width=40, height=40)
                
                # Rendi il pezzo trascinabile solo se è del mio colore
                if pezzo.color == self.mioColore:
                    immaginePezzoDrag = ft.Image(src=nomeImgPezzo, width=60, height=60)
                    # Aggiungi GestureDetector per gestire il click
                    draggable = ft.Draggable(
                        group="scacchi", 
                        content=immaginePezzo, 
                        content_when_dragging=ft.Container(content=immaginePezzoDrag, opacity=0.5), 
                        data=nomeCasella
                    )
                    contenitore.content = ft.GestureDetector(
                        content=draggable,
                        on_tap=lambda e, casella=nomeCasella: self.clickSuPezzo(e, casella)
                    )
                else:
                    contenitore.content = immaginePezzo
            else:
                # Se non c'è pezzo, mantieni l'evidenziazione se necessario
                if nomeCasella not in self.mosseValideEvidenziate and nomeCasella != self.casellaSelezionata:
                    contenitore.bgcolor = None
                    contenitore.border = None
                # Altrimenti l'evidenziazione è già stata impostata sopra
        self.pagina.update()

    def formatta_tempo(self, secondi):
        secondi = max(0, int(secondi))
        minuti = secondi // 60
        residuo = secondi % 60
        return f"{minuti:02d}:{residuo:02d}"

    def aggiorna_timer_ui(self, tempo_bianco, tempo_nero):
        self.tempo_bianco = tempo_bianco
        self.tempo_nero = tempo_nero
        if self.testoTempoBianco:
            self.testoTempoBianco.value = f"Tempo Bianco: {self.formatta_tempo(tempo_bianco)}"
        if self.testoTempoNero:
            self.testoTempoNero.value = f"Tempo Nero: {self.formatta_tempo(tempo_nero)}"
        if self.testoTempoBianco or self.testoTempoNero:
            self.pagina.update()

    def richiediMosseValide(self, casella):
        """Richiede al server le mosse valide per una casella"""
        if self.socket_client and self.mioTurno:
            try:
                self.socket_client.send(f"MOVES|{casella}".encode())
            except (ConnectionResetError, OSError, BrokenPipeError) as e:
                print(f"Errore invio richiesta mosse: {e}")
                self.gestisci_disconnessione()
    
    def clickSuPezzo(self, evento, nomeCasella):
        """Gestisce il click su un pezzo per selezionarlo"""
        if not self.mioTurno:
            return
        
        # Se clicco sullo stesso pezzo, deseleziona
        if self.casellaSelezionata == nomeCasella:
            self.casellaSelezionata = None
            self.mosseValideEvidenziate = []
            self.aggiornaPezzi()
            return
        
        # Verifica che ci sia un pezzo del mio colore su questa casella
        pezzo = self.scacchiera.piece_at(chess.parse_square(nomeCasella))
        if pezzo and pezzo.color == self.mioColore:
            self.casellaSelezionata = nomeCasella
            self.richiediMosseValide(nomeCasella)
    
    def clickSuCasella(self, evento, nomeCasella):
        """Gestisce il click su una casella per muovere il pezzo selezionato"""
        if not self.mioTurno:
            return
        
        # Se ho un pezzo selezionato e clicco su una casella valida, muovo
        if self.casellaSelezionata and nomeCasella in self.mosseValideEvidenziate:
            casella_partenza = self.casellaSelezionata
            casella_arrivo = nomeCasella
            
            mossa = None
            try:
                mossa = self.scacchiera.find_move(chess.parse_square(casella_partenza), chess.parse_square(casella_arrivo))
            except:
                try:
                    mossa = chess.Move.from_uci(f"{casella_partenza}{casella_arrivo}q")
                except:
                    mossa = None
            
            if mossa and mossa in self.scacchiera.legal_moves:
                self.scacchiera.push(mossa)
                self.casellaSelezionata = None
                self.mosseValideEvidenziate = []
                self.aggiornaPezzi()
                self.mioTurno = False
                self.etichettaStatoAttuale.value = "Turno avversario..."
                self.pagina.update()
                
                try:
                    self.socket_client.send(mossa.uci().encode())
                except (ConnectionResetError, OSError, BrokenPipeError) as e:
                    print(f"Errore invio mossa: {e}")
                    self.gestisci_disconnessione()
        # Se clicco su un altro pezzo del mio colore, lo seleziono
        elif nomeCasella in self.caselleGrafica:
            pezzo = self.scacchiera.piece_at(chess.parse_square(nomeCasella))
            if pezzo and pezzo.color == self.mioColore:
                self.clickSuPezzo(None, nomeCasella)
    
    def rilascioPezzo(self, evento: ft.DragTargetEvent):
        # 1. Controllo preliminare Client: è il mio turno?
        if not self.mioTurno: return
        
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
            self.casellaSelezionata = None
            self.mosseValideEvidenziate = []
            self.aggiornaPezzi()
            self.mioTurno = False
            self.etichettaStatoAttuale.value = "Turno avversario..."
            self.pagina.update()
            
            # INVIO AL SERVER
            try:
                self.socket_client.send(mossa.uci().encode())
            except (ConnectionResetError, OSError, BrokenPipeError) as e:
                print(f"Errore invio mossa: {e}")
                self.gestisci_disconnessione()
        else:
            self.aggiornaPezzi() # Reset visuale in caso di mossa invalida (il pezzo torna indietro)

    def mossaAvversario(self, mossa_uci):
        try:
            mossa = chess.Move.from_uci(mossa_uci)
            # Qui ci fidiamo del server (che ha già validato la mossa)
            self.scacchiera.push(mossa)
            self.casellaSelezionata = None
            self.mosseValideEvidenziate = []
            self.mioTurno = True
            self.etichettaStatoAttuale.value = "TOCCA A TE!"
            self.aggiornaPezzi()
        except:
            pass # Ignora errori di parsing se arrivano dati sporchi

def main(pagina: ft.Page):
    ClientScacchi(pagina)

ft.app(target=main, assets_dir="assets")