# Samples

The private integration replay is not checked in. Set `ROFL_TEST_FILE` to its
absolute path. Its SHA-256 and measured expectations are in `fixture-report.json`.

`local/` is ignored and holds normalized replay JSON, raw research exports,
temporary uploads, and optional extracted client sections used for offline
research. Do not publish the directory or commit game executable sections.

`histogram.json` is a transport scan of the actual supplied replay, not demo data.
