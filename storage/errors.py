"""Backward-compatible imports for storage failures."""

from soc.errors import StorageError, StorageReadError, StorageWriteError

__all__ = ["StorageError", "StorageReadError", "StorageWriteError"]
