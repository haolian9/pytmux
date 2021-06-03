from collections import deque
from queue import Empty, Full, Queue

import pytest


def test_fifo():
    q = Queue(3)

    q.put(1)
    q.put(2)
    q.put(3)

    with pytest.raises(Full):
        q.put_nowait(4)

    assert q.get() == 1
    assert q.get() == 2
    assert q.get() == 3

    with pytest.raises(Empty):
        q.get_nowait()


def test_deque():
    dq = deque([], 3)

    dq.append(1)
    dq.append(2)
    dq.append(3)
    dq.append(4)

    assert dq.popleft() == 2
    assert dq.popleft() == 3
    assert dq.popleft() == 4

    with pytest.raises(IndexError):
        dq.popleft()
