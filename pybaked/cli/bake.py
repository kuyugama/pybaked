import json
from argparse import ArgumentParser
from pathlib import Path

from . import colors
from .colors import cyan, green, red, blue, yellow, purple

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


def bake():
    args = bake_parser.parse_args()

    if args.no_colors:
        colors.USE_COLORS = False

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
