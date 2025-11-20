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
        # FIX COLORE: Uso codice HEX invece di ft.colors
        self.page.bgcolor = "#263238" 
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        self.sock = None
        self.board = chess.Board()
        self.my_color = None 
        self.is_my_turn = False
        
        self.squares_ui = {} 

        # UI Components
        self.nickname_input = ft.TextField(label="Nickname", width=200, text_align=ft.TextAlign.CENTER)
        self.status_text = ft.Text("Inserisci il nome per giocare", size=20)
        
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
        self.page.add(
            ft.Column([
                ft.ProgressRing(),
                ft.Text("In attesa di un avversario...", size=20)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
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
        """Ascolta i messaggi dal server"""
        while True:
            try:
                data = self.sock.recv(1024).decode()
                if not data: break
                
                if data.startswith("START|"):
                    color_str = data.split("|")[1]
                    self.my_color = chess.WHITE if color_str == "WHITE" else chess.BLACK
                    self.is_my_turn = (self.my_color == chess.WHITE)
                    print(f"Partita iniziata! Io sono: {color_str}")
                    self.build_game_ui()
                
                else:
                    self.handle_opponent_move(data)
                    
            except Exception as e:
                print(f"Errore rete: {e}")
                break

    def build_game_ui(self):
        self.page.clean()
        
        # Sfondo scacchiera
        board_img = ft.Image(src="board.png", width=400, height=400, fit=ft.ImageFit.FILL)
        
        # Griglia logica
        grid_column = ft.Column(spacing=0, width=400, height=400)
        
        ranks = range(7, -1, -1) if self.my_color == chess.WHITE else range(8)
        files = range(8) if self.my_color == chess.WHITE else range(7, -1, -1)

        for rank in ranks:
            row_controls = []
            for file in files:
                square_index = chess.square(file, rank)
                square_name = chess.square_name(square_index)
                
                piece_container = ft.Container(width=50, height=50, alignment=ft.alignment.center)
                
                drop_target = ft.DragTarget(
                    group="chess",
                    content=piece_container,
                    on_accept=self.on_drop,
                    data=square_name
                )
                
                self.squares_ui[square_name] = piece_container
                row_controls.append(drop_target)
            
            grid_column.controls.append(ft.Row(controls=row_controls, spacing=0))

        game_area = ft.Stack([board_img, grid_column], width=400, height=400)
        
        info_text = "Tocca a te! (Bianco)" if self.my_color == chess.WHITE else "Attendi il bianco..."
        self.status_lbl = ft.Text(info_text, size=20, weight="bold")

        self.page.add(
            self.status_lbl,
            # FIX COLORE: Uso "white" invece di ft.colors.WHITE
            ft.Container(game_area, border=ft.border.all(2, "white")),
            ft.Text(f"Tu giochi con i: {'BIANCHI' if self.my_color == chess.WHITE else 'NERI'}")
        )
        
        self.update_pieces()
        self.page.update()

    def update_pieces(self):
        board_map = self.board.piece_map()
        
        for square_name, container in self.squares_ui.items():
            sq_idx = chess.parse_square(square_name)
            piece = board_map.get(sq_idx)
            
            container.content = None 
            
            if piece:
                img_name = f"{'w' if piece.color else 'b'}{piece.symbol().upper()}.png"
                img = ft.Image(src=img_name, width=40, height=40)
                
                if piece.color == self.my_color:
                    draggable = ft.Draggable(
                        group="chess",
                        content=img,
                        content_when_dragging=ft.Container(content=img, opacity=0.5),
                        data=square_name
                    )
                    container.content = draggable
                else:
                    container.content = img 

        self.page.update()

    # FIX EVENTO: Aggiornato a ft.DragTargetEvent
    def on_drop(self, e: ft.DragTargetEvent):
        if not self.is_my_turn:
            print("Non è il tuo turno!")
            return

        # Recupero i dati. In alcune versioni src_id non basta, 
        # ma proviamo a recuperare il controllo draggable dalla pagina
        src = self.page.get_control(e.src_id).data
        dst = e.control.data 
        
        try:
            move = self.board.find_move(chess.parse_square(src), chess.parse_square(dst))
        except:
            try:
                move = chess.Move.from_uci(f"{src}{dst}q")
            except:
                move = None

        if move and move in self.board.legal_moves:
            self.board.push(move)
            self.update_pieces()
            self.sock.send(move.uci().encode())
            
            self.is_my_turn = False
            self.status_lbl.value = "Turno avversario..."
            self.page.update()
        else:
            print("Mossa non valida")
            self.update_pieces()

    def handle_opponent_move(self, uci_move):
        try:
            move = chess.Move.from_uci(uci_move)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.is_my_turn = True
                self.status_lbl.value = "TOCCA A TE!"
                self.update_pieces()
        except:
            print("Errore mossa avversario")

def main(page: ft.Page):
    ChessClient(page)

ft.app(target=main, assets_dir="assets")