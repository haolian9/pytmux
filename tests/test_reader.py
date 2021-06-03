import pytest
from pytmux import reader, types


def test_stream_reader_1_multiline_event():
    data = bytearray(
        b"""%begin 1622538780 64363 1
26: 1 windows (created Tue Jun  1 16:43:28 2021) (attached)
default: 1 windows (created Mon May 31 17:43:57 2021)
pytmux: 2 windows (created Mon May 31 17:44:30 2021) (attached)
scratchpad: 2 windows (created Mon May 31 17:40:20 2021) (attached)
%end 1622538780 64363 1
"""
    )

    sr = reader.StreamReader()

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
        assert isinstance(event, types.Reply)


def test_streamreader_1_oneline_event():
    sr = reader.StreamReader()

    data = bytearray(b"%session-window-changed $3 @30\n")

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


def test_streamreader_multiline_events(multiline_events: bytes):
    data = bytearray(multiline_events)
    sr = reader.StreamReader()

    while True:
        if not data:
            break
        try:
            sr.feed(data)
        except reader.FulFiled as e:
            readn = e.readn
            assert data[readn - 1 : readn] == b"\n"
            data = data[readn:]
            sr.flush()
        except reader.NeedMore:
            pytest.fail("should not reach NeedMore")
        else:
            pytest.fail("should be FULFILED")


def test_streamreader_list_keys(multiline_events_list_keys: bytes):
    data = bytearray(multiline_events_list_keys)

    sr = reader.StreamReader()

    start = 0
    end = len(data) - 1
    total_events = 0
    while True:
        if start > end:
            break

        try:
            sr.feed(data[start:])
        except reader.FulFiled as e:
            event = sr.flush()
            total_events += 1
            print(event)
            start += e.readn
        except reader.NeedMore:
            pytest.fail("should never reach here")
        else:
            pytest.fail("should never reach here")

    assert total_events == 3


def test_eventreader(multiline_events: bytes):
    data = bytearray(multiline_events)

    class EventReader(reader.EventReaderABC):
        def __init__(self):
            self._lines = []

        @property
        def fulfiled(self):
            return False

        def feed(self, line: bytes):
            self._lines.append(line)

        def flush(self):
            pass

    sr = reader.StreamReader(EventReader())

    try:
        sr.feed(data)
    except reader.NeedMore:
        # pylint: disable=no-member
        lines = sr._er._lines  # type: ignore
        assert b"".join(lines) == data
    else:
        pytest.fail("should not reach here")
