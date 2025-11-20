import flet as ft
import socket
import threading
import chess

HOST = "localhost"
PORT = 5000

class ChessClient:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Client Scacchi"
        self.page.bgcolor = "#263238"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        self.sock = None
        self.board = chess.Board()
        self.my_color = None 
        self.is_my_turn = False
        self.squares_ui = {} 

        # UI Login
        self.nickname_input = ft.TextField(label="Nickname", width=200, text_align=ft.TextAlign.CENTER)
        self.status_lbl = ft.Text("", size=20, weight="bold")
        
        self.show_login()

    def show_login(self):
        self.page.clean()
        self.page.add(
            ft.Column([
                ft.Text("Scacchi Online", size=40, weight="bold"),
                self.nickname_input,
                ft.ElevatedButton("Entra in Coda", on_click=self.connect_to_server)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    def show_waiting(self):
        self.page.clean()
        self.page.add(ft.Column([ft.ProgressRing(), ft.Text("In attesa...", size=20)], alignment=ft.MainAxisAlignment.CENTER))
        self.page.update()

    def connect_to_server(self, e):
        if not self.nickname_input.value: return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.sock.send(self.nickname_input.value.encode())
            self.show_waiting()
            threading.Thread(target=self.network_loop, daemon=True).start()
        except Exception as err:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Errore: {err}"))
            self.page.snack_bar.open = True
            self.page.update()

    def network_loop(self):
        while True:
            try:
                data = self.sock.recv(1024).decode()
                if not data: break
                
                if data.startswith("START|"):
                    color = data.split("|")[1]
                    self.my_color = chess.WHITE if color == "WHITE" else chess.BLACK
                    self.is_my_turn = (self.my_color == chess.WHITE)
                    self.build_game_ui()
                
                elif data.startswith("ERROR|"):
                    err_msg = data.split("|")[1]
                    print(f"ERRORE DAL SERVER: {err_msg}")
                    # Se il server dice errore, probabilmente siamo desincronizzati.
                    # Qui potremmo richiedere la scacchiera intera, ma per ora stampiamo solo.
                    
                else:
                    # È una mossa dell'avversario (es. "e2e4")
                    self.handle_opponent_move(data)
                    
            except Exception as e:
                print(f"Disconnesso: {e}")
                break

    def build_game_ui(self):
        self.page.clean()
        board_img = ft.Image(src="board.png", width=400, height=400, fit=ft.ImageFit.FILL)
        grid_col = ft.Column(spacing=0, width=400, height=400)
        
        # Orientamento scacchiera
        ranks = range(7, -1, -1) if self.my_color == chess.WHITE else range(8)
        files = range(8) if self.my_color == chess.WHITE else range(7, -1, -1)

        for rank in ranks:
            row = []
            for file in files:
                sq_name = chess.square_name(chess.square(file, rank))
                container = ft.Container(width=50, height=50, alignment=ft.alignment.center)
                target = ft.DragTarget(group="chess", content=container, on_accept=self.on_drop, data=sq_name)
                self.squares_ui[sq_name] = container
                row.append(target)
            grid_col.controls.append(ft.Row(controls=row, spacing=0))

        self.status_lbl.value = "Tocca a te!" if self.is_my_turn else "Attendi avversario..."
        
        self.page.add(
            self.status_lbl,
            ft.Container(ft.Stack([board_img, grid_col], width=400, height=400), border=ft.border.all(2, "white")),
            ft.Text(f"Tu sei: {'BIANCO' if self.my_color == chess.WHITE else 'NERO'}")
        )
        self.update_pieces()
        self.page.update()

    def update_pieces(self):
        board_map = self.board.piece_map()
        for sq_name, container in self.squares_ui.items():
            piece = board_map.get(chess.parse_square(sq_name))
            container.content = None
            if piece:
                img_src = f"{'w' if piece.color else 'b'}{piece.symbol().upper()}.png"
                img = ft.Image(src=img_src, width=40, height=40)
                if piece.color == self.my_color:
                    container.content = ft.Draggable(group="chess", content=img, content_when_dragging=ft.Container(content=img, opacity=0.5), data=sq_name)
                else:
                    container.content = img
        self.page.update()

    def on_drop(self, e: ft.DragTargetEvent):
        # 1. Controllo preliminare Client
        if not self.is_my_turn: return
        
        src = self.page.get_control(e.src_id).data
        dst = e.control.data
        
        try:
            # Logica gestione promozione semplificata (sempre Regina)
            move = self.board.find_move(chess.parse_square(src), chess.parse_square(dst))
        except:
            try: move = chess.Move.from_uci(f"{src}{dst}q")
            except: move = None

        # 2. Se legale localmente, invia al server
        if move and move in self.board.legal_moves:
            # Eseguiamo localmente "con fiducia" (Optimistic UI update)
            self.board.push(move)
            self.update_pieces()
            self.is_my_turn = False
            self.status_lbl.value = "Turno avversario..."
            self.page.update()
            
            # INVIO AL SERVER
            self.sock.send(move.uci().encode())
        else:
            self.update_pieces() # Reset visuale mossa invalida

    def handle_opponent_move(self, uci_move):
        try:
            move = chess.Move.from_uci(uci_move)
            # Qui ci fidiamo del server (che ha già validato)
            self.board.push(move)
            self.is_my_turn = True
            self.status_lbl.value = "TOCCA A TE!"
            self.update_pieces()
        except:
            pass # Mossa strana ricevuta

def main(page: ft.Page):
    ChessClient(page)

ft.app(target=main, assets_dir="assets")