import contextlib
import os
import select
import threading
from collections import deque
from queue import Empty, Queue

import attr

from .reader import FulFiled, NeedMore, StreamReader
from .types import Exit, Notification, Reply


class ReplyQ:
    def __init__(self, capacity: int):
        self._queue: Queue = Queue(capacity)

    def __len__(self):
        return self._queue.qsize()

    def get(self):
        """
        when queue is empty, get will block until an item available
        """
        return self._queue.get()

    def get_nowait(self):
        return self._queue.get_nowait()

    def put(self, item):
        """
        when queue is full, put will block until space available
        """
        return self._queue.put(item)


class NotiQ:
    def __init__(self, capacity: int):
        self._queue = deque("", capacity)

    def __len__(self):
        return len(self._queue)

    def get(self):
        try:
            return self._queue.popleft()
        except IndexError as e:
            raise Empty from e

    get_nowait = get

    def put(self, item):
        return self._queue.append(item)


@attr.s
class Listener:
    # pylint: disable=invalid-name
    fd: int = attr.ib()
    term: threading.Event = attr.ib()
    replyq: ReplyQ = attr.ib()
    notiq: NotiQ = attr.ib()

    _dingdong: threading.Condition = attr.ib(init=False)
    _thread: threading.Thread = attr.ib(init=False, default=None)
    _dead: bool = attr.ib(init=False, default=False)

    @classmethod
    def from_args(cls, fd: int, reply_cap: int, noti_cap: int):
        return cls(fd, threading.Event(), ReplyQ(reply_cap), NotiQ(noti_cap))

    def listen_in_background(self):
        if self._dead:
            raise RuntimeError("listener was dead, can not listen anymore")

        if self._thread:
            return

        self._dingdong = threading.Condition()
        self._thread = Thread(self)
        self._thread.start()

    @contextlib.contextmanager
    def dingdong(self):
        """
        :raise: ValueError when term.is_set()
        """

        if self.term.is_set():
            raise ValueError("term has been set")

        with self._dingdong:
            self._dingdong.wait()

            yield

    def __enter__(self):
        return

    def __exit__(self, etype, exc, traceback):
        self.close()

    def close(self):
        if self._dead:
            return

        if not self._thread:
            return

        self.term.set()
        self._thread.join()
        self._dead = True
        self._thread.raise_if_any()


class Thread(threading.Thread):
    # pylint: disable=too-many-arguments
    def __init__(self, listener: Listener):
        self._listener = listener
        self._exc = None

        super().__init__(daemon=True)

    def raise_if_any(self):
        if self._exc:
            raise self._exc

    def run(self):
        try:
            self._mainloop()
        # pylint: disable=broad-except
        except Exception as e:
            self._exc = e

    def _mainloop(self):
        term = self._listener.term
        fd = self._listener.fd
        reader = StreamReader()

        with select.epoll() as poller:
            poller.register(fd, select.EPOLLIN)

            while True:
                if term.is_set():
                    break

                events = poller.poll(0.05)
                for _ in events:
                    self._handle_read(reader)

    def _handle_read(self, reader: StreamReader):
        term = self._listener.term
        fd = self._listener.fd
        replyq = self._listener.replyq
        notiq = self._listener.notiq
        bufsize = select.PIPE_BUF
        dingdong = self._listener._dingdong

        # TODO@haoliang consider using os.readv for less copy
        data = os.read(fd, bufsize)
        if data == b"":
            raise BrokenPipeError("remote closed pipe")

        while True:
            if data == b"":
                break

            try:
                reader.feed(data)
            except NeedMore as e:
                assert e.readn == len(data)
                break
            except FulFiled as e:
                # pylint: disable=raise-missing-from

                assert e.readn > 0
                data = data[e.readn :]

                event = reader.flush()

                with dingdong:
                    if isinstance(event, Notification):
                        # TODO@haoliang should be notify_all() ?
                        notiq.put(event)
                    elif isinstance(event, Reply):
                        replyq.put(event)
                    else:
                        raise RuntimeError(f"received an unknown event: {event}")

                    if isinstance(event, Exit):
                        term.set()
                        dingdong.notify_all()
                        raise BrokenPipeError("remote exited")

                    dingdong.notify()

            else:
                raise RuntimeError("should never reach here")
