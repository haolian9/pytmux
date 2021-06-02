def test_rfind():
    barr = bytearray(b"a b c\nd e f\n")

    assert barr.rfind(b"\n") == len(barr) - 1
    assert barr.rfind(b"\n", 0, -1) == len(b"a b c\n") - 1
    assert barr.find(b"\n", len(b" a b c\n")) == len(barr) - 1


def test_reuse_same_range():
    barr = bytearray(b"abcdefghijklmnop")

    defg = barr[3:7]

    barr[3:7] = b"x" * 8

    assert defg == b"defg"
    assert len(barr) == 16 - 4 + 8
