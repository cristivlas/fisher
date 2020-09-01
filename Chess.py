from kivy.config import Config
Config.set('graphics', 'multisamples', 8)
Config.set('graphics', 'resizable', False)
#Config.set('kivy', 'log_level', 'debug')
from kivy.app import App
from kivy.atlas import Atlas
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.graphics import *
from kivy.graphics.texture import Texture
from kivy.properties import Property, StringProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from utils import is_mobile
from os import path
from Engine import Engine
from msgbox import MessageBox


ABOUT = """Fisher 0.1: Kivy interface for the Sunfish chess engine.
https://github.com/cristivlas/fisher
https://github.com/thomasahle/sunfish"""

class Root(GridLayout):
    pass


class Style:
    piece_name = {'p': 'pawn', 'r': 'rook', 'k': 'king', 'q': 'queen', 'b': 'bishop', 'n': 'knight'}
    def __init__(self):
        self.black = Atlas('style/default/black.atlas')
        self.white = Atlas('style/default/white.atlas')
        self.tex = {}

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
        Logger.info('{}Board: {}, {}x8x8'.format(__name__, self.grid_size, self.cell_size))
    
    def on_move(self, *_):
        pass

    def on_touch_down(self, touch):
        Logger.trace('{}Board: on_touch_down({} {})'.format(__name__, touch.pos, self.xyo))
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
                texture = self.style.piece_texture(p)
                Rectangle(pos=self.xy(file, rank), size=2*[self.cell_size], source=texture)

    def redraw(self, *args):
        Logger.info('{}Board: redraw {}'.format(__name__, args))
        self.calc_size()
        self.redraw_board()
        self.redraw_pieces()

    def select(self, move):
        self.redraw_pieces()
        for pos in move[:2], move[2:]:
            if not pos:
                break
            with self.canvas:
                x, y = self.xy(*pos)
                w, h = self.cell_size, self.cell_size
                Color(0.7, 0.7, 0.7, 1)
                Line(points=[x, y, x+w, y, x+w, y+h, x, y+h, x, y], width=2)

    def xy(self, file, rank):
        col, row = 'abcdefgh'.index(file), int(rank) - 1
        return [o + i * self.cell_size for o, i in zip(self.xyo, [col, row])]

class Chess(App):
    __events__ = ('on_checkmate', 'on_update',)

    icon = 'chess.png'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.engine = Engine(self.dispatch)
        self.modal = None

    def about(self):
        self.message_box('About', ABOUT, font_size=14)

    @property
    def board(self):
        return self.root.ids['board']

    @property
    def new_button(self):
        return self.root.ids['new']

    @property
    def undo_button(self):
        return self.root.ids['undo']

    @property
    def move_label(self):
        return self.root.ids['move']

    @property
    def status_label(self):
        return self.root.ids['status']

    def build(self):
        if is_mobile():
            Window.maximize()
        else:
            Window.size = (600, 720)
        Window.bind(on_request_close=self.on_quit)
        root = Root()
        root.ids['board'].bind(on_move=self.on_move)
        return root

    def on_checkmate(self, winner):
        self.message_box('Checkmate!', '{} won!'.format(winner))

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
        self.status_label.text = status
        if pieces:
            self.board.pieces = pieces
        self.move_label.text = move or ''
        if move:
            self.board.select(move)

    def start_game(self):
        self.on_update(*self.engine.status())

    def new_game(self, *args):
        def start_new_game():
            self.engine = Engine(self.dispatch, resume=False)
            self.start_game()
        self.confirm('Abandon game and start new one', start_new_game)

    def undo_move(self, *args):
        if self.engine.can_undo():
            self.confirm('Take back last move', self.engine.undo_move)

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