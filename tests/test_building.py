from datetime import datetime

from pybaked import BakedReader


def test_default(temp_baked_package, test_files):
    reader = BakedReader(temp_baked_package)

    assert isinstance(reader.created, datetime)

    package_name = temp_baked_package.name.split(".", 1)[0]

    for file in test_files:
        extension = file.split(".", 1)[-1]
        # Module name in package
        # is stored as package_name.module_name_without_suffix
        module_name = package_name + "." + file.split(".", 1)[0]

        if extension == "py":
            assert module_name in reader.modules_dict
        else:
            assert module_name not in reader.modules_dict


def test_metadata(temp_baked_package_metadata, test_metadata):
    reader = BakedReader(temp_baked_package_metadata)

    assert reader.metadata == test_metadata


def test_hash(temp_baked_package_hashed):
    reader = BakedReader(temp_baked_package_hashed)

    assert reader.hash_match is True
