import threading
from collections import deque


__IN__, __OUT__ = 0, 1


class Locking:
    def __init__(self):
        self.__lock = threading.Lock()

    def synchronized(f):
        def inner(self, *args):
            with self.__lock:
                return f(self, *args)
        return inner


class WorkerThreadServer(Locking):
    def __init__(self):
        super().__init__()
        self.__thread = threading.Thread(target=self.__main)
        self.__thread.daemon = True
        self.__queues = (deque(), deque())  # in / out
        self.__events = (threading.Event(), threading.Event())
        self.__active = True
        self.__paused = False
        self.__thread.start()

    @Locking.synchronized
    def pop(self, inout):
        return self.__pop(inout)

    def __pop(self, inout):
        queue = self.__queues[inout]
        event = self.__events[inout]
        m = queue.popleft() if queue else None
        if not queue:
            event.clear()
        return m

    @Locking.synchronized
    def __put_message(self, inout, m):
        if inout == __IN__:
            assert self.__active
            if self.__paused:
                return
        queue = self.__queues[inout]
        if queue and queue[-1] == m:
            return # redundant message?

        queue.append(m)
        self.__events[inout].set()

    def __get_message(self, inout):
        while True:
            self.__events[inout].wait()
            m = self.pop(inout)
            if m is not None:
                return m

    @Locking.synchronized
    def messages(self):
        while True:
            msg = self.__pop(__OUT__)
            if msg is None:
                break
            yield msg

    ''' receive message from worker (blocking) '''
    def read_message(self):
        return self.__get_message(__OUT__)

    ''' send message to worker '''
    def send_message(self, m):
        return self.__put_message(__IN__, m)

    def __main(self):
        while self.__active:
            work_item = self.__get_message(__IN__)
            # self.post(work_item())
            work_item()

    ''' post message to outbound queue '''
    #def post(self, msg, *args):
    #    self.__put_message(__OUT__, (msg, args))

    @Locking.synchronized
    def pause(self):
        result = not self.__paused
        self.__paused = True
        self.__queues[__IN__].clear()
        return result

    @Locking.synchronized
    def resume(self):
        if self.__paused:
            self.__paused = False
            self.__events[__IN__].set()
            return True

    @Locking.synchronized
    def stop(self):
        self.__active = False

    def __enter__(self):
        return self

    def __exit__(self, exception, *_):
        self.__active = exception is None
        self.__thread.join()
        if exception: raise

'''
if __name__ == '__main__':
    import random

    with WorkerThreadServer() as worker:            
        worker.send_message(lambda: 'hello')
        print (worker.read_message())

        worker.send_message(lambda: random.choice(range(1, 7)))
        print (worker.read_message())

        worker.send_message(lambda: random.choice(range(1, 7)))
        worker.send_message(lambda: random.choice(range(1, 7)))
        worker.send_message(worker.stop)
        
        for m in worker.messages():
            print(m)
'''
