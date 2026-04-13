# Caller-Scoped Checklist

Check these questions explicitly:

- Is the caller allowed by scope family (`read`, `write`, `export`)?
- Is the source visible to this caller?
- Is the source or capability runtime-ready on this host?
- Does `deny_reason` distinguish permission denial from runtime unavailability?
- Does `/api/system/features` expose the right capability level for this caller?
- If a capability is future-facing, is it still clearly marked `not_implemented` instead of silently widening?

Report widening risk when the runtime, authz, and API payload drift apart.
