#!/usr/bin/env python3
"""Deterministically recover logical pixel cells from raster observations."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat
except ImportError as exc:  # pragma: no cover - depends on the host environment
    raise SystemExit(
        "This script requires Pillow: python -m pip install Pillow"
    ) from exc


ART_FORMAT = "pixel-art/v1"
REPORT_FORMAT = "pixel-art-extraction-report/v1"
IMAGE_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
HEX_RGB = re.compile(r"^#[0-9A-Fa-f]{6}$")
PALETTE_ALIASES = {
    "black-white": ("#000000", "#FFFFFF"),
    "black-and-white": ("#000000", "#FFFFFF"),
    "bw": ("#000000", "#FFFFFF"),
    "monochrome": ("#000000", "#FFFFFF"),
}


class ExtractionError(RuntimeError):
    """Raised when an input cannot yield a defensible logical lattice."""


@dataclass(frozen=True)
class AxisEstimate:
    lines: list[int]
    period: float
    confidence: float
    evidence: str


@dataclass(frozen=True)
class Lattice:
    image: Image.Image
    x: AxisEstimate
    y: AxisEstimate
    mode: str
    explicit: bool


def parse_size(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*[xX,]\s*(\d+)\s*", value)
    if not match:
        raise argparse.ArgumentTypeError("expected WIDTHxHEIGHT")
    width, height = (int(part) for part in match.groups())
    if width < 1 or height < 1:
        raise argparse.ArgumentTypeError("dimensions must be positive")
    return width, height


def parse_pair(value: str) -> tuple[float, float]:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[xX,]\s*(\d+(?:\.\d+)?)\s*", value)
    if not match:
        raise argparse.ArgumentTypeError("expected XxY")
    x, y = (float(part) for part in match.groups())
    if x <= 0 or y <= 0:
        raise argparse.ArgumentTypeError("values must be positive")
    return x, y


def parse_crop(value: str) -> tuple[int, int, int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected LEFT,TOP,WIDTH,HEIGHT")
    try:
        left, top, width, height = (int(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("crop values must be integers") from exc
    if left < 0 or top < 0 or width < 1 or height < 1:
        raise argparse.ArgumentTypeError(
            "crop coordinates must be non-negative and dimensions positive"
        )
    return left, top, width, height


def parse_corners(value: str) -> tuple[float, ...]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 8:
        raise argparse.ArgumentTypeError(
            "expected TL_X,TL_Y,TR_X,TR_Y,BR_X,BR_Y,BL_X,BL_Y"
        )
    try:
        return tuple(float(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("corner coordinates must be numbers") from exc


def parse_colour(value: str) -> tuple[int, int, int]:
    if not HEX_RGB.fullmatch(value):
        raise argparse.ArgumentTypeError("colours must use #RRGGBB")
    return tuple(bytes.fromhex(value[1:]))  # type: ignore[return-value]


def parse_palette(value: str | None) -> list[tuple[int, int, int]] | None:
    if value is None or value.strip().lower() in {"", "none", "unrestricted"}:
        return None
    raw = PALETTE_ALIASES.get(
        value.strip().lower(),
        tuple(part.strip() for part in value.split(",") if part.strip()),
    )
    colours: list[tuple[int, int, int]] = []
    for item in raw:
        colour = parse_colour(item)
        if colour not in colours:
            colours.append(colour)
    if not colours:
        raise argparse.ArgumentTypeError("palette must contain at least one colour")
    if len(colours) > 256:
        raise argparse.ArgumentTypeError("exact palettes are limited to 256 colours")
    return colours


def moving_average(values: Sequence[float], radius: int) -> list[float]:
    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)
    result: list[float] = []
    for index in range(len(values)):
        left = max(0, index - radius)
        right = min(len(values), index + radius + 1)
        result.append((prefix[right] - prefix[left]) / (right - left))
    return result


def robust_scale(values: Sequence[float]) -> tuple[float, float]:
    centre = statistics.median(values)
    spread = statistics.median(abs(value - centre) for value in values)
    return centre, max(spread, 1e-6)


def autocorrelation_period(values: Sequence[float]) -> tuple[float, float]:
    if len(values) < 20:
        return 0.0, 0.0
    baseline = moving_average(values, 4)
    signal = [value - base for value, base in zip(values, baseline)]
    maximum = min(96, len(signal) // 4)
    scored: list[tuple[int, float]] = []
    for lag in range(3, maximum + 1):
        first = signal[:-lag]
        second = signal[lag:]
        numerator = sum(a * b for a, b in zip(first, second))
        denominator = math.sqrt(sum(a * a for a in first) * sum(b * b for b in second))
        scored.append((lag, numerator / denominator if denominator else 0.0))
    best_score = max((score for _, score in scored), default=0.0)
    if best_score < 0.10:
        return 0.0, max(0.0, best_score)
    eligible = [
        lag for lag, score in scored if score >= best_score * 0.84 and score >= 0.10
    ]
    return float(min(eligible)), best_score


def fit_axis_lines(
    values: Sequence[float], period: float, correlation: float
) -> AxisEstimate:
    if period < 3:
        return AxisEstimate([], 0.0, 0.0, "none")
    smooth = moving_average(values, 1)
    centre, spread = robust_scale(smooth)
    threshold = centre + 0.35 * spread
    candidates = [
        index
        for index in range(1, len(smooth) - 1)
        if smooth[index] >= threshold
        and smooth[index] >= smooth[index - 1]
        and smooth[index] >= smooth[index + 1]
    ]
    candidates.sort(key=lambda index: smooth[index], reverse=True)
    separated: list[int] = []
    minimum_gap = max(2, round(period * 0.42))
    for candidate in candidates:
        if all(abs(candidate - chosen) >= minimum_gap for chosen in separated):
            separated.append(candidate)
    separated.sort()
    if len(separated) < 4:
        return AxisEstimate([], period, 0.0, "periodic projection")

    best_matches: dict[int, int] = {}
    best_weight = -1.0
    for anchor in sorted(separated, key=lambda index: smooth[index], reverse=True)[:24]:
        matches: dict[int, int] = {}
        weight = 0.0
        for position in separated:
            lattice_index = round((position - anchor) / period)
            error = abs(position - (anchor + lattice_index * period))
            if error <= period * 0.28:
                previous = matches.get(lattice_index)
                if previous is None or smooth[position] > smooth[previous]:
                    matches[lattice_index] = position
        for position in matches.values():
            weight += max(0.0, smooth[position] - centre)
        if len(matches) >= 4 and (len(matches), weight) > (
            len(best_matches),
            best_weight,
        ):
            best_matches = matches
            best_weight = weight
    if len(best_matches) < 4:
        return AxisEstimate([], period, 0.0, "periodic projection")

    indices = list(best_matches)
    positions = [best_matches[index] for index in indices]
    mean_index = statistics.fmean(indices)
    mean_position = statistics.fmean(positions)
    denominator = sum((index - mean_index) ** 2 for index in indices)
    fitted_period = (
        sum(
            (index - mean_index) * (position - mean_position)
            for index, position in zip(indices, positions)
        )
        / denominator
        if denominator
        else period
    )
    fitted_origin = mean_position - fitted_period * mean_index
    if fitted_period < 2:
        return AxisEstimate([], period, 0.0, "periodic projection")

    lower, upper = min(indices), max(indices)
    predicted: list[int] = []
    snap_radius = max(1, round(fitted_period * 0.24))
    for lattice_index in range(lower, upper + 1):
        location = round(fitted_origin + fitted_period * lattice_index)
        left = max(0, location - snap_radius)
        right = min(len(smooth) - 1, location + snap_radius)
        snapped = max(range(left, right + 1), key=lambda index: smooth[index])
        predicted.append(snapped)
    predicted = sorted(set(predicted))
    if len(predicted) < 4:
        return AxisEstimate([], fitted_period, 0.0, "periodic projection")

    if predicted[0] <= fitted_period * 1.35:
        previous = max(0, round(predicted[0] - fitted_period))
        if previous < predicted[0]:
            predicted.insert(0, previous)
    remaining = len(values) - predicted[-1]
    if remaining <= fitted_period * 1.35:
        following = min(len(values), round(predicted[-1] + fitted_period))
        if following > predicted[-1]:
            predicted.append(following)

    expected = upper - lower + 1
    coverage = min(1.0, len(best_matches) / expected)
    residuals = [
        abs(position - (fitted_origin + fitted_period * index))
        for index, position in best_matches.items()
    ]
    regularity = max(0.0, 1.0 - statistics.fmean(residuals) / (fitted_period * 0.35))
    confidence = max(0.0, min(1.0, correlation * (0.55 + 0.45 * coverage) * regularity))
    return AxisEstimate(predicted, fitted_period, confidence, "periodic projection")


def feature_images(image: Image.Image, embroidery: bool) -> dict[str, Image.Image]:
    rgb = image.convert("RGB")
    red, green, blue = rgb.split()
    cyan = ImageChops.subtract(ImageChops.add(green, blue, scale=2.0), red)
    grey = ImageOps.grayscale(rgb)
    darkness = grey.point(lambda value: min(255 - value, 72) * 3)
    features = {"chromatic-lines": cyan, "clipped-darkness": darkness}
    if embroidery:
        edges = grey.filter(ImageFilter.FIND_EDGES).point(
            lambda value: min(value, 96) * 2
        )
        features["texture-edges"] = edges
    return features


def projection(feature: Image.Image, axis: str) -> list[float]:
    if axis == "x":
        reduced = feature.resize((feature.width, 1), Image.Resampling.BOX)
    else:
        reduced = feature.resize((1, feature.height), Image.Resampling.BOX)
    return [float(value) for value in reduced.getdata()]


def estimate_axis(features: dict[str, Image.Image], axis: str) -> AxisEstimate:
    estimates: list[AxisEstimate] = []
    for evidence, feature in features.items():
        values = projection(feature, axis)
        period, correlation = autocorrelation_period(values)
        estimate = fit_axis_lines(values, period, correlation)
        estimates.append(
            AxisEstimate(estimate.lines, estimate.period, estimate.confidence, evidence)
        )
    return max(estimates, key=lambda estimate: estimate.confidence)


def scale_axis(estimate: AxisEstimate, factor: float, maximum: int) -> AxisEstimate:
    lines = sorted(
        set(max(0, min(maximum, round(value * factor))) for value in estimate.lines)
    )
    return AxisEstimate(
        lines, estimate.period * factor, estimate.confidence, estimate.evidence
    )


def uniform_lines(length: int, cells: int) -> list[int]:
    lines = [round(index * length / cells) for index in range(cells + 1)]
    if len(set(lines)) != len(lines):
        raise ExtractionError("the requested grid has more cells than source pixels")
    return lines


def cell_size_lines(length: int, size: float) -> list[int]:
    count = int(length / size)
    if count < 1:
        raise ExtractionError("cell size is larger than the source")
    used = count * size
    offset = (length - used) / 2
    lines = [round(offset + index * size) for index in range(count + 1)]
    return sorted(set(lines))


def solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    size = len(vector)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-10:
            raise ExtractionError(
                "the supplied corners do not define a usable quadrilateral"
            )
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


def perspective_coefficients(
    output_size: tuple[int, int], source_corners: Sequence[tuple[float, float]]
) -> tuple[float, ...]:
    width, height = output_size
    output_corners = (
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    )
    matrix: list[list[float]] = []
    vector: list[float] = []
    for (u, v), (x, y) in zip(output_corners, source_corners):
        matrix.append([u, v, 1, 0, 0, 0, -x * u, -x * v])
        vector.append(x)
        matrix.append([0, 0, 0, u, v, 1, -y * u, -y * v])
        vector.append(y)
    return tuple(solve_linear(matrix, vector))


def rectify_corners(
    image: Image.Image, corners: tuple[float, ...], grid_size: tuple[int, int]
) -> Image.Image:
    tlx, tly, trx, try_, brx, bry, blx, bly = corners
    columns, rows = grid_size
    cell_pixels = 16
    output_size = (columns * cell_pixels, rows * cell_pixels)
    coefficients = perspective_coefficients(
        output_size,
        ((tlx, tly), (trx, try_), (brx, bry), (blx, bly)),
    )
    return image.transform(
        output_size,
        Image.Transform.PERSPECTIVE,
        coefficients,
        Image.Resampling.BICUBIC,
    )


def estimate_lattice(image: Image.Image, args: argparse.Namespace) -> Lattice:
    if args.corners:
        if not args.grid_size:
            raise ExtractionError("--corners requires --grid-size")
        image = rectify_corners(image, args.corners, args.grid_size)
        columns, rows = args.grid_size
        x_lines = uniform_lines(image.width, columns)
        y_lines = uniform_lines(image.height, rows)
        explicit = AxisEstimate(
            x_lines, image.width / columns, 1.0, "supplied corners and grid size"
        )
        explicit_y = AxisEstimate(
            y_lines, image.height / rows, 1.0, "supplied corners and grid size"
        )
        return Lattice(image, explicit, explicit_y, args.mode, True)

    if args.grid_size:
        columns, rows = args.grid_size
        x_lines = uniform_lines(image.width, columns)
        y_lines = uniform_lines(image.height, rows)
        return Lattice(
            image,
            AxisEstimate(x_lines, image.width / columns, 1.0, "supplied grid size"),
            AxisEstimate(y_lines, image.height / rows, 1.0, "supplied grid size"),
            args.mode,
            True,
        )

    if args.cell_size:
        cell_width, cell_height = args.cell_size
        return Lattice(
            image,
            AxisEstimate(
                cell_size_lines(image.width, cell_width),
                cell_width,
                1.0,
                "supplied cell size",
            ),
            AxisEstimate(
                cell_size_lines(image.height, cell_height),
                cell_height,
                1.0,
                "supplied cell size",
            ),
            args.mode,
            True,
        )

    requested_mode = args.mode
    if requested_mode == "native" and max(image.size) <= 256:
        return Lattice(
            image,
            AxisEstimate(
                list(range(image.width + 1)), 1.0, 1.0, "native source pixels"
            ),
            AxisEstimate(
                list(range(image.height + 1)), 1.0, 1.0, "native source pixels"
            ),
            "native",
            True,
        )

    scale = min(1.0, 1400 / max(image.size))
    analysis = (
        image
        if scale == 1.0
        else image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.BILINEAR,
        )
    )

    modes = (
        [requested_mode]
        if requested_mode != "auto"
        else ["grid", "embroidery", "native"]
    )
    candidates: list[tuple[float, str, AxisEstimate, AxisEstimate]] = []
    for mode in modes:
        if mode == "native" and max(image.size) <= 256:
            x = AxisEstimate(
                list(range(image.width + 1)), 1.0, 1.0, "native source pixels"
            )
            y = AxisEstimate(
                list(range(image.height + 1)), 1.0, 1.0, "native source pixels"
            )
            return Lattice(image, x, y, mode, True)
        features = feature_images(analysis, embroidery=mode in {"embroidery", "native"})
        if mode == "native":
            grey = ImageOps.grayscale(analysis)
            features = {"native-edges": grey.filter(ImageFilter.FIND_EDGES)}
        x_small = estimate_axis(features, "x")
        y_small = estimate_axis(features, "y")
        score = math.sqrt(x_small.confidence * y_small.confidence)
        candidates.append((score, mode, x_small, y_small))

    score, mode, x_small, y_small = max(candidates, key=lambda item: item[0])
    if not x_small.lines or not y_small.lines:
        raise ExtractionError(
            "no defensible lattice was found; supply --grid-size, --cell-size, or --corners"
        )
    x = scale_axis(x_small, 1 / scale, image.width)
    y = scale_axis(y_small, 1 / scale, image.height)
    if len(x.lines) < 2 or len(y.lines) < 2:
        raise ExtractionError("the inferred lattice contains no cells")
    return Lattice(image, x, y, mode, False)


def median_rgba(image: Image.Image) -> tuple[int, int, int, int]:
    median = ImageStat.Stat(image.convert("RGBA")).median
    return tuple(int(value) for value in median)  # type: ignore[return-value]


def cell_boxes(lattice: Lattice, inset: float) -> Iterable[tuple[int, int, int, int]]:
    """Yield the inset sampling box for every logical cell in row-major order."""
    x_lines, y_lines = lattice.x.lines, lattice.y.lines
    for row in range(len(y_lines) - 1):
        top, bottom = y_lines[row], y_lines[row + 1]
        for column in range(len(x_lines) - 1):
            left, right = x_lines[column], x_lines[column + 1]
            dx = max(0, round((right - left) * inset))
            dy = max(0, round((bottom - top) * inset))
            yield (
                min(right - 1, left + dx),
                min(bottom - 1, top + dy),
                max(left + 1, right - dx),
                max(top + 1, bottom - dy),
            )


def sample_cells(
    lattice: Lattice, inset: float
) -> tuple[list[tuple[int, int, int, int]], int, int]:
    x_lines, y_lines = lattice.x.lines, lattice.y.lines
    columns, rows = len(x_lines) - 1, len(y_lines) - 1
    samples = [
        median_rgba(lattice.image.crop(box)) for box in cell_boxes(lattice, inset)
    ]
    return samples, columns, rows


def strongest_cell_colours(
    lattice: Lattice,
    inset: float,
    background: Sequence[int],
    fraction: float = 0.20,
) -> list[tuple[int, int, int]]:
    """Keep a second, strongly covered colour observation for every cell.

    A single cell median is robust for occupancy, but it folds paper, incomplete
    coverage, and lighting into the putative ink colour. The most distant fifth
    of the inset pixels retains evidence from the strongest part of the mark.
    It remains an observed colour rather than a claim about the original ink.
    """
    observations: list[tuple[int, int, int]] = []
    for box in cell_boxes(lattice, inset):
        pixels = [
            pixel[:3]
            for pixel in lattice.image.crop(box).convert("RGBA").getdata()
            if pixel[3] >= 128
        ]
        if not pixels:
            observations.append((0, 0, 0))
            continue
        pixels.sort(
            key=lambda colour: colour_distance(colour, background), reverse=True
        )
        retained = pixels[: max(1, round(len(pixels) * fraction))]
        observations.append(
            tuple(
                round(statistics.median(colour[channel] for colour in retained))
                for channel in range(3)
            )  # type: ignore[arg-type]
        )
    return observations


def colour_distance(first: Sequence[int], second: Sequence[int]) -> float:
    return math.sqrt(sum((int(a) - int(b)) ** 2 for a, b in zip(first[:3], second[:3])))


def modal_background(
    samples: Sequence[tuple[int, int, int, int]], width: int, height: int
) -> tuple[int, int, int]:
    border_indices = {
        index
        for index in range(width * height)
        if index // width in {0, height - 1} or index % width in {0, width - 1}
    }
    border = [samples[index] for index in sorted(border_indices)]

    def bin_colour(colour: Sequence[int]) -> tuple[int, int, int]:
        return tuple(min(255, round(channel / 16) * 16) for channel in colour[:3])  # type: ignore[return-value]

    border_counts = Counter(bin_colour(colour) for colour in border if colour[3] > 0)
    population = border
    if not border_counts or border_counts.most_common(1)[0][1] < max(
        2, len(border) * 0.35
    ):
        population = list(samples)
    counts = Counter(bin_colour(colour) for colour in population if colour[3] > 0)
    if not counts:
        return (0, 0, 0)
    winning_bin = counts.most_common(1)[0][0]
    members = [
        colour
        for colour in population
        if colour[3] > 0 and bin_colour(colour) == winning_bin
    ]
    return tuple(
        int(statistics.median(colour[channel] for colour in members))
        for channel in range(3)
    )  # type: ignore[return-value]


def otsu_threshold(distances: Sequence[float]) -> float:
    histogram = [0] * 442
    for distance in distances:
        histogram[min(441, max(0, round(distance)))] += 1
    total = sum(histogram)
    if total == 0:
        return 0.0
    weighted_total = sum(index * count for index, count in enumerate(histogram))
    background_weight = 0
    background_sum = 0.0
    best_variance = -1.0
    best_threshold = 0
    for threshold, count in enumerate(histogram):
        background_weight += count
        if background_weight == 0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break
        background_sum += threshold * count
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_total - background_sum) / foreground_weight
        variance = (
            background_weight
            * foreground_weight
            * (background_mean - foreground_mean) ** 2
        )
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return float(best_threshold)


def reduce_colours(
    colours: Sequence[tuple[int, int, int]], maximum: int
) -> list[tuple[int, int, int]]:
    if len(set(colours)) <= maximum:
        return list(colours)
    strip = Image.new("RGB", (len(colours), 1))
    strip.putdata(colours)
    reduced = strip.quantize(
        colors=maximum, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    ).convert("RGB")
    return [tuple(colour) for colour in reduced.getdata()]


def rgb_quantisation_diagnostics(
    observed: Sequence[tuple[int, int, int]],
    mapped: Sequence[tuple[int, int, int]],
) -> tuple[list[int], dict[str, Any]]:
    representatives = sorted(set(mapped))
    counts = Counter(mapped)
    errors = [
        colour_distance(colour, mapped_colour)
        for colour, mapped_colour in zip(observed, mapped)
    ]
    ambiguous: list[int] = []
    margins: list[float] = []
    for index, colour in enumerate(observed):
        distances = sorted(
            colour_distance(colour, candidate) for candidate in representatives
        )
        margin = distances[1] - distances[0] if len(distances) > 1 else math.inf
        margins.append(margin)
        if margin < 4.0:
            ambiguous.append(index)
    rare_limit = max(2, math.ceil(len(observed) * 0.02))
    return ambiguous, {
        "method": "median-cut-rgb",
        "cell_evidence": "median",
        "inferred_colours": len(representatives),
        "cluster_sizes": sorted(counts.values()),
        "rare_cluster_limit": rare_limit,
        "rare_clusters": sum(size <= rare_limit for size in counts.values()),
        "mean_observed_rgb_error": round(statistics.fmean(errors), 3),
        "maximum_observed_rgb_error": round(max(errors), 3),
        "minimum_assignment_margin": round(min(margins), 3),
        "original_ink_values_recoverable": True,
    }


def substrate_ray(
    colour: Sequence[int], background: Sequence[int]
) -> tuple[float, float, float]:
    direction = tuple(
        float(colour[channel] - background[channel]) for channel in range(3)
    )
    magnitude = math.sqrt(sum(value * value for value in direction))
    if magnitude < 1e-9:
        return (0.0, 0.0, 0.0)
    return tuple(value / magnitude for value in direction)  # type: ignore[return-value]


def squared_vector_distance(first: Sequence[float], second: Sequence[float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(first, second))


def physical_colour_reduction(
    observed: Sequence[tuple[int, int, int]],
    strongest: Sequence[tuple[int, int, int]],
    maximum: int,
    background: Sequence[int],
) -> tuple[list[tuple[int, int, int]], list[int], dict[str, Any]]:
    """Cluster physical-media samples by their direction away from the substrate.

    Median-cut in RGB space spends entries on common coverage and lighting
    variants. Farthest-first ray seeds retain chromatically distinct rare marks;
    deterministic Lloyd iterations then consolidate nearby observations. Output
    colours are robust observed estimates, not reconstructed original ink values.
    """
    if len(observed) != len(strongest):
        raise ExtractionError("internal colour evidence length mismatch")
    features = [substrate_ray(colour, background) for colour in strongest]
    unique_indices: list[int] = []
    seen_features: set[tuple[float, float, float]] = set()
    for index, feature in enumerate(features):
        key = tuple(round(value, 12) for value in feature)
        if key not in seen_features:
            seen_features.add(key)
            unique_indices.append(index)
    cluster_count = min(maximum, len(unique_indices))
    if cluster_count < 1:
        raise ExtractionError(
            "no physical colour evidence remains after substrate removal"
        )

    first_seed = max(
        unique_indices,
        key=lambda index: (colour_distance(strongest[index], background), -index),
    )
    seed_indices = [first_seed]
    while len(seed_indices) < cluster_count:
        seed_indices.append(
            max(
                (index for index in unique_indices if index not in seed_indices),
                key=lambda index: (
                    min(
                        squared_vector_distance(features[index], features[seed])
                        for seed in seed_indices
                    ),
                    -index,
                ),
            )
        )

    centres = [features[index] for index in seed_indices]
    assignments: list[int] = []
    for _iteration in range(50):
        updated_assignments = [
            min(
                range(cluster_count),
                key=lambda cluster: (
                    squared_vector_distance(feature, centres[cluster]),
                    cluster,
                ),
            )
            for feature in features
        ]
        if updated_assignments == assignments:
            break
        assignments = updated_assignments
        updated_centres: list[tuple[float, float, float]] = []
        for cluster in range(cluster_count):
            members = [
                features[index]
                for index, assignment in enumerate(assignments)
                if assignment == cluster
            ]
            if not members:
                updated_centres.append(centres[cluster])
                continue
            updated_centres.append(
                tuple(
                    sum(member[channel] for member in members) / len(members)
                    for channel in range(3)
                )  # type: ignore[arg-type]
            )
        centres = updated_centres

    representatives: list[tuple[int, int, int]] = []
    cluster_sizes: list[int] = []
    for cluster in range(cluster_count):
        members = [
            strongest[index]
            for index, assignment in enumerate(assignments)
            if assignment == cluster
        ]
        cluster_sizes.append(len(members))
        representatives.append(
            tuple(
                round(statistics.median(colour[channel] for colour in members))
                for channel in range(3)
            )  # type: ignore[arg-type]
        )

    mapped = [representatives[assignment] for assignment in assignments]
    margins: list[float] = []
    residuals: list[float] = []
    ambiguous: list[int] = []
    for index, (feature, assignment) in enumerate(zip(features, assignments)):
        distances = sorted(
            math.sqrt(squared_vector_distance(feature, centre)) for centre in centres
        )
        residuals.append(distances[0])
        margin = distances[1] - distances[0] if len(distances) > 1 else math.inf
        margins.append(margin)
        if margin < 0.015:
            ambiguous.append(index)

    rgb_errors = [
        colour_distance(colour, mapped_colour)
        for colour, mapped_colour in zip(observed, mapped)
    ]
    rare_limit = max(2, math.ceil(len(observed) * 0.02))
    diagnostics = {
        "method": "substrate-ray-clustering",
        "cell_evidence": "median-and-strongest-20-percent",
        "requested_maximum": maximum,
        "inferred_colours": cluster_count,
        "cluster_sizes": sorted(cluster_sizes),
        "rare_cluster_limit": rare_limit,
        "rare_clusters": sum(size <= rare_limit for size in cluster_sizes),
        "mean_ray_residual": round(statistics.fmean(residuals), 6),
        "maximum_ray_residual": round(max(residuals), 6),
        "mean_observed_rgb_error": round(statistics.fmean(rgb_errors), 3),
        "maximum_observed_rgb_error": round(max(rgb_errors), 3),
        "minimum_assignment_margin": round(min(margins), 6),
        "original_ink_values_recoverable": False,
    }
    return mapped, ambiguous, diagnostics


def mixture_palette_choice(
    sample: Sequence[int],
    background: Sequence[int],
    palette: Sequence[tuple[int, int, int]],
) -> tuple[tuple[int, int, int], float, float]:
    """Choose the ink whose substrate-to-ink mixture best explains a sample."""
    scored: list[tuple[float, tuple[int, int, int], float]] = []
    observed = [float(sample[channel] - background[channel]) for channel in range(3)]
    for ink in palette:
        direction = [float(ink[channel] - background[channel]) for channel in range(3)]
        magnitude = sum(value * value for value in direction)
        coverage = (
            sum(value * axis for value, axis in zip(observed, direction)) / magnitude
            if magnitude
            else 1.0
        )
        coverage = max(0.0, min(1.0, coverage))
        fitted = [
            background[channel] + coverage * direction[channel] for channel in range(3)
        ]
        residual = math.sqrt(
            sum((sample[channel] - fitted[channel]) ** 2 for channel in range(3))
        )
        # The residual measures hue direction. A small endpoint term resolves nearly
        # parallel ink rays in favour of the observed solid colour at high coverage.
        score = residual + 0.02 * colour_distance(sample, ink)
        scored.append((score, ink, coverage))
    scored.sort(key=lambda item: (item[0], item[1]))
    best_score, best_ink, best_coverage = scored[0]
    margin = scored[1][0] - best_score if len(scored) > 1 else math.inf
    return best_ink, best_coverage, margin


def cross_ink_palette_choice(
    sample: Sequence[int],
    background: Sequence[int],
    palette: Sequence[tuple[int, int, int]],
    current: tuple[int, int, int],
) -> tuple[tuple[int, int, int], float] | None:
    """Find a lighter dominant ink hidden by a smaller darker overrun."""

    # If the one-ink model already selected the darkest available ink, there is
    # no still-darker palette mark to explain as overrun. Leaving these cells
    # alone also protects pale and antialiased boundaries of dark artwork.
    if (
        colour_distance(current, background)
        >= max(colour_distance(ink, background) for ink in palette) - 1e-9
    ):
        return None

    observed = [float(sample[channel] - background[channel]) for channel in range(3)]

    direction = [float(current[channel] - background[channel]) for channel in range(3)]
    magnitude = sum(value * value for value in direction)
    coverage = (
        sum(value * axis for value, axis in zip(observed, direction)) / magnitude
        if magnitude
        else 1.0
    )
    coverage = max(0.0, min(1.0, coverage))
    fitted = [
        background[channel] + coverage * direction[channel] for channel in range(3)
    ]
    single_score = math.sqrt(
        sum((sample[channel] - fitted[channel]) ** 2 for channel in range(3))
    ) + 0.02 * colour_distance(sample, current)

    best: tuple[float, tuple[int, int, int]] | None = None
    for first_index, first in enumerate(palette):
        first_direction = [
            float(first[channel] - background[channel]) for channel in range(3)
        ]
        for second in palette[first_index + 1 :]:
            second_direction = [
                float(second[channel] - background[channel]) for channel in range(3)
            ]
            first_squared = sum(value * value for value in first_direction)
            second_squared = sum(value * value for value in second_direction)
            cross = sum(
                first_axis * second_axis
                for first_axis, second_axis in zip(first_direction, second_direction)
            )
            determinant = first_squared * second_squared - cross * cross
            if abs(determinant) < 1e-9:
                continue
            first_observed = sum(
                value * axis for value, axis in zip(observed, first_direction)
            )
            second_observed = sum(
                value * axis for value, axis in zip(observed, second_direction)
            )
            first_coverage = (
                first_observed * second_squared - second_observed * cross
            ) / determinant
            second_coverage = (
                second_observed * first_squared - first_observed * cross
            ) / determinant

            # A small overlap is expected at hand-drawn boundaries. Allow modest
            # overprint (sum above one), but reject unconstrained colour mixtures.
            if not (
                0.05 <= first_coverage <= 1.0
                and 0.05 <= second_coverage <= 1.0
                and first_coverage + second_coverage <= 1.25
            ):
                continue
            if max(first_coverage, second_coverage) < 1.08 * min(
                first_coverage, second_coverage
            ):
                continue

            dominant, dominant_coverage = (
                (first, first_coverage)
                if first_coverage > second_coverage
                else (second, second_coverage)
            )
            if dominant == current:
                continue
            # The correction is specifically for a light ink darkened by overrun.
            # It must not recolour a pale boundary of a genuinely dark mark.
            if colour_distance(dominant, background) >= colour_distance(
                current, background
            ):
                continue

            pair_fitted = [
                background[channel]
                + first_coverage * first_direction[channel]
                + second_coverage * second_direction[channel]
                for channel in range(3)
            ]
            residual = math.sqrt(
                sum(
                    (sample[channel] - pair_fitted[channel]) ** 2
                    for channel in range(3)
                )
            )
            pair_score = residual + 4.0
            improvement = single_score - pair_score
            if improvement < 8.0 or dominant_coverage < 0.40:
                continue
            candidate = (improvement, dominant)
            if best is None or candidate > best:
                best = candidate

    return (best[1], best[0]) if best is not None else None


def largest_orthogonal_group(indices: Sequence[int], width: int, height: int) -> int:
    remaining = set(indices)
    largest = 0
    while remaining:
        seed = remaining.pop()
        pending = [seed]
        size = 1
        while pending:
            current = pending.pop()
            row, column = divmod(current, width)
            for neighbour_row, neighbour_column in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                if not (0 <= neighbour_row < height and 0 <= neighbour_column < width):
                    continue
                neighbour = neighbour_row * width + neighbour_column
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    pending.append(neighbour)
                    size += 1
        largest = max(largest, size)
    return largest


def classify_cells(
    samples: Sequence[tuple[int, int, int, int]],
    width: int,
    height: int,
    lattice_mode: str,
    args: argparse.Namespace,
    lattice: Lattice | None = None,
) -> tuple[list[tuple[int, int, int, int]], dict[str, Any]]:
    background_mode = args.background
    if background_mode == "auto":
        background_mode = "keep" if lattice_mode == "native" else "transparent"

    exact_palette = parse_palette(args.palette)
    if exact_palette is not None and args.max_colours is not None:
        raise ExtractionError("use either --palette or --max-colours, not both")

    if args.background_colour:
        background_colour = parse_colour(args.background_colour)
    else:
        background_colour = modal_background(samples, width, height)
    distances = [colour_distance(sample, background_colour) for sample in samples]
    threshold = (
        float(args.foreground_threshold)
        if args.foreground_threshold is not None
        else max(10.0, otsu_threshold(distances))
    )

    transparent: list[bool] = []
    for sample, distance in zip(samples, distances):
        source_transparent = sample[3] < 128
        if background_mode == "keep":
            transparent.append(source_transparent)
        else:
            transparent.append(source_transparent or distance <= threshold)

    visible_rgb = [
        sample[:3] for sample, hidden in zip(samples, transparent) if not hidden
    ]
    if not visible_rgb:
        raise ExtractionError(
            "no foreground cells remain; check the grid, background colour, or foreground threshold"
        )
    palette_mapping = "none"
    palette_ambiguous_visible_indices: list[int] = []
    cross_ink_corrected_visible_indices: list[int] = []
    estimated_coverages: list[float] = []
    colour_reduction: dict[str, Any] | None = None
    palette_recovery = "sampled-observation"
    review_reasons: list[str] = []
    if exact_palette is not None:
        if background_mode == "transparent":
            choices = [
                mixture_palette_choice(colour, background_colour, exact_palette)
                for colour in visible_rgb
            ]
            mapped_rgb = [choice[0] for choice in choices]
            estimated_coverages = [choice[1] for choice in choices]
            palette_ambiguous_visible_indices = [
                index for index, choice in enumerate(choices) if choice[2] < 4.0
            ]
            visible_source_indices = [
                index for index, hidden in enumerate(transparent) if not hidden
            ]
            source_colours: list[tuple[int, int, int] | None] = [None] * len(samples)
            for source_index, colour in zip(visible_source_indices, mapped_rgb):
                source_colours[source_index] = colour
            corrected = list(mapped_rgb)
            for visible_index, (source_index, sample, current) in enumerate(
                zip(visible_source_indices, visible_rgb, mapped_rgb)
            ):
                candidate = cross_ink_palette_choice(
                    sample, background_colour, exact_palette, current
                )
                if candidate is None:
                    continue
                dominant, _improvement = candidate
                row, column = divmod(source_index, width)
                neighbour_support = 0
                for row_offset in (-1, 0, 1):
                    for column_offset in (-1, 0, 1):
                        if row_offset == 0 and column_offset == 0:
                            continue
                        neighbour_row = row + row_offset
                        neighbour_column = column + column_offset
                        if not (
                            0 <= neighbour_row < height
                            and 0 <= neighbour_column < width
                        ):
                            continue
                        neighbour_index = neighbour_row * width + neighbour_column
                        if source_colours[neighbour_index] == dominant:
                            neighbour_support += 1
                if neighbour_support < 2:
                    continue
                corrected[visible_index] = dominant
                cross_ink_corrected_visible_indices.append(visible_index)
            mapped_rgb = corrected
            palette_ambiguous_visible_indices = sorted(
                set(
                    palette_ambiguous_visible_indices
                    + cross_ink_corrected_visible_indices
                )
            )
            palette_mapping = "substrate-and-cross-ink-mixture"
            palette_recovery = "exact-supplied-palette"
        else:
            mapped_rgb = [
                min(
                    exact_palette,
                    key=lambda candidate: colour_distance(colour, candidate),
                )
                for colour in visible_rgb
            ]
            palette_mapping = "nearest-rgb"
            palette_recovery = "exact-supplied-palette"
        rule: dict[str, Any] = {
            "mode": "exact",
            "colours": [
                "#{:02X}{:02X}{:02X}".format(*colour) for colour in exact_palette
            ],
        }
    elif args.max_colours is not None:
        physical_media = background_mode == "transparent" and lattice_mode != "native"
        if physical_media and lattice is not None:
            strongest = strongest_cell_colours(
                lattice, args.cell_inset, background_colour
            )
            visible_strongest = [
                colour for colour, hidden in zip(strongest, transparent) if not hidden
            ]
            (
                mapped_rgb,
                palette_ambiguous_visible_indices,
                colour_reduction,
            ) = physical_colour_reduction(
                visible_rgb,
                visible_strongest,
                args.max_colours,
                background_colour,
            )
            palette_mapping = "substrate-ray-clustering"
            palette_recovery = "observed-physical-media-estimate"
            review_reasons.append(
                "maximum-colour physical-media extraction estimates observed marks; "
                "the original ink values require an exact palette or calibration"
            )
        else:
            mapped_rgb = reduce_colours(visible_rgb, args.max_colours)
            (
                palette_ambiguous_visible_indices,
                colour_reduction,
            ) = rgb_quantisation_diagnostics(visible_rgb, mapped_rgb)
            palette_mapping = "median-cut"
            palette_recovery = "observed-rgb-quantisation"
        rule = {"mode": "max", "count": args.max_colours}
    else:
        mapped_rgb = list(visible_rgb)
        palette_mapping = "sampled-rgb"
        rule = {"mode": "unrestricted"}

    mapped_iterator = iter(mapped_rgb)
    result: list[tuple[int, int, int, int]] = []
    for hidden in transparent:
        result.append((0, 0, 0, 0) if hidden else (*next(mapped_iterator), 255))

    margin = max(4.0, threshold * 0.20)
    threshold_ambiguous_indices = [
        index
        for index, distance in enumerate(distances)
        if abs(distance - threshold) <= margin
    ]
    visible_source_indices = [
        index for index, hidden in enumerate(transparent) if not hidden
    ]
    palette_ambiguous_indices = [
        visible_source_indices[index] for index in palette_ambiguous_visible_indices
    ]
    ambiguous_indices = sorted(
        set(threshold_ambiguous_indices + palette_ambiguous_indices)
    )
    ambiguous_fraction = len(ambiguous_indices) / len(distances)
    palette_ambiguous_fraction = (
        len(palette_ambiguous_indices) / len(visible_rgb) if visible_rgb else 0.0
    )
    largest_palette_ambiguous_group = largest_orthogonal_group(
        palette_ambiguous_indices, width, height
    )
    if (
        exact_palette is not None
        and palette_ambiguous_fraction > 0.05
        and largest_palette_ambiguous_group >= 3
    ):
        review_reasons.append(
            "a coherent region has materially ambiguous exact-palette assignments"
        )
    classification_confidence = max(
        0.0,
        min(
            1.0,
            1.0
            - len(threshold_ambiguous_indices) / len(distances) * 4.0
            - palette_ambiguous_fraction * 2.0,
        ),
    )
    details = {
        "background_mode": background_mode,
        "background_colour": "#{:02X}{:02X}{:02X}".format(*background_colour),
        "foreground_threshold": round(threshold, 3),
        "palette_mapping": palette_mapping,
        "palette_recovery": palette_recovery,
        "colour_reduction": colour_reduction,
        "palette_ambiguous_cells": len(palette_ambiguous_indices),
        "palette_ambiguous_fraction": round(palette_ambiguous_fraction, 6),
        "largest_palette_ambiguous_group": largest_palette_ambiguous_group,
        "cross_ink_corrected_cells": len(cross_ink_corrected_visible_indices),
        "median_estimated_ink_coverage": (
            round(statistics.median(estimated_coverages), 6)
            if estimated_coverages
            else None
        ),
        "ambiguous_cells": len(ambiguous_indices),
        "ambiguous_fraction": round(ambiguous_fraction, 6),
        "classification_confidence": round(classification_confidence, 6),
        "review_required": bool(review_reasons),
        "review_reasons": review_reasons,
        "threshold_ambiguous_source_cells_zero_based": [
            [index % width, index // width] for index in threshold_ambiguous_indices
        ],
        "palette_ambiguous_source_cells_zero_based": [
            [index % width, index // width] for index in palette_ambiguous_indices
        ],
        "colour_rule": rule,
        "ambiguous_indices": ambiguous_indices,
    }
    return result, details


def connected_groups(
    pixels: Sequence[tuple[int, int, int, int]], width: int, height: int, gap: int
) -> list[set[int]]:
    occupied = {index for index, colour in enumerate(pixels) if colour[3] > 0}
    groups: list[set[int]] = []
    radius = gap + 1
    while occupied:
        seed = occupied.pop()
        group = {seed}
        pending = deque([seed])
        while pending:
            current = pending.popleft()
            x, y = current % width, current // width
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < width and 0 <= ny < height):
                        continue
                    neighbour = ny * width + nx
                    if neighbour in occupied:
                        occupied.remove(neighbour)
                        group.add(neighbour)
                        pending.append(neighbour)
        groups.append(group)
    return sorted(groups, key=lambda group: min(group))


def crop_component(
    pixels: Sequence[tuple[int, int, int, int]],
    width: int,
    height: int,
    members: set[int],
    padding: int,
    trim: bool,
    restrict: bool,
) -> tuple[list[tuple[int, int, int, int]], int, int, tuple[int, int, int, int]]:
    if not members:
        raise ExtractionError("cannot crop an empty component")
    if trim:
        xs = [index % width for index in members]
        ys = [index // width for index in members]
        left = max(0, min(xs) - padding)
        top = max(0, min(ys) - padding)
        right = min(width, max(xs) + padding + 1)
        bottom = min(height, max(ys) + padding + 1)
    else:
        left, top, right, bottom = 0, 0, width, height
    output: list[tuple[int, int, int, int]] = []
    for y in range(top, bottom):
        for x in range(left, right):
            index = y * width + x
            output.append(
                pixels[index] if not restrict or index in members else (0, 0, 0, 0)
            )
    return output, right - left, bottom - top, (left, top, right, bottom)


def canonical_data(
    pixels: Sequence[tuple[int, int, int, int]],
    width: int,
    height: int,
    rule: dict[str, Any],
) -> dict[str, Any]:
    used = set(pixels)
    palette: list[tuple[int, int, int, int]] = []
    if (0, 0, 0, 0) in used:
        palette.append((0, 0, 0, 0))
    if rule["mode"] == "exact":
        for value in rule["colours"]:
            rgb = tuple(bytes.fromhex(value[1:]))
            colour = (*rgb, 255)
            if colour not in palette:
                palette.append(colour)
    for colour in sorted(used):
        if colour not in palette:
            palette.append(colour)
    indices = {colour: index for index, colour in enumerate(palette)}
    index_width = max(2, (((len(palette) - 1).bit_length() + 7) // 8) * 2)
    rows = [
        "".join(
            f"{indices[pixels[y * width + x]]:0{index_width}X}" for x in range(width)
        )
        for y in range(height)
    ]
    return {
        "format": ART_FORMAT,
        "size": [width, height],
        "colourRule": rule,
        "alphaMode": "binary" if any(colour[3] == 0 for colour in used) else "opaque",
        "palette": ["#{:02X}{:02X}{:02X}{:02X}".format(*colour) for colour in palette],
        "indexWidth": index_width,
        "pixels": rows,
    }


def validate_canonical(data: dict[str, Any]) -> bool:
    width, height = data.get("size", [0, 0])
    palette = data.get("palette", [])
    index_width = data.get("indexWidth", 0)
    rows = data.get("pixels", [])
    if data.get("format") != ART_FORMAT or width < 1 or height < 1 or not palette:
        return False
    if len(rows) != height or any(len(row) != width * index_width for row in rows):
        return False
    if any(not re.fullmatch(r"#[0-9A-F]{8}", value) for value in palette):
        return False
    try:
        indices = [
            int(row[offset : offset + index_width], 16)
            for row in rows
            for offset in range(0, len(row), index_width)
        ]
    except ValueError:
        return False
    return bool(indices) and max(indices) < len(palette)


def render_canonical(data: dict[str, Any]) -> Image.Image:
    width, height = data["size"]
    palette = [tuple(bytes.fromhex(value[1:])) for value in data["palette"]]
    index_width = data["indexWidth"]
    indices = [
        int(row[offset : offset + index_width], 16)
        for row in data["pixels"]
        for offset in range(0, len(row), index_width)
    ]
    image = Image.new("RGBA", (width, height))
    image.putdata([palette[index] for index in indices])
    return image


def indexed_png_image(data: dict[str, Any]) -> tuple[Image.Image, int | None]:
    """Build an Aseprite-friendly indexed image from canonical palette indices."""
    width, height = data["size"]
    palette = [tuple(bytes.fromhex(value[1:])) for value in data["palette"]]
    if len(palette) > 256:
        raise ValueError(
            "indexed PNG supports at most 256 palette entries; "
            f"the canonical palette contains {len(palette)}"
        )
    if any(colour[3] not in {0, 255} for colour in palette):
        raise ValueError(
            "Aseprite-friendly indexed PNG does not support partial-alpha palette entries"
        )
    transparent_indices = [
        index for index, colour in enumerate(palette) if colour[3] == 0
    ]
    if len(transparent_indices) > 1:
        raise ValueError(
            "Aseprite-friendly indexed PNG needs at most one transparent palette entry"
        )

    index_width = data["indexWidth"]
    indices = [
        int(row[offset : offset + index_width], 16)
        for row in data["pixels"]
        for offset in range(0, len(row), index_width)
    ]
    image = Image.new("P", (width, height))
    image.putpalette(
        [
            component
            for red, green, blue, _ in palette
            for component in (red, green, blue)
        ]
    )
    image.putdata(indices)
    transparent_index = transparent_indices[0] if transparent_indices else None
    if transparent_index is not None:
        image.info["transparency"] = transparent_index
    return image, transparent_index


def checkerboard_preview(image: Image.Image, scale: int) -> Image.Image:
    enlarged = image.resize(
        (image.width * scale, image.height * scale), Image.Resampling.NEAREST
    )
    background = Image.new("RGBA", enlarged.size, (246, 246, 246, 255))
    draw = ImageDraw.Draw(background)
    tile = 8
    for top in range(0, enlarged.height, tile):
        for left in range(0, enlarged.width, tile):
            if (left // tile + top // tile) % 2:
                draw.rectangle(
                    (
                        left,
                        top,
                        min(left + tile - 1, enlarged.width),
                        min(top + tile - 1, enlarged.height),
                    ),
                    fill=(218, 218, 218, 255),
                )
    background.alpha_composite(enlarged)
    return background.convert("RGB")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def diagnostic_overlay(
    lattice: Lattice,
    ambiguous_indices: Sequence[int],
    width: int,
    output: Path,
) -> None:
    overlay = lattice.image.convert("RGB").copy()
    draw = ImageDraw.Draw(overlay)
    for x in lattice.x.lines:
        draw.line((x, 0, x, overlay.height - 1), fill=(220, 30, 45), width=1)
    for y in lattice.y.lines:
        draw.line((0, y, overlay.width - 1, y), fill=(220, 30, 45), width=1)
    for index in ambiguous_indices:
        row, column = divmod(index, width)
        if row + 1 >= len(lattice.y.lines) or column + 1 >= len(lattice.x.lines):
            continue
        draw.rectangle(
            (
                lattice.x.lines[column],
                lattice.y.lines[row],
                lattice.x.lines[column + 1],
                lattice.y.lines[row + 1],
            ),
            outline=(255, 193, 7),
            width=2,
        )
    maximum = 2000
    if max(overlay.size) > maximum:
        scale = maximum / max(overlay.size)
        overlay = overlay.resize(
            (round(overlay.width * scale), round(overlay.height * scale)),
            Image.Resampling.LANCZOS,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(output, format="PNG")


def crop_source(
    image: Image.Image, crop: tuple[int, int, int, int] | None
) -> Image.Image:
    if crop is None:
        return image
    left, top, width, height = crop
    if left + width > image.width or top + height > image.height:
        raise ExtractionError("the requested crop extends outside the source image")
    return image.crop((left, top, left + width, top + height))


def extract_one(
    input_path: Path, output_dir: Path, args: argparse.Namespace
) -> dict[str, Any]:
    source = ImageOps.exif_transpose(Image.open(input_path)).convert("RGBA")
    original_size = source.size
    source = crop_source(source, args.crop)
    lattice = estimate_lattice(source, args)
    samples, width, height = sample_cells(lattice, args.cell_inset)
    pixels, classification = classify_cells(
        samples, width, height, lattice.mode, args, lattice=lattice
    )

    all_occupied = {index for index, colour in enumerate(pixels) if colour[3] > 0}
    if not all_occupied:
        raise ExtractionError("the extraction contains no visible cells")
    warnings: list[str] = []
    if args.split_components:
        groups = connected_groups(pixels, width, height, args.merge_gap)
        retained = [group for group in groups if len(group) >= args.min_component_cells]
        omitted = len(groups) - len(retained)
        if omitted:
            warnings.append(
                f"omitted {omitted} component(s) below the minimum cell count"
            )
        if not retained:
            raise ExtractionError("component filtering removed every visible cell")
    else:
        retained = [all_occupied]

    output_dir.mkdir(parents=True, exist_ok=True)
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", input_path.stem).strip("-.") or "artwork"
    indexed_output = getattr(args, "indexed_png", False)
    outputs: list[dict[str, Any]] = []
    for number, members in enumerate(retained, start=1):
        suffix = f"-{number:02d}" if len(retained) > 1 else ""
        name = f"{base}{suffix}"
        component_pixels, component_width, component_height, bounds = crop_component(
            pixels,
            width,
            height,
            members,
            args.padding,
            not args.no_trim,
            args.split_components,
        )
        data = canonical_data(
            component_pixels,
            component_width,
            component_height,
            classification["colour_rule"],
        )
        valid = validate_canonical(data)
        if not valid:
            raise ExtractionError("internal canonical validation failed")
        canonical_path = output_dir / f"{name}.pixel-art.json"
        logical_path = output_dir / f"{name}.png"
        preview_path = output_dir / f"{name}@{args.preview_scale}x.png"
        transparent_index: int | None = None
        if indexed_output:
            logical, transparent_index = indexed_png_image(data)
        else:
            logical = render_canonical(data)
        write_json(canonical_path, data)
        logical.save(logical_path, format="PNG", optimize=False)
        checkerboard_preview(logical.convert("RGBA"), args.preview_scale).save(
            preview_path, format="PNG", optimize=False
        )
        output_record = {
            "canonical": canonical_path.name,
            "logical_png": logical_path.name,
            "preview_png": preview_path.name,
            "size": [component_width, component_height],
            "source_cell_bounds": list(bounds),
            "visible_cells": sum(colour[3] > 0 for colour in component_pixels),
            "canonical_valid": valid,
        }
        if indexed_output:
            output_record["logical_png_mode"] = "indexed"
            output_record["transparent_index"] = transparent_index
        outputs.append(output_record)

    lattice_confidence = math.sqrt(lattice.x.confidence * lattice.y.confidence)
    classification_confidence = classification["classification_confidence"]
    overall_confidence = math.sqrt(lattice_confidence * classification_confidence)
    status = (
        "accepted"
        if lattice_confidence >= 0.45
        and overall_confidence >= 0.58
        and classification["ambiguous_fraction"] <= 0.08
        and not classification["review_required"]
        else "needs_review"
    )
    if lattice_confidence < 0.45:
        warnings.append("automatic lattice confidence is low; supply explicit geometry")
    if classification["ambiguous_fraction"] > 0.08:
        warnings.append("many cells are close to the foreground decision boundary")
    warnings.extend(classification["review_reasons"])

    report: dict[str, Any] = {
        "format": REPORT_FORMAT,
        "extractor": {"name": "extract_pixel_art.py", "version": 1},
        "source": str(input_path),
        "source_sha256": sha256_file(input_path),
        "status": status,
        "mode_requested": args.mode,
        "mode_used": lattice.mode,
        "source_size": list(original_size),
        "normalisation": {
            "crop": list(args.crop) if args.crop else None,
            "corners_after_crop": list(args.corners) if args.corners else None,
            "supplied_grid_size": list(args.grid_size) if args.grid_size else None,
            "supplied_cell_size": list(args.cell_size) if args.cell_size else None,
            "working_size": list(source.size),
            "rectified_size": list(lattice.image.size),
            "cell_inset": args.cell_inset,
        },
        "grid": {
            "columns": width,
            "rows": height,
            "x_period_pixels": round(lattice.x.period, 4),
            "y_period_pixels": round(lattice.y.period, 4),
            "x_evidence": lattice.x.evidence,
            "y_evidence": lattice.y.evidence,
            "explicit": lattice.explicit,
            "x_lines_pixels": lattice.x.lines,
            "y_lines_pixels": lattice.y.lines,
        },
        "confidence": {
            "lattice": round(lattice_confidence, 6),
            "classification": classification_confidence,
            "overall": round(overall_confidence, 6),
        },
        "classification": {
            key: value
            for key, value in classification.items()
            if key != "ambiguous_indices"
        },
        "outputs": outputs,
        "warnings": warnings,
    }
    if args.diagnostics:
        diagnostic_name = f"{base}.extraction-grid.png"
        diagnostic_overlay(
            lattice,
            classification["ambiguous_indices"],
            width,
            output_dir / diagnostic_name,
        )
        report["diagnostic_overlay"] = diagnostic_name
    report_path = output_dir / "extraction-report.json"
    write_json(report_path, report)
    report["report"] = str(report_path)
    return report


def discover_inputs(paths: Sequence[Path]) -> list[Path]:
    discovered: list[Path] = []
    for path in paths:
        if path.is_dir():
            discovered.extend(
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES
            )
        elif path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            discovered.append(path)
        else:
            raise ExtractionError(f"not a supported image or directory: {path}")
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in discovered:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def batch_target(path: Path, output_dir: Path, repeated_stems: set[str]) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-.") or "artwork"
    if path.stem in repeated_stems:
        digest = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:8]
        safe = f"{safe}-{digest}"
    return output_dir / safe


def batch_worker(payload: tuple[str, str, dict[str, Any]]) -> dict[str, Any]:
    input_value, output_value, options = payload
    try:
        return extract_one(
            Path(input_value), Path(output_value), argparse.Namespace(**options)
        )
    except Exception as exc:  # noqa: BLE001 - batch must preserve the rest of the collection
        return {
            "format": REPORT_FORMAT,
            "source": input_value,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


def add_extraction_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode", choices=("auto", "native", "grid", "embroidery"), default="auto"
    )
    parser.add_argument(
        "--crop", type=parse_crop, help="LEFT,TOP,WIDTH,HEIGHT before grid recovery"
    )
    parser.add_argument(
        "--grid-size", type=parse_size, help="known logical WIDTHxHEIGHT"
    )
    parser.add_argument(
        "--cell-size", type=parse_pair, help="known source-pixel cell size XxY"
    )
    parser.add_argument(
        "--corners",
        type=parse_corners,
        help="TL_X,TL_Y,TR_X,TR_Y,BR_X,BR_Y,BL_X,BL_Y after crop; requires --grid-size",
    )
    parser.add_argument(
        "--cell-inset",
        type=float,
        default=0.20,
        help="fraction excluded at every cell edge",
    )
    parser.add_argument(
        "--palette", default="unrestricted", help="comma-separated #RRGGBB colours"
    )
    parser.add_argument("--max-colours", type=int)
    parser.add_argument(
        "--background", choices=("auto", "keep", "transparent"), default="auto"
    )
    parser.add_argument("--background-colour", help="known substrate colour as #RRGGBB")
    parser.add_argument("--foreground-threshold", type=float)
    parser.add_argument("--split-components", action="store_true")
    parser.add_argument(
        "--merge-gap", type=int, default=1, help="blank-cell gap bridged while grouping"
    )
    parser.add_argument("--min-component-cells", type=int, default=2)
    parser.add_argument("--padding", type=int, default=0)
    parser.add_argument("--no-trim", action="store_true")
    parser.add_argument("--preview-scale", type=int, default=8)
    parser.add_argument(
        "--indexed-png",
        action="store_true",
        help="write the logical PNG with canonical palette indices for Aseprite",
    )
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--fail-on-review", action="store_true")


def validate_arguments(args: argparse.Namespace) -> None:
    if not 0 <= args.cell_inset < 0.5:
        raise ExtractionError("--cell-inset must be at least 0 and below 0.5")
    if args.max_colours is not None and not 1 <= args.max_colours <= 256:
        raise ExtractionError("--max-colours must be between 1 and 256")
    if args.merge_gap < 0 or args.min_component_cells < 1 or args.padding < 0:
        raise ExtractionError("component and padding values must be non-negative")
    if args.preview_scale < 1:
        raise ExtractionError("--preview-scale must be positive")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recover logical pixel cells and emit canonical pixel-art/v1 data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="extract one source image")
    extract.add_argument("input", type=Path)
    extract.add_argument("--output-dir", type=Path, required=True)
    add_extraction_arguments(extract)

    batch = subparsers.add_parser(
        "batch", help="extract image files or directories in parallel"
    )
    batch.add_argument("inputs", type=Path, nargs="+")
    batch.add_argument("--output-dir", type=Path, required=True)
    batch.add_argument("--jobs", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    add_extraction_arguments(batch)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_arguments(args)
        if args.command == "extract":
            report = extract_one(args.input, args.output_dir, args)
            print(json.dumps(report, indent=2))
            return 2 if args.fail_on_review and report["status"] != "accepted" else 0

        if args.jobs < 1:
            raise ExtractionError("--jobs must be positive")
        inputs = discover_inputs(args.inputs)
        if not inputs:
            raise ExtractionError("no supported images were found")
        stem_counts = Counter(path.stem for path in inputs)
        repeated = {stem for stem, count in stem_counts.items() if count > 1}
        options = vars(args).copy()
        for key in ("command", "inputs", "output_dir", "jobs"):
            options.pop(key, None)
        payloads = [
            (str(path), str(batch_target(path, args.output_dir, repeated)), options)
            for path in inputs
        ]
        if args.jobs == 1:
            reports = [batch_worker(payload) for payload in payloads]
        else:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=args.jobs
            ) as executor:
                reports = list(executor.map(batch_worker, payloads))
        summary = {
            "format": "pixel-art-extraction-batch/v1",
            "input_count": len(reports),
            "accepted": sum(report["status"] == "accepted" for report in reports),
            "needs_review": sum(
                report["status"] == "needs_review" for report in reports
            ),
            "failed": sum(report["status"] == "failed" for report in reports),
            "records": reports,
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(args.output_dir / "batch-report.json", summary)
        print(json.dumps(summary, indent=2))
        if summary["failed"]:
            return 1
        if args.fail_on_review and summary["needs_review"]:
            return 2
        return 0
    except (ExtractionError, OSError, ValueError) as exc:
        print(
            json.dumps({"status": "failed", "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
