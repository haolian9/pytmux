"""
see:
* https://effectivepython.com/2019/10/22/memoryview-bytearray-zero-copy-interactions
* https://julien.danjou.info/high-performance-in-python-with-zero-copy-and-the-buffer-protocol/
"""

import memory_profiler


@memory_profiler.profile
def illuminate():
    b0 = b"a" * (10 ** 6)
    b1 = b"b" * (2 * 10 ** 7)

    b0_0 = b0  # +0

    ba = bytearray(b1)  # +1
    mv = memoryview(b1)  # +0

    ba.extend(b0)  # +1
    ba.extend(mv)  # +1

    ba_b = bytes(ba)  # +1

    mv_slice = mv[2:]  # +0
    ba_slice = ba[2:]  # +1

    def pass_bytes(data):
        new_b = data[1:]  # +1

    def pass_bytearray(data):
        new_ba = data[1:]  # +1

    def pass_memoryview(data):
        new_mv = data[1:]  # +0

    pass_bytes(b1)
    pass_bytearray(ba)
    pass_memoryview(mv)

    b_list = [b0, mv, ba]  # +0

    b_joined = b"".join(b_list)  # +1

    ba_1 = bytearray()  # +0
    ba_1.extend(b0)  # +1
    ba_1.extend(mv)  # +1
    ba_1.extend(b0)  # +1


if __name__ == "__main__":
    illuminate()
