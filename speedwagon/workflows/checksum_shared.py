import enum


class ResultsValues(enum.Enum):
    SOURCE_FILE = "source_filename"
    SOURCE_HASH = "checksum_hash"
    CHECKSUM_FILE = "checksum_file"
