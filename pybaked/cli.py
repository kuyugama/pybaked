import json
import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Sequence

from pybaked import protocol

bake_parser = ArgumentParser()
bake_parser.add_argument("package", help="Package to bake")
bake_parser.add_argument(
    "-o", "--output", help="Output file name", default=None, required=False
)
bake_parser.add_argument(
    "-H",
    "--hash",
    help="Hash content and write it to file",
    action="store_true",
    default=False,
)
bake_parser.add_argument(
    "--no-colors", help="Don't color output", action="store_true", default=False
)
bake_parser.add_argument(
    "-m",
    "--metadata",
    help="JSON encoded metadata",
    required=False,
    default="{}",
)
bake_parser.add_argument(
    "-M",
    "--metadata-file",
    help="JSON encoded metadata file path",
    required=False,
    default=None,
)

read_parser = ArgumentParser()
read_parser.add_argument(
    "baked_package",
    help="Baked package file",
)
read_parser.add_argument(
    "-m",
    "--module",
    help="Read specific module source",
    required=False,
    default=None,
)
read_parser.add_argument(
    "--no-colors", help="Don't color output", action="store_true", default=False
)

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


def bake():
    args = bake_parser.parse_args()

    if args.no_colors:
        global USE_COLORS
        USE_COLORS = False

    package_path = Path(args.package)

    if not package_path.is_dir():
        print(red(f"Package {yellow(args.package)} not found"))
        return -1

    metadata = json.loads(args.metadata)

    if args.metadata_file is not None:
        mf = Path(args.metadata_file)
        if not mf.is_file():
            print(
                red(
                    f"Metadata file {yellow(args.metadata_file)} is not "
                    f"exists or is not a file"
                )
            )
            return -2

        metadata = json.loads(mf.read_text())

    from pybaked import BakedMaker

    baker = BakedMaker.from_package(package_path, args.hash, metadata)

    print(
        cyan(
            f"Baking {yellow(args.package)} as {yellow(args.output or package_path.name)}..."
        ),
        flush=True,
        end="\r",
    )

    filename = baker.file(args.output or package_path)

    print(
        green(
            f"Baked package {yellow(args.package)} into file {cyan(filename)}"
        )
    )

    return 0


def format_metadata(metadata: dict[str, Any]) -> str:
    lines = []
    for key, value in metadata.items():
        if isinstance(value, dict):
            value = "\n\t" + format_metadata(value).replace("\n", "\n\t")

        elif isinstance(value, list):
            value = "\n" + "\n".join((f"\t- {e}" for e in value))

        elif isinstance(value, str):
            value = green(repr(value))

        elif isinstance(value, (int, float)):
            value = blue(value)

        elif isinstance(value, bool):
            value = green(value) if value else red(value)

        else:
            value = yellow(repr(value))

        key = yellow(key) + ": "

        lines.append(f"{key}{value}")

    return "\n".join(lines)


def format_modules(modules: Sequence[str]) -> str:
    try:
        from asciitree import LeftAligned
        from asciitree.drawing import BoxStyle, BOX_LIGHT

        render = LeftAligned(draw=BoxStyle(gfx=BOX_LIGHT))

        tree = {}
        for module in modules:
            package = tree
            parts = module.split(".")

            for deep, part in enumerate(parts):
                if deep == len(parts) - 1:
                    real = module.split(".", 1)[1]
                    part += f" ({yellow(real)})"
                package = package.setdefault(purple(part), {})

        return green(render(tree))

    except ImportError:
        pass

    modules_formatted: dict[str, str] = {}

    for name in modules:
        modules_formatted["/".join(map(purple, name.split(".")[1:]))] = yellow(
            ".".join(name.split(".")[1:])
        )

    return "\n".join(
        f"\t- {pretty} ({real})" for pretty, real in modules_formatted.items()
    )


def read():
    args = read_parser.parse_args()

    if args.no_colors or args.module is not None:
        global USE_COLORS
        USE_COLORS = False

    if args.baked_package.endswith(".py"):
        print(
            red(
                f"Expected baked package. But given python module {yellow(args.baked_package)}"
            )
        )
        return -2

    baked_package = args.baked_package

    if not args.baked_package.endswith(protocol.EXTENSION):
        package_name = args.baked_package
        baked_package = args.baked_package + protocol.EXTENSION
    else:
        package_name = args.baked_package[: -len(protocol.EXTENSION)]

    package_path = Path(baked_package)

    if not package_path.is_file():
        print(red(f"Package {yellow(baked_package)} not found"))
        return -1

    from pybaked import BakedReader

    if args.module is None:
        print(cyan(f"Reading {yellow(baked_package)}..."), flush=True, end="\r")

    reader = BakedReader(package_path)
    modules = reader.modules_dict
    packages = reader.packages[1:]

    if args.module is not None:
        module = args.module
        if not module.startswith(reader.name):
            module = reader.name + "." + module

        if module not in modules:
            print(f"Module {args.module} not found in {baked_package}")
            return -3

        source = reader.read_specific(modules[module])
        print(source.decode())

        return 0

    print(
        green(f"Package {yellow(baked_package)} read successfully"), end="\n\n"
    )

    print(green(f"Hash supported: {yellow(reader.hash_match is not None)}"))
    if reader.hash_match is not None:
        color = green if reader.hash_match else red
        print(green(f"Hash matched: {color(reader.hash_match)}"))

    print(green(f"Creation date: {blue(str(reader.created))}"))
    print(green("Metadata:"))
    print(format_metadata(reader.metadata), "\n")
    print(green(f"Subpackages ({blue(len(packages))}):"))
    print(
        "\n".join(
            "\t- " + yellow(".").join(map(purple, package.split(".")[1:]))
            for package in packages
        ),
        end="\n\n",
    )
    print(green(f"Modules ({blue(len(modules))}):"))
    print(format_modules(list(modules.keys())))
