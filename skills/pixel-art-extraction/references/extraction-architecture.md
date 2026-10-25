# Extraction architecture

## Design goal

Recover an existing cell design faithfully and cheaply across roughly a thousand inputs. Optimise for deterministic throughput, inspectable failure, and repeatability—not for making every source look plausible.

The pipeline has one stable middle representation:

```text
source image
  -> oriented/cropped/rectified raster
  -> lattice boundaries
  -> robust RGBA sample per logical cell
  -> substrate mask and palette mapping
  -> pixel-art/v1 artwork(s)
  -> report, logical render (RGBA or indexed PNG), preview, diagnostic overlay
```

Native pixels, paper, and embroidery differ mainly in how the lattice is observed. Once cell boundaries exist, they should share sampling, segmentation, palette mapping, canonical encoding, and quality control. This separation prevents format-specific heuristics from leaking into the data contract.

## Why this is the default architecture

- **Pillow plus the standard library is enough for the common path.** Installation remains small and every result can be reproduced locally without a service or GPU.
- **Cell sampling is more stable than image segmentation.** Median colour from the centre of a cell ignores grid lines, marker edges, thread boundaries, JPEG ringing, and much of the lighting variation.
- **Known constraints beat general intelligence.** A supplied grid size, crop, palette, or four corners removes a large search space at negligible cost.
- **Abstention controls dataset quality.** A wrong but confident-looking sprite is more damaging than a report that requests review.
- **Canonical art and extraction evidence have different lifecycles.** `pixel-art/v1` stays portable and editable; the sidecar report records how this particular observation was decoded.

## Geometry modes

### Native

Use for one-source-pixel-per-cell artwork or integer nearest-neighbour enlargements. Small images are treated as logical pixels. Enlarged images are decoded from repeated edge rhythm when the signal is strong; otherwise specify `--grid-size` or `--cell-size`.

Lossy JPEG, browser resampling, and screenshots with fractional scale weaken automatic native-grid detection. Prefer the original PNG. If it is unavailable, explicit dimensions are safer than guessing.

### Visible grid

Use for graph paper and printed charts. The extractor compares chromatic line evidence with clipped darkness projections, finds a repeating period on each axis, fits a consistent phase, and snaps predicted boundaries to nearby line peaks. Interior sampling then excludes the boundaries themselves.

Automatic visible-grid recovery assumes the grid is approximately axis-aligned after EXIF orientation. A small crop often improves the estimate more than another algorithm because it removes page edges, labels, and unrelated marks.

### Embroidery and other textured cells

Embroidery usually exposes periodicity through stitch edges rather than inked grid lines. The extractor therefore includes edge rhythm in this mode. Uneven tension, curved fabric, shadows, and non-square stitches can make a single global lattice inappropriate.

Use explicit dimensions whenever the chart size is known. Use four corners for planar perspective. Divide warped fabric into locally regular crops; a non-linear dewarper is deliberately outside the cheap deterministic core.

### Perspective

`--corners` accepts the post-crop coordinates of top-left, top-right, bottom-right, and bottom-left corners. With `--grid-size`, the extractor maps that quadrilateral to a regular raster before sampling. Corner selection is a small, auditable intervention and is usually cheaper than installing a general feature-matching stack.

If many sources share a capture rig, correct the rig once or reuse a calibrated crop and geometry. Do not make a model rediscover the same transform per image.

## Cell classification

The centre of every cell is reduced to a median RGBA sample. For physical-media palette estimation, retain a second observation from the most substrate-distant fifth of the inset pixels. The median remains the stable occupancy signal; the strongly covered observation preserves evidence that paper, blur, and incomplete coverage otherwise suppress. For transparent-background extraction, a substrate colour is estimated from border cells unless `--background-colour` supplies it. Distance from that colour becomes a one-dimensional foreground signal; an Otsu split supplies the default threshold.

This works well when substrate and marks form separate populations. Supply a threshold when faint pencil, pale thread, stains, or shadows overlap. The report records the ambiguous fraction: cells close to the boundary reduce confidence and can force review.

Map foreground samples to an exact palette when it is known. A physical mark often covers only part of a boundary cell, so its median is a mixture of substrate and ink rather than a faded new colour. For each exact ink, project the sample onto the line from substrate to ink and choose the line with the smallest residual. Record the estimated coverage, but emit the fully opaque logical ink colour. Nearest-RGB matching incorrectly turns black-on-warm-paper boundaries brown because the mixture can be numerically closer to tan or maroon than to solid black.

Ink can also cross a cell boundary or be overdrawn by a neighbouring, darker mark. When a one-ink fit selects a darker palette entry but a two-ink fit strongly favours a lighter dominant ink plus smaller dark contamination, use the lighter ink only when nearby cells independently support it. This combines physical evidence with a deliberately narrow spatial prior: it repairs boundary overrun without smoothing a genuine isolated dark detail whose sample already fits its palette colour.

Use nearest-RGB matching for opaque native artwork where no substrate is being removed. When an exact physical-media palette is unavailable, cluster the strongly covered observations by their normalised direction away from the substrate. Deterministic farthest-first seeds protect rare chromatically distinct marks before Lloyd iterations consolidate nearby rays. Report cluster sizes, ray residuals, RGB reconstruction error, assignment margins, and rare clusters so the result can be audited cell by cell.

This direction-based reduction separates ink families more reliably than median-cut RGB, but it still cannot identify the original ink endpoints: capture lighting and colour cast can change hue as well as apparent coverage. Emit the robust observed cluster representatives, label them `observed-physical-media-estimate`, and require review. Use a supplied exact palette or a calibrated colour target when authoritative hex values matter. Keep median-cut for native or opaque observations whose source pixels are the colours being recovered.

## Multiple motifs

Component splitting operates on occupied logical cells, not source-image blobs. Nearby fragments can be merged across a configurable number of blank cells so an eye, foot, or detached stitch remains part of its motif. Inspect the diagnostic result: semantic grouping is intentionally not guessed.

Keep splitting off when relative placement is meaningful or when one pattern legitimately contains distant marks. Turn it on for sheets of independent sprites or motifs.

## Confidence and review policy

Confidence is evidence about extraction mechanics, not artistic correctness. The report combines:

- lattice periodicity, coverage, and regularity;
- distance of cells from the substrate decision boundary;
- whether geometry was explicitly supplied;
- canonical validation of every emitted artwork.

Use three operational states:

- `accepted`: mechanics are strong enough for normal use;
- `needs_review`: inspect and rerun with better constraints;
- `failed`: no canonical output could be produced.

An unknown physical-media palette always requires review because its emitted values are observed estimates. With an exact palette, isolated low-margin cells can be ordinary coverage variation; a coherent orthogonally connected group of ambiguous cells is more likely to represent a collapsed semantic region and also requires review. Report both threshold and palette ambiguity as zero-based source-lattice coordinates.

For a large collection, review every abstention and a random sample of accepted items from each source group. Measure cell error on a small manually labelled set before trusting a new capture method. A useful batch metric is exact-cell accuracy, supplemented by per-colour precision and recall when the background dominates.

The bundled round-trip suite supplies the first regression layer. It creates canonical ground truth, renders it, applies deterministic capture damage, recovers it through the production extractor, and compares decoded RGBA cells. It includes axis-aligned noise, partial ink coverage, independently displaced cell marks, cross-boundary ink overrun, rotation, and a compound perspective, line, colour, and noise case. The off-centre cases vary each occupied cell's horizontal offset, vertical offset, and opacity from a stable seed. They also assert that the offsets are genuinely varied and that reduced coverage or the cross-ink correction path was exercised, so a weak distortion cannot pass accidentally. Exact recovery is required because the inputs and geometry are controlled.

The real graph-paper fixture complements the synthetic cases with unequal colour populations, a one-cell accent, similar nose and lip hues, similar eye and hair hues, paint coverage variation, blur, and capture colour shift. Its unknown-palette case measures semantic cluster purity and requires abstention; its exact-palette case verifies that a coherent ambiguous lip region is reported instead of silently accepted. Add further real fixtures for capture behaviours that the synthetic corruptions do not represent.

## Escalation ladder

Escalate only as far as the evidence requires:

1. Automatic local extraction.
2. Re-run with crop, dimensions, cell size, palette, or background colour.
3. Supply four corners or divide a warped source into regular regions.
4. Correct a small number of ambiguous cells in canonical JSON and regenerate derivatives.
5. Use a vision model or specialised computer-vision stack only for the unresolved exception set.

This ladder keeps the average cost near a simple local program while preserving a route for genuinely difficult material.
