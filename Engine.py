from kivy.clock import mainthread
from kivy.storage.dictstore import DictStore
from kivy.logger import Logger
from worker import WorkerThreadServer
from sunfish.sunfish import (initial, parse, print_pos, render, Position, Searcher, MATE_LOWER,MATE_UPPER)
import re
import time

#############################################################################
# Interface with the sunfish engine
#############################################################################
class Engine:
    def __init__(self, dispatch, resume=True):
        self.__dispatch = dispatch
        self.__worker = WorkerThreadServer()
        self.hist = [Position(initial, 0, (True,True), (True,True), 0, 0)]
        self.moves = [] # in file-rank notation
        self.searcher = Searcher()        
        self.store = DictStore('fisher.dat')
        self.checkmate = False
        if resume:
            self.load_game()

    @mainthread
    def dispatch(self, event, *args):
        self.__dispatch(event, *args)

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

    def game_over(self, winner):
        self.checkmate = True
        self.dispatch('on_checkmate', winner)

    def apply_move(self, move):
        self.hist.append(self.hist[-1].move(move))
        move = self.render(move)
        self.moves.append(move)
        self.dispatch('on_update', *self.status(), move)        

    def input_move(self, move):

        # Fire up the engine to look for a move -- in the background thread
        def search_move():
            start = time.time()
            for depth, move, score in self.searcher.search(self.hist[-1], self.hist):
                if time.time() - start > 1:
                    break
            if score >= MATE_UPPER:
                self.game_over('I')
            self.apply_move(move)
            self.save_game()
        if self.hist[-1].score <= -MATE_LOWER:
            Logger.debug('{}: You lost!'.format(__name__))

        move = self.parse_and_validate(move)
        if move:
            self.apply_move(move)
            if self.hist[-1].score <= -MATE_LOWER:
                self.game_over('You')
            else:
                self.__worker.send_message(search_move)

    def parse_and_validate(self, move):
        if not self.checkmate:
            match = re.match('([a-h][1-8])'*2, move)
            if match:
                m = parse(match.group(1)), parse(match.group(2))
                if m in self.hist[-1].gen_moves():
                    return m

    def render(self, move):
        if self.humans_turn:
            move = [119 - m for m in move]
        return '{}{}'.format(*(render(m) for m in move))

    def status_message(self):
        if self.checkmate:
            return 'Checkmate'
        return 'Your turn' if self.humans_turn else 'Thinking...'

    @property
    def humans_turn(self):
        # we start with the empty position
        return len(self.hist) % 2

    def status(self):
        pos = self.hist[-1] if self.hist else None
        if pos and not self.humans_turn:
            pos = pos.rotate()
        return self.position(pos), self.status_message()

    def can_undo(self):
        return len(self.hist) > 1

    def undo_move(self):
        if self.can_undo():
            assert len(self.hist) >= 2
            self.checkmate = False
            self.hist = self.hist[:-2]
            self.moves = self.moves[:-2]
            self.dispatch('on_update', *self.status(), self.last_move)

    @property
    def last_move(self):
        return self.moves[-1] if self.moves else None
        
    def load_game(self):
        Logger.debug('{}: save'.format(__name__))
        if self.store.exists('game'):
            data = self.store.get('game')
            self.hist = data.get('hist', [])
            self.moves = data.get('moves', [])
            self.checkmate = data.get('checkmate', False)

    def save_game(self):
        Logger.debug('{}: save'.format(__name__))
        self.store.put('game', hist=self.hist, moves=self.moves, checkmate=self.checkmate)
