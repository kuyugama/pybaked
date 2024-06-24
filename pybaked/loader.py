import importlib.util
import sys
import types
from importlib.abc import MetaPathFinder, Loader
from pathlib import Path

from pybaked import BakedReader


def execute(source: str | bytes, module: types.ModuleType):
    code = compile(source, module.__file__, "exec")
    exec(code, module.__dict__)


class BakedPathFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=...):
        entries = sys.path
        if path is not None:
            entries.extend(path)
        # Search in default places
        for path_entry in entries:
            path_entry = Path(path_entry)

            package_name = fullname.rsplit(".", 1)

            if len(package_name) == 1:
                package_name = fullname
            else:
                package_name, _ = package_name

            baked_package = Path(f"{path_entry}")

            inner_module_name = fullname

            parts = fullname.split(".")

            for i, part in enumerate(parts):
                baked_package /= part

                if baked_package.with_suffix(
                    ".py.baked"
                ).exists():
                    baked_package = baked_package.with_suffix(
                        ".py.baked"
                    )
                    inner_module_name = ".".join(parts[i:])
                    break

            if baked_package.exists():
                reader = BakedReader(baked_package)
                location = str(baked_package.joinpath(*inner_module_name.split(".")[1:]))

                for module, _ in reader.modules:
                    if module == inner_module_name:
                        location += ".py"
                        break

                    if (
                        module.endswith("__init__")
                        and module[: -len("__init__") - 1] == inner_module_name
                    ):
                        break
                else:
                    continue

                return importlib.util.spec_from_file_location(
                    inner_module_name,
                    location,
                    loader=BakedLoader(reader, package_name),
                )
        return None


class BakedLoader(Loader):
    def __init__(self, reader: BakedReader, package_name: str):
        self.reader = reader
        self.package_name = package_name

    def create_module(self, spec):
        return types.ModuleType(spec.name)

    def exec_module(self, module):
        module_package = module.__name__ in self.reader.packages

        module.__package__ = module.__name__.rsplit(".", 1)[0]

        formatted_name = ".".join(module.__name__.split("."))

        if module_package:
            module.__package__ = module.__name__
            formatted_name += ".__init__"

        formatted_name = formatted_name.strip(".")

        module.__file__ = (
            str(self.reader.path / Path(*formatted_name.split(".")[1:])) + ".py"
        )

        module.__path__ = [self.reader.path]

        for module_name, source_offset in self.reader.modules:
            if self.reader.path.name.split(".")[0] == module.__package__:
                module.__metadata__ = self.reader.metadata

            if module_name == formatted_name:
                source = self.reader.read_specific(source_offset)
                execute(source, module)


def init():
    sys.meta_path.append(BakedPathFinder())
