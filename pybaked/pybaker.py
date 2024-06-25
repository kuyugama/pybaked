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


class PyBaker:
    def __init__(
        self,
        source_package_path: str | Path,
        metadata: dict[str, Any],
        hash_content: bool = False,
    ) -> None:
        if isinstance(source_package_path, str):
            source_package_path = Path(source_package_path)

        self._source_package_path = source_package_path.absolute()
        self._metadata = metadata

        if not self._source_package_path.is_dir():
            raise ValueError("Source package path is not a directory")

        if not isinstance(self._metadata, dict):
            raise TypeError("Metadata is not a dictionary")

        if "--fh" in self._metadata:
            raise ValueError(
                "'--fh' name in metadata is reserved for content hash"
            )

        self._hash_content = hash_content

    @property
    def source_package_path(self) -> Path:
        return self._source_package_path

    @property
    def format(self):
        return ".py.baked"

    def _bake(self):
        logger.debug(f"Started baking {self.source_package_path}")
        buffer = io.BytesIO()

        write_content(
            buffer,
            protocol.serialize(datetime.utcnow()),
        )
        logger.debug("Written creation date to buffer")

        fragments = protocol.Fragments()

        logger.debug(
            f"Looking for modules to include in {self.source_package_path}"
        )

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
                logger.debug(f"Including module at {absolute_fp}")

        if self._hash_content:
            self._metadata.update({"--fh": fragments.hash()})
            logger.debug(
                "Added to metadata hash of the fragments",
                extra={"hash": self._metadata["--fh"]},
            )

        write_content(
            buffer,
            protocol.serialize(self._metadata),
        )
        logger.debug("Written metadata to buffer")

        fragments.write(buffer)
        logger.debug("Written fragmented modules to buffer")
        logger.debug(f"Baked {self.source_package_path}")

        return buffer.getvalue()

    def bake(self) -> io.BytesIO:
        logger.debug(f"Baking {self.source_package_path} into memory")
        return io.BytesIO(self._bake())

    def bake_to_file(self, filename: str = None) -> str:
        if filename is not None:
            filename = filename + self.format
        else:
            filename = self._source_package_path.name + self.format

        logger.debug(f"Baking {self.source_package_path} into {filename} file")

        with open(filename, "wb") as file:
            file.write(self._bake())

        return filename
