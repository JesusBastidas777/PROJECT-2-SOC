# Local housekeeping

Housekeeping coordinates audit, backup, optional retention, alert compaction,
and final verification in that order. `maintenance plan` is read-only;
`maintenance run` is protected by a non-waiting exclusive lock so two runs
cannot overlap. Retention is omitted unless an age or size policy is supplied.

Completed and failed runs are appended to a separate operational journal with
policy, step results and durations, artifacts, timestamps, and outcome. A
truncated final journal line is ignored during reads. `maintenance history`
shows journal entries and `status` includes the latest completed run. Scheduling
is intentionally external to the SOC.
