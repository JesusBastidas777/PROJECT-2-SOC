"""Opaque, query-bound cursor helpers for deterministic local pagination."""

import base64
import hashlib
import json

from soc.errors import QueryError


CURSOR_VERSION = 1


def query_fingerprint(filters):
    payload = json.dumps(filters, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def event_fingerprint(event):
    payload = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def encode_cursor(query_hash, anchor, occurrence):
    payload = json.dumps(
        {"v": CURSOR_VERSION, "q": query_hash, "a": anchor, "n": occurrence},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(value, expected_query_hash):
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(value + padding))
        if (
            not isinstance(payload, dict)
            or payload.get("v") != CURSOR_VERSION
            or payload.get("q") != expected_query_hash
            or not isinstance(payload.get("a"), str)
            or not isinstance(payload.get("n"), int)
            or payload["n"] <= 0
        ):
            raise ValueError
        return payload["a"], payload["n"]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise QueryError("cursor is invalid or does not match this query") from exc
