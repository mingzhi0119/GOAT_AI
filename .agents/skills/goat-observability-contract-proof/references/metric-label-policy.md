# Metric and Label Policy

Use the exporter as the canonical contract:

- `EXPORTED_METRIC_FAMILIES`
- `EXPORTED_METRIC_LABELS`

Check both:

- family names remain valid and approved
- labels used in metric selectors or `sum by (...)` / grouping clauses are still exported by the metric family they reference

If a query depends on labels such as `feature`, `gate_kind`, `reason`, `outcome`, or `retrieval_profile`, treat selector drift as a real observability regression. Dashboard legend text is still worth reviewing, but do not claim it is mechanically proven unless the tests explicitly cover it.
