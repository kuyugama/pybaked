import json
import os
import io
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Any

from . import protocol


def write_content(buffer: io.BytesIO, content: bytes):
    buffer.write(len(content).to_bytes(8, byteorder="little"))
    buffer.write(content)


class PyBaker:
    def __init__(
        self, source_package_path: str | Path, metadata: dict[str, Any]
    ) -> None:
        if isinstance(source_package_path, str):
            source_package_path = Path(source_package_path)

        self._source_package_path = source_package_path.absolute()
        self._metadata = metadata

        if not self._source_package_path.is_dir():
            raise ValueError("Source package path is not a directory")

        if not isinstance(self._metadata, dict):
            raise TypeError("Metadata is not a dictionary")

    @property
    def source_package_path(self) -> Path:
        return self._source_package_path

    @property
    def format(self):
        return ".py.baked"

    def _bake(self):
        buffer = io.BytesIO()
        write_content(
            buffer,
            protocol.serialize(datetime.utcnow()),
        )
        write_content(
            buffer,
            protocol.serialize(self._metadata),
        )

        fragments = protocol.Fragments()

        for path, dirs, files in os.walk(self.source_package_path):
            path = Path(path)

            if path.name == "__pycache__":
                continue

            relative_path = path.relative_to(self.source_package_path)

            for file in files:
                if not file.endswith(".py"):
                    continue

                absolute_fp = path / file
                relative_fp = relative_path / file

                parts = relative_fp.parts[:-1] + (relative_fp.stem,)

                for part in parts:
                    if not part.isidentifier():
                        raise NameError(
                            f"Invalid identifier: {part} in {absolute_fp} (relative to {path}: {relative_fp}) "
                        )

                fragments.add(
                    (".".join(parts).encode(), absolute_fp.read_bytes())
                )

        fragments.write(buffer)

        return buffer.getvalue()

    def bake(self) -> bytes:
        return self._bake()

    def bake_to_file(self, filename: str = None) -> str:

        if filename is not None:
            filename = filename + self.format
        else:
            filename = self._source_package_path.name + self.format

        with open(filename, "wb") as file:
            file.write(self._bake())

        return filename
