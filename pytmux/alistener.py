import logging
import select
import subprocess

import trio

from pytmux.reader import StreamReader


async def main():
    command = ["/usr/bin/tmux", "-C", "attach-session", "-t", "controlmode"]
    proc: trio.Process = await trio.open_process(
        command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None
    )
    reader = StreamReader()

    async with proc:
        stdin: trio.abc.SendStream = proc.stdin
        stdout: trio.abc.ReceiveStream = proc.stdout

        logging.debug("sending a command")
        await stdin.send_all(b"list-sessions\n")

        while True:
            out = await stdout.receive_some(select.PIPE_BUF)
            if out == b"":
                logging.debug("remote pipe was closed")
                break

            for event in reader.feed(out):
                print(event)


if __name__ == "__main__":
    logging.basicConfig(
        level="DEBUG",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
        format="{asctime} {message}",
    )

    trio.run(main)
