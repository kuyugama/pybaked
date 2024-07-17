from datetime import datetime
from pathlib import Path
from typing import Any
import logging
import os
import io

from . import protocol

logger = logging.getLogger(__name__)


def write_content(buffer: io.BytesIO, content: bytes):
    logger.debug(
        f"Writing {len(content)} bytes into a buffer",
    )
    buffer.write(len(content).to_bytes(8, byteorder="little"))
    buffer.write(content)


def find_modules(package_path: Path):
    modules: list[tuple[str, str]] = []
    for dir_path, _, files in os.walk(package_path):
        dir_path = Path(dir_path)
        for module_file in filter(lambda name: name.endswith(".py"), files):
            module_path = dir_path / module_file

            module_name = ".".join(
                (module_path.relative_to(package_path)).with_suffix("").parts
            )

            modules.append((module_name, str(module_path)))

    return modules


class BakedMaker:
    logger = logger.getChild("BakedMaker")

    @classmethod
    def from_package(
        cls,
        package_path: str | Path,
        hash_content: bool = False,
        metadata: dict[str, Any] = None,
    ) -> "BakedMaker":
        """
        Lookup path for python modules and create BakedMaker instance
        including all this modules
        :param package_path: Path to package
        :param hash_content: Whether to hash the content
        :param metadata: Metadata dictionary
        :return: The created BakedMaker instance
        """
        if isinstance(package_path, str):
            package_path = Path(package_path)

        package_path = package_path.absolute()

        if not package_path.is_dir():
            raise ValueError("Package path is not a directory")

        if not (modules := find_modules(package_path)):
            raise ValueError("No modules found in package")

        instance = cls(hash_content, metadata)

        for import_name, module_file in modules:
            cls.logger.debug(
                f"Including '{module_file}' as '{import_name}' from '{package_path}'"
            )
            instance.include_module(
                import_name.encode(), Path(module_file).read_bytes()
            )

        return instance

    def __init__(
        self, hash_content: bool = False, metadata: dict[str, Any] = None
    ):
        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dict")

        self._hash_content = hash_content
        self._metadata = metadata

        self._fragments = protocol.Fragments()

    def get_metadata(self) -> dict[str, Any]:
        """
        Get the metadata dictionary

        :return: Metadata dictionary
        """
        return self._metadata

    def set_metadata(self, metadata: dict[str, Any] = None) -> "BakedMaker":
        """
        Set the new metadata for this maker.
        If metadata is None - metadata will be cleared

        :param metadata: New metadata to set
        :return: The same instance of BakedMaker
        """
        if metadata is None:
            metadata = {}

        self._metadata = metadata
        return self

    def update_metadata(
        self, data: dict[str, Any] = None, **values: Any
    ) -> "BakedMaker":
        """
        Update metadata for this maker with the new values.

        :param data: The dictionary that will be used to update the metadata
        :param values: Keywords that will update the metadata
        :return: The same instance of BakedMaker
        """
        if data is None:
            data = values
        else:
            data.update(values)

        self._metadata.update(data)

        return self

    def include_module(
        self, import_name: bytes, source_code: bytes
    ) -> "BakedMaker":
        """
        Include module in BakedMaker

        :param import_name: Module name if import format (example: baked_package.module_name)
        :param source_code: Module source code
        :return: The same instance of BakedMaker
        """
        self._fragments.add(
            (
                import_name,
                source_code,
            )
        )

        return self

    def _build_content(self) -> io.BytesIO:
        self.logger.debug("Started building content")
        buffer = io.BytesIO()
        creation_date = datetime.utcnow()
        write_content(
            buffer,
            protocol.serialize(
                creation_date,
            ),
        )
        self.logger.debug(
            "Creation date was written to a buffer",
            extra={"creation_date": creation_date},
        )
        if self._hash_content:
            fragments_hash = self._fragments.hash()
            self._metadata.update({"--fh": fragments_hash})
            self.logger.debug(
                "Fragments was hashed",
                extra={"hash": int.from_bytes(fragments_hash, "big")},
            )

        write_content(buffer, protocol.serialize(self._metadata))
        self.logger.debug(
            "Metadata was written to a buffer",
        )

        self._fragments.write(buffer)
        self.logger.debug("Fragments was written to a buffer")

        self.logger.debug("Building content finished")

        buffer.seek(0)
        return buffer

    def bytes(self):
        """
        Make baked package in bytes from stored content

        :return: package bytes
        """
        return self._build_content().read()

    def file(self, filename: str | Path) -> Path:
        """
        Make baked package file from stored content

        :param filename: output file name
        :return: path to file created
        """
        if isinstance(filename, str):
            filename = Path(filename)

        if not filename.name.endswith(protocol.EXTENSION):
            filename = filename.with_name(
                filename.name.split(".", 1)[0] + protocol.EXTENSION
            )

        with filename.open("wb") as f:
            f.write(self.bytes())

        return filename
