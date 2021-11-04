from kivy.clock import mainthread
from kivy.storage.dictstore import DictStore
from kivy.logger import Logger
from worker import WorkerThread
from sunfish.sunfish import (initial, parse, render, Position, Searcher, MATE_LOWER,MATE_UPPER)
import chess
import re
import time

#############################################################################
# Interface with the Sunfish engine directly, no xboard / uci
#############################################################################
class Engine:
    def __init__(self, dispatch, resume=True):
        self.__dispatch = dispatch
        self.__worker = WorkerThread()
        self.hist = [Position(initial, 0, (True,True), (True,True), 0, 0)]
        self.board = chess.Board()
        self.redo = []
        self.searcher = Searcher()
        self.store = DictStore('fisher.dat')
        if resume:
            self.load_game()

    @mainthread
    def dispatch(self, event, *args):
        self.__dispatch(event, *args)

    @property
    def is_game_over(self):
        return self.board.is_game_over()

    @property
    def moves(self):
        return self.board.move_stack

    # convert sunfish position into a list of pieces with their file and rank
    def position(self, pos=None):
        pos = pos or self.hist[-1]
        pieces = []
        for rank, row in enumerate(pos.board.split()):
            for file, p in enumerate(row):
                if p=='.':
                    continue
                pieces.append('{}{}{}'.format(p, 'abcdefgh'[file], 8-rank))
        return pieces

    def validate(self, _move):
        try:
            move = chess.Move.from_uci(_move)
        except:
            return None
        while True:
            if move in self.board.legal_moves:
                return move
            if self.humans_turn:
                break            
            # Sunfish move deemed illegal by python-chess? likely a promotion
            assert not move.promotion
            if not self.humans_turn:
                move.promotion = chess.QUEEN

    def apply_move(self, _move):
        move = self.validate(self.decode(_move))
        if move:
            self.board.push(move) 
            self.hist.append(self.hist[-1].move(_move))
            
            # after the machine's move, check if redo list still valid
            if self.humans_turn:
                self.check_redo()
            self.dispatch('on_update', *self.status(), move.uci())
            if not self.is_game_over:
                return move

    def input_move(self, move):
        move = self.parse_and_validate(move)
        if move and self.apply_move(move):
            self.search_move()

    def parse_and_validate(self, move):
        if not self.is_game_over:
            match = re.match('([a-h][1-8])'*2, move)
            if match:
                return parse(match.group(1)), parse(match.group(2))

    def decode(self, move):
        if not self.humans_turn:
            move = [119 - m for m in move]
        return '{}{}'.format(*(render(m) for m in move))

    # Fire up the engine to look for a move -- in the background thread
    def search_move(self):
        def search():
            start = time.time()
            for _depth, move, _score in self.searcher.search(self.hist[-1], self.hist):
                if time.time() - start > 1:
                    break
            self.apply_move(move)
            self.save_game()
        self.__worker.send_message(search)

    def status_message(self):
        if self.board.is_stalemate():
            return 'Stalemate'
        if self.board.is_checkmate():
            return 'Checkmate!'
        if self.board.is_check():
            return 'Check!'
        return 'Your turn' if self.humans_turn else 'Thinking...'

    @property
    def humans_turn(self):
        return self.board.turn == chess.WHITE

    def status(self):
        pos = self.hist[-1] if self.hist else None
        if pos and not self.humans_turn:
            pos = pos.rotate()
        return self.position(pos), self.status_message()

    def __can_use(self, moves_list):
        return len(moves_list) > 0 and (self.humans_turn or self.is_game_over)

    def can_undo(self):
        return self.__can_use(self.moves)

    def can_redo(self):
        return self.__can_use(self.redo)

    def check_redo(self):
        if self.redo and self.last_move != self.redo[-1]:
            # history took a different turn; redo list is invalid
            self.redo.clear()

    def undo_move(self):
        assert self.can_undo()
        assert len(self.hist) >= 2
        # Assuming human plays white -- careful if/when implementing a "switch" feature
        # Moves count should be even, unless we lost.
        # Length of position history is odd because of initial empty position.
        assert len(self.hist) % 2 or self.is_game_over
        n = 1 if len(self.moves) % 2 else 2
        self.hist = self.hist[:-n]
        self.redo.append(self.moves[-n].uci())
        while n > 0:
            self.board.pop()
            n -= 1
        self.redo.append(self.last_move)
        self.dispatch('on_update', *self.status(), self.last_move)

    def redo_move(self):
        assert self.redo
        assert len(self.redo) % 2 == 0
        move = self.redo.pop()
        assert move == self.last_move
        move = self.redo.pop()
        self.input_move(move)

    def start(self):
        if not self.humans_turn:
            self.search_move()
    
    @property
    def last_move(self):
        return self.moves[-1].uci() if self.moves else None
        
    def load_game(self):
        Logger.debug('{}: load'.format(__name__))
        if self.store.exists('game'):
            data = self.store.get('game')
            self.hist = data.get('hist', [])
            for move in data.get('moves', []):
                self.board.push(move)

    def save_game(self):
        Logger.debug('{}: save'.format(__name__))
        self.store.put('game', hist=self.hist, moves=self.moves)
