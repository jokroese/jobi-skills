# Forward-test record

Date: 2026-10-25. Model: gpt-6-luna, high reasoning. One independent paired trial of the `shared-service` case in `evals.json`; the baseline could use official documentation but could not read the skill. No live Coolify instance or image pulls were used.

## Observed outcomes

Both runs produced parseable Compose with matching generated database credentials, private database networking, a persistent PostgreSQL volume and the actual Docker Compose Empty Service workflow. Both correctly stated that live runtime behaviour remained unverified. Both passed local Compose schema validation with dummy values.

The skill-assisted output also included a runtime-native API health check and explicitly distinguished manual template updates from pulling image tags, including preservation of component and credential identifiers. The baseline omitted the API container probe, but did identify DNS/proxy prerequisites for generated HTTPS more clearly.

The skill-assisted output implied that Coolify would provision HTTPS without adequately stating those prerequisites. Added explicit resolved-scheme, DNS, proxy and certificate checks to the routing and Service guidance, and extended the case assertion. The revised text was reviewed and structurally validated; the paired trial was not rerun after that correction.

This is one qualitative trial, not a measured improvement across the ten-case suite. The other cases are supplied for future evaluation and were not executed as a benchmark.

## Bundled example checks

- Repository strict validator and skill-creator validator passed.
- Compose schema validation passed with disposable generated-value substitutes.
- Resolved Compose checks passed for shared credentials, scheme-bearing public URL, private ports, dependency readiness, literal container-side variables and the PostgreSQL 17 mount path.
- Missing required APP_IMAGE correctly failed Compose interpolation.
- Hadolint returned success, with an informational note about the named `node` user; the template explicitly requires an image providing that user.

Container builds and live Coolify deployment were not verified. Record any further runtime checks separately rather than treating these static checks as a deployment result.
