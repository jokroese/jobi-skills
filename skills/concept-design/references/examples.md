# Boundary Examples

## Reservation: separate access from availability management

A restaurant system may initially appear to have one `Reservation` concept serving both diners and owners.

A better decomposition can be:

### Reserving[Slot, User]
Purpose: ensure access to a resource.

OP: a user reserves an available slot and later redeems the reservation to gain access.

State: slots that can be owned; reservations and their owners.

Actions: reserve, cancel, redeem, expire as required.

### Availability[Resource, Time]
Purpose: maximise useful allocation of resources by deciding what capacity is offered when.

OP: an operator exposes slots according to resource/time constraints and changes availability when operational conditions change.

State: slots, times, resource placement/capacity constraints.

Actions: create/withdraw/change slots and related availability policy.

Why split: diner-facing reserving and operator-facing availability have different stakeholders, actions, state, evolution, and independent reuse. This is behavioural separability, not merely two differently worded purposes.

## User: common conflation

Avoid:

`User {username, passwordHash, displayName, avatar, theme, karma, admin}`

Potential concepts:

- `PasswordAuthentication[Principal]` — establish control of a registered secret.
- `Profile[Principal]` — present chosen descriptive information about an actor.
- `Preference[Principal, Setting]` — preserve user-selected behaviour/settings.
- `Reputation[Principal]` — accumulate/evaluate standing from relevant events.
- `RoleAssignment[Principal, Role]` — assign roles used by app policy.

Do not split mechanically by fields. Validate that each candidate has a complete purpose, OP, and independent behaviour.

## Reaction vs ranking signal

If clicking one control both expresses an emotion to an author and increases content ranking, ask whether the actor may want one without the other.

If yes, consider independent concepts such as:

- `Reaction[Target, Kind]` — communicate a chosen response about a target.
- `Upvote[Target, Voter]` or another ranking mechanism — contribute a preference signal to ordering/selection.

The UI may still present a convenient combined interaction through synchronisation. Conceptual separation does not require UI fragmentation.

## Queue vs Reservation: similar purpose, non-redundant behaviour

Do not merge merely because both handle scarce resources.

`Queue` allocates opportunity according to waiting/order as availability arises.

`Reserving` creates a commitment concerning future access.

Their operational principles and user expectations differ. Similar high-level purpose does not imply redundancy.

## Comment specialised to posts

Avoid `PostComment` if the actual behaviour does not depend on post-specific semantics.

Prefer `Comment[Target]` and configure/synchronise it with posts, replies, images, documents, or other targets as needed.

Generalisation is invalid if comments on different target types genuinely obey materially different semantic laws.
