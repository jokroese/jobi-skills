# Bayesian workflow evidence record

Read this reference when producing an analysis plan, audit, implementation handoff, or report. Adapt the headings to the project, but preserve the distinction among validation questions.

## Analysis target

- Scientific question:
- Estimand, prediction, or decision:
- Utility or loss criterion:
- Population and units of observation:
- Design and measurement process:
- Data transformations, exclusions, and missingness:
- Confirmatory versus exploratory status:

## Model map

- Aspirational data-generating narrative:
- Initial model and parameterization:
- Important omissions from the initial model:
- Claim-relevant summaries and the failure each could expose:
- Priors and domain rationale:

## Reproducibility

- Code and data locations:
- Software and versions:
- Random seeds or seed policy:
- Model version or commit:
- Simulation and posterior draw counts:
- Hardware or runtime notes when relevant:

## Evidence matrix

Use only `pass`, `warning`, `fail`, `not-run`, or `blocked`.

| Validation question | Status | Evidence artifact | Finding | Action and rerun |
| --- | --- | --- | --- | --- |
| Prior predictive plausibility | not-run | | | |
| Computational diagnostics | not-run | | | |
| Simulation-based calibration | not-run | | | |
| Sensitivity/design resolution | not-run | | | |
| Posterior predictive adequacy | not-run | | | |
| Prior/model sensitivity of comparison, if used | not-run | | | |

## Model ledger

| Version | Change and rationale | Expected effect | Checks rerun | Decision |
| --- | --- | --- | --- | --- |
| M0 | Initial model | Baseline | | |

## Scientific result

- Posterior quantities relevant to the target:
- Decision or scientific interpretation:
- Evidence that makes this interpretation usable:
- Checks that were not run or did not pass:
- Sensitivity of the conclusion to priors, model choices, and design:
- What the data did not resolve:
- Next model, design, or data-collection step:

Do not collapse the evidence matrix into a claim that “the model passed.” State which distinct claim each check supports and preserve warnings that limit interpretation.
