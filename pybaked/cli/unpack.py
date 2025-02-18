from argparse import ArgumentParser
from pathlib import Path

from pybaked import BakedReader, protocol
from pybaked.cli import colors

parser = ArgumentParser()
parser.add_argument(
    "baked_package",
    help="Baked package file",
)
parser.add_argument(
    "-o",
    "--output",
    help="Output package",
    default=None,
    required=False,
)
parser.add_argument(
    "--no-colors", help="Don't color output", action="store_true", default=False
)


def unpack():
    args = parser.parse_args()

    if args.no_colors:
        colors.USE_COLORS = False

    baked_package = args.baked_package

    if not args.baked_package.endswith(protocol.EXTENSION):
        baked_package = args.baked_package + protocol.EXTENSION

    display_name = colors.yellow(baked_package)

    source = Path(baked_package)
    if not source.is_file():
        print(colors.red(f"Package {display_name} not found"))
        exit(1)

    print(colors.cyan(f"Reading {display_name}..."), flush=True, end="\r")

    try:
        package = BakedReader(source)
    except ValueError as e:
        print(colors.red(f"Cannot read package: {e.args[0]}"))
        exit(2)
    except Exception as e:
        print(colors.red(f"Unexpected error: {e}"))
        exit(2)

    print(
        colors.green(
            f"Package {colors.yellow(baked_package)} read successfully"
        ),
        end="\n\n",
    )
    print(colors.cyan(f"Creation date: {colors.blue(str(package.created))}"))
    print(
        colors.cyan(f"Modules: {colors.yellow(len(package.modules))}"),
        end="\n\n",
    )

    output = args.output
    if output is None:
        output = source.name.split(".", 1)[0]

    print(
        colors.cyan(f"Unpacking {display_name} into {colors.yellow(output)}...")
    )
    for name, offset in package.modules_dict.items():
        name = name.split(".")[1:]
        module = Path(output, *name).with_suffix(".py")

        module.parent.mkdir(parents=True, exist_ok=True)

        module.write_bytes(package.read_specific(offset))

        print(colors.cyan(f"Created {colors.yellow(module)} module"))

    print(
        colors.green(
            f"\nSuccessfully unpacked {display_name} into {colors.yellow(output)}!"
        )
    )
