"""Shared data for checksum workflows."""

import enum


class ResultsValues(enum.Enum):
    """Values for results for Checksum reports."""

    SOURCE_FILE = "source_filename"
    SOURCE_HASH = "checksum_hash"
    CHECKSUM_FILE = "checksum_file"
