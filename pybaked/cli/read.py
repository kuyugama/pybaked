from . import colors
from .. import protocol
from pathlib import Path
from typing import Sequence, Any
from argparse import ArgumentParser
from .colors import green, yellow, purple, red, cyan, blue

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


# noinspection PyPackageRequirements,PyUnresolvedReferences
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
        colors.USE_COLORS = False

    if args.baked_package.endswith(".py"):
        print(
            red(
                f"Expected baked package. But given python module {yellow(args.baked_package)}"
            )
        )
        return -2

    baked_package = args.baked_package

    if not args.baked_package.endswith(protocol.EXTENSION):
        baked_package = args.baked_package + protocol.EXTENSION

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
