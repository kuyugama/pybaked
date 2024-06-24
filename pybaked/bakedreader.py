from datetime import datetime
from functools import lru_cache
from pathlib import Path

from . import protocol


class BakedReader:
    def __init__(self, baked_path: str | Path):
        if not isinstance(baked_path, Path):
            baked_path = Path(baked_path)

        self._path = baked_path

        if not self._path.is_file() or not self._path.name.endswith(
            ".py.baked"
        ):
            raise ValueError(f"Baked file does not exist: {self._path}")

        self._file = self._path.open("rb")
        self._cursor = 0

        data = self._read_next()

        if not data:
            raise ValueError(
                "Cannot decode baked file: creation timestamp not found"
            )

        self._created = protocol.deserialize(data)

        data = self._read_next()

        if not data:
            raise ValueError("Cannot decode baked file: metadata not found")

        self._metadata = protocol.deserialize(data)

        self._modules_offset = self._cursor

    @property
    def path(self):
        return self._path

    def _read_next(self) -> bytes | None:
        length_bytes = self._file.read(8)
        if len(length_bytes) != 8:
            return None

        length = int.from_bytes(length_bytes, "little")

        self._cursor += 8 + length

        return self._file.read(length)

    @property
    def metadata(self):
        return self._metadata.copy()

    @property
    def created(self) -> datetime:
        return self._created

    @property
    def name(self):
        return self._path.name[: -len(".py.baked")]

    @property
    @lru_cache
    def modules(self) -> list[tuple[str, int]]:
        mods = []

        self._file.seek(self._modules_offset)
        fragments = protocol.read_fragments(self._file)

        for name, offset in fragments:
            mods.append((self.name + "." + name.decode(), offset))

        return mods

    @property
    @lru_cache
    def packages(self):
        packs = []

        for name, _ in self.modules:
            if name.endswith("__init__"):
                packs.append((name[: -len("__init__") - 1]).strip("."))

        return packs

    def read_specific(self, offset: int) -> bytes:
        self._file.seek(offset)

        return self._read_next()

    def __del__(self):
        self._file.close()
