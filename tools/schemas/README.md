# Canonical Tool Input Schemas

This directory contains one Draft 2020-12 input schema named
`{tool_name}.schema.json` for every tool in the WS3 tau-retail candidate
contract. `arguments_valid` must be computed from these files before execution;
a missing schema is not treated as valid.

These schemas validate transport shape only. Retail policy, entity existence,
and current-state rules are enforced by the shared simulator core and reported
as structured errors.
