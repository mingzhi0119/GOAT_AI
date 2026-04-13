# Sandbox Runtime Checklist

Check these questions explicitly:

- Did the change affect queued-only control, running cancellation, retry
  posture, or restart recovery?
- Did the provider or supervisor behavior change, or only the HTTP/application
  adapter?
- Is `network_policy` still truthful for the current runtime, or did a new
  allowlist claim appear without enforcement proof?
- Did durable event or log replay behavior change?
- Did `/api/code-sandbox/*` or the operator docs move in a way that requires
  contract-sync or governance tests?

Report widening risk when runtime behavior, API docs, and operator runbooks
drift apart.
