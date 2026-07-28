# Canonical Benchmark Tools

Frameworks should bind canonical names directly where possible and adapters
should normalize only unavoidable aliases.

- `tau_retail_contract.json` is the WS3 candidate contract for the 16-tool retail registry
  surface used by the local tau-retail tasks and prepared E5 cases.
- `schemas/` contains one Draft 2020-12 input schema per canonical tool.
- `tool_registry.example.json` remains an empty template for future domains; it
  is not the active tau-retail registry.

See `docs/ws3_tau_retail_contract.md` for reset, state, structured-error, and
minimum-fixture behavior.
