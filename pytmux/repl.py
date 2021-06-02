import atexit
import logging
import os
import select
import subprocess
from threading import Event, Thread

from pytmux import reader, types


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
            if term.is_set():
                break

            events = epoll.poll(0.01)
            for _fd, _etype in events:
                if _fd != fd:
                    continue
                if _etype != select.EPOLLIN:
                    continue

                data = bytearray(os.read(fd, pipebuf))
                while True:
                    if not data:
                        break
                    try:
                        sr.feed(data)
                    except reader.NeedMore as e:
                        assert e.readn == len(data)
                        break
                    except reader.FulFiled as e:
                        assert e.readn > 0
                        event = sr.flush()
                        if isinstance(event, types.Output):
                            print("output event, ommitted ...")
                        else:
                            print(event)
                        data = data[e.readn :]
                    else:
                        raise RuntimeError("should never reach here")


# tmux -CC
# tmux -C new-session -s controlmode [-d]
# tmux -C attach-session -t controlmode

proc = subprocess.Popen(
    ["/usr/bin/tmux", "-C", "attach-session", "-t", "controlmode"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    shell=False,
    cwd="/",
    text=False,
    close_fds=False,
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


atexit.register(cleanup)


def send_command(command: str):
    cmd = command.encode()
    if not cmd.endswith(b"\n"):
        cmd = cmd + b"\n"

    wrote = os.write(infd, cmd)

    assert wrote == len(cmd)
