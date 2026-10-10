"""Non-blocking keypress detection for terminal UIs (POSIX only)."""

import os
import select
import sys
import termios
import tty
from collections.abc import Callable, Iterator
from contextlib import contextmanager


@contextmanager
def keypress() -> Iterator[Callable[[], bool]]:
    """Yield a function that returns True if a key has been pressed.

    Inside the `with`, the terminal is in cbreak mode: keys arrive one at a
    time without Enter and are not echoed (so they don't garble rich output).
    Ctrl-C still raises KeyboardInterrupt. The old mode is restored on exit.
    If stdin is not a terminal (e.g. piped), the function always says False.
    """
    if not sys.stdin.isatty():
        yield lambda: False
        return

    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)

    def pressed() -> bool:
        # select with timeout 0 = "is there input ready?" without blocking.
        if select.select([fd], [], [], 0)[0]:
            os.read(fd, 1024)  # consume it so it doesn't leak to the shell
            return True
        return False

    tty.setcbreak(fd)
    try:
        yield pressed
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
