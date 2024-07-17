import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import protocol, BakedMaker

logger = logging.getLogger(__name__)


class BakedReader:
    def __init__(self, path: str | Path):
        if not isinstance(path, Path):
            path = Path(path)

        self._path = path.absolute()

        if not self._path.is_file() or not self._path.name.endswith(
            protocol.EXTENSION
        ):
            raise ValueError(f"Baked file does not exist: {self._path}")

        self._file = self._path.open("rb")

        data = self._read_next()

        if not data:
            raise ValueError(
                "Cannot decode baked file: creation timestamp not found"
            )

        self._created = protocol.deserialize(data)
        logger.debug(f"Read creation date from {path} => {self._created}")

        data = self._read_next()

        if not data:
            raise ValueError("Cannot decode baked file: metadata not found")

        self._metadata = protocol.deserialize(data)
        logger.debug(f"Read metadata from {path} => {self._metadata}")

        self._modules_offset = self._file.tell()

    def _read_next(self) -> bytes | None:
        """
        Read next data from the file
        """
        length_bytes = self._file.read(8)
        if len(length_bytes) != 8:
            return None

        length = int.from_bytes(length_bytes, "little")

        return self._file.read(length)

    def read_specific(self, offset: int) -> bytes:
        self._file.seek(offset)

        logger.debug(f"Reading data at {offset} from {self._path}")

        return self._read_next()

    @property
    def path(self):
        return self._path

    @property
    @lru_cache
    def hash_match(self) -> bool | None:
        """
        Match hash written in metadata with real hash

        :return: None if no hash is present in metadata, bool - hash match
        """
        if "--fh" not in self._metadata:
            return

        return self.real_hash == self._metadata["--fh"]

    @property
    @lru_cache
    def real_hash(self) -> bytes:
        """
        Real content hash of the file

        :return: hash bytes
        """
        self._file.seek(self._modules_offset)

        return protocol.hash_fragments(self._file)

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata.copy()

    @property
    def created(self) -> datetime:
        return self._created

    @property
    def name(self):
        return self._path.name[: -len(protocol.EXTENSION)]

    @property
    @lru_cache
    def modules_dict(self) -> dict[str, int]:
        return dict(self.modules)

    @property
    @lru_cache
    def modules(self) -> list[tuple[str, int]]:
        found_modules = []

        logger.debug(f"Reading modules from {self._path}")

        self._file.seek(self._modules_offset)
        fragments = protocol.read_fragments(self._file)

        for name, offset in fragments:
            found_modules.append((self.name + "." + name.decode(), offset))

        logger.debug(
            f"Read {len(found_modules)} modules from {self._path}",
            extra={"modules": found_modules},
        )

        return found_modules

    @property
    @lru_cache
    def packages(self):
        found_packages = []

        logger.debug(f"Defining packages for {self._path}")

        for name in self.modules_dict:
            name = name.rsplit(".", 1)[0]

            if name not in found_packages:
                found_packages.append(name)

        logger.debug(
            f"Found {len(found_packages)} packages in {self._path}",
            extra={"packages": found_packages},
        )

        return list(found_packages)

    def to_maker(self) -> BakedMaker:
        maker = BakedMaker("--fh" in self.metadata, self.metadata)

        for module_name, source_offset in self.modules_dict.items():
            maker.include_module(
                module_name[len(self.name) + 1 :].encode(),
                self.read_specific(source_offset),
            )

        return maker

    def __del__(self):
        self._file.close()
