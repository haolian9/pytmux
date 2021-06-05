import abc
import logging
import typing as T

from . import types

_log = logging.getLogger(__name__)


class ProtocolError(Exception):
    ...


def header_in_line(line: bytes) -> bytes:
    assert line.endswith(b"\n")

    if not line.startswith(b"%"):
        raise ProtocolError("head wrap not started with %")

    sep = line.find(b" ")
    if sep >= 0:
        header = bytes(line[:sep])
    else:
        header = bytes(line[:-1])

    return header


_ONELINE_EVENTS = {noti.header: noti for noti in types.ALL_NOTI}
_MULTILINE_EVENTS = {types.Reply.header: types.Reply}
_BLOCK_END_HEADERS = {e.value for e in types.BlockEnd}


class EventReaderABC(abc.ABC):
    @abc.abstractmethod
    def feed(self, line: bytes) -> T.Iterable[types.Event]:
        pass

    @abc.abstractproperty
    def clean(self) -> bool:
        pass


class EventReader(EventReaderABC):
    def __init__(self):
        self._lines: T.List[bytes] = []
        self._event_cls: T.Optional[types.Event] = None

        self._current = self._head_wrap

    @property
    def clean(self):
        return not self._lines

    def feed(self, line: bytes):
        yield from self._current(line)

    def _head_wrap(self, line: bytes):
        assert not self._lines
        assert not self._event_cls
        # pylint: disable=comparison-with-callable
        assert self._current == self._head_wrap

        header = header_in_line(line)

        try:
            cls = _ONELINE_EVENTS[header]
        except KeyError:
            pass
        else:
            self._event_cls = cls
            self._lines.append(line)

            _log.debug("head wrap indicates oneline event, FULFILED")
            yield self._flush()
            return

        try:
            cls = _MULTILINE_EVENTS[header]  # type: ignore
        except KeyError:
            pass
        else:
            self._event_cls = cls
            self._lines.append(line)
            _log.debug("head wrap indicates multiline event, waiting for body")
            self._current = self._body
            return

        raise ProtocolError("unknown head wrap")

    def _body(self, line: bytes):
        assert self._event_cls

        self._lines.append(line)

        if self._is_end_wrap(line):
            _log.debug("reached end wrap, FULFILED")
            yield self._flush()

    @classmethod
    def _is_end_wrap(cls, line: bytes):
        if not line.startswith(b"%"):
            return False

        header = header_in_line(line)

        if header not in _BLOCK_END_HEADERS:
            return False

        return True

    def _flush(self) -> types.Event:
        lines = self._lines
        assert self._event_cls
        event = self._event_cls.from_lined_bytes(lines)

        self._lines = []
        self._event_cls = None
        self._current = self._head_wrap

        return event


class StreamReader:
    def __init__(self, er: EventReaderABC = None):
        # TODO@haoliang maybe using io.BytesIO
        # shot: not enough for a line
        self._short = bytearray()

        self._er = er if er else EventReader()

    @property
    def clean(self):
        return self._er.clean and not self._short

    def feed(self, data: bytes) -> T.Iterable[types.Event]:
        _log.debug("feed %s bytes", len(data))

        start = 0
        end = len(data) - 1

        while True:
            short = self._short
            assert b"\n" not in short

            eol = data.find(b"\n", start)
            if eol < 0:
                short.extend(data[start:])
                assert b"\n" not in short
                break

            short.extend(data[start : eol + 1])
            assert short.endswith(b"\n")
            start = eol + 1

            line = short
            self._short = bytearray()

            yield from self._er.feed(line)

            if start > end:
                break
