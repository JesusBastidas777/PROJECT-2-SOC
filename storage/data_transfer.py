"""Explicit JSONL import and export operations."""

import json
from pathlib import Path

from normalization.time_utils import parse_timestamp
from storage.errors import StorageReadError, StorageWriteError
from storage.file_lock import exclusive_file_lock


class DataTransfer:
    def __init__(self, reader, store, normalizer, lock_timeout=5.0):
        self.reader = reader
        self.store = store
        self.normalizer = normalizer
        self.lock_timeout = lock_timeout

    def export_events(self, destination, **filters):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        try:
            with exclusive_file_lock(destination, self.lock_timeout):
                with destination.open("w", encoding="utf-8", newline="\n") as output:
                    for event in self.reader.read_events():
                        if not self._matches(event, filters):
                            continue
                        output.write(json.dumps(event, ensure_ascii=False) + "\n")
                        count += 1
        except OSError as exc:
            raise StorageWriteError(f"cannot export events to: {destination}") from exc
        return {"path": str(destination), "exported": count}

    @staticmethod
    def _matches(event, filters):
        mappings = {"hostname": "host", "source": "source", "severity": "severity"}
        for argument, field in mappings.items():
            if filters.get(argument) is not None and event.get(field) != filters[argument]:
                return False
        event_time = parse_timestamp(event.get("timestamp"))
        start = parse_timestamp(filters.get("start_timestamp"))
        end = parse_timestamp(filters.get("end_timestamp"))
        if start and (event_time is None or event_time < start):
            return False
        if end and (event_time is None or event_time > end):
            return False
        return True

    def import_events(self, source, *, dry_run=False):
        source = Path(source)
        result = {"path": str(source), "read": 0, "stored": 0, "duplicates": 0, "invalid": 0}
        seen = set()
        try:
            with source.open("r", encoding="utf-8") as input_file:
                for line in input_file:
                    if not line.strip():
                        continue
                    result["read"] += 1
                    try:
                        value = json.loads(line)
                        normalized = self.normalizer.normalize(value)
                    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
                        result["invalid"] += 1
                        continue
                    uid = normalized.get("event_uid")
                    if dry_run:
                        if uid in seen or self.reader.find_by_uid(uid) is not None:
                            result["duplicates"] += 1
                        else:
                            seen.add(uid)
                            result["stored"] += 1
                        continue
                    _, stored = self.store.store_once(normalized)
                    result["stored" if stored else "duplicates"] += 1
        except OSError as exc:
            raise StorageReadError(f"cannot import events from: {source}") from exc
        result["dry_run"] = dry_run
        return result
