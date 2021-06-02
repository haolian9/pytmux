import pytest
from pytmux import reader, types


def test_reader_feed_block():
    sr = reader.StreamReader()

    data = b"""%begin 1622538780 64363 1
26: 1 windows (created Tue Jun  1 16:43:28 2021) (attached)
default: 1 windows (created Mon May 31 17:43:57 2021)
pytmux: 2 windows (created Mon May 31 17:44:30 2021) (attached)
scratchpad: 2 windows (created Mon May 31 17:40:20 2021) (attached)
%end 1622538780 64363 1
"""

    try:
        sr.feed(data[:3])
    except reader.NeedMore:
        pass

    eol_first = data.find(b"\n")
    try:
        sr.feed(data[3 : eol_first + 1])
    except reader.NeedMore:
        pass

    try:
        sr.feed(data[eol_first + 1 :])
    except reader.FulFiled as e:
        assert e.readn == len(data) - eol_first - 1

        event = sr.flush()
        assert isinstance(event, types.Block)


def test_reader_feed_noti():
    sr = reader.StreamReader()

    data = b"%session-window-changed $3 @30\n"

    with pytest.raises(reader.NeedMore):
        sr.feed(data[:3])

    try:
        sr.feed(data[3:])
    except reader.FulFiled as e:
        assert e.readn == len(data) - 3

        try:
            sr.feed(b"0000")
        except reader.FulFiled as e:
            assert e.readn == 0
        else:
            pytest.fail("should be fulfiled")

        event: types.SessionWindowChanged = sr.flush()
        assert isinstance(event, types.SessionWindowChanged)
        assert event.session == 3
        assert event.window == 30
    else:
        pytest.fail("should be fulfiled")


def test_reader_feed_reuse():
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
    ]
    sr = reader.StreamReader()

    for line in feed:
        try:
            sr.feed(line)
        except reader.FulFiled as e:
            assert e.readn == len(line)
            event = sr.flush()
            assert isinstance(event, types.Notification)
            assert line.startswith(event.header)
        else:
            pytest.fail("should be fulfiled")


def test_reader_feed_reuse_complicated():
    data = b"""%begin 1622542575 70394 0
%end 1622542575 70394 0
%window-add @35
%sessions-changed
%session-changed $27 27
%output %78 \\033[1m\\033[7m%\\033[27m\\033[1m\\033[0m \\015 \\015
%output %78 \\015\\033[0m\\033[27m\\033[24m\\033[J\\033[0m\\033[49m\\033[39m\\033[0m\\033[49m\\033[34m!w /\\033[0m\\033[34m\\033[49m\\033[34m\\033[0m\\033[34m\\033[49m \\033[0m\\033[34m\\033[49m\\033[32m>\\033[0m\\033[32m\\033[49m\\033[32m\\033[0m\\033[32m\\033[49m\\033[30m\\033[0m\\033[30m\\033[49m\\033[39m \\033[0m\\033[49m\\033[39m\\033[K\\033[72C\\033[0m\\033[49m\\033[39m\\033[72D
%output %78 \\033[?2004h
"""
    sr = reader.StreamReader()

    start = 0
    try:
        sr.feed(data)
    except reader.FulFiled as e:
        readn = e.readn
        start += readn
        event = sr.flush()
        print(event)
        assert isinstance(event, types.Block)
        assert event.body == b""
        assert event.success
    else:
        pytest.fail("should be fulfiled")

    assert start == len(b"%begin 1622542575 70394 0\n%end 1622542575 70394 0\n")

    feed = data[start:]
    while True:
        if not feed:
            break
        try:
            sr.feed(feed)
        except reader.FulFiled as e:
            readn = e.readn
            assert feed[readn - 1 : readn] == b"\n"
            feed = feed[readn:]
            sr.flush()
        except reader.NeedMore:
            pytest.fail("should not reach NeedMore")
        else:
            pytest.fail("should be FULFILED")

    # try:
    #     sr.feed(data[start:])
    # except reader.FulFiled as e:
    #     readn = e.readn
    #     start += readn
    #     event = sr.flush()
    #     assert isinstance(event, types.WindowAdd)
    # else:
    #     pytest.fail("should be fulfiled")


def test_find_eol():
    data = b"""%begin 1622542575 70394 0
%end 1622542575 70394 0
%window-add @35
%sessions-changed
%session-changed $27 27
%output %78 \\033[1m\\033[7m%\\033[27m\\033[1m\\033[0m \\015 \\015
%output %78 \\015\\033[0m\\033[27m\\033[24m\\033[J\\033[0m\\033[49m\\033[39m\\033[0m\\033[49m\\033[34m!w /\\033[0m\\033[34m\\033[49m\\033[34m\\033[0m\\033[34m\\033[49m \\033[0m\\033[34m\\033[49m\\033[32m>\\033[0m\\033[32m\\033[49m\\033[32m\\033[0m\\033[32m\\033[49m\\033[30m\\033[0m\\033[30m\\033[49m\\033[39m \\033[0m\\033[49m\\033[39m\\033[K\\033[72C\\033[0m\\033[49m\\033[39m\\033[72D
%output %78 \\033[?2004h
"""

    start = 0
    total_lines = 8
    count = 0
    while True:
        eol = data.find(b"\n", start)
        if eol < 0:
            break
        count += 1
        start = eol + 1
        assert data[start - 1 : start] == b"\n"

    assert count == total_lines


def test_reader_feed_list_keys(list_keys_output: bytes):
    sr = reader.StreamReader()

    start = 0
    end = len(list_keys_output) - 1
    total_events = 0
    while True:
        if start > end:
            break

        try:
            sr.feed(list_keys_output[start:])
        except reader.FulFiled as e:
            event = sr.flush()
            total_events += 1
            print(event)
            start += e.readn
        except reader.NeedMore:
            raise RuntimeError("should never reach here")
        else:
            raise RuntimeError("should never reach here")

    assert total_events == 3


def test_streamreader(data2: bytes = b""):
    data = b"""%begin 1622542575 70394 0
%end 1622542575 70394 0
%window-add @35
%sessions-changed
%session-changed $27 27
%output %78 \\033[1m\\033[7m%\\033[27m\\033[1m\\033[0m \\015 \\015
%output %78 \\015\\033[0m\\033[27m\\033[24m\\033[J\\033[0m\\033[49m\\033[39m\\033[0m\\033[49m\\033[34m!w /\\033[0m\\033[34m\\033[49m\\033[34m\\033[0m\\033[34m\\033[49m \\033[0m\\033[34m\\033[49m\\033[32m>\\033[0m\\033[32m\\033[49m\\033[32m\\033[0m\\033[32m\\033[49m\\033[30m\\033[0m\\033[30m\\033[49m\\033[39m \\033[0m\\033[49m\\033[39m\\033[K\\033[72C\\033[0m\\033[49m\\033[39m\\033[72D
%output %78 \\033[?2004h
"""

    if data2:
        data = data2

    class EventReader:
        def __init__(self):
            self._lines = []
            self.fulfiled = False

        def feed(self, line: bytes):
            self._lines.append(line)

    sr = reader.StreamReader(EventReader)

    try:
        sr.feed(data)
    except reader.NeedMore:
        lines = sr._event._lines
        for line in lines:
            print(line)
        # assert len(lines) == 8
        assert b"".join(lines) == data
    else:
        pytest.fail("should not reach here")


if __name__ == "__main__":
    import logging
    from pathlib import Path

    logging.basicConfig(
        level="DEBUG",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
        format="{asctime} {message}",
    )

    file = Path(__file__).resolve().parent.joinpath("testdata", "list-keys.output")
    with file.open("rb") as fp:
        data = fp.read()

    # test_streamreader(data)
    test_reader_feed_list_keys(data)

    # test_reader_feed_reuse_complicated()
    # test_streamreader()
