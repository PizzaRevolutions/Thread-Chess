import flet as ft
import socket
import threading
import chess
import re
import time

# Costanti di connessione (valori di default)
INDIRIZZO_SERVER = "localhost"
PORTA_SERVER = 5000

class ClientScacchi:
    def __init__(self, pagina: ft.Page):
        self.pagina = pagina
        self.pagina.title = "Client Scacchi"
        self.pagina.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.pagina.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        self.socket_client = None
        self.scacchiera = chess.Board()
        self.mioColore = None 
        self.mioTurno = False
        self.caselleGrafica = {} # Dizionario per mappare le caselle UI
        self.casellaSelezionata = None # Casella del pezzo selezionato
        self.mosseValideEvidenziate = [] # Lista delle caselle con mosse valide evidenziate
        # Durata timer (in secondi) per la partita corrente.
        # Viene impostata in base alla modalità scelta nel menu.
        self.durataTimer = 600
        self.tempo_bianco = self.durataTimer
        self.tempo_nero = self.durataTimer
        self.testoTempoBianco = None
        self.testoTempoNero = None
        self.partitaTerminata = False
        self.listaMessaggiChat = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        self.campoInputChat = ft.TextField(hint_text="Scrivi un messaggio...", expand=True, on_submit=self.invia_messaggio_chat)

        # Lista semplice di parole vietate lato client
        self.parole_vietate = [
            "cazzo",
            "merda",
            "stronzo",
            "vaffanculo",
        ]

        # Mappatura modalità -> durata in secondi (0 = nessun timer)
        self.mappa_modalita_timer = {
            "600": 600,   # Rapid 10'
            "1200": 1200, # Classic 20'
            "300": 300,   # Blitz 5'
            "180": 180,   # Blitz 3'
            "60": 60,     # Bullet 1'
            "0": 0,       # No time
        }
        self.valore_modalita_selezionata = "600"  # default Rapid 10'

        # UI Login
        self.campoNickname = ft.TextField(label="Nickname", width=250, text_align=ft.TextAlign.CENTER)
        # Campo per selezionare un server diverso da quello di default.
        # Formato consigliato: "indirizzo:porta" (es. "192.168.1.10:5000").
        # Se lasciato vuoto, verranno usati i valori di default definiti sopra.
        self.campoServer = ft.TextField(
            label="Server (es. 192.168.1.10:5000)",
            width=250,
            text_align=ft.TextAlign.CENTER,
            value=f"{INDIRIZZO_SERVER}:{PORTA_SERVER}",
        )
        # Funzione helper per creare l'opzione con immagine personalizzata
        def opzione_con_immagine(key, text, image_path):
            return ft.dropdown.Option(
                key=key,
                content=ft.Row(
                    [
                        ft.Image(src=image_path, width=20, height=20), # La tua icona PNG
                        ft.Text(text),                                 # Il testo dell'opzione
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # È importante lasciare anche 'text' per la visualizzazione quando il menu è chiuso
                text=text 
            )
        # Selettore tema scacchiera
        self.dropdownTemaScacchiera = ft.Dropdown(
            label="Tema scacchiera",
            width=250,
            options=[
                opzione_con_immagine(key="board.png", text="Default", image_path="board.png"),
                opzione_con_immagine(key="darkgreen_board.png", text="Verde Scuro", image_path="darkgreen_board.png"),
                opzione_con_immagine(key="lightgreen_board.png", text="Verde chiaro", image_path="lightgreen_board.png"),
                opzione_con_immagine(key="aqua_board.png", text="Acqua", image_path="aqua_board.png"),
                opzione_con_immagine(key="brown_board.png", text="Marrone", image_path="brown_board.png"),
                opzione_con_immagine(key="bw_board.png", text="Bianco e Nero", image_path="bw_board.png"),
                opzione_con_immagine(key="gray_board.png", text="Grigio", image_path="gray_board.png"),
                opzione_con_immagine(key="pink_board.png", text="Rosa", image_path="pink_board.png"),
                opzione_con_immagine(key="purple_board.png", text="Viola", image_path="purple_board.png"),
                opzione_con_immagine(key="red_board.png", text="Rosso", image_path="red_board.png"),
                opzione_con_immagine(key="yellow_board.png", text="Giallo", image_path="yellow_board.png"),
            ],
            on_change=self.on_cambio_tema_scacchiera,
        )
        # Selettore modalità / timer
        self.dropdownModalita = ft.Dropdown(
            label="Modalità di gioco",
            width=250,
            value=self.valore_modalita_selezionata,
            options=[
                opzione_con_immagine(key="1200", text="Classic (20 minuti)", image_path="classic.png"),
                opzione_con_immagine(key="600", text="Rapid (10 minuti)", image_path="rapid.png"),
                opzione_con_immagine(key="300", text="Blitz (5 minuti)", image_path="blitz.png"),
                opzione_con_immagine(key="180", text="Blitz (3 minuti)", image_path="blitz.png"),
                opzione_con_immagine(key="60", text="Bullet (1 minuto)", image_path="bullet.png"),
                opzione_con_immagine(key="0", text="No time", image_path="no_time.png"),
            ],
            on_change=self.on_cambio_modalita,
        )
        self.etichettaStatoAttuale = ft.Text("", size=16, weight="bold", color="red")
        self.schermataLogin()

    def schermataLogin(self):
        self.pagina.overlay.clear()
        self.pagina.clean()
        self.etichettaStatoAttuale.value = ""  # Resetta il testo vecchio
        self.pagina.add(
            ft.Column([
                ft.Text("Scacchi Online", size=40, weight="bold"),
                self.campoNickname,
                self.dropdownTemaScacchiera,
                self.campoServer,
                self.dropdownModalita,
                self.etichettaStatoAttuale,
                ft.ElevatedButton("Entra in Coda", on_click=self.connetti_al_server),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
    
    def invia_messaggio_chat(self, e):
        testo = self.campoInputChat.value
        if not testo or not self.socket_client:
            return
        
        try:
            # Pulisci il campo input
            self.campoInputChat.value = ""
            self.campoInputChat.focus()
            self.pagina.update()
            
            # Invia al server
            msg = f"CHAT|{testo}"
            self.socket_client.send(msg.encode())
        except Exception as ex:
            print(f"Errore invio chat: {ex}")
            self.gestisci_disconnessione()

    def nickname_valido(self, nickname: str) -> bool:
        """Valida il nickname: non vuoto, non troppo lungo, senza parolacce o simboli strani."""
        nickname = (nickname or "").strip()

        if not nickname:
            self.etichettaStatoAttuale.value = "Inserisci un nickname."
            self.pagina.update()
            return False

        # Lunghezza massima
        if len(nickname) > 16:
            self.etichettaStatoAttuale.value = "Nickname troppo lungo (max 16 caratteri)."
            self.pagina.update()
            return False

        # Solo lettere, numeri e underscore
        if not re.fullmatch(r"[A-Za-z0-9_]+", nickname):
            self.etichettaStatoAttuale.value = "Nickname: solo lettere, numeri e _ (niente simboli strani)."
            self.pagina.update()
            return False

        # Controllo parolacce (match parziale, case-insensitive)
        nick_lower = nickname.lower()
        for parola in self.parole_vietate:
            if parola in nick_lower:
                self.etichettaStatoAttuale.value = "Nickname non consentito."
                self.pagina.update()
                return False

        # Se tutto ok, pulisco eventuali messaggi di errore
        self.etichettaStatoAttuale.value = ""
        self.pagina.update()
        return True

    def on_cambio_modalita(self, evento: ft.ControlEvent):
        """Aggiorna il valore della modalità selezionata e la durata del timer locale."""
        valore = evento.control.value or "600"
        self.valore_modalita_selezionata = valore
        durata = self.mappa_modalita_timer.get(valore, 600)
        self.durataTimer = durata
    
    def on_cambio_tema_scacchiera(self, evento: ft.ControlEvent):
        self.tema_scacchiera = evento.control.value or "board.png"


    def nome_modalita_corrente(self) -> str:
        """Restituisce una descrizione leggibile della modalità in base al timer selezionato."""
        durata = self.durataTimer
        if durata == 1200:
            return "Classic (20 minuti)"
        if durata == 600:
            return "Rapid (10 minuti)"
        if durata == 300:
            return "Blitz (5 minuti)"
        if durata == 180:
            return "Blitz (3 minuti)"
        if durata == 60:
            return "Bullet (1 minuto)"
        if durata == 0:
            return "No time"
        return f"Custom ({durata} s)"

    def mostra_schermata_attesa(self):
        self.pagina.clean()
        self.pagina.add(ft.Column([ft.ProgressRing(), ft.Text("In attesa dell'avversario...", size=20)],alignment=ft.MainAxisAlignment.CENTER))
        self.pagina.update()

    def connetti_al_server(self, evento):
        nickname = self.campoNickname.value or ""
        if not self.nickname_valido(nickname):
            return

        # Normalizzo il valore (ad es. senza spazi esterni)
        self.campoNickname.value = nickname.strip()

        # Lettura e parsing del server selezionato
        testo_server = (self.campoServer.value or "").strip()
        host = INDIRIZZO_SERVER
        porta = PORTA_SERVER
        if testo_server:
            try:
                if ":" in testo_server:
                    host_part, porta_part = testo_server.rsplit(":", 1)
                    host_part = host_part.strip() or host
                    porta = int(porta_part.strip())
                    host = host_part
                else:
                    # Se non è specificata la porta, uso quella di default
                    host = testo_server
            except Exception:
                self.etichettaStatoAttuale.value = "Formato server non valido. Usa es. 'indirizzo:5000'."
                self.pagina.update()
                return

        # Aggiorno la durata del timer locale in base alla modalità selezionata
        durata_selezionata = self.mappa_modalita_timer.get(self.valore_modalita_selezionata, 600)
        self.durataTimer = durata_selezionata

        try:
            self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_client.connect((host, porta))
            # Invia al server nickname e durata timer (in secondi). 0 = nessun timer.
            messaggio_iniziale = f"{self.campoNickname.value}|{durata_selezionata}"
            self.socket_client.send(messaggio_iniziale.encode())
            
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

        # Se la connessione cade, proviamo prima a dedurre un esito sensato
        # usando l'informazione locale (scacchiera e timer), così evitiamo
        # il generico "Disconnesso dal server" nei casi di fine partita.
        try:
            # 1) Se per le regole degli scacchi la posizione è già finita (matto/stallo)
            #    usiamo il risultato della scacchiera.
            if self.scacchiera.is_game_over() and self.mioColore is not None:
                risultato = self.scacchiera.result()  # "1-0", "0-1", "1/2-1/2", ecc.
                if risultato == "1-0":
                    messaggio = "Hai vinto!" if self.mioColore == chess.WHITE else "Hai perso!"
                elif risultato == "0-1":
                    messaggio = "Hai vinto!" if self.mioColore == chess.BLACK else "Hai perso!"
                else:
                    messaggio = "Patta!"
                self.mostra_schermata_fine_partita(messaggio)
            # 2) Altrimenti, se abbiamo informazioni di timer, deduciamo una
            #    possibile vittoria/sconfitta/patta per tempo.
            elif self.mioColore is not None and self.tempo_bianco is not None and self.tempo_nero is not None:
                # Determina il mio tempo e quello avversario dagli ultimi valori noti
                if self.mioColore == chess.WHITE:
                    mio_tempo = self.tempo_bianco
                    tempo_avversario = self.tempo_nero
                else:
                    mio_tempo = self.tempo_nero
                    tempo_avversario = self.tempo_bianco

                if mio_tempo <= 0 and tempo_avversario > 0:
                    messaggio = "Hai perso per tempo!"
                    self.mostra_schermata_fine_partita(messaggio)
                elif tempo_avversario <= 0 and mio_tempo > 0:
                    messaggio = "Hai vinto per tempo (tempo avversario esaurito)!"
                    self.mostra_schermata_fine_partita(messaggio)
                elif mio_tempo <= 0 and tempo_avversario <= 0:
                    messaggio = "Patta: tempo esaurito per entrambi."
                    self.mostra_schermata_fine_partita(messaggio)
                else:
                    # Nessuna conclusione chiara: messaggio generico.
                    self.mioTurno = False
                    self.etichettaStatoAttuale.value = "Disconnesso dal server. Ricarica la pagina."
                    self.pagina.update()
            else:
                # Nessuna informazione sufficiente: messaggio generico.
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
                    messaggioErrore = datoRicevuto.split("|", 1)[1] if "|" in datoRicevuto else "Errore dal server"
                    print(f"ERRORE DAL SERVER: {messaggioErrore}")
                    # Torno alla schermata di login mostrando l'errore
                    self.schermataLogin()
                    self.etichettaStatoAttuale.value = messaggioErrore
                    self.pagina.update()
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
                elif datoRicevuto.startswith("TIMEOUT|"):
                    # Informazione di compatibilità: il vero esito è già stato inviato
                    # tramite GAMEOVER|...; se per qualche motivo non è arrivato,
                    # usiamo comunque un messaggio di tempo scaduto.
                    if self.partitaTerminata:
                        continue
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
                elif datoRicevuto.startswith("CHAT|"):
                    parti = datoRicevuto.split("|", 2)
                    if len(parti) >= 3:
                        nick_mittente = parti[1]
                        msg_text = parti[2]
                        
                        # Formattazione diversa se sono io o l'avversario
                        is_me = (nick_mittente == self.campoNickname.value)
                        colore_testo = "green" if is_me else "orange"
                        align = ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START
                        
                        bolla = ft.Row(
                            [ft.Text(f"{nick_mittente}: {msg_text}", color=colore_testo, selectable=True)],
                            alignment=align
                        )
                        self.listaMessaggiChat.controls.append(bolla)
                        self.pagina.update()
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

    def abbandona_partita(self, e):
        # 1. Chiudi "logicamente" il dialog per avviare la chiusura
        self.dialogo_abbandono.open = False
        time.sleep(0.3)
        self.pagina.update() 

        # 2. Rimuovi BRUTALMENTE il dialog dall'overlay
        # Questo distrugge l'oggetto dialog e la sua barriera associata
        self.pagina.overlay.clear()
        time.sleep(0.3)
        
        # 3. UPDATE FONDAMENTALE:
        # Questo ridisegna la pagina "pulita" (senza dialog e senza ombra)
        # È vitale farlo PRIMA di chiamare schermataLogin()
        self.pagina.update()

        # 4. Logica di gioco (disconnessione, reset variabili)
        self.partitaTerminata = True
        
        if self.socket_client:
            try:
                self.socket_client.close()
            except:
                pass
            self.socket_client = None

        self.scacchiera = chess.Board()
        self.caselleGrafica = {}
        self.mioTurno = False
        self.casellaSelezionata = None
        self.mosseValideEvidenziate = []
        self.partitaTerminata = False 

        # 5. Adesso che la grafica è pulita, carichiamo la Login
        self.schermataLogin()

    def schermataScacchiera(self):
        self.pagina.clean()
        self.tempo_bianco = self.durataTimer
        self.tempo_nero = self.durataTimer
        
        # Pulisco la chat vecchia se c'era
        self.listaMessaggiChat.controls.clear()

        # --- Codice esistente per creare la scacchiera (immagineScacchiera, colonnaGriglia, ecc.) ---
        # (Copia pure la parte di creazione di immagineScacchiera e colonnaGriglia dal tuo codice originale)
        immagineScacchiera = ft.Image(src=self.tema_scacchiera, width=400, height=400, fit=ft.ImageFit.FILL)
        colonnaGriglia = ft.Column(spacing=0, width=400, height=400, tight=True)
        
        righe = range(7, -1, -1) if self.mioColore == chess.WHITE else range(8)
        colonne = range(8) if self.mioColore == chess.WHITE else range(7, -1, -1)
        
        # ... (Loop creazione caselle identico al file originale) ...
        for riga_idx in righe:
            rigaComponenti = []
            for colonna_idx in colonne:
                nomeCasella = chess.square_name(chess.square(colonna_idx, riga_idx))
                slot = ft.Container(width=50, height=50, alignment=ft.alignment.center)
                bersaglio = ft.GestureDetector(
                    content=ft.DragTarget(group="scacchi", content=slot, on_accept=self.rilascioPezzo, data=nomeCasella),
                    on_tap=lambda e, casella=nomeCasella: self.clickSuCasella(e, casella)
                )
                self.caselleGrafica[nomeCasella] = slot
                rigaComponenti.append(bersaglio)
            colonnaGriglia.controls.append(ft.Row(controls=rigaComponenti, spacing=0, width=400, height=50, tight=True))

        # --- Container Scacchiera (Stack) ---
        container_scacchiera = ft.Container(
            ft.Stack([immagineScacchiera, colonnaGriglia], width=400, height=400),
            border=ft.border.all(2, "white"),
            padding=0
        )

        # --- Dialogo Abbandono (Codice esistente) ---
        def chiudi_popup(e):
            self.dialogo_abbandono.open = False
            self.pagina.update()

        def apri_popup(e):
            self.dialogo_abbandono.open = True
            self.pagina.update()

        self.dialogo_abbandono = ft.AlertDialog(
            modal=True, title=ft.Text("Conferma Abbandono"),
            content=ft.Text("Sei sicuro di voler abbandonare la partita?"),
            actions=[ft.TextButton("No", on_click=chiudi_popup), ft.TextButton("Sì, Abbandona", on_click=self.abbandona_partita)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.pagina.overlay.append(self.dialogo_abbandono)

        # --- UI Info e Controlli ---
        bottone_resa = ft.IconButton(icon="flag", icon_color="red", tooltip="Abbandona", on_click=apri_popup)
        self.testoTempoBianco = ft.Text("", size=18, weight="bold", color="white")
        self.testoTempoNero = ft.Text("", size=18, weight="bold", color="white")
        
        info_panel = ft.Column([
            ft.Row([bottone_resa, self.etichettaStatoAttuale], alignment=ft.MainAxisAlignment.START),
            ft.Row([self.testoTempoBianco, self.testoTempoNero], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=400) if self.durataTimer > 0 else ft.Container(),
            ft.Text(f"Tu sei: {'BIANCO' if self.mioColore == chess.WHITE else 'NERO'} | {self.nome_modalita_corrente()}")
        ])

        # --- NUOVA SEZIONE CHAT (Colonna Destra) ---
        colonna_chat = ft.Container(
            content=ft.Column([
                ft.Text("Chat Partita", weight="bold", size=16),
                ft.Container(
                    content=self.listaMessaggiChat,
                    expand=True,
                    border=ft.border.all(1, "grey"),
                    border_radius=5,
                    padding=5,
                    bgcolor="#222222" # Sfondo scuro per la chat
                ),
                ft.Row([
                    self.campoInputChat,
                    ft.IconButton(icon="send", on_click=self.invia_messaggio_chat)
                ])
            ]),
            width=250, # Larghezza fissa per la chat
            height=500, # Altezza simile alla scacchiera + info
            padding=10,
            bgcolor="#1a1a1a",
            border_radius=10
        )

        # --- LAYOUT PRINCIPALE: Row (Scacchiera + Info) | Chat ---
        layout_gioco = ft.Row(
            [
                ft.Column([info_panel, container_scacchiera], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.VerticalDivider(width=1, color="grey"),
                colonna_chat
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.START
        )

        self.etichettaStatoAttuale.value = ("Tocca a te!" if self.mioTurno else "Attendi avversario...")
        self.pagina.add(layout_gioco)
        
        if self.durataTimer > 0:
            self.aggiorna_timer_ui(self.tempo_bianco, self.tempo_nero)
            
        self.aggiornaPezzi()
        self.pagina.update()

    def aggiornaPezzi(self):
        mappaPezzi = self.scacchiera.piece_map()
        
        for nomeCasella, contenitore in self.caselleGrafica.items():
            pezzo = mappaPezzi.get(chess.parse_square(nomeCasella))
            
            # Differenzia casella selezionata (bg) da mosse valide (marker)
            marker_control = None
            # default: no border/bg
            contenitore.bgcolor = None
            contenitore.border = None

            # Se è la casella selezionata:
            if nomeCasella == self.casellaSelezionata:
                contenitore.bgcolor = "#D1F2FFFF"  
                contenitore.border = ft.border.all(4, "#7EA0A1")
            # Se è una mossa valida, distingui se è una cattura
            elif nomeCasella in self.mosseValideEvidenziate:
                is_capture = False
                try:
                    if self.casellaSelezionata:
                        mv = self.scacchiera.find_move(
                            chess.parse_square(self.casellaSelezionata),
                            chess.parse_square(nomeCasella),
                        )
                        is_capture = self.scacchiera.is_capture(mv)
                except Exception:
                    # fallback: se nella casella di destinazione è presente un pezzo, considerala capture
                    try:
                        dest_piece = self.scacchiera.piece_at(chess.parse_square(nomeCasella))
                        is_capture = dest_piece is not None
                    except Exception:
                        is_capture = False

                # usa immagini diverse per capture vs normale
                if is_capture:
                    marker_control = ft.Image(src="selected_marker.png", width=48, height=48, fit=ft.ImageFit.CONTAIN)
                else:
                    marker_control = ft.Image(src="move_marker.png", width=48, height=48, fit=ft.ImageFit.CONTAIN)

            contenitore.content = None

            if pezzo:
                # Esempio nome file: wP.png (White Pawn) o bK.png (Black King)
                nomeImgPezzo = f"{ 'w' if pezzo.color else 'b' }{pezzo.symbol().upper()}.png"
                immaginePezzo = ft.Image(src=nomeImgPezzo, width=40, height=40)

                # Se c'è un marker, mettilo dietro al pezzo usando Stack
                if pezzo.color == self.mioColore:
                    immaginePezzoDrag = ft.Image(src=nomeImgPezzo, width=60, height=60)
                    draggable = ft.Draggable(
                        group="scacchi",
                        content=immaginePezzo,
                        content_when_dragging=ft.Container(content=immaginePezzoDrag, opacity=0.5),
                        data=nomeCasella
                    )
                    if marker_control:
                        contenitore.content = ft.GestureDetector(
                            content=ft.Stack(
                                controls=[
                                    ft.Container(content=marker_control, width=50, height=50, alignment=ft.alignment.center),
                                    ft.Container(content=draggable, width=50, height=50, alignment=ft.alignment.center),
                                ],
                                width=50,
                                height=50,
                            ),
                            on_tap=lambda e, casella=nomeCasella: self.clickSuPezzo(e, casella)
                        )
                    else:
                        contenitore.content = ft.GestureDetector(
                            content=draggable,
                            on_tap=lambda e, casella=nomeCasella: self.clickSuPezzo(e, casella)
                        )
                else:
                    if marker_control:
                        contenitore.content = ft.Stack(
                            controls=[
                                ft.Container(content=marker_control, width=50, height=50, alignment=ft.alignment.center),
                                ft.Container(content=immaginePezzo, width=50, height=50, alignment=ft.alignment.center),
                            ],
                            width=50,
                            height=50,
                        )
                    else:
                        contenitore.content = immaginePezzo
            else:
                # Se non c'è pezzo, mostra il marker se presente
                if marker_control:
                    contenitore.content = ft.Container(content=marker_control, alignment=ft.alignment.center)
                else:
                    # nessun pezzo e nessun marker -> rimuovi bordo
                    contenitore.border = None
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
        if self.socket_client and self.mioTurno and not self.partitaTerminata:
            try:
                self.socket_client.send(f"MOVES|{casella}".encode())
            except (ConnectionResetError, OSError, BrokenPipeError, AttributeError) as e:
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
                    # Può capitare che il socket sia stato chiuso tra la mossa locale
                    # e l'invio, quindi verifichiamo prima che esista ancora.
                    if self.socket_client and not self.partitaTerminata:
                        self.socket_client.send(mossa.uci().encode())
                except (ConnectionResetError, OSError, BrokenPipeError, AttributeError) as e:
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
                if self.socket_client and not self.partitaTerminata:
                    self.socket_client.send(mossa.uci().encode())
            except (ConnectionResetError, OSError, BrokenPipeError, AttributeError) as e:
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