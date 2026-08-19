


# SOC Event Schema v1

## Required Fields

timestamp
host
event_type
source
severity

`timestamp` uses ISO 8601 and is normalized to an explicit UTC offset. New
events without a timestamp receive the current UTC time. Invalid timestamps
and missing required fields are rejected with `EventValidationError`. Older
stored events remain readable and are not retroactively rejected.

Input may use legacy `hostname`; normalized output always uses `host`.
Producer-specific fields are retained.

# Process Fields

process_name
pid
parent_process
user

These process investigation fields are preserved during normalization when
present. Missing optional fields are represented by `null`.

## Network Fields

src_ip
dst_ip
src_port
dst_port
protocol

## File Fields

file_name
file_path
file_hash

## Detection Fields

rule_name
mitre_technique
confidence


`event_id` is optional and may be a string or integer.

## Identity and provenance

Newly ingested events receive an `event_uid` that identifies the event record
without changing the producer-specific meaning of `event_id`. Producers may
supply an `event_uid` containing 1-128 letters, digits, dots, underscores,
colons, or hyphens. Otherwise the SOC derives a stable SHA-256-based identifier
from the normalized event.

`ingested_at` records when the SOC normalized the event, `event_schema_version`
identifies this additive event contract, and `provenance.source` records the
declared source. Existing stored events without these fields remain readable.
