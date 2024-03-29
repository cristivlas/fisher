from kivy.config import Config
Config.set('graphics', 'resizable', False)

from kivy.app import App
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.graphics import *
from kivy.graphics.opengl import *
from kivy.properties import Property, StringProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from utils import is_mobile
from os import path
from Engine import Engine
from msgbox import MessageBox


ABOUT = """Kivy-based interface for the Sunfish engine.
https://github.com/thomasahle/sunfish
https://github.com/cristivlas/fisher"""

class Root(GridLayout):
    pass


class Style:
    piece_name = {'p': 'pawn', 'r': 'rook', 'k': 'king', 'q': 'queen', 'b': 'bishop', 'n': 'knight'}

    @property
    def background(self):
        return path.join('style', 'default', 'plywood.jpg')

    @property
    def board_source(self):
        return path.join('style', 'default', 'board.png')

    def piece_texture(self, p):
        id = Style.piece_name[p.lower()]
        atlas = 'white' if p.isupper() else 'black'
        return path.join('atlas://', 'style', 'default', atlas, id)


class Board(Widget):
    __events__ = ('on_move',)
    pieces = Property([])
    move = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.margin = 10
        self.style = Style()
        self.calc_size()
        self.bind(size = self.redraw)
        self.bind(pieces = self.redraw_pieces)

    def calc_size(self):
        self.grid_size = min(i - 2 * self.margin for i in self.size)
        self.cell_size = self.grid_size / 8
        self.xyo = [(i - self.grid_size) / 2 for i in self.size]
        Logger.info('{}.Board: {:.2f}, {:.2f}x8x8'.format(__name__, self.grid_size, self.cell_size))

    def on_move(self, *_):
        pass

    def on_touch_down(self, touch):
        Logger.trace('{}.Board: on_touch_down({} {})'.format(__name__, touch.pos, self.xyo))
        x,y = [(i - j) / self.cell_size for i, j in zip(touch.pos, self.xyo)]
        if 0 <= x < 8 and 0 <= y < 8:
            move = 'abcdefgh'[int(x)] + str(1 + int(y))
            self.move += move
            if len(self.move) < 4:
                self.select(move)
            else:
                self.dispatch('on_move', self.move)
                self.move = ''

    def redraw_board(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 1)
            Rectangle(pos=[i-4 for i in self.xyo], size=2*[8 + self.grid_size])
            Color(1, 1, 1, 1)
            Rectangle(pos=self.xyo, size=2*[self.grid_size], source=self.style.background)
            Rectangle(pos=self.xyo, size=2*[self.grid_size], source=self.style.board_source)

    def redraw_pieces(self, *_):
        self.canvas.clear()
        with self.canvas:
            for p,file,rank in self.pieces:
                x,y = self.xy(file, rank)
                w,h = 2 * [self.cell_size]
                texture = self.style.piece_texture(p)
                Rectangle(pos=(x+16, y+2), size=(w-32, h-4), source=texture)

    def redraw(self, *args):
        Logger.info('{}.Board: redraw {}'.format(__name__, args))
        self.calc_size()
        self.redraw_board()
        self.redraw_pieces()

    # select square(s) in the move -- in uci notation
    def select(self, move: str):
        self.redraw_pieces()
        color = [(0.5, 0.65, 0.5, 1), (0.65, 0.75, 0.65, 1)]
        for i, pos in enumerate([move[i:i+2] for i in range(0, min(4, len(move)), 2)]):
            with self.canvas:
                x, y = [j for j in self.xy(*pos)]
                w, h = 2*[self.cell_size]
                Color(*color[i])
                Line(points=[x, y, x+w, y, x+w, y+h, x, y+h, x, y], width=2)

    def xy(self, file, rank):
        col, row = 'abcdefgh'.index(file), int(rank) - 1
        return [o + i * self.cell_size for o, i in zip(self.xyo, [col, row])]

class Chess(App):
    __events__ = ('on_update',)

    icon = 'chess.png'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = Engine(self.dispatch)
        self.modal = None

    def about(self):
        self.message_box('Fisher v0.4', ABOUT, font_size=16)

    def build(self):
        if is_mobile():
            Window.maximize()
        else:
            Window.size = (600, 720)
        Window.bind(on_request_close=self.on_quit)
        Window.bind(on_keyboard=self.on_keyboard)
        root = Root()
        for id, wid in root.ids.items():
            cls = str(wid.__class__).split('.')[-1].split('\'')[0].lower()
            setattr(self, id if id==cls else id + '_' + cls, wid)
        self.board.bind(on_move=self.on_move)
        return root

    # Ctrl+z or Android back button
    def on_keyboard(self, window, keycode1, keycode2, text, modifiers):
        undo = keycode1 in [27, 1001] if is_mobile() else (keycode1==122 and 'ctrl' in modifiers)
        if undo and self.engine.can_undo():
            self.confirm('Take back last move', self.undo_move)
            return True
        elif keycode1==27:
            return True # don't close on Escape

    def on_move(self, _, move):
        Logger.debug('{}: on_move {}'.format(__name__, move))
        self.engine.input_move(move)

    def on_quit(self, *_):
        self.engine.save_game()

    def on_start(self, *args):
        Logger.debug('{}: on_start {}'.format(__name__, args))
        self.start_game()

    def on_update(self, pieces, status, move=None):
        Logger.trace('{}: on_update {}'.format(__name__, pieces))
        self.new_button.disabled = not self.engine.can_undo()
        self.undo_button.disabled = not self.engine.can_undo()
        self.redo_button.disabled = not self.engine.can_redo()
        self.status_label.text = '[b][i]{}[/b][/i]'.format(status)
        if pieces:
            self.board.pieces = pieces
        self.move_label.text = move or ''
        if move:
            self.board.select(move)

    def start_game(self):
        self.engine.start()
        self.on_update(*self.engine.status(), self.engine.last_move)

    def new_game(self, *args):
        def start_new_game():
            self.engine = Engine(self.dispatch, resume=False)
            self.start_game()
        self.confirm('Abandon game and start new one', start_new_game)

    def undo_move(self, *_):
        if self.engine.can_undo():
            self.undo_button.disabled = True
            self.engine.undo_move()

    def redo_move(self, *_):
        if self.engine.can_redo():
            self.redo_button.disabled = True
            self.engine.redo_move()

    def message_box(self, title, text, on_close=None, font_size=22):
        def modal_done(on_close):
            if self.modal and on_close:
                on_close(self.modal)
            self.modal = None

        if not self.modal:
            self.modal = MessageBox(title, text, on_close=lambda *_: modal_done(on_close), font_size=font_size)

    def confirm(self, text, action):
        def callback(msgbox):
            if msgbox.value == 'Yes':
                return action()
        self.message_box(title='Confirm', text=text + '?', on_close=callback)
