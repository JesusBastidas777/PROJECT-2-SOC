"""Rebuildable event UID offsets; the JSONL remains the only source of truth."""

import json
import logging
import os
from pathlib import Path
import tempfile


logger = logging.getLogger(__name__)
INDEX_VERSION = 1


def file_signature(path):
    path = Path(path)
    if not path.exists():
        return None
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_mtime_ns, stat.st_size]


class UIDIndex:
    def __init__(self, event_path, index_path=None):
        self.event_path = Path(event_path)
        self.path = Path(index_path) if index_path else self.event_path.with_name(
            self.event_path.name + ".uid-index.jsonl"
        )
        self.meta_path = self.path.with_name(self.path.name + ".meta.json")
        self.offsets = {}
        self.signature = None

    def _load(self):
        with self.meta_path.open("r", encoding="utf-8") as source:
            value = json.load(source)
        if (
            not isinstance(value, dict)
            or value.get("version") != INDEX_VERSION
            or not isinstance(value.get("signature"), list)
        ):
            raise ValueError("invalid UID index")
        self.signature = value["signature"]
        offsets = {}
        with self.path.open("r", encoding="utf-8") as source:
            for line in source:
                entry = json.loads(line)
                if (
                    not isinstance(entry, list) or len(entry) != 2
                    or not isinstance(entry[0], str) or not isinstance(entry[1], int)
                ):
                    raise ValueError("invalid UID index entry")
                offsets.setdefault(entry[0], entry[1])
        self.offsets = offsets

    def _atomic_json(self, path, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", delete=False, dir=path.parent,
                prefix=path.name + ".", newline="\n",
            ) as output:
                temporary = Path(output.name)
                json.dump(value, output, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _save_meta(self):
        self._atomic_json(self.meta_path, {
            "version": INDEX_VERSION, "signature": self.signature,
        })

    def _save_full(self):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", delete=False, dir=self.path.parent,
                prefix=self.path.name + ".", newline="\n",
            ) as output:
                temporary = Path(output.name)
                for uid, offset in self.offsets.items():
                    output.write(json.dumps([uid, offset], ensure_ascii=False) + "\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
            temporary = None
            self._save_meta()
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def rebuild(self):
        offsets = {}
        if self.event_path.exists():
            with self.event_path.open("rb") as source:
                while True:
                    offset = source.tell()
                    line = source.readline()
                    if not line:
                        break
                    try:
                        value = json.loads(line.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    uid = value.get("event_uid") if isinstance(value, dict) else None
                    if isinstance(uid, str) and uid not in offsets:
                        offsets[uid] = offset
        self.offsets = offsets
        self.signature = file_signature(self.event_path)
        try:
            self._save_full()
        except OSError:
            logger.warning("UID index could not be persisted; using rebuilt memory index")
        return self

    def ensure_current(self):
        current = file_signature(self.event_path)
        if self.signature == current and self.signature is not None:
            return self
        try:
            self._load()
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return self.rebuild()
        if self.signature != current:
            return self.rebuild()
        return self

    def get_event(self, event_uid):
        offset = self.offsets.get(event_uid)
        if offset is None:
            return None
        try:
            with self.event_path.open("rb") as source:
                source.seek(offset)
                value = json.loads(source.readline().decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return None
        if isinstance(value, dict) and value.get("event_uid") == event_uid:
            return value
        return None

    def record(self, event_uid, offset):
        self.offsets[event_uid] = offset
        self.signature = file_signature(self.event_path)
        try:
            with self.path.open("a", encoding="utf-8", newline="\n") as output:
                output.write(json.dumps([event_uid, offset], ensure_ascii=False) + "\n")
                output.flush()
                os.fsync(output.fileno())
            self._save_meta()
        except OSError:
            logger.warning("event persisted but UID index update failed; it will be rebuilt")

    def invalidate(self):
        self.signature = None
        self.offsets = {}
        try:
            self.path.unlink(missing_ok=True)
            self.meta_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("could not remove stale UID index: %s", self.path)
