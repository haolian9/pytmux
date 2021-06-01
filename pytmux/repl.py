import logging
import os
import select
import subprocess
from threading import Event, Thread

from pytmux import reader


class Reporter(Thread):
    def __init__(self, fd: int, epoll: select.epoll, term: Event):
        self._fd = fd
        self._epoll = epoll
        self._term = term

        super().__init__(daemon=False)

    def run(self):
        term = self._term
        fd = self._fd
        epoll = self._epoll
        pipebuf = select.PIPE_BUF

        sr = reader.StreamReader()

        while True:
            if term.set():
                break

            events = epoll.poll(0.01)
            for _fd, _etype in events:
                if _fd != fd:
                    continue
                if _etype != select.EPOLLIN:
                    continue

                data = os.read(fd, pipebuf)
                while True:
                    if not data:
                        break
                    try:
                        sr.feed(data)
                    except reader.NeedMore:
                        continue
                    except reader.FulFiled as e:
                        event = sr.flush()
                        print(event)
                        data = data[e.readn :]
                    else:
                        raise RuntimeError("should never reach here")


proc = subprocess.Popen(
    ["/usr/bin/tmux", "-C"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    shell=False,
    cwd="/",
    text=False,
    close_fds=True,
)

epoll = select.epoll()

logging.debug("pid: %d", proc.pid)

assert proc.stdin and proc.stdout

infd = proc.stdin.fileno()
outfd = proc.stdout.fileno()

# a thread for read {reply, noti} then push into specific queues
# a thread handles noti

logging.debug("register outfd to epoll")
epoll.register(outfd, select.EPOLLIN)

term = Event()

reporter = Reporter(outfd, epoll, term)
reporter.start()


def cleanup():
    with proc, epoll:
        term.set()
        reporter.join()
        send_command("\n")


def send_command(command: str):
    cmd = command.encode()
    if not cmd.endswith(b"\n"):
        cmd = cmd + b"\n"

    wrote = os.write(infd, cmd)

    assert wrote == len(cmd)
