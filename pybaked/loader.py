import importlib.util
import sys
import types
from importlib.abc import MetaPathFinder, Loader
from pathlib import Path

from pybaked import BakedReader


def execute_module(source: str | bytes, module: types.ModuleType):
    code = compile(source, module.__file__, "exec")
    exec(code, module.__dict__)


class BakedPathFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=...):
        # Define path entries in which finder will search baked packages
        entries = sys.path
        # Extend entries with package path
        if path is not None:
            entries.extend(path)

        for path_entry in entries:
            # Using more convenient interface for working with path
            baked_package = Path(path_entry)

            # Find baked package inside path entry following
            # the module name parts
            parts = fullname.split(".")
            for i, part in enumerate(parts):
                baked_package /= part

                # If this is baked package - use it and break loop
                with_suffix = baked_package.with_suffix(".py.baked")
                if with_suffix.exists():
                    baked_package = with_suffix

                    # Define inner module name relative to
                    inner_module_name = ".".join(parts[i:])
                    break
            else:
                # If package was not found - skip this path entry
                continue

            # Defining baked package reader to search module inside
            reader = BakedReader(baked_package)

            # Define module location
            location = str(
                baked_package.joinpath(*inner_module_name.split(".")[1:])
            )

            # If it is a normal module - add .py suffix (just in case)
            if inner_module_name in reader.modules_dict:
                location += ".py"

            # If module not found and it is not a package
            # inside with this name - skip this baked package
            elif inner_module_name not in reader.packages:
                continue

            # Build spec for module
            return importlib.util.spec_from_file_location(
                fullname,
                location,
                loader=BakedLoader(reader, inner_module_name),
            )
        return None


class BakedLoader(Loader):
    def __init__(self, reader: BakedReader, inner_module_name: str):
        self.reader = reader
        self.inner_module_name = inner_module_name

    def create_module(self, spec):
        return types.ModuleType(spec.name)

    def exec_module(self, module):
        # Define what module will be read from reader.
        # If module is the package then it may be
        # package_name + .__init__ if exists module with that name
        module_name = self.inner_module_name

        # If module is the package - package must be equal to module name
        if module_name in self.reader.packages:
            module.__package__ = module.__name__

            # If package has __init__ module - load it
            if module_name + ".__init__" in self.reader.modules_dict:
                module_name += ".__init__"
        else:
            module.__package__ = module.__name__.rsplit(".", 1)[0]

        # Location module inside the baked package
        # (first element is the name of the package)
        module_location_inside = module_name.split(".")[1:]

        # Define path of the module file
        module.__file__ = (
            str(self.reader.path / Path(*module_location_inside)) + ".py"
        )

        # Define package module resolution path
        module.__path__ = [self.reader.path]

        # If module not found in the package - leaving from loader
        if module_name not in self.reader.modules_dict:
            return

        # Offset of the module source in the baked package file
        source_offset = self.reader.modules_dict[module_name]

        # Source of the module
        source = self.reader.read_specific(source_offset)

        # Compile and execute module code
        execute_module(source, module)

        # Install metadata read by reader to all root modules of the baked package
        # Use it to recognize baked modules in code
        if module_name.split(".")[0] == module.__package__:
            module.__baked_metadata__ = self.reader.metadata


def init():
    sys.meta_path.append(BakedPathFinder())
