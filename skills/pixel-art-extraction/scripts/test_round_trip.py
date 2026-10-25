#!/usr/bin/env python3
"""Exercise extraction against deterministic synthetic capture damage."""

from __future__ import annotations

import argparse
import json
import random
import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Sequence

from PIL import Image, ImageDraw

import extract_pixel_art as extractor


PALETTE = [(72, 65, 63), (191, 133, 100), (42, 113, 103), (114, 66, 60)]
PAPER = (239, 235, 222)
WIDTH = 16
HEIGHT = 12
REAL_FIXTURE_PALETTE = (
    "#D49E6F",
    "#A8704D",
    "#3F2D1E",
    "#5D4229",
    "#D5BD93",
    "#D6A11A",
    "#B85D46",
)


def ground_truth_pixels() -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 0)] * (WIDTH * HEIGHT)

    def paint(colour: tuple[int, int, int], cells: set[tuple[int, int]]) -> None:
        for x, y in cells:
            pixels[y * WIDTH + x] = (*colour, 255)

    dark = {
        (2, 3),
        (3, 3),
        (4, 3),
        (5, 3),
        (6, 3),
        (8, 3),
        (1, 4),
        (2, 4),
        (3, 4),
        (4, 4),
        (5, 4),
        (6, 4),
        (7, 4),
        (2, 5),
        (3, 5),
        (4, 5),
        (5, 5),
        (6, 5),
        (7, 5),
        (8, 5),
        (3, 6),
        (4, 6),
        (5, 6),
        (6, 6),
        (7, 6),
        (8, 6),
        (4, 7),
        (5, 7),
        (7, 7),
        (8, 7),
        (3, 8),
        (8, 8),
    }
    red = {(9, 3), (10, 3), (11, 3), (9, 4), (10, 4), (11, 4), (10, 5)}
    green = {(12, 7), (11, 8), (12, 8), (13, 8), (12, 9)}
    paint(PALETTE[0], dark)
    paint(PALETTE[1], red)
    paint(PALETTE[2], green)
    return pixels


def ground_truth_data() -> dict[str, object]:
    rule = {
        "mode": "exact",
        "colours": ["#{:02X}{:02X}{:02X}".format(*colour) for colour in PALETTE],
    }
    return extractor.canonical_data(ground_truth_pixels(), WIDTH, HEIGHT, rule)


def render_chart(cell_size: int = 22, mixed_coverage: bool = False) -> Image.Image:
    logical = extractor.render_canonical(ground_truth_data())
    if mixed_coverage:
        observed = Image.new("RGBA", logical.size, (*PAPER, 255))
        source_pixels = list(logical.getdata())
        observed_pixels = []
        for index, colour in enumerate(source_pixels):
            if colour[3] == 0:
                observed_pixels.append((*PAPER, 255))
                continue
            x, y = index % WIDTH, index // WIDTH
            coverage = 0.40 + 0.10 * ((x * 3 + y * 5) % 6)
            mixed = tuple(
                round(PAPER[channel] * (1.0 - coverage) + colour[channel] * coverage)
                for channel in range(3)
            )
            observed_pixels.append((*mixed, 255))
        observed.putdata(observed_pixels)
        logical = observed
    enlarged = logical.resize(
        (WIDTH * cell_size, HEIGHT * cell_size), Image.Resampling.NEAREST
    )
    paper = Image.new("RGBA", enlarged.size, (*PAPER, 255))
    paper.alpha_composite(enlarged)
    draw = ImageDraw.Draw(paper)
    line = (136, 184, 196, 150)
    for x in range(0, paper.width + 1, cell_size):
        draw.line((x, 0, x, paper.height), fill=line, width=1)
    for y in range(0, paper.height + 1, cell_size):
        draw.line((0, y, paper.width, y), fill=line, width=1)
    return paper.convert("RGB")


def independent_mark_parameters(index: int, cell_size: int) -> tuple[int, int, int]:
    rng = random.Random(0x5EED_0000 + index * 104_729)
    maximum_shift = round(cell_size * 0.27)
    return (
        rng.randint(-maximum_shift, maximum_shift),
        rng.randint(-maximum_shift, maximum_shift),
        rng.randint(round(255 * 0.68), round(255 * 0.82)),
    )


def render_off_centre_chart(
    cell_size: int = 22,
) -> tuple[Image.Image, list[tuple[int, int, int]]]:
    logical = extractor.render_canonical(ground_truth_data())
    paper = Image.new("RGBA", (WIDTH * cell_size, HEIGHT * cell_size), (*PAPER, 255))
    placements: list[tuple[int, int, int]] = []
    for index, colour in enumerate(logical.getdata()):
        if colour[3] == 0:
            continue
        x, y = index % WIDTH, index // WIDTH
        horizontal, vertical, opacity = independent_mark_parameters(index, cell_size)
        mark = Image.new("RGBA", (cell_size, cell_size), (*colour[:3], opacity))
        paper.alpha_composite(
            mark,
            dest=(x * cell_size + horizontal, y * cell_size + vertical),
        )
        placements.append((horizontal, vertical, opacity))

    draw = ImageDraw.Draw(paper)
    line = (136, 184, 196, 150)
    for x in range(0, paper.width + 1, cell_size):
        draw.line((x, 0, x, paper.height), fill=line, width=1)
    for y in range(0, paper.height + 1, cell_size):
        draw.line((0, y, paper.width, y), fill=line, width=1)
    return paper.convert("RGB"), placements


def add_cross_ink_overrun(image: Image.Image, cell_size: int = 22) -> Image.Image:
    damaged = image.copy()
    target = PALETTE[1]
    contaminant = PALETTE[0]
    mixed = tuple(
        max(
            0,
            min(
                255,
                round(
                    PAPER[channel]
                    + 0.60 * (target[channel] - PAPER[channel])
                    + 0.30 * (contaminant[channel] - PAPER[channel])
                ),
            ),
        )
        for channel in range(3)
    )
    x, y = 10, 3
    ImageDraw.Draw(damaged).rectangle(
        (
            x * cell_size + 1,
            y * cell_size + 1,
            (x + 1) * cell_size - 1,
            (y + 1) * cell_size - 1,
        ),
        fill=mixed,
    )
    return damaged


def add_off_centre_cross_ink_overrun(
    image: Image.Image, cell_size: int = 22
) -> Image.Image:
    damaged = image.convert("RGBA")
    spill = Image.new("RGBA", damaged.size, (0, 0, 0, 0))
    target_x, target_y = 9, 3
    ImageDraw.Draw(spill).rectangle(
        (
            round((target_x - 0.55) * cell_size),
            target_y * cell_size + 2,
            target_x * cell_size + round(cell_size * 0.64),
            (target_y + 1) * cell_size - 2,
        ),
        fill=(*PALETTE[0], round(255 * 0.35)),
    )
    damaged.alpha_composite(spill)
    return damaged.convert("RGB")


def solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    size = len(vector)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            raise RuntimeError("singular perspective transform")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][-1] for row in range(size)]


def inverse_perspective_coefficients(
    destination: Sequence[tuple[float, float]], source_size: tuple[int, int]
) -> tuple[float, ...]:
    width, height = source_size
    source = (
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    )
    matrix: list[list[float]] = []
    vector: list[float] = []
    for (u, v), (x, y) in zip(destination, source):
        matrix.append([u, v, 1, 0, 0, 0, -x * u, -x * v])
        vector.append(x)
        matrix.append([0, 0, 0, u, v, 1, -y * u, -y * v])
        vector.append(y)
    return tuple(solve_linear(matrix, vector))


def discolour_and_noise(image: Image.Image, seed: int, amount: int) -> Image.Image:
    rng = random.Random(seed)
    pixels = []
    for red, green, blue in image.convert("RGB").getdata():
        noise = rng.randint(-amount, amount)
        pixels.append(
            (
                max(0, min(255, round(red * 1.04 + 7 + noise))),
                max(0, min(255, round(green * 0.96 + 3 + noise))),
                max(0, min(255, round(blue * 0.90 + noise))),
            )
        )
    damaged = Image.new("RGB", image.size)
    damaged.putdata(pixels)
    return damaged


def warp_chart(
    chart: Image.Image,
    destination: Sequence[tuple[float, float]],
    canvas_size: tuple[int, int],
) -> Image.Image:
    coefficients = inverse_perspective_coefficients(destination, chart.size)
    return chart.transform(
        canvas_size,
        Image.Transform.PERSPECTIVE,
        coefficients,
        Image.Resampling.BICUBIC,
        fillcolor=PAPER,
    )


def extraction_args(
    corners: Sequence[tuple[float, float]] | None,
    automatic: bool,
    foreground_threshold: float | None,
    indexed_png: bool = False,
) -> SimpleNamespace:
    flattened = (
        tuple(value for point in corners for value in point) if corners else None
    )
    return SimpleNamespace(
        mode="grid",
        crop=None,
        grid_size=None if automatic else (WIDTH, HEIGHT),
        cell_size=None,
        corners=flattened,
        cell_inset=0.20,
        palette=",".join("#{:02X}{:02X}{:02X}".format(*colour) for colour in PALETTE),
        max_colours=None,
        background="transparent",
        background_colour=None,
        foreground_threshold=foreground_threshold,
        split_components=False,
        merge_gap=1,
        min_component_cells=1,
        padding=0,
        no_trim=True,
        preview_scale=8,
        indexed_png=indexed_png,
        diagnostics=True,
        fail_on_review=True,
    )


def decode(path: Path) -> list[tuple[int, int, int, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(extractor.render_canonical(data).getdata())


def run_case(
    root: Path,
    name: str,
    image: Image.Image,
    corners: Sequence[tuple[float, float]] | None,
    automatic: bool = False,
    foreground_threshold: float | None = None,
    expect_partial_coverage: bool = False,
    expect_cross_ink_correction: bool = False,
    indexed_png: bool = False,
    source_checks: dict[str, bool] | None = None,
) -> dict[str, object]:
    source_path = root / f"{name}.png"
    output_dir = root / name
    image.save(source_path, format="PNG")
    report = extractor.extract_one(
        source_path,
        output_dir,
        extraction_args(corners, automatic, foreground_threshold, indexed_png),
    )
    canonical_path = output_dir / report["outputs"][0]["canonical"]
    recovered = decode(canonical_path)
    truth = ground_truth_pixels()
    correct = sum(actual == expected for actual, expected in zip(recovered, truth))
    accuracy = correct / len(truth) if len(recovered) == len(truth) else 0.0
    classification = report["classification"]
    checks = {"exact_rgba": accuracy == 1.0}
    logical_path = output_dir / report["outputs"][0]["logical_png"]
    if indexed_png:
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        index_width = canonical["indexWidth"]
        expected_indices = [
            int(row[offset : offset + index_width], 16)
            for row in canonical["pixels"]
            for offset in range(0, len(row), index_width)
        ]
        with Image.open(logical_path) as logical:
            checks["logical_png_is_indexed"] = logical.mode == "P"
            checks["canonical_indices_preserved"] = (
                list(logical.getdata()) == expected_indices
            )
            checks["indexed_rgba_preserved"] = (
                list(logical.convert("RGBA").getdata()) == recovered
            )
        checks["indexed_mode_reported"] = (
            report["outputs"][0].get("logical_png_mode") == "indexed"
        )
    else:
        with Image.open(logical_path) as logical:
            checks["default_logical_png_is_rgba"] = logical.mode == "RGBA"
    if source_checks:
        checks.update(source_checks)
    if expect_partial_coverage:
        checks["partial_coverage_exercised"] = (
            classification["median_estimated_ink_coverage"] < 0.80
        )
    if expect_cross_ink_correction:
        checks["cross_ink_correction_exercised"] = (
            classification["cross_ink_corrected_cells"] >= 1
        )
    return {
        "name": name,
        "status": report["status"],
        "passed": all(checks.values()),
        "accuracy": accuracy,
        "correct_cells": correct,
        "total_cells": len(truth),
        "checks": checks,
        "output": str(output_dir),
    }


def real_fixture_args(*, exact_palette: bool) -> SimpleNamespace:
    return SimpleNamespace(
        mode="grid",
        crop=(0, 3, 729, 880),
        grid_size=(14, 16),
        cell_size=None,
        corners=None,
        cell_inset=0.20,
        palette=",".join(REAL_FIXTURE_PALETTE) if exact_palette else "unrestricted",
        max_colours=None if exact_palette else 8,
        background="transparent",
        background_colour="#F2F0EC",
        foreground_threshold=73.0,
        split_components=False,
        merge_gap=1,
        min_component_cells=1,
        padding=0,
        no_trim=False,
        preview_scale=8,
        indexed_png=False,
        diagnostics=True,
        fail_on_review=False,
    )


def semantic_cluster_purity(
    recovered: Sequence[tuple[int, int, int, int]],
    expected: Sequence[tuple[int, int, int, int]],
) -> float:
    clusters: dict[tuple[int, int, int, int], Counter[tuple[int, int, int, int]]] = {}
    visible = 0
    for actual, truth in zip(recovered, expected):
        if truth[3] == 0:
            continue
        visible += 1
        clusters.setdefault(actual, Counter())[truth] += 1
    correct = sum(counts.most_common(1)[0][1] for counts in clusters.values())
    return correct / visible if visible else 0.0


def run_real_fixture(root: Path) -> list[dict[str, object]]:
    fixtures = Path(__file__).resolve().parent.parent / "evals" / "fixtures"
    source = fixtures / "graph-paper-face-source.png"
    expected_path = fixtures / "graph-paper-face-expected.png"
    with Image.open(expected_path) as expected_image:
        expected = list(expected_image.convert("RGBA").getdata())
        expected_size = expected_image.size

    unknown_output = root / "real-graph-paper-face-unknown-palette"
    unknown_report = extractor.extract_one(
        source, unknown_output, real_fixture_args(exact_palette=False)
    )
    unknown_path = unknown_output / unknown_report["outputs"][0]["canonical"]
    unknown = decode(unknown_path)
    width, height = expected_size

    def at(
        pixels: Sequence[tuple[int, int, int, int]], x: int, y: int
    ) -> tuple[int, int, int, int]:
        return pixels[y * width + x]

    purity = semantic_cluster_purity(unknown, expected)
    unknown_classification = unknown_report["classification"]
    unknown_checks = {
        "expected_size": unknown_report["outputs"][0]["size"] == [width, height],
        "occupancy_preserved": all(
            (actual[3] > 0) == (truth[3] > 0)
            for actual, truth in zip(unknown, expected)
        ),
        "rare_semantic_colours_preserved": (
            at(unknown, 10, 9) != at(unknown, 0, 8)
            and len({at(unknown, x, 11) for x in (4, 5, 6)}) == 1
            and at(unknown, 5, 11) != at(unknown, 5, 8)
            and at(unknown, 2, 6) != at(unknown, 1, 6)
        ),
        "semantic_cluster_purity_at_least_95_percent": purity >= 0.95,
        "physical_palette_is_an_estimate": (
            unknown_classification["palette_recovery"]
            == "observed-physical-media-estimate"
            and not unknown_classification["colour_reduction"][
                "original_ink_values_recoverable"
            ]
        ),
        "unknown_physical_palette_requires_review": (
            unknown_report["status"] == "needs_review"
            and unknown_classification["review_required"]
        ),
    }

    exact_output = root / "real-graph-paper-face-exact-palette"
    exact_report = extractor.extract_one(
        source, exact_output, real_fixture_args(exact_palette=True)
    )
    exact_path = exact_output / exact_report["outputs"][0]["canonical"]
    exact = decode(exact_path)
    exact_accuracy = sum(
        actual == truth for actual, truth in zip(exact, expected)
    ) / len(expected)
    palette_ambiguous = {
        tuple(cell)
        for cell in exact_report["classification"][
            "palette_ambiguous_source_cells_zero_based"
        ]
    }
    exact_checks = {
        "occupancy_preserved": all(
            (actual[3] > 0) == (truth[3] > 0) for actual, truth in zip(exact, expected)
        ),
        "exact_accuracy_at_least_98_percent": exact_accuracy >= 0.98,
        "ambiguous_lips_reported_cell_by_cell": {
            (5, 12),
            (6, 12),
            (7, 12),
        }.issubset(palette_ambiguous),
        "ambiguous_exact_palette_requires_review": (
            exact_report["status"] == "needs_review"
            and exact_report["classification"]["review_required"]
        ),
    }
    return [
        {
            "name": "real-graph-paper-face-unknown-palette",
            "status": unknown_report["status"],
            "passed": all(unknown_checks.values()),
            "semantic_cluster_purity": round(purity, 6),
            "checks": unknown_checks,
            "output": str(unknown_output),
        },
        {
            "name": "real-graph-paper-face-exact-palette",
            "status": exact_report["status"],
            "passed": all(exact_checks.values()),
            "accuracy": round(exact_accuracy, 6),
            "checks": exact_checks,
            "output": str(exact_output),
        },
    ]


def run_suite(root: Path) -> dict[str, object]:
    extractor.write_json(root / "ground-truth.pixel-art.json", ground_truth_data())
    chart = render_chart()
    clean = discolour_and_noise(chart, seed=100, amount=3)
    partial_coverage = discolour_and_noise(
        render_chart(mixed_coverage=True), seed=150, amount=3
    )
    cross_ink_overrun = discolour_and_noise(
        add_cross_ink_overrun(render_chart()), seed=175, amount=3
    )
    off_centre_source, placements = render_off_centre_chart()
    off_centre = discolour_and_noise(off_centre_source, seed=180, amount=3)
    off_centre_cross_ink = discolour_and_noise(
        add_off_centre_cross_ink_overrun(off_centre_source), seed=185, amount=3
    )

    rotated_quad = ((66.0, 49.0), (432.0, 31.0), (447.0, 320.0), (51.0, 338.0))
    rotated = discolour_and_noise(
        warp_chart(chart, rotated_quad, (500, 370)), seed=200, amount=7
    )

    perspective_quad = ((81.0, 63.0), (421.0, 91.0), (454.0, 321.0), (42.0, 348.0))
    compound = discolour_and_noise(
        warp_chart(chart, perspective_quad, (510, 390)), seed=300, amount=12
    )
    draw = ImageDraw.Draw(compound)
    draw.line((12, 177, 493, 181), fill=(103, 144, 157), width=2)
    draw.line((247, 9, 252, 374), fill=(118, 158, 169), width=2)

    cases = [
        run_case(
            root,
            "discoloured-noisy-grid",
            clean,
            None,
            automatic=True,
            indexed_png=True,
        ),
        run_case(
            root,
            "partial-coverage-warm-paper",
            partial_coverage,
            None,
            foreground_threshold=60.0,
        ),
        run_case(root, "cross-ink-overrun", cross_ink_overrun, None),
        run_case(
            root,
            "off-centre-partial-coverage",
            off_centre,
            None,
            expect_partial_coverage=True,
            source_checks={
                "independent_cell_offsets_exercised": (
                    len(
                        {
                            (horizontal, vertical)
                            for horizontal, vertical, _ in placements
                        }
                    )
                    >= len(placements) // 2
                    and len({horizontal for horizontal, _, _ in placements}) >= 7
                    and len({vertical for _, vertical, _ in placements}) >= 7
                )
            },
        ),
        run_case(
            root,
            "off-centre-cross-ink-overrun",
            off_centre_cross_ink,
            None,
            expect_cross_ink_correction=True,
            source_checks={
                "independent_cell_offsets_exercised": (
                    len(
                        {
                            (horizontal, vertical)
                            for horizontal, vertical, _ in placements
                        }
                    )
                    >= len(placements) // 2
                )
            },
        ),
        run_case(root, "rotated-noisy-grid", rotated, rotated_quad),
        run_case(root, "perspective-lines-colour-noise", compound, perspective_quad),
        *run_real_fixture(root),
    ]
    passed = all(case["passed"] for case in cases)
    result = {
        "suite": "pixel-art-extraction-round-trip/v1",
        "seeded": True,
        "passed": passed,
        "synthetic_required_accuracy": 1.0,
        "real_unknown_minimum_semantic_cluster_purity": 0.95,
        "real_exact_minimum_accuracy": 0.98,
        "cases": cases,
    }
    (root / "round-trip-report.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep", type=Path, help="retain generated sources and diagnostics here"
    )
    args = parser.parse_args()
    if args.keep:
        if args.keep.exists() and any(args.keep.iterdir()):
            parser.error("--keep must name a new or empty directory")
        args.keep.mkdir(parents=True, exist_ok=True)
        result = run_suite(args.keep)
    else:
        with tempfile.TemporaryDirectory(
            prefix="pixel-art-extraction-round-trip-"
        ) as temporary:
            result = run_suite(Path(temporary))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
