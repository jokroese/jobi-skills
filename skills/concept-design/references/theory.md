# Canonical Concept Design Theory

## Thesis

Design software by discovering valuable user-facing behaviours, factoring them at their natural boundaries of independent variation, making each factor complete and context-independent, reusing familiar factors where possible, and expressing application-specific relationships and coordination outside them.

A concept is simultaneously:

- a mental construct a user needs to understand; and
- a coherent unit of user-facing functionality.

This alignment is the basis of conceptual modularity.

## Concept model

Use:

`C = <Name, Purpose, OP, State, Actions, Parameters>`

- **Name** identifies the mental construct.
- **Purpose** states the generic valuable need.
- **OP** explains, through an archetypal scenario, how the behaviour fulfils that need.
- **State** records the abstract semantic information required.
- **Actions** define semantic transitions and queries.
- **Parameters** abstract over external types without coupling concepts.

Concept identity is not determined by purpose alone.

## Purpose

Require a purpose to be valuable, need-focused, specific enough to constrain the concept, end-to-end, evaluable, and application-independent.

Reject purposes that merely name the mechanism (`manage reservations`, `allow login`), enumerate actions, or describe the reason this one application happens to use the concept.

Keep separate:

1. **Concept purpose** — why the concept is valuable in general.
2. **Application rationale** — why this application includes it.
3. **Stakeholder effects** — who gains/loses information, power, cost, risk, options, or utility.

## Operational principle

Use the shortest representative history that makes the concept intelligible. Include enough lifecycle to establish how the purpose is achieved. Keep UI and unrelated concept actions out of the OP.

Use OPs as a diagnostic: a candidate whose OP cannot be told without unrelated behaviour is probably fragmented, coupled, or badly bounded.

## State and actions

Model a concept as an abstract state machine `S --a--> S'`.

State is semantic, not a database layout. Actions are atomic at the conceptual level, not necessarily at the UI or implementation level.

Include the lifecycle needed for the purpose: setup, use, change, cancellation/undo, expiry/recovery/closure where semantically intrinsic.

## Boundary laws

### Completeness

A concept delivers its purpose end-to-end by itself. A fragment that matters only because another concept acts is usually not a concept.

### Independence

A concept is understandable/definable without another concept. It does not call another concept, inspect its state, or assume its fields. External objects become generic parameters where appropriate.

### Separability

A concept contains one behaviourally inseparable concern.

Use these tests:

- counterfactual independence;
- evolution independence;
- reuse independence;
- state/action factorisation;
- explanatory independence.

If state approximates `S1 x S2`, actions split correspondingly, and each part has independent value, prefer two concepts.

This refines the older one-concept/one-purpose slogan. Natural-language purposes can be merged/split arbitrarily; behavioural separability is the stronger boundary criterion.

## Redundancy

Two concepts are redundant when, within the application, they impose distinct user-visible mechanisms for substantially the same behavioural role without a meaningful distinction.

Shared abstract purpose is not enough. Reservation and Queue may both mediate scarce resources but have distinct operational principles.

## Familiarity and reuse

Prefer familiar concepts when behaviour fits. Most novelty should come from composition or meaningful variations rather than unnecessary reinvention.

Generalise accidental domain-specific references into type parameters when semantics permit.

## Composition

Concepts remain intrinsically independent. Compose instances with:

- **synchronisations** for action-to-action coordination;
- **configuration** for app-specific relationships/mappings;
- **application dependencies** for rationale/inclusion structure.

Do not place reusable behaviour in synchronisations merely to keep concepts small.

## Lifting

When concept state contains a relation whose meaning is how concepts are configured together rather than intrinsic to either concept, move it to application configuration.

If lifting exposes a global invariant with significant standalone behaviour, investigate whether that invariant is itself a concept.

## Extent

Choose the smallest concept instance extent that preserves genuine invariants. If populations do not need to interact, prefer separate instances.

## Integrity

Preserve the same conceptual laws wherever a concept occurs. Composition must not silently invalidate the expectations established by its OP.

## Canonical objective

Use:

`conceptual modularity ~= behavioural separability + completeness + independence`

subject to familiarity, integrity, and economical composition.

Optimise conceptual complexity rather than concept count.
