# EDR pattern reuse decision

The neighboring EDR uses Rich as a bounded terminal dashboard. SOC reuses its
pure-renderer separation, semantic theme, bounded output, `NO_COLOR`, refresh
throttling, empty-state defaults, injection, and failure isolation.

SOC does not copy the EDR runtime loop or snapshot/heartbeat publication. The
in-process `FOREXWorkflow(SOCService(...))` boundary is simpler here. A file
publication contract belongs in a future separate-process deployment only.
