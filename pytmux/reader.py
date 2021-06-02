import logging
import typing as T

from . import types

_log = logging.getLogger(__name__)


class FulFiled(Exception):
    def __init__(self, readn: int):
        super().__init__()

        self.readn = readn


class NeedMore(Exception):
    def __init__(self, readn: int):
        super().__init__()

        self.readn = readn


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
_MULTILINE_EVENTS = {types.Block.header: types.Block}
_BLOCK_END_HEADERS = {e.value for e in types.BlockEnd}


class EventReader:
    def __init__(self):
        self._buffer = bytearray()
        self._event_cls: T.Optional = None
        self._fulfiled = False

        self._current = self._head_wrap

    @property
    def fulfiled(self):
        return self._fulfiled

    def feed(self, line: bytes):
        if self._fulfiled:
            raise FulFiled(0)

        self._current(line)

    def _head_wrap(self, line: bytes):
        assert not self._buffer
        assert not self._event_cls
        assert not self._fulfiled
        assert self._current == self._head_wrap

        header = header_in_line(line)

        try:
            cls = _ONELINE_EVENTS[header]
        except KeyError:
            pass
        else:
            self._event_cls = cls
            self._buffer.extend(line)
            self._fulfiled = True

            _log.debug("head wrap indicates oneline event, FULFILED")
            raise FulFiled(len(line))

        try:
            cls = _MULTILINE_EVENTS[header]  # type: ignore
        except KeyError:
            pass
        else:
            self._event_cls = cls
            self._buffer.extend(line)
            _log.debug("head wrap indicates multiline event, waiting for body")
            self._current = self._body
            raise NeedMore(len(line))

        raise ProtocolError("unknown head wrap")

    def _body(self, line: bytes):
        self._buffer.extend(line)

        if self._is_end_wrap(line):
            _log.debug("reached end wrap, FULFILED")
            self._fulfiled = True
            raise FulFiled(len(line))

        raise NeedMore(len(line))

    @classmethod
    def _is_end_wrap(cls, line: bytes):
        if not line.startswith(b"%"):
            return False

        header = header_in_line(line)

        if header not in _BLOCK_END_HEADERS:
            return False

        return True

    def flush(self) -> types.Event:
        if not self._fulfiled:
            raise NeedMore(0)

        data = self._buffer
        cls = self._event_cls
        assert issubclass(cls, types.Event)
        event = cls.from_bytes(data)

        self._buffer = bytearray()
        self._event_cls = None
        self._fulfiled = False
        self._current = self._head_wrap

        return event


class StreamReader:
    def __init__(self, eventreader_cls=EventReader):
        self._short = bytearray()
        self._event: EventReader = eventreader_cls()

    def feed(self, data: bytes):
        _log.debug("feed %s data", len(data))

        if self._event.fulfiled:
            raise FulFiled(0)

        self._feed(data)

    def _feed(self, data: bytes):

        start = 0
        end = len(data) - 1

        while True:
            short = self._short
            assert b"\n" not in short

            eol = data.find(b"\n", start)
            if eol < 0:
                short.extend(data[start:])
                assert b"\n" not in short
                raise NeedMore(len(data))

            short.extend(data[start : eol + 1])
            assert short.endswith(b"\n")
            start = eol + 1

            line = short
            self._short = bytearray()

            try:
                self._event.feed(line)
            except FulFiled as e:
                line_rest = len(line) - e.readn
                data_rest = end - start
                readn = end - data_rest - line_rest
                assert readn >= 0
                # pylint: disable=raise-missing-from
                raise FulFiled(readn)
            except NeedMore as e:
                assert e.readn == len(line)

            if start > end:
                raise NeedMore(len(data))

    def flush(self):
        if not self._event.fulfiled:
            raise NeedMore(0)

        return self._event.flush()
