from pytmux import reader, types


def test_noti_from_bytes():

    feed = [
        b"%window-pane-changed @3 %68\n",
        b"%unlinked-window-add @32\n",
        b"%client-session-changed /dev/pts/9 $24 24\n",
        b"%client-session-changed /dev/pts/7 $1 scratchpad"
        b"%client-detached /dev/pts/9\n",
        b"%client-detached client-410578" b"%unlinked-window-close @32\n",
        b"%window-pane-changed @3 %46\n",
        b"%sessions-changed\n",
        b"%exit\n",
        b"%window-add @35\n",
        b"%layout-change @59 3369,232x48,0,0,119 3369,232x48,0,0,119 *\n",
    ]

    headers = {noti.header: noti for noti in types.ALL_NOTI}

    for line in feed:
        header = reader.header_in_line(line)
        cls = headers[header]
        cls.from_bytes(line)


def test_block_from_bytes():

    data = b"""%begin 1622538780 64363 1
26: 1 windows (created Tue Jun  1 16:43:28 2021) (attached)
default: 1 windows (created Mon May 31 17:43:57 2021)
pytmux: 2 windows (created Mon May 31 17:44:30 2021) (attached)
scratchpad: 2 windows (created Mon May 31 17:40:20 2021) (attached)
%end 1622538780 64363 1
"""

    # header = reader.header_in_line(data[:data.find(b'\n')+1])
    reply = types.Reply.from_bytes(data)

    assert reply.success
    assert reply.head_wrap.header == b"%begin"
    assert reply.end_wrap.header == b"%end"
    assert reply.body[0].startswith(b"26")
    assert reply.body[-1].endswith(b"attached)\n")
