"""Predictable failures raised by JSONL persistence components."""


class StorageError(Exception):
    """Base class for event persistence failures."""


class StorageReadError(StorageError):
    """Raised when the event log cannot be read."""


class StorageWriteError(StorageError):
    """Raised when an event cannot be persisted."""
