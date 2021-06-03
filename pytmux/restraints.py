import subprocess
from distutils.version import StrictVersion


def ensure_tmux_suffice():
    cp = subprocess.run(["tmux", "-V"], stdout=subprocess.PIPE, check=True)
    out: bytes = cp.stdout

    prefix = b"tmux "
    assert out.startswith(prefix)

    local = StrictVersion(out[len(prefix) :])
    least = StrictVersion("3.2")

    if local < least:
        raise RuntimeError("installed tmux too old")
