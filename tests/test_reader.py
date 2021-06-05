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

    for event in sr.feed(data[:3]):
        pytest.fail("should not have a complete event")
    assert not sr.clean

    eol_first = data.find(b"\n")

    for event in sr.feed(data[3 : eol_first + 1]):
        pytest.fail("should not have a complete event")
    assert not sr.clean

    for event in sr.feed(data[eol_first + 1 :]):
        assert isinstance(event, types.Reply)
    assert sr.clean


def test_streamreader_1_oneline_event():
    sr = reader.StreamReader()

    data = bytearray(b"%session-window-changed $3 @30\n")

    for event in sr.feed(data[:3]):
        pytest.fail("should not have a complete event")
    assert not sr.clean

    for event in sr.feed(data[3:]):
        assert isinstance(event, types.SessionWindowChanged)
        assert event.session == 3
        assert event.window == 30
    assert sr.clean


def test_streamreader_multiline_events(multiline_events: bytes):
    data = bytearray(multiline_events)
    sr = reader.StreamReader()

    for event in sr.feed(data):
        assert isinstance(event, types.Event)
    assert sr.clean


def test_streamreader_list_keys(multiline_events_list_keys: bytes):
    data = bytearray(multiline_events_list_keys)
    sr = reader.StreamReader()

    total_events = 0
    for event in sr.feed(data):
        total_events += 1
        assert isinstance(event, types.Event)
    assert sr.clean
    assert total_events == 3


def test_eventreader(multiline_events: bytes):
    data = bytearray(multiline_events)

    class EventReader(reader.EventReaderABC):
        def feed(self, line: bytes):
            yield line

        @property
        def clean(self):
            return True

    sr = reader.StreamReader(EventReader())

    lines = []

    for line in sr.feed(data):
        assert line.endswith(b"\n")  # type: ignore
        lines.append(line)

    assert b"".join(lines) == data  # type: ignore
