import logging
import subprocess
from distutils.version import StrictVersion

from pytmux.listener import Listener


def listen_all_events(tmux_args: list):
    command = ["/usr/bin/tmux", "-C"]
    command.extend(tmux_args)

    # pylint: disable=consider-using-with
    proc = subprocess.Popen(
        command,
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=None,
        shell=False,
        cwd="/",
        text=False,
        close_fds=True,
    )
    logging.debug("pid: %d", proc.pid)

    with proc:

        assert proc.stdout
        listener = Listener.from_args(proc.stdout.fileno(), 10, 10)

        try:
            listener.listen_in_background()

            with listener:
                try:
                    while True:
                        with listener.dingdong():
                            while listener.notiq:
                                print(listener.notiq.get_nowait())
                            while listener.replyq:
                                print(listener.replyq.get_nowait())
                except ValueError:
                    pass
        finally:
            proc.kill()


def ensure_tmux_compatible():
    cp = subprocess.run(["tmux", "-V"], stdout=subprocess.PIPE, check=True)
    out: bytes = cp.stdout.decode().rstrip()

    prefix = "tmux "
    if not out.startswith(prefix):
        raise SystemExit("can not understand tmux version output")

    held = StrictVersion(out[len(prefix) :])
    least = StrictVersion("3.2")

    if held < least:
        raise SystemExit(f"tmux too old, least: {least}")
