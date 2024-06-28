import contextlib
import importlib
import io

import pybaked


def test_loading(
    temp_dir, temp_baked_package, test_files, python_module_stdout_template
):
    pybaked.loader.init()

    relative_package_path = temp_baked_package.relative_to(
        temp_dir.parent
    ).with_name(temp_baked_package.name.split(".", 1)[0])

    package_name = ".".join(relative_package_path.parts)

    for file in test_files:
        # Only python modules are included into package
        if not file.endswith(".py"):
            continue

        module_name = file[:-3]

        import_name = package_name + "." + module_name

        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            importlib.import_module(import_name)

        assert (
            stdout.getvalue()
            == python_module_stdout_template.format(file=file) + "\n"
        )


def test_loading_metadata(
    temp_dir, temp_baked_package_metadata, test_files, test_metadata
):
    pybaked.loader.init()

    relative_package_path = temp_baked_package_metadata.relative_to(
        temp_dir.parent
    ).with_name(temp_baked_package_metadata.name.split(".", 1)[0])

    package_name = ".".join(relative_package_path.parts)

    for file in test_files:
        # Only python modules are included into package
        if not file.endswith(".py"):
            continue

        module_name = file[:-3]

        import_name = package_name + "." + module_name

        module = importlib.import_module(import_name)

        assert module.__baked_metadata__ == test_metadata
