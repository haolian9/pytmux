"""
see: https://github.com/tmux/tmux/wiki/Control-Mode
"""

import typing as T
from enum import Enum

import attr


def _to_str(data: bytes):
    return data.decode()


def _to_int(data: bytes):
    return int(data, 10)


def _percent_int(data: bytes):
    assert data.startswith(b"%")
    return int(data[1:], 10)


def _at_int(data: bytes):
    assert data.startswith(b"@")
    return int(data[1:], 10)


def _dollar_int(data: bytes):
    assert data.startswith(b"$")
    return int(data[1:], 10)


class BlockEnd(Enum):
    END = b"%end"
    ERROR = b"%error"


class Event:
    @classmethod
    def from_bytes(cls, data: bytearray):
        raise NotImplementedError()


@attr.s
class _BlockWrap(Event):
    header: bytes = attr.ib()
    timestamp: int = attr.ib(converter=_to_int)
    number: int = attr.ib(converter=_to_int)  # unique command number
    flags: int = attr.ib(converter=_to_int)

    @classmethod
    def from_bytes(cls, data: bytearray):
        header, timestamp, number, flags = data.split(b" ", maxsplit=3)

        return cls(header, timestamp, number, flags)


@attr.s
class Reply(Event):
    """Every %begin, %end or %error has three arguments:
    * the time as seconds from epoch;
    * a unique command number;
    * flags, at the moment this is always one.
    """

    header = b"%begin"

    head_wrap: _BlockWrap = attr.ib()
    body: bytes = attr.ib()  # could be multi-line
    end_wrap: _BlockWrap = attr.ib()

    @property
    def success(self):
        return self.end_wrap.header == BlockEnd.END.value

    @classmethod
    def from_bytes(cls, data: bytearray):
        eol_first = data.find(b"\n")
        hdata = data[: eol_first + 1]
        eol_last = data.rfind(b"\n", 0, -2)
        edata = data[eol_last + 1 :]
        body = data[eol_first + 1 : eol_last + 1]

        head_wrap = _BlockWrap.from_bytes(hdata)
        end_wrap = _BlockWrap.from_bytes(edata)

        return cls(head_wrap, body, end_wrap)


ALL_NOTI: T.List["Notification"] = []


class Notification(Event):
    header = b""

    def __init_subclass__(cls, **kwargs):
        global ALL_NOTI

        super().__init_subclass__(**kwargs)

        if cls.header == Notification.header:
            raise NotImplementedError(f"{cls}.header is missing")

        ALL_NOTI.append(cls)

    @classmethod
    def from_bytes(cls, data: bytearray):
        assert data.startswith(cls.header)
        assert data.endswith(b"\n")

        fields = attr.fields(cls)

        if not fields:
            return cls()

        _, *parts = data[:-1].split(b" ", maxsplit=len(fields) - 1 + 1)

        return cls(*parts)


@attr.s
class PaneModeChanged(Notification):
    """%pane-mode-changed %pane
    A pane's mode was changed.
    """

    header = b"%pane-mode-changed"
    pane: int = attr.ib(converter=_percent_int)  # %\d+


@attr.s
class WindowPaneChanged(Notification):
    """%window-pane-changed @window %pane
    A window's active pane changed.
    """

    header = b"%window-pane-changed"
    window: int = attr.ib(converter=_at_int)
    pane: int = attr.ib(converter=_percent_int)


@attr.s
class WindowClose(Notification):
    """%window-close @window
    A window was closed in the attached session.
    """

    header = b"%window-close"
    window: int = attr.ib(converter=_at_int)


@attr.s
class UnlinkedWindowClose(Notification):
    """%unlinked-window-close @window
    A window was closed in another session.
    """

    header = b"%unlinked-window-close"
    window: int = attr.ib(converter=_at_int)


@attr.s
class WindowAdd(Notification):
    """%window-add @window
    A window was added to the attached session.
    """

    header = b"%window-add"
    window: int = attr.ib(converter=_at_int)


@attr.s
class UnlinkedWindowAdd(Notification):
    """%unlinked-window-add @window
    A window was added to another session.
    """

    header = b"%unlinked-window-add"
    window: int = attr.ib(converter=_at_int)


@attr.s
class WindowRenamed(Notification):
    """%window-renamed @window new-name
    A window was renamed in the attached session.
    """

    header = b"%window-renamed"
    window: int = attr.ib(converter=_at_int)
    new_name: str = attr.ib(converter=_to_str)


@attr.s
class UnlinkedWindowRenamed(Notification):
    """%unlinked-window-renamed @window new-name
    A window was renamed in another session.
    """

    header = b"%unlinked-window-renamed"
    window: int = attr.ib(converter=_at_int)
    new_name: str = attr.ib(converter=_to_str)


@attr.s
class SessionChanged(Notification):
    """%session-changed $session session-name
    The attached session was changed.
    """

    header = b"%session-changed"
    session: int = attr.ib(converter=_dollar_int)
    session_name: str = attr.ib(converter=_to_str)


@attr.s
class ClientSessionChanged(Notification):
    """%client-session-changed client $session session-name
    Another client's attached session was changed.
    """

    header = b"%client-session-changed"
    client: str = attr.ib(converter=_to_str)
    session: int = attr.ib(converter=_dollar_int)
    session_name: str = attr.ib(converter=_to_str)


@attr.s
class SessionRenamed(Notification):
    """%session-renamed $session new-name
    A session was renamed.
    """

    header = b"%session-renamed"
    session: int = attr.ib(converter=_dollar_int)
    new_name: str = attr.ib(converter=_to_str)


@attr.s
class SessionsChanged(Notification):
    """%sessions-changed
    A session was created or destroyed.
    """

    header = b"%sessions-changed"


@attr.s
class SessionWindowChanged(Notification):
    """%session-window-changed $session @window
    A session's current window was changed.
    """

    header = b"%session-window-changed"
    session: int = attr.ib(converter=_dollar_int)
    window: int = attr.ib(converter=_at_int)


@attr.s
class ClientDetached(Notification):
    """%client-detached client
    The client has detached.
    """

    header = b"%client-detached"
    client: str = attr.ib(_to_str)


@attr.s
class Continue(Notification):
    """%continue pane-id
    The pane has been continued after being paused (if the pause-after flag is set, see refresh-client -A).
    """

    header = b"%continue"

    pane: int = attr.ib(converter=_percent_int)


@attr.s
class Exit(Notification):
    """%exit [reason]
    The tmux client is exiting immediately, either because it is not attached to any session or an error occurred.  If present, reason describes why the client exited.
    """

    header = b"%exit"
    reason: T.Optional[bytes] = attr.ib(default=None)


@attr.s
class ExtendedOutput(Notification):
    """%extended-output pane-id age ... : value
    New form of %output sent when the pause-after flag is set.  age is the time in milliseconds for which tmux had buffered the output before it was sent.  Any subsequent arguments up until a single ‘:’ are for future use and should be ignored.
    """

    header = b"%extended-output"
    pane: int = attr.ib(converter=_percent_int)
    # TODO@haoliang
    rest: bytes = attr.ib()


@attr.s
class Output(Notification):
    """%output pane-id value
    A window pane produced output.  value escapes non-printable characters and backslash as octal.
    """

    header = b"%output"
    pane: int = attr.ib(converter=_percent_int)
    # TODO@haoliang
    value: bytes = attr.ib()


@attr.s
class LayoutChange(Notification):
    """%layout-change window-id window-layout window-visible-layout window-flags
    The layout of a window with ID window-id changed.  The new layout is window-layout.  The window's visible layout is window-visible-layout and the window flags are window-flags.
    """

    # TODO@haoliang
    header = b"%layout-change"

    window: int = attr.ib(converter=_at_int)
    window_layout: bytes = attr.ib()
    window_visible_layout: bytes = attr.ib()
    window_flags: bytes = attr.ib()


@attr.s
class Pause(Notification):
    """%pause pane-id
    The pane has been paused (if the pause-after flag is set).
    """

    header = b"%pause"
    pane: int = attr.ib(converter=_percent_int)


@attr.s
class SubscriptionChanged(Notification):
    """%subscription-changed name session-id window-id window-index pane-id ... : value
    The value of the format associated with subscription name has changed to value.  See refresh-client -B.  Any arguments after pane-id up until a single ‘:’ are for future use and should be ignored.
    """

    header = b"%subscription-changed"
    name: bytes = attr.ib()
    session: int = attr.ib(converter=_dollar_int)
    window: int = attr.ib(converter=_at_int)
    window_idx: int = attr.ib(converter=_at_int)
    pane: int = attr.ib(converter=_percent_int)
    # TODO@haoliang
    rest: bytes = attr.ib()
