from kivy.clock import mainthread
from kivy.storage.dictstore import DictStore
from kivy.logger import Logger
from worker import WorkerThreadServer
from sunfish.sunfish import (initial, parse, print_pos, render, Position, Searcher, MATE_LOWER,MATE_UPPER)
from functools import partial
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
        self.searcher = Searcher()        
        self.store = DictStore('fisher.dat')
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

    def input_move(self, move):
        if self.hist[-1].score <= -MATE_LOWER:
            Logger.debug('{}: You lost!'.format(__name__))
            self.dispatch('on_update', None, 'You lost')
            return

        def process_move(move):
            if move:
                self.hist.append(self.hist[-1].move(move))
                self.dispatch('on_update', *self.status())
                if self.hist[-1].score <= -MATE_LOWER:
                    self.dispatch('on_checkmate', 'You')
                    return
                # Fire up the engine to look for a move.
                start = time.time()
                for depth, move, score in self.searcher.search(self.hist[-1], self.hist):
                    if time.time() - start > 1:
                        break
                Logger.info('{}: depth={}, move={}'.format(__name__, depth, self.render(move)))
                if score >= MATE_UPPER:
                    self.dispatch('on_checkmate', 'I')
                self.hist.append(self.hist[-1].move(move))
                self.save_game()
                self.dispatch('on_update', *self.status())

        move = self.parse_and_validate(move)
        if move:
            self.__worker.send_message(partial(process_move, move))

    def parse_and_validate(self, move):
        match = re.match('([a-h][1-8])'*2, move)
        if match:
            m = parse(match.group(1)), parse(match.group(2))
            if m in self.hist[-1].gen_moves():
                return m

    @staticmethod
    def render(move):
        return '{}{}'.format(*(render(119-m) for m in move))

    def status_message(self, humans_turn):
        return 'Your turn' if humans_turn else 'Thinking...'

    def status(self):
        humans_turn = len(self.hist) % 2
        pos = self.hist[-1] if self.hist else None
        if pos and not humans_turn:
            pos = pos.rotate()
        return self.position(pos), self.status_message(humans_turn)

    def can_undo(self):
        return len(self.hist) > 1

    def undo_move(self):
        if self.can_undo():
            self.hist = self.hist[:-2]
            self.dispatch('on_update', *self.status())

    def load_game(self):
        Logger.debug('{}: save'.format(__name__))
        if self.store.exists('game'):
            data = self.store.get('game')
            self.hist = data.get('hist', [])

    def save_game(self):
        Logger.debug('{}: save'.format(__name__))
        self.store.put('game', hist=self.hist)
