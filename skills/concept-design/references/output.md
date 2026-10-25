# Output Patterns

Use the smallest pattern that fully serves the request.

## Full repository/project audit

```markdown
# Concept design review

## Executive model
One paragraph: what the product does conceptually, the main problem with the current model, and the recommended direction.

## Evidence and assumptions
- Scope inspected
- Key behavioural evidence
- Explicit assumptions / unknowns

## Current inferred concepts
| Concept | Purpose | Key state/actions | Evidence | Confidence |
|---|---|---|---|---|

## Findings
For each important issue:
### [Finding]
- Classification: conflation / fragmentation / coupling / redundancy / etc.
- Evidence
- Why it matters
- Minimal repair

## Target concept model
### ConceptName[Parameters]
**Purpose:** ...
**OP:** ...
**State:** ...
**Actions:** ...

## Composition
### Configuration
...
### Synchronisations
...
### Application dependencies
...
### Stakeholder effects
...

## Delta
| Current | Target | Move | Reason | Behaviour impact |
|---|---|---|---|---|

## Implementation implications
Only if repository modification or migration matters.

## Open questions
Only ambiguities that could materially alter the design.
```

## Concise critique

Use:

1. **Model** — the concepts you think exist.
2. **Main defects** — no more than the decisive issues.
3. **Target** — proposed split/merge/generalisation.
4. **Why** — completeness/independence/separability evidence.
5. **Unknowns** — only material uncertainties.

## Concept catalogue entry

```markdown
## ConceptName[Parameters]
**Purpose:** [generic valuable need]

**OP:** [short archetypal scenario]

**State**
- ...

**Actions**
- `action(args) -> result`: semantic effect

**Variants:** [only meaningful behavioural variants]
**Challenges:** [hard semantic issues/invariants]
**Related:** [similar or commonly composed concepts]
```

## Refactor proposal

```markdown
# Concept refactor

## Before
[current conceptual structure]

## After
[target conceptual structure]

## Transformations
| Move | From | To | Why |

## Behaviour
- Preserved: ...
- Intentionally changed: ...
- At risk / requires verification: ...

## Composition changes
- Configuration: ...
- Synchronisations: ...
- Extents/dependencies: ...

## Repository migration
1. ...
```

## Alternative designs

For each alternative, vary concept boundaries materially. Compare on:

- conceptual coherence;
- independence;
- separability;
- familiarity;
- configuration/sync complexity;
- stakeholder consequences;
- migration cost if relevant.

End with a preferred model and the decisive reason.

## Evidence notation

When file-line citations are available, cite each major repository inference inline. Otherwise name paths/symbols precisely, e.g. `src/auth/session.ts::renew()` or `docs/booking.md`.

Mark claims as:

- **Observed** — directly supported by evidence.
- **Inferred** — best semantic explanation of evidence.
- **Proposed** — recommended future design.
- **Uncertain** — meaningful unresolved ambiguity.
