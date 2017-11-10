import abc


class AbsTool(metaclass=abc.ABCMeta):
    name = None  # type: str
    description = None  # type: str
    options = []  # type: ignore


class MakeChecksumBatch(AbsTool):
    name = "Make Checksum Batch"
    description = "Makes a checksums"
    options = [
        ("input",),
        ("output",)
    ]

class Foo(AbsTool):
    name = "Foo"
    description = "foo boo"
