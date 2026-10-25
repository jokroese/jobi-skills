# Workflow and diagnostic map

Read this reference for a full implementation or audit. Adapt simulation counts, thresholds, and plots to the model's cost and the consequences of error. A small pilot can validate the pipeline before a larger run, but do not present a pilot as strong calibration evidence.

## Contents

1. Model ladder
2. Prior predictive checks
3. Computational faithfulness
4. Sensitivity and design calibration
5. Observed-data fit
6. Posterior predictive checks
7. Model expansion and comparison
8. Diagnostic routing

## 1. Model ladder

Write the aspirational model as a data-generating narrative. Include latent processes, observation and selection mechanisms, hierarchical variation, dependence, nonlinearities, measurement error, missingness, and temporal or spatial structure when they can affect the question.

Construct the initial model as the smallest coherent approximation that can address the target. Record what the initial model omits and which summaries should expose each consequential omission. A rich design-based starting model is acceptable, but it is still not the aspirational model merely because it contains all regression interactions or varying effects available in a formula interface.

Maintain a model ledger:

| Version | Change and scientific reason | Expected diagnostic change | Checks rerun | Outcome |
| --- | --- | --- | --- | --- |
| M0 | Initial model | Baseline | All | Pending |

## 2. Prior predictive checks

For each replicate:

1. Draw parameters from the joint prior: `theta_sim ~ p(theta)`.
2. Simulate a complete dataset under the real design: `y_sim ~ p(y | theta_sim, design)`.
3. Compute summaries `t(y_sim)` and retain enough raw draws for graphical checks.

Check both ordinary behavior and rare but consequential events. Useful summaries may include location, dispersion, tail probabilities, zero or boundary mass, group variation, correlations, time trends, event counts, order constraints, and scientifically meaningful contrasts. Evaluate on the measurement scale even when the likelihood uses a transformed or link scale.

Revise a prior when the likelihood is appropriate but its joint prior predictions give implausible mass. Revise the likelihood, link, or observation model when no defensible prior can make its predictions realistic. Do not tune priors solely to place the observed statistic near the center of the prior predictive distribution.

## 3. Computational faithfulness

Use layered evidence:

- unit or round-trip checks for transforms, dimensions, indexing, and generated quantities;
- recovery on simple cases with analytic or trusted reference answers where available;
- chain and geometry diagnostics from the chosen inference engine;
- SBC for the actual generative and fitting programs when feasible.

For SBC, repeatedly draw `theta_sim`, simulate `y_sim`, fit the model, and compute the rank of `theta_sim` among posterior draws for each monitored quantity. Rank distributions should be compatible with discrete uniformity after accounting for finite simulation and posterior sample sizes. Inspect rank empirical CDFs or rank histograms with uncertainty bands; avoid judging noisy histograms by eye alone.

Interpret deviations cautiously:

- systematic slope or asymmetry suggests bias;
- U-shaped ranks can indicate under-dispersed posteriors or unresolved autocorrelation;
- inverted-U ranks can indicate over-dispersion;
- boundary spikes can indicate strong autocorrelation or sampling pathologies.

Before blaming the inference engine, check that simulation and fitting use exactly the same parameterization, design, transforms, likelihood, prior, and data constraints. SBC validates computation internally under the assumed model; it does not validate that assumption against reality.

## 4. Sensitivity and design calibration

Reuse prior-to-data simulations, but now ask whether the posterior is useful for the target. For scalar parameters, two coarse diagnostics from the paper are:

```text
posterior z-score = (posterior mean - simulated truth) / posterior SD
posterior contraction = 1 - posterior variance / prior variance
```

Across many simulated datasets, examine bias, interval coverage, interval width, contraction, decision error, sign error, false discovery, true discovery, predictive utility, or a domain-specific loss. Use the joint distribution, not one convenient simulation.

The z-score/contraction plane supports diagnosis, not automatic rejection:

| Pattern | Likely interpretation |
| --- | --- |
| Small absolute z, high contraction | Accurate and informative for that simulation |
| Small absolute z, low contraction | Poor identification or weak design resolution |
| Large absolute z, high contraction | Confident error or overfitting to simulated noise |
| Large absolute z, low contraction | Prior-likelihood conflict or weakly identified bias |

If performance is unacceptable, consider a larger or different design, a simpler estimand, stronger defensible prior information, a reparameterized model, or a more modest claim. More observations do not guarantee resolution for every parameter.

## 5. Observed-data fit

Only interpret posterior quantities after the inference diagnostics are credible. Use the diagnostics native to the selected engine and parameterization. Inspect warnings, convergence across chains or approximations, effective sample size, Monte Carlo standard error relative to the required reporting precision, energy or geometry pathologies, and trace or marginal behavior.

When computation fails, diagnose before spending more computation. Typical responses include correcting code, rescaling, non-centering or otherwise reparameterizing, improving defensible priors, changing the likelihood geometry, or using a more appropriate inference method. Any material change to the model or program invalidates relevant prior SBC and sensitivity evidence until rerun.

## 6. Posterior predictive checks

Draw `theta_rep ~ p(theta | y)` and `y_rep ~ p(y | theta_rep)`. Compare `t(y_rep)` with `t(y)` for each claim-relevant summary. Include stratified checks by groups, conditions, time, or covariates when aggregate fit can hide the relevant failure.

A discrepancy is actionable when it is large enough to matter and consistent with a plausible missing feature. It may also reflect an extreme dataset under an adequate model. Record the judgment and its scientific rationale; do not automatically expand the model until every observed statistic looks typical.

Posterior predictive checks measure absolute, question-specific adequacy. Cross-validation and predictive information criteria measure relative predictive performance among candidates. Use both when appropriate, but do not substitute one for the other.

## 7. Model expansion and comparison

Expand toward the aspirational model using a diagnosed mismatch: for example, add heterogeneity when group-stratified dispersion is missed, a heavy-tailed likelihood when consequential tail behavior is missed, or a time component when residual drift is present. Predict which checks should improve before fitting the expansion.

After each expansion:

1. rerun prior predictive checks for changed joint implications;
2. rerun computational validation affected by changed code or geometry;
3. rerun sensitivity analyses for changed inferential behavior;
4. fit observed data and rerun posterior predictive checks;
5. compare with the prior adequate version and keep rollback possible.

Use model comparison only among models credible enough for the intended scientific use. When reporting Bayes factors or marginal likelihoods, inspect numerical stability and prior sensitivity; diffuse priors are not neutral, and nuisance-parameter priors can materially affect the result.

## 8. Diagnostic routing

| Evidence | What it can support | What it cannot support | Usual next action on failure |
| --- | --- | --- | --- |
| Prior predictive check | Joint prior-model implications are domain-plausible | Inference code is correct; model fits observed data | Revise prior, likelihood, link, or measurement model |
| Sampler diagnostics | This observed fit appears numerically reliable | Program is calibrated over possible datasets | Debug, reparameterize, or improve inference settings |
| SBC | Inference implementation is calibrated under the model | Parameters are well identified; model is scientifically adequate | Check simulation/fitting equivalence, code, and computation |
| Sensitivity/design simulation | Design and model can answer the target often enough | Observed data are typical; model matches reality | Redesign, simplify target, or temper claim |
| Posterior predictive check | Model reproduces selected observed-data features | Model is true; computation is calibrated | Localize mismatch and expand only with a scientific rationale |
| Cross-validation/model comparison | Relative predictive performance for a defined task | Absolute adequacy | Improve candidate set or accept that all candidates are inadequate |

Primary source: Daniel J. Schad, Michael Betancourt, and Shravan Vasishth, “Toward a principled Bayesian workflow in cognitive science” (2020), https://arxiv.org/abs/1904.12765.
