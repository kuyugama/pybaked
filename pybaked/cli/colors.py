from typing import Any

USE_COLORS = True


def color(s: str, code: int) -> str:
    if not USE_COLORS:
        return str(s)

    s = str(s)

    if "\x1b[0m" in s:
        s = s.replace("\033[0m", f"\033[{code}m")

    return f"\033[{code}m{s}\033[0m"


def red(s: Any) -> str:
    return color(s, 31)


def green(s: Any) -> str:
    return color(s, 32)


def yellow(s: Any) -> str:
    return color(s, 33)


def cyan(s: Any) -> str:
    return color(s, 36)


def blue(s: Any) -> str:
    return color(s, 34)


def purple(s: Any) -> str:
    return color(s, 35)
