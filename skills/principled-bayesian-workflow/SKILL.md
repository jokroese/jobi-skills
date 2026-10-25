---
name: principled-bayesian-workflow
description: Implement, plan, or audit a simulation-grounded Bayesian workflow that checks prior plausibility, computational faithfulness, inferential sensitivity, and posterior predictive adequacy. Use for Bayesian model development, analysis plans, design calibration, model criticism, or reviews of whether a Bayesian analysis supports its scientific claim. Do not use for a simple probability calculation or a request that only asks to fit a pre-specified model without workflow validation.
---

# Principled Bayesian Workflow

Treat a Bayesian analysis as iterative model development, not as one model fit followed by posterior summaries. Preserve the user's scientific question, software stack, and authorization boundaries.

## Select the operating mode

- **Plan:** turn the scientific question into an executable analysis and validation plan. Do not imply that unrun checks passed.
- **Implement:** inspect the project and use its existing language, model framework, tests, data conventions, and output structure. Add the smallest reusable simulation and diagnostic machinery that exercises the actual model code.
- **Audit:** compare the available code, outputs, and report with this workflow. Label missing evidence; do not modify files unless asked.

For a full implementation or audit, read [references/workflow.md](references/workflow.md). When creating an analysis record or report, also read [references/evidence-record.md](references/evidence-record.md).

## Establish the scientific target

Before fitting observed data, make these items explicit or mark them as unresolved:

- the scientific question, estimand, prediction, or decision;
- what result would be useful, including a utility or loss criterion when decisions are involved;
- the units of observation, sampling design, measurement process, exclusions, missingness, and transformations;
- an **aspirational model** describing the important features of the data-generating and measurement processes without current computational or sample-size constraints;
- an **initial model** that is tractable and contains the structure needed for the primary question;
- domain-relevant summaries or visual checks that can expose scientifically consequential failures.

The model is the joint combination of likelihood, parameterization, priors, and observation process. Do not assess priors independently of their joint consequences for simulated observations.

## Follow the validation loop

1. **Make the model generative.** Implement simulation from the prior and likelihood using the same transformations, indexing, and design structure used for fitting.
2. **Check prior predictive implications.** Simulate complete hypothetical datasets. Compare domain summaries, constraints, and extreme-event rates with defensible plausibility ranges. Revise the prior, likelihood, or measurement model when joint predictions are implausible; document the reason for each revision.
3. **Verify computational faithfulness.** Check model construction and sampler diagnostics, then use simulation-based calibration (SBC) when feasible for the actual model, design, and inference program. SBC tests the calibration of the implemented inference procedure; it does not establish that the scientific model is adequate or that one dataset identifies a parameter.
4. **Assess inferential sensitivity and design resolution.** Across simulated datasets, evaluate the quantities that matter to the question. Use parameter recovery summaries such as posterior z-scores and contraction when suitable, but prefer a task-specific utility when available. If the design cannot resolve the target, simplify the claim, redesign, or state that the question is not answerable with the available data.
5. **Fit observed data.** Inspect convergence, effective sampling, Monte Carlo error, geometry warnings, and chain behavior before interpreting posterior summaries. Fix computation or reparameterize; do not hide a failed diagnostic by reporting more digits or only increasing iterations without a diagnosis.
6. **Check posterior predictive adequacy.** Simulate replicated data from the fitted model. Reuse pre-specified domain summaries and add graphical or stratified checks that localize important mismatches. Predictive criteria can compare models, but they are not an absolute adequacy check.
7. **Expand deliberately.** If a discrepancy matches a plausible missing feature of the aspirational model, add one coherent feature and rerun every affected earlier check. Retain the last adequate model so an unsuccessful expansion is reversible. Do not chase every random discrepancy or search model space without a scientific narrative.
8. **Interpret conditionally.** Report what the model learned only after separating four claims: prior plausibility, computational faithfulness, inferential sensitivity, and predictive adequacy. A valid conclusion can be that the experiment was not informative.

## Preserve these invariants

- Use simulations as executable specifications of the model and design.
- Choose checks because they could reveal a failure relevant to the scientific claim; generic plots alone are insufficient.
- Treat thresholds as context-dependent decision aids, not universal pass/fail laws.
- Keep prior elicitation and any observed-data-driven prior revision transparent. When the observed data influenced a prior or model choice, distinguish exploration from confirmation and use sensitivity analysis, held-out prediction, or new data where appropriate.
- Do not confuse SBC with parameter recovery, parameter recovery with model adequacy, or posterior predictive fit with proof that the model is true.
- Do not proceed to Bayes factors or model weights until candidate models are computationally faithful and adequate for the intended comparison. Show sensitivity to priors, including nuisance-parameter priors, when model evidence is reported.
- Preserve seeds, software versions, model versions, simulation counts, warnings, and failed checks. Never label an unrun check as passed.

## Deliver an auditable result

Provide code and evidence appropriate to the request, plus a compact record that states:

- what was tested and why it matters;
- status as `pass`, `warning`, `fail`, `not-run`, or `blocked`;
- the artifact or output supporting the status;
- the action taken and which checks were rerun;
- remaining limitations and how they constrain the conclusion.

Base the workflow on Schad, Betancourt, and Vasishth, *Toward a principled Bayesian workflow in cognitive science* (2020), while applying its general principles beyond cognitive science when appropriate: https://arxiv.org/abs/1904.12765
