"""Small process-safe advisory lock for local JSONL files."""

from contextlib import contextmanager
import fcntl
from pathlib import Path
from time import monotonic, sleep

from storage.errors import StorageWriteError


@contextmanager
def exclusive_file_lock(target, timeout=5.0, poll_interval=0.01):
    """Hold an exclusive sidecar lock for *target* or raise on timeout."""
    target = Path(target)
    lock_path = target.with_name(target.name + ".lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+", encoding="utf-8")
    except OSError as exc:
        raise StorageWriteError(f"cannot initialize file lock: {lock_path}") from exc

    deadline = monotonic() + timeout
    acquired = False
    try:
        while not acquired:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError as exc:
                if monotonic() >= deadline:
                    raise StorageWriteError(
                        f"timed out waiting for file lock: {target}",
                        details={"path": str(target), "timeout_seconds": timeout},
                    ) from exc
                sleep(poll_interval)
        yield
    finally:
        if acquired:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
