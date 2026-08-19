


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
