"""V3 reflection-band-aware physical outer-edge experiment for shaft OD measurement.

Design goals
------------
* YOLO supplies only the horizontal measurement location / a generous ROI.
* Pair acceptance never uses ``box_h * ratio``.
* A physical silhouette is preferred: bright->dark at the top (negative
  gradient), dark->bright at the bottom (positive gradient), with background
  brighter than the material immediately inside the boundary.
* The 31 columns are selected jointly with dynamic programming, then robust
  top/bottom lines are fitted and one line-consistent pass is made.
* Sub-pixel interpolation, MAD filtering, median reporting, and the existing
  3-point calibration are retained.

This is an experimental file.  It does not modify any V1 source file.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True)
class Pair:
    top_i: int
    bottom_i: int
    top: float
    bottom: float
    diameter: float
    top_gradient: float
    bottom_gradient: float
    strength_score: float
    contrast_score: float
    local_score: float


def subpixel_peak(abs_gradient: np.ndarray, index: int) -> float:
    if index <= 0 or index >= len(abs_gradient) - 1:
        return float(index)
    g1, g2, g3 = map(float, abs_gradient[index - 1:index + 2])
    denominator = g1 - 2.0 * g2 + g3
    if abs(denominator) < 1e-12:
        return float(index)
    offset = np.clip(0.5 * (g1 - g3) / denominator, -1.0, 1.0)
    return float(index + offset)


def local_extrema(values: np.ndarray, negative: bool) -> np.ndarray:
    """Indices of signed local gradient peaks, excluding end points."""
    if len(values) < 3:
        return np.empty(0, dtype=int)
    if negative:
        mask = (values[1:-1] < values[:-2]) & (values[1:-1] <= values[2:])
    else:
        mask = (values[1:-1] > values[:-2]) & (values[1:-1] >= values[2:])
    return np.flatnonzero(mask) + 1


def robust01(values: np.ndarray) -> np.ndarray:
    if len(values) == 0:
        return values.astype(float)
    lo, hi = np.percentile(values, [20, 95])
    return np.clip((values - lo) / max(float(hi - lo), 1e-9), 0.0, 1.0)


def edge_contrast(profile: np.ndarray, y: int, radius: int, top: bool) -> float:
    """Multi-scale evidence that the outside is background, not a reflection band.

    A narrow bright/dark machining stripe can satisfy a 5-pixel contrast test.
    The wider separated bands below require the brightness change to persist on
    both sides of the candidate, which is characteristic of the silhouette.
    """
    n = len(profile)
    if top:
        outside = profile[max(0, y - 4 * radius):max(0, y - radius)]
        inside = profile[min(n, y + radius):min(n, y + 4 * radius)]
    else:
        inside = profile[max(0, y - 4 * radius):max(0, y - radius)]
        outside = profile[min(n, y + radius):min(n, y + 4 * radius)]
    if len(outside) == 0 or len(inside) == 0:
        return -255.0
    return float(np.mean(outside) - np.mean(inside))


def _largest_true_run(mask_1d: np.ndarray) -> tuple[int, int] | None:
    """Return [start, end) of the longest True run."""
    best = None
    start = None
    for i, v in enumerate(mask_1d.tolist() + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if best is None or (i - start) > (best[1] - best[0]):
                best = (start, i)
            start = None
    return best


def build_reflection_mask(gray: np.ndarray) -> tuple[np.ndarray, dict]:
    """Detect narrow reflection/machining bands without hard-coded image coordinates.

    Seven OpenCV mechanisms are used:
      1) threshold / inRange
      2) morphology OPEN / CLOSE
      3) MORPH_TOPHAT
      4) MORPH_BLACKHAT
      5) connectedComponentsWithStats
      6) contour width/height/aspect filtering
      7) automatic ROI-interior / silhouette-fringe masking

    The mask is NOT painted into the image.  It is used only to reject edge
    candidates that lie on detected reflection bands.
    """
    h, w = gray.shape
    if h < 20 or w < 10:
        return np.zeros_like(gray, dtype=np.uint8), {"components": 0, "mask_pixels": 0}

    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # 1) Intensity threshold / inRange.
    otsu_t, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    p15, p85 = np.percentile(blur, [15, 85])
    bright_low = int(np.clip(max(float(otsu_t) + 12.0, float(p85)), 0, 255))
    dark_high = int(np.clip(min(float(otsu_t) - 12.0, float(p15)), 0, 255))
    bright = cv2.inRange(blur, bright_low, 255)
    dark = cv2.inRange(blur, 0, dark_high)

    # 3,4) Thin horizontal bright/dark band emphasis.
    ky = max(9, int(round(0.035 * h)))
    if ky % 2 == 0:
        ky += 1
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, ky))
    top_hat = cv2.morphologyEx(blur, cv2.MORPH_TOPHAT, vertical_kernel)
    black_hat = cv2.morphologyEx(blur, cv2.MORPH_BLACKHAT, vertical_kernel)

    top_thr = max(6, int(np.percentile(top_hat, 90)))
    black_thr = max(6, int(np.percentile(black_hat, 90)))
    _, top_bin = cv2.threshold(top_hat, top_thr, 255, cv2.THRESH_BINARY)
    _, black_bin = cv2.threshold(black_hat, black_thr, 255, cv2.THRESH_BINARY)

    # Use intensity AND morphology evidence to avoid masking the bright background.
    candidate = cv2.bitwise_or(
        cv2.bitwise_and(bright, top_bin),
        cv2.bitwise_and(dark, black_bin),
    )

    # 2) Morphology OPEN/CLOSE: remove speckle, connect horizontal bands.
    open_w = max(3, int(round(0.02 * w)))
    close_w = max(7, int(round(0.10 * w)))
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (open_w, 1))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_w, 3))
    cleaned = cv2.morphologyEx(candidate, cv2.MORPH_OPEN, open_kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, close_kernel)

    # Coarse silhouette from dark-row occupancy.  This is only for restricting
    # where a detected band may be masked; it does not define the measured OD.
    _, dark_body = cv2.threshold(blur, int(otsu_t), 255, cv2.THRESH_BINARY_INV)
    row_fraction = np.mean(dark_body > 0, axis=1)
    run = _largest_true_run(row_fraction >= 0.35)

    allowed_region = np.zeros_like(gray, dtype=np.uint8)
    coarse_top = None
    coarse_bottom = None
    if run is not None and (run[1] - run[0]) >= max(30, int(0.15 * h)):
        coarse_top, coarse_bottom = run
        guard = max(5, int(round(0.012 * (coarse_bottom - coarse_top))))
        # 7a) central/interior reflection mask region.
        i1 = min(h, coarse_top + guard)
        i2 = max(0, coarse_bottom - guard)
        if i2 > i1:
            allowed_region[i1:i2, :] = 255

        # 7b) very narrow fringe just OUTSIDE the coarse silhouette.
        # Keep a 2-pixel safety gap so the primary silhouette edge itself is not masked.
        fringe = max(8, int(round(0.018 * h)))
        t1, t2 = max(0, coarse_top - fringe), max(0, coarse_top - 2)
        b1, b2 = min(h, coarse_bottom + 2), min(h, coarse_bottom + fringe)
        if t2 > t1:
            allowed_region[t1:t2, :] = 255
        if b2 > b1:
            allowed_region[b1:b2, :] = 255
    else:
        # Conservative fallback: only the middle 80% of ROI.
        allowed_region[int(0.10*h):int(0.90*h), :] = 255

    cleaned = cv2.bitwise_and(cleaned, allowed_region)

    # 5) Connected component filtering.
    nlab, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
    comp_mask = np.zeros_like(cleaned)
    kept_components = 0
    min_width = max(12, int(round(0.22 * w)))
    max_height = max(10, int(round(0.055 * h)))
    min_area = max(20, int(round(0.003 * w * h)))
    for lab in range(1, nlab):
        x, y, cw, ch, area = stats[lab]
        aspect = cw / max(ch, 1)
        if cw >= min_width and ch <= max_height and aspect >= 3.0 and area >= min_area:
            comp_mask[labels == lab] = 255
            kept_components += 1

    # 6) Contour width/height/aspect filtering as a second geometric guard.
    contour_mask = np.zeros_like(comp_mask)
    contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    kept_contours = 0
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = cw / max(ch, 1)
        if cw >= min_width and ch <= max_height and aspect >= 3.0:
            cv2.drawContours(contour_mask, [cnt], -1, 255, thickness=cv2.FILLED)
            kept_contours += 1

    info = {
        "otsu_threshold": float(otsu_t),
        "bright_low": int(bright_low),
        "dark_high": int(dark_high),
        "components": int(kept_components),
        "contours": int(kept_contours),
        "mask_pixels": int(np.count_nonzero(contour_mask)),
        "mask_ratio": float(np.count_nonzero(contour_mask) / contour_mask.size),
        "coarse_top": None if coarse_top is None else int(coarse_top),
        "coarse_bottom": None if coarse_bottom is None else int(coarse_bottom),
    }
    return contour_mask, info


def _candidate_is_masked(mask: np.ndarray | None, y: int, x1: int, x2: int) -> bool:
    if mask is None or mask.size == 0:
        return False
    h, w = mask.shape
    yy1, yy2 = max(0, y - 2), min(h, y + 3)
    xx1, xx2 = max(0, x1), min(w, x2)
    patch = mask[yy1:yy2, xx1:xx2]
    if patch.size == 0:
        return False
    # Require material coverage around the candidate, not one noisy pixel.
    return float(np.mean(patch > 0)) >= 0.20


def candidates_for_x(gray: np.ndarray, x: int, max_each: int = 14, reflection_mask: np.ndarray | None = None) -> list[Pair]:
    """Generate physical silhouette pairs without any box-height diameter gate."""
    x1, x2 = max(0, x - 3), min(gray.shape[1], x + 4)
    profile = np.mean(gray[:, x1:x2], axis=1).astype(np.float32)
    profile = cv2.GaussianBlur(profile[:, None], (1, 5), 0).ravel()
    gradient = np.gradient(profile)
    absolute = np.abs(gradient)
    h = len(profile)

    # Exact expected signs for a dark shaft against a bright background.
    tops = local_extrema(gradient, negative=True)
    bottoms = local_extrema(gradient, negative=False)
    margin = max(6, int(round(0.01 * h)))
    tops = tops[(tops >= margin) & (tops < h - margin) & (gradient[tops] < 0)]
    bottoms = bottoms[(bottoms >= margin) & (bottoms < h - margin) & (gradient[bottoms] > 0)]

    # Keep strong signed peaks only.  This threshold is image-derived, not box_h-derived.
    signed_strengths = np.r_[-gradient[tops], gradient[bottoms]]
    if len(signed_strengths) == 0:
        return []
    threshold = max(2.0, float(np.percentile(signed_strengths, 65)))
    tops = tops[-gradient[tops] >= threshold]
    bottoms = bottoms[gradient[bottoms] >= threshold]
    tops = tops[np.argsort(-(-gradient[tops]))[:max_each]]
    bottoms = bottoms[np.argsort(-gradient[bottoms])[:max_each]]

    # V3: reject narrow reflection/machining-band candidates detected in 2D ROI.
    tops = np.array(
        [i for i in tops if not _candidate_is_masked(reflection_mask, int(i), x1, x2)],
        dtype=int,
    )
    bottoms = np.array(
        [i for i in bottoms if not _candidate_is_masked(reflection_mask, int(i), x1, x2)],
        dtype=int,
    )
    if len(tops) == 0 or len(bottoms) == 0:
        return []

    raw: list[tuple[int, int, float, float, float]] = []
    # Wide context rejects narrow internal reflection/machining bands.
    radius = max(12, int(round(0.018 * h)))
    for top_i in tops:
        top_c = edge_contrast(profile, int(top_i), radius, top=True)
        for bottom_i in bottoms:
            if bottom_i <= top_i + 20:  # only ordering/degeneracy guard; no expected diameter
                continue
            bottom_c = edge_contrast(profile, int(bottom_i), radius, top=False)
            # At least weak physical outside-to-inside contrast on both boundaries.
            if top_c <= 0.0 or bottom_c <= 0.0:
                continue
            strength = float(-gradient[top_i] + gradient[bottom_i])
            contrast = float(top_c + bottom_c)
            raw.append((int(top_i), int(bottom_i), strength, contrast,
                        float(bottom_i - top_i)))
    if not raw:
        return []

    strengths = robust01(np.array([r[2] for r in raw], dtype=float))
    contrasts = robust01(np.array([r[3] for r in raw], dtype=float))
    # Outwardness is a tie-breaker only.  A large gap cannot beat wrong sign/contrast.
    gaps = robust01(np.array([r[4] for r in raw], dtype=float))
    scores = 0.40 * strengths + 0.42 * contrasts + 0.18 * gaps
    order = np.argsort(-scores)[:32]
    result: list[Pair] = []
    for k in order:
        top_i, bottom_i, strength, contrast, _ = raw[int(k)]
        top = subpixel_peak(absolute, top_i)
        bottom = subpixel_peak(absolute, bottom_i)
        result.append(Pair(
            top_i, bottom_i, top, bottom, bottom - top,
            float(gradient[top_i]), float(gradient[bottom_i]),
            float(strengths[k]), float(contrasts[k]), float(scores[k]),
        ))
    return result


def transition_cost(left: Pair, right: Pair, dx: float) -> float:
    """Continuity prior between adjacent x positions (units normalized by dx)."""
    scale = max(dx, 1.0)
    top_jump = abs(right.top - left.top) / scale
    bottom_jump = abs(right.bottom - left.bottom) / scale
    diameter_jump = abs(right.diameter - left.diameter) / scale
    return 0.30 * (top_jump + bottom_jump) + 0.55 * diameter_jump


def select_continuous_path(xs: np.ndarray, all_candidates: list[list[Pair]]) -> list[Pair | None]:
    """Jointly select the most physical, continuous top/bottom contour pair."""
    usable = [(i, c) for i, c in enumerate(all_candidates) if c]
    if len(usable) < 8:
        raise RuntimeError("Edge 후보가 있는 x 위치가 8개 미만입니다.")
    first_i, first = usable[0]
    costs = np.array([-p.local_score for p in first], dtype=float)
    backrefs: list[np.ndarray] = []
    previous_i, previous = first_i, first
    for current_i, current in usable[1:]:
        dx = float(xs[current_i] - xs[previous_i])
        new_costs = np.full(len(current), np.inf)
        back = np.full(len(current), -1, dtype=int)
        for j, right in enumerate(current):
            options = np.array([
                costs[k] + transition_cost(left, right, dx)
                for k, left in enumerate(previous)
            ])
            k = int(np.argmin(options))
            new_costs[j] = options[k] - right.local_score
            back[j] = k
        backrefs.append(back)
        costs, previous_i, previous = new_costs, current_i, current

    selected_indices = [int(np.argmin(costs))]
    for back in reversed(backrefs):
        selected_indices.append(int(back[selected_indices[-1]]))
    selected_indices.reverse()
    path: list[Pair | None] = [None] * len(xs)
    for (position_i, candidates), choice in zip(usable, selected_indices):
        path[position_i] = candidates[choice]
    return path


def robust_line_mask(xs: np.ndarray, ys: np.ndarray, sigma: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    mask = np.ones(len(xs), dtype=bool)
    coef = np.polyfit(xs, ys, 1)
    for _ in range(3):
        coef = np.polyfit(xs[mask], ys[mask], 1)
        residual = ys - np.polyval(coef, xs)
        center = np.median(residual[mask])
        mad = np.median(np.abs(residual[mask] - center))
        if mad <= 1e-12:
            break
        mask = np.abs(residual - center) <= sigma * 1.4826 * mad
        if np.count_nonzero(mask) < 8:
            mask[:] = True
            break
    return coef, mask


def reselect_near_lines(xs: np.ndarray, candidates: list[list[Pair]], path: list[Pair | None]) -> list[Pair | None]:
    valid_i = np.array([i for i, p in enumerate(path) if p is not None], dtype=int)
    chosen = [path[i] for i in valid_i]
    top_coef, _ = robust_line_mask(xs[valid_i], np.array([p.top for p in chosen]))
    bottom_coef, _ = robust_line_mask(xs[valid_i], np.array([p.bottom for p in chosen]))
    result: list[Pair | None] = [None] * len(xs)
    for i, pairs in enumerate(candidates):
        if not pairs:
            continue
        predicted_top = float(np.polyval(top_coef, xs[i]))
        predicted_bottom = float(np.polyval(bottom_coef, xs[i]))
        # Candidate must earn its place with physical score and agreement to both lines.
        result[i] = min(
            pairs,
            key=lambda p: (
                0.35 * abs(p.top - predicted_top)
                + 0.35 * abs(p.bottom - predicted_bottom)
                - 2.0 * p.local_score
            ),
        )
    return result


def mad_mask(values: np.ndarray, sigma: float = 3.0) -> np.ndarray:
    median = float(np.median(values))
    deviation = np.abs(values - median)
    mad = float(np.median(deviation))
    if mad <= 1e-12:
        return np.ones(len(values), dtype=bool)
    return deviation <= sigma * 1.4826 * mad


def parse_box(text: str | None) -> tuple[int, int, int, int] | None:
    if text is None:
        return None
    values = [int(v.strip()) for v in text.split(",")]
    if len(values) != 4:
        raise ValueError("--box 형식은 x1,y1,x2,y2 입니다.")
    return tuple(values)  # type: ignore[return-value]


def yolo_box(image_path: Path, model_path: Path) -> tuple[tuple[int, int, int, int], float]:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("ultralytics가 없습니다. 설치하거나 --box를 지정하세요.") from exc
    model = YOLO(str(model_path))
    results = model.predict(source=str(image_path), conf=0.25, imgsz=640, verbose=False)
    boxes = [box for result in results if result.boxes is not None for box in result.boxes]
    if not boxes:
        raise RuntimeError("YOLO ROI 검출 실패")
    best = max(boxes, key=lambda b: float(b.conf[0]))
    coords = best.xyxy[0].cpu().numpy().astype(int).tolist()
    return tuple(coords), float(best.conf[0])  # type: ignore[return-value]


def measure(image_path: Path, box: tuple[int, int, int, int], confidence: float,
            calibration: dict, output_dir: Path) -> dict:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(image_path)
    image_h, image_w = image.shape[:2]
    x1, y1, x2, y2 = box
    x1, x2 = max(0, x1), min(image_w, x2)
    # Deliberately generous vertical search band. box_h never gates diameter.
    box_h = max(1, y2 - y1)
    margin = max(24, int(round(0.12 * box_h)))
    search_y1, search_y2 = max(0, y1 - margin), min(image_h, y2 + margin)
    roi = image[search_y1:search_y2, x1:x2]
    if roi.size == 0:
        raise RuntimeError("측정 ROI 생성 실패")
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # V3 reflection/machining-band mask.  The original gray image is untouched.
    reflection_mask, reflection_info = build_reflection_mask(gray)
    output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_dir / f"{image_path.stem}_reflection_mask.png"), reflection_mask)

    xs = np.linspace(int(gray.shape[1] * 0.18), int(gray.shape[1] * 0.82), 31).astype(int)
    candidate_sets = [
        candidates_for_x(gray, int(x), reflection_mask=reflection_mask)
        for x in xs
    ]
    path = select_continuous_path(xs, candidate_sets)
    path = reselect_near_lines(xs, candidate_sets, path)
    valid_i = np.array([i for i, p in enumerate(path) if p is not None], dtype=int)
    selected = [path[i] for i in valid_i]
    diameters = np.array([p.diameter for p in selected], dtype=float)
    top = np.array([p.top for p in selected], dtype=float)
    bottom = np.array([p.bottom for p in selected], dtype=float)

    top_coef, top_mask = robust_line_mask(xs[valid_i], top)
    bottom_coef, bottom_mask = robust_line_mask(xs[valid_i], bottom)
    valid_mask = mad_mask(diameters) & top_mask & bottom_mask
    if np.count_nonzero(valid_mask) < 8:
        raise RuntimeError("선 피팅/MAD 제거 후 유효 측정점이 8개 미만입니다.")
    valid_diameters = diameters[valid_mask]
    measured_pixel = float(np.median(valid_diameters))
    mean_pixel = float(np.mean(valid_diameters))
    std_pixel = float(np.std(valid_diameters))
    a, b = float(calibration["a"]), float(calibration["b"])

    edge_csv = output_dir / f"{image_path.stem}_edge_points.csv"
    with edge_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["x_roi", "x_image", "top_y_image", "bottom_y_image", "diameter_pixel",
                         "top_gradient", "bottom_gradient", "strength_score", "contrast_score",
                         "local_score", "valid_after_line_and_mad"])
        valid_lookup = {int(i): bool(ok) for i, ok in zip(valid_i, valid_mask)}
        for i, p in enumerate(path):
            if p is None:
                continue
            writer.writerow([int(xs[i]), int(x1 + xs[i]), p.top + search_y1, p.bottom + search_y1,
                             p.diameter, p.top_gradient, p.bottom_gradient, p.strength_score,
                             p.contrast_score, p.local_score, valid_lookup.get(i, False)])

    overlay = image.copy()
    for i, p in enumerate(path):
        if p is None:
            continue
        color = (0, 255, 0) if valid_lookup.get(i, False) else (0, 165, 255)
        cv2.circle(overlay, (int(x1 + xs[i]), int(round(search_y1 + p.top))), 5, color, -1)
        cv2.circle(overlay, (int(x1 + xs[i]), int(round(search_y1 + p.bottom))), 5, color, -1)
    cv2.imwrite(str(output_dir / f"{image_path.stem}_EDGE_V3_REFLECTION_overlay.jpg"), overlay)

    return {
        "image": str(image_path), "confidence": confidence, "box": [x1, y1, x2, y2],
        "box_h": box_h, "measured_pixel": measured_pixel, "mean_pixel": mean_pixel,
        "std_pixel": std_pixel, "valid_point_count": int(np.count_nonzero(valid_mask)),
        "measured_pixel_per_box_h": measured_pixel / box_h,
        "measured_mm_existing_calibration": a * measured_pixel + b,
        "top_line_slope": float(top_coef[0]), "bottom_line_slope": float(bottom_coef[0]),
        "reflection_mask_info": reflection_info,
        "top_edges_image_y": [float(v + search_y1) for v in top[valid_mask]],
        "bottom_edges_image_y": [float(v + search_y1) for v in bottom[valid_mask]],
        "edge_points_csv": str(edge_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--model", type=Path, default=Path(__file__).resolve().parent / "models" / "best.pt")
    parser.add_argument("--box", help="YOLO 대신 사용할 x1,y1,x2,y2 (재현/진단용)")
    parser.add_argument("--calibration", type=Path, default=Path(__file__).resolve().parent / "calibration_config_abc.json")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "output_EDGE_V3_REFLECTION")
    args = parser.parse_args()
    with args.calibration.open("r", encoding="utf-8") as stream:
        calibration = json.load(stream)
    box = parse_box(args.box)
    if box is None:
        box, confidence = yolo_box(args.image, args.model)
    else:
        confidence = float("nan")
    result = measure(args.image, box, confidence, calibration, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
