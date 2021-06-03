import errno
import os

import pytest


def test_write_on_closed_fd():
    fd = os.open("/dev/null", os.O_WRONLY | os.O_APPEND)
    os.write(fd, b"hello and welcome")

    os.close(fd)

    try:
        os.write(fd, b"xxx")
    except OSError as e:
        assert e.errno == errno.EBADF
    else:
        pytest.fail("should be OSError")


def test_read_on_closed_fd():
    fd = os.open("/dev/zero", os.O_RDONLY)
    os.read(fd, 1)

    os.close(fd)

    try:
        os.read(fd, 1)
    except OSError as e:
        assert e.errno == errno.EBADF
    else:
        pytest.fail("should be OSError")


def test_red_on_closed_pipe():
    rfd, wfd = os.pipe()
    os.write(wfd, b"1")
    out = os.read(rfd, 1)
    assert out == b"1"

    os.close(wfd)

    out = os.read(rfd, 1)
    assert out == b""
