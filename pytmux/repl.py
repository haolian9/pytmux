import atexit
import logging
import os
import subprocess

from pytmux.listener import Listener

# tmux -CC
# tmux -C new-session -s controlmode [-d]
# tmux -C attach-session -t controlmode

# pylint: disable=consider-using-with
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

logging.debug("pid: %d", proc.pid)

assert proc.stdin and proc.stdout
infd = proc.stdin.fileno()
outfd = proc.stdout.fileno()

listener = Listener.from_args(outfd, 10, 10)
listener.listen_in_background()


def cleanup():
    with proc:
        listener.close()
        send_command("\n")


atexit.register(cleanup)


def send_command(command: str):
    cmd = command.encode()
    if not cmd.endswith(b"\n"):
        cmd = cmd + b"\n"

    wrote = os.write(infd, cmd)

    assert wrote == len(cmd)
