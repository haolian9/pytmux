"""
# TODO@haoliang avoid output mixed up stdin while typing
"""

import logging
import select
import subprocess
import sys

import trio
from pytmux.reader import StreamReader
from pytmux.types import Notification, Reply
from trio import MemoryReceiveChannel, MemorySendChannel
from trio.abc import ReceiveStream, SendStream
from trio.lowlevel import FdStream


async def basic_listener():
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


async def main():
    async def report(
        wlock: trio.Lock, stdout: FdStream, receiver: MemoryReceiveChannel
    ):
        async with receiver:
            async for event in receiver:
                async with wlock:
                    await stdout.send_all(str(event).encode())
                    await stdout.send_all(b"\n")

    async def forward_stdin(src: ReceiveStream, dest: SendStream):
        banned_prefixes = {
            b"run-shell",
        }

        bufsize = select.PIPE_BUF

        buf = bytearray()
        while True:
            chunk: bytes = await src.receive_some(bufsize)
            eol_at = chunk.find(b"\n")

            if eol_at < 0:
                buf.extend(chunk)
                continue

            buf.extend(chunk[: eol_at + 1])
            line = buf
            buf = bytearray(chunk[eol_at + 1 :])

            for banned in banned_prefixes:
                if line.startswith(banned):
                    logging.info("%s was banned, skipping line: %s", banned, line)
                    break
            else:
                await dest.send_all(line)

    async def listen(
        stdout: ReceiveStream,
        reply_sender: MemorySendChannel,
        noti_sender: MemorySendChannel,
    ):
        reader = StreamReader()
        bufsize = select.PIPE_BUF

        reply_send = reply_sender.send
        noti_send = noti_sender.send
        recv = stdout.receive_some

        async with reply_sender, noti_sender:
            while True:
                data = await recv(bufsize)

                if data == b"":
                    raise BrokenPipeError("remote closed pipe")

                for event in reader.feed(data):
                    if isinstance(event, Notification):
                        await noti_send(event)
                    elif isinstance(event, Reply):
                        await reply_send(event)
                    else:
                        raise RuntimeError(f"received an unknown event: {event}")

    command = ["/usr/bin/tmux", "-C", "attach-session", "-t", "controlmode"]
    proc: trio.Process = await trio.open_process(
        command,
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
    )

    stdout = FdStream(1)
    wlock = trio.Lock()

    async with proc:
        async with trio.open_nursery() as nursery:

            nursery.start_soon(forward_stdin, FdStream(sys.stdin.fileno()), proc.stdin)

            reply_sender, reply_receiver = trio.open_memory_channel(5)
            noti_sender, noti_receiver = trio.open_memory_channel(10)

            async with reply_sender, noti_sender, reply_receiver, noti_receiver:
                nursery.start_soon(
                    listen, proc.stdout, reply_sender.clone(), noti_sender.clone()
                )
                nursery.start_soon(report, wlock, stdout, reply_receiver.clone())
                nursery.start_soon(report, wlock, stdout, noti_receiver.clone())


if __name__ == "__main__":
    logging.basicConfig(
        level="DEBUG",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
        format="{asctime} {name} {message}",
    )

    trio.run(main)
