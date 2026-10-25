---
name: concept-design
description: Design, discover, critique, simplify, refactor, compare, and document the user-facing concepts of a software repository, product, service, API, protocol, or project description using concept design. Use when asked to identify conceptual models, define concepts and operational principles, review concept boundaries, find conflation/fragmentation/coupling/redundancy, reduce conceptual complexity, split or merge concepts, generalise concepts, lift configuration, define synchronisations, assess stakeholder effects, or map a proposed conceptual redesign back to an existing codebase. Prefer repository evidence and user-visible behaviour over class, database, service, or UI-component boundaries.
---

# Concept Design

## Objective

Factor software into the smallest practical set of complete, independent, behaviourally coherent user-facing concepts whose composition fulfils the project's needs.

Treat concept design as **functional modularity at the semantic/user-facing level**. Do not confuse concepts with classes, entities, services, screens, features, routes, tables, or nouns in the domain.

Read `references/theory.md` before substantial design or critique. Read `references/output.md` when producing a formal audit, redesign, or concept catalogue. Read `references/examples.md` when boundaries remain ambiguous or a concrete decomposition example would help.

## Core rules

Apply these rules as defaults:

1. **Purpose justifies; it does not uniquely identify.** Define a concept by its purpose, operational principle, and behaviour together. Do not force one-to-one textual uniqueness of purpose statements.
2. **Use behavioural separability for boundaries.** Split behaviour when substantial parts can be desired, varied, evolved, explained, or reused independently.
3. **Require completeness.** A concept must deliver its purpose end-to-end rather than represent a fragment of a workflow.
4. **Require independence.** Define each concept without depending on another concept's state, fields, actions, or identity. Represent external objects by generic parameters where possible.
5. **Prefer familiar, reusable concepts.** Invent a new concept only when existing patterns do not capture materially different behaviour.
6. **Separate concept purpose, application rationale, and stakeholder effects.** Never overload a generic purpose with app-specific motivation or every consequence for every stakeholder.
7. **Compose externally.** Put reusable behaviour inside concepts; put cross-concept coordination in synchronisations and app-specific relationships in configuration.
8. **Preserve integrity.** A concept should mean and behave consistently wherever it appears.
9. **Optimise the conceptual model, not the concept count.** Merge redundancy and accidental fragmentation; split conflation. Do not pursue fewer concepts as an end in itself.
10. **Ground claims in evidence.** When analysing a repository, cite or point to the files, behaviours, tests, docs, routes, schemas, or user flows that support each important inference.

## Workflow

### 1. Establish the task and evidence

Classify the request as one or more modes:

- **Discover**: infer concepts from an existing repository/product.
- **Design**: propose concepts for a new project or requirement.
- **Critique**: evaluate an explicit or inferred concept model.
- **Reduce**: simplify the model without losing required behaviour.
- **Refactor**: split, merge, rename, generalise, lift, or recombine concepts.
- **Extend**: incorporate a new requirement while preserving conceptual integrity.
- **Compare**: evaluate alternative conceptual models.
- **Implement**: map an agreed conceptual redesign into repository changes.

If repository/files are available, inspect them before making architecture claims. Prefer evidence in this rough order:

1. user-facing behaviour, product docs, examples, acceptance tests;
2. API/protocol semantics and public contracts;
3. state transitions and domain/application tests;
4. routes, commands, events, schemas, and persistence;
5. class/module/service boundaries.

Treat implementation structure as evidence, never as the conceptual decomposition by default.

If information is incomplete, proceed with explicit assumptions and confidence levels rather than inventing behaviour. Ask only when an unresolved ambiguity would materially change the design.

### 2. Inventory behaviours and stakeholders

Extract:

- actors/stakeholders;
- valuable needs and pain points;
- user-visible actions and outcomes;
- persistent semantic state;
- lifecycle events, including setup, cancellation, undo, expiry, deletion, recovery, and exceptional semantic cases;
- constraints and invariants;
- cross-cutting app policy;
- current vocabulary and apparent mental model.

Separate **needs** from mechanisms and implementation details.

### 3. Form candidate concepts

For each candidate, define:

- **Name**: pithy, stable, preferably familiar.
- **Purpose**: concise, generic, need-focused, end-to-end, evaluable.
- **Operational principle (OP)**: shortest archetypal scenario showing how the concept fulfils its purpose.
- **State**: abstract semantic information required by the behaviour.
- **Actions**: semantic state transitions/queries.
- **Parameters**: generic external types, if required.

Use this compact form:

```text
Concept Name[Parameters]
Purpose: ...
OP: ...
State: ...
Actions: ...
```

Do not put application-specific cross-concept relationships into a generic concept definition.

### 4. Test every boundary

Evaluate each candidate against:

- **User-facing**: does a user or API consumer experience the behaviour?
- **Semantic**: is it abstract behaviour rather than presentation/implementation?
- **Purposive**: does it solve a valuable need?
- **Complete**: can it fulfil that need end-to-end by itself?
- **Independent**: can it be understood and defined without other concepts?
- **Separable**: does it avoid bundling independently variable behaviours?
- **Familiar/reusable**: is it recognisable and portable where appropriate?
- **Integrity**: is its meaning stable wherever used?

Use these separability probes:

- **Counterfactual**: could a reasonable actor want A without B?
- **Evolution**: could A change substantially without B?
- **Reuse**: would A be useful where B is absent?
- **State factorisation**: does state approximately decompose as `S1 x S2`?
- **Action factorisation**: do actions approximately partition into independent sets?
- **Explanation**: can each part support its own purpose and OP?

Multiple beneficial consequences do not by themselves imply multiple concepts.

### 5. Diagnose design smells

Identify only smells supported by evidence:

- **Conflation**: separable behaviours bundled together.
- **Fragmentation**: one end-to-end behaviour split into pieces that have little value alone.
- **Coupling**: one concept knows another concept's details.
- **Redundancy**: two concepts occupy substantially the same behavioural role without a useful distinction.
- **Over-specialisation**: a generic concept is tied unnecessarily to one domain/context.
- **Mechanistic purpose**: purpose merely restates actions or implementation.
- **Vague purpose**: purpose is too broad to constrain design.
- **CRUD shell**: entity storage is mistaken for a concept.
- **UI leakage**: widgets/screens are mistaken for semantics.
- **Integrity failure**: the same concept behaves inconsistently across contexts.
- **Configuration leakage**: app-specific relations live inside reusable concepts.
- **Hidden concept**: rich independent behaviour is buried in a sync, helper, field cluster, policy, or submodule.

For every smell, state the consequence and the smallest credible repair.

### 6. Optimise the model

Consider these moves deliberately:

- **Split** conflated concepts.
- **Merge** redundant or fragmented concepts.
- **Delete** concepts that do not earn their cognitive/behavioural cost.
- **Rename** to match the actual mental construct.
- **Generalise** accidental domain specialisation into parameters.
- **Extract** a hidden concept with independent value.
- **Lift** app-specific mappings/relations into configuration.
- **Move coordination** into synchronisations.
- **Change extent** when independent populations need separate instances.
- **Replace** a bespoke concept with a familiar one when behaviour matches.

Optimise for **minimum accidental conceptual complexity**, not minimum number of names.

When reducing, preserve all explicitly required user-visible capabilities and invariants unless the user explicitly authorises removing them.

### 7. Define composition

After concept definitions stabilise, define application composition separately:

- concept instances and extents;
- application rationale for including each concept;
- configuration relations between instances;
- synchronisations between actions;
- application-level inclusion dependencies;
- stakeholder effects, powers, costs, risks, and incentives.

Represent synchronisation conceptually as:

```text
ConceptA.action(...) -> ConceptB.action(...), ConceptC.action(...)
```

Do not make this coordination an intrinsic dependency of ConceptA unless it is genuinely part of ConceptA's reusable semantics.

### 8. Compare current and target models

For refactors, produce an explicit delta:

```text
Current -> Target -> Move -> Reason -> Behaviour preserved/changed
```

Use moves such as `split`, `merge`, `rename`, `generalise`, `extract`, `lift`, `delete`, `replace`, `change extent`, and `resynchronise`.

Distinguish:

- **semantic changes**: user-visible behaviour changes;
- **conceptual-only changes**: better factorisation of existing behaviour;
- **implementation changes**: code/storage/API changes required to realise the target model.

Never imply that a concept refactor is behaviour-preserving unless you have checked the relevant contracts/invariants.

### 9. Map back to a repository only after the target model is clear

If implementation is requested:

1. Map each target concept to current implementation evidence.
2. Identify shared persistence/API compatibility constraints.
3. Choose seams that allow incremental migration.
4. Preserve external contracts unless changes are explicitly allowed.
5. Move code according to semantic ownership, not merely file size.
6. Add or update tests around concept actions, invariants, and synchronisations.
7. Re-run relevant tests/lint/type checks where tools permit.

Do not undertake broad code churn solely to make directories resemble the conceptual model. Conceptual modularity is primary; physical structure should support it pragmatically.

## Decision discipline

### Do not enforce literal purpose bijection

Natural-language purposes have no canonical granularity or equality relation. Treat apparent purpose overlap as a prompt for analysis, not proof of redundancy.

Two concepts with similar high-level purposes may be legitimate when their operational principles and behavioural roles differ materially. Two concepts with differently worded purposes may still be redundant if they are behaviourally substitutable in the application.

### Separate stakeholder effects from concept boundaries

Do not split a concept merely because several stakeholders benefit from it. Split when the underlying behaviours are independently variable or independently valuable.

Conversely, actively inspect different stakeholder behaviours: they often reveal genuine hidden separability.

### Prefer behavioural evidence over naming

Names such as `User`, `Account`, `Manager`, `Service`, `Thing`, or `Resource` are weak evidence. Inspect actions, state, lifecycle, and invariants before treating them as concepts.

### Preserve uncertainty

Use labels such as `observed`, `inferred`, `proposed`, and `uncertain`. Do not present inferred concept boundaries as facts when repository evidence is incomplete.

## Output behaviour

Match depth to the request. For a quick critique, give the smallest useful diagnosis and target model. For a full audit/redesign, follow `references/output.md`.

Always make recommendations concrete. Prefer:

> Split `User` into `PasswordAuthentication`, `Profile`, and `Preference` because their state/actions vary independently and each is reusable.

rather than:

> Improve separation of concerns.

When the user asks for the **smallest** or **most DRY** model, minimise accidental concepts, duplicated mechanisms, concept-specific variants, and configuration embedded inside concepts while preserving semantic distinctions that users need.

When the user asks for alternatives, present materially different decompositions and state the trade-offs rather than inventing cosmetic variants.

## Final self-review

Before answering, verify:

- every proposed concept has a compelling purpose and OP;
- every concept is complete and independent;
- no proposed split is justified only by prose granularity;
- no proposed merge erases independently variable behaviour;
- stakeholder effects are not confused with generic purpose;
- app rationale/configuration/synchronisation are not embedded inside concept definitions;
- important claims about an existing repository are traceable to evidence;
- the target model is simpler in semantic structure, not just shorter on paper.
