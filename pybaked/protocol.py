import hashlib
from datetime import datetime
from typing import Any, Callable, TypeVar


def pack_type(data: bytes, type_: str) -> bytes:
    return type_.encode() + b"/" + data


def unpack_type(data: bytes) -> tuple[bytes, str]:
    type_, data = data.split(b"/", 1)

    return (data, type_.decode())


def int_serialize(i: int) -> bytes:
    return pack_type(i.to_bytes(8, "little"), "int")


def int_deserialize(b: bytes) -> int:
    return int.from_bytes(b, "little")


def bool_serialize(b: bool) -> bytes:
    return pack_type(b.to_bytes(1, "little"), "bool")


def bool_deserialize(b: bytes) -> bool:
    return bool(int_deserialize(b))


def str_serialize(s: str) -> bytes:
    return pack_type(s.encode(), "str")


def str_deserialize(b: bytes) -> str:
    return b.decode()


def float_serialize(f: float) -> bytes:
    f_str = str(f)
    f_parts = f_str.split(".")

    exp = len(f_parts[1])
    exp_bytes = exp.to_bytes(1, "little")

    real = int("".join(f_parts))
    real_bytes = real.to_bytes(8, "little")

    return pack_type(exp_bytes + b"-" + real_bytes, "float")


def float_deserialize(b: bytes) -> float:
    exp_bytes, real_bytes = b.split(b"-")

    exp = 10 ** int.from_bytes(exp_bytes, "little")

    real = int.from_bytes(real_bytes, "little")

    return real / exp


def list_serialize(lst: list) -> bytes:
    buffer = b""

    for i, element in enumerate(lst):
        try:
            buffer += pack_message(serialize(element))
        except TypeError as e:
            raise TypeError(f"Unsupported type for {i}") from e

    return pack_type(buffer, "list")


def list_deserialize(b: bytes) -> list:
    elements = []

    cursor = 0

    while len(length_bytes := b[cursor : cursor + 8]) > 0:
        cursor += len(length_bytes)
        length = int.from_bytes(length_bytes, "little")

        elements.append(deserialize(b[cursor : cursor + length]))

        cursor += length

    return elements


def dict_serialize(d: dict[str, Any]) -> bytes:
    buffer = b""

    for key, value in d.items():
        buffer += pack_message(key.encode())

        try:
            buffer += pack_message(serialize(value))
        except TypeError as e:
            raise TypeError(f"Unsupported value type for {key}") from e

    return pack_type(buffer, "dict")


def dict_deserialize(b: bytes) -> dict[str, Any]:
    dct: dict[str, Any] = {}

    cursor = 0

    while len(length_bytes := b[cursor : cursor + 8]) > 0:
        cursor += len(length_bytes)
        length = int.from_bytes(length_bytes, "little")

        element_key = b[cursor : cursor + length]

        cursor += len(element_key)

        length_bytes = b[cursor : cursor + 8]
        cursor += len(length_bytes)
        length = int.from_bytes(length_bytes, "little")

        dct[element_key.decode()] = deserialize(b[cursor : cursor + length])

        cursor += length

    return dct


def datetime_serialize(d: datetime) -> bytes:
    return pack_type(unpack_type(float_serialize(d.timestamp()))[0], "datetime")


def datetime_deserialize(b: bytes) -> datetime:
    return datetime.fromtimestamp(float_deserialize(b))


_types = {
    "int": (
        int_serialize,
        int_deserialize,
    ),
    "str": (str_serialize, str_deserialize),
    "float": (float_serialize, float_deserialize),
    "list": (list_serialize, list_deserialize),
    "bool": (bool_serialize, bool_deserialize),
    "dict": (dict_serialize, dict_deserialize),
    "datetime": (datetime_serialize, datetime_deserialize),
}


def deserialize(b: bytes) -> Any:
    data, type_ = unpack_type(b)

    if type_ == "bytes":
        return data

    if type_ not in _types:
        raise TypeError(f"Unsupported data type: {type_}")

    _, deserialize = _types[type_]

    return deserialize(data)


def serialize(data: Any) -> bytes:
    type_ = type(data).__name__

    if type_ == "bytes":
        return pack_type(data, "bytes")

    if type_ not in _types:
        raise TypeError(f"Unsupported data type: {type_}")

    serialize, _ = _types[type_]

    return serialize(data)


T = TypeVar("T")


def register_type(
    type_: type[T],
    serialize: Callable[[T], bytes],
    deserialize: Callable[[bytes], T],
):
    if type_ in _types:
        raise ValueError("Type already registered")
    _types[type_.__name__] = (serialize, deserialize)


def pack_message(message: bytes) -> bytes:
    return len(message).to_bytes(8, "little") + message


class Fragments:
    def __init__(self):
        self._fragments: list[tuple[bytes, bytes]] = []

    def hash(self) -> bytes:
        hash_ = hashlib.sha256()

        for name, content in self._fragments:
            hash_.update(name + content)

        return hash_.digest()

    def add(self, fragment: tuple[bytes, bytes]):
        self._fragments.append(fragment)

    def measure_offset(self, offset: int):
        return sum(
            map(lambda x: len(x[0]) + 24, self._fragments),
        ) + sum(map(lambda x: len(x[1]) + 8, self._fragments[:offset]))

    def write(self, buffer):
        for i, element in enumerate(self._fragments):
            buffer.write(pack_message(element[0]))
            buffer.write(
                pack_message(self.measure_offset(i).to_bytes(8, "little"))
            )

        for element in self._fragments:
            buffer.write(pack_message(element[1]))

    def __iter__(self):
        return iter(self._fragments)


def read_buffer(buffer) -> bytes:
    """
    Reads message from the buffer and returns it. Raises ValueError otherwise.

    MESSAGE := 8 bytes of length + bytes of message
    :param buffer: file-like object with rb mode
    :return: bytes read
    """
    length_bytes = buffer.read(8)
    if len(length_bytes) != 8:
        raise ValueError(
            "Buffer ended unexpectedly while reading length of the message"
        )

    length = int.from_bytes(length_bytes, byteorder="little", signed=False)

    data = buffer.read(length)

    if len(data) != length:
        raise ValueError(
            "Buffer ended unexpectedly while reading the message content"
        )

    return data


def read_fragments(buffer) -> list[tuple[bytes, int]]:
    """
    Reads all fragments from buffer. Returns a list of tuples (name, offset).
    Where the offset is the body position of the fragment and name is the fragment name

    :param buffer: file-like object with rb mode
    :return: tuples of fragment name and offset to its content
    """

    position = buffer.tell()

    fragments = []

    name = read_buffer(buffer)

    offset = int.from_bytes(read_buffer(buffer), "little", signed=False)
    latest_name_offset = position + offset
    next_offset = buffer.tell()

    while next_offset <= latest_name_offset:
        fragments.append((name, position + offset))

        buffer.seek(next_offset)

        name = read_buffer(buffer)

        offset = int.from_bytes(read_buffer(buffer), "little", signed=False)

        next_offset = buffer.tell()

    return fragments


def hash_fragments(buffer) -> bytes:
    """
    Reads all fragments and its content from file and makes hash of it.

    :param buffer: file-like object with rb mode
    """
    hash_ = hashlib.sha256()
    for name, offset in read_fragments(buffer):
        hash_.update(name)

        buffer.seek(offset)
        content = read_buffer(buffer)
        hash_.update(content)

    return hash_.digest()
