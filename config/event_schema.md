


# SOC Event Schema v1

## Required Fields

timestamp
host
event_type
source
severity

`timestamp` uses ISO 8601. New events without a valid timestamp receive the
current UTC time during normalization. Older stored events without this field
remain supported.

# Process Fields

process_name
pid
parent_process
user

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


## event id

