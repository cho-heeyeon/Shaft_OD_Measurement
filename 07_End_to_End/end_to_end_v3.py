
import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np


# ============================================================
# Shaft OD End-to-End V3
# Current project closing version
# ============================================================
#
# IMPORTANT
# - Uses the existing measurement_engine_EDGE_V3_REFLECTION.py unchanged.
# - Uses the confirmed 2026-10-21 final shaft ROI.
# - Pixel -> mm equation below is DIAGNOSTIC ONLY.
# - Calibration linearity is NOT validated (R^2 ~= 0.03645, monotonic=False).
# - Do NOT use this script as a production metrology / final OK-NG authority.
# ============================================================


BASE_W = 16320
BASE_H = 7532

# Final shaft measurement ROI for the 2026-10-21 capture set
SHAFT_ROI_BASE = (8008, 3329, 8280, 4276)

# Product specification
SPEC_LOWER_MM = 20.010
SPEC_UPPER_MM = 20.030

# Diagnostic 3-point calibration result
# NO6 : 748.622508 px -> 20.011 mm (9 valid images, one excluded)
# NO2 : 749.889325 px -> 20.020 mm
# NO3 : 748.836126 px -> 20.028 mm
CAL_A = 0.0023942128453839483
CAL_B = 18.22612354938321
CAL_R2 = 0.036449783915076917
CAL_MONOTONIC = False

CALIBRATION_STATUS = "NOT_VALIDATED_DIAGNOSTIC_ONLY"


def parse_args():
    p = argparse.ArgumentParser(
        description="Shaft OD End-to-End V3 using existing V3 Reflection engine"
    )

    p.add_argument(
        "--image",
        required=True,
        help="Input shaft image path"
    )

    p.add_argument(
        "--engine",
        required=True,
        help="measurement_engine_EDGE_V3_REFLECTION.py path"
    )

    p.add_argument(
        "--output",
        default="end_to_end_output",
        help="Output folder"
    )

    p.add_argument(
        "--reference-mm",
        type=float,
        default=None,
        help="Optional micrometer reference value for error calculation"
    )

    return p.parse_args()


def read_image_unicode(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def load_engine(engine_path: Path):
    if not engine_path.exists():
        raise FileNotFoundError(
            f"V3 engine not found: {engine_path}"
        )

    spec = importlib.util.spec_from_file_location(
        "measurement_engine_EDGE_V3_REFLECTION",
        str(engine_path),
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load V3 engine module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def scaled_box(img, box):
    h, w = img.shape[:2]

    sx = w / BASE_W
    sy = h / BASE_H

    x1, y1, x2, y2 = box

    return (
        int(round(x1 * sx)),
        int(round(y1 * sy)),
        int(round(x2 * sx)),
        int(round(y2 * sy)),
    )


def get_ascii_temp_root():
    drive = Path.cwd().drive

    if drive:
        temp_root = Path(
            drive + r"\shaft_e2e_temp"
        )
    else:
        temp_root = Path("/tmp/shaft_e2e_temp")

    temp_root.mkdir(
        parents=True,
        exist_ok=True
    )

    return temp_root


def copy_engine_outputs(src_dir: Path, dst_dir: Path):
    dst_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    for path in src_dir.iterdir():
        if path.is_file():
            shutil.copy2(
                path,
                dst_dir / path.name
            )


def main():
    args = parse_args()

    image_path = Path(args.image)
    engine_path = Path(args.engine)
    output_dir = Path(args.output)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    if not image_path.exists():
        raise FileNotFoundError(
            f"Input image not found: {image_path}"
        )

    image = read_image_unicode(
        image_path
    )

    if image is None:
        raise RuntimeError(
            f"Failed to read input image: {image_path}"
        )

    shaft_box = scaled_box(
        image,
        SHAFT_ROI_BASE
    )

    engine = load_engine(
        engine_path
    )

    # --------------------------------------------------------
    # Use ASCII-only temp path so unchanged V3 engine can read
    # Windows paths even when the original path contains Korean.
    # --------------------------------------------------------
    temp_root = get_ascii_temp_root()

    temp_run_dir = (
        temp_root / "run"
    )

    if temp_run_dir.exists():
        shutil.rmtree(
            temp_run_dir
        )

    temp_run_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    ascii_image_path = (
        temp_run_dir / "input_image.jpg"
    )

    shutil.copy2(
        image_path,
        ascii_image_path
    )

    engine_output_dir = (
        temp_run_dir / "engine_output"
    )

    engine_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Dummy calibration only satisfies the existing engine interface.
    # The engine's mm output is intentionally ignored.
    dummy_calibration = {
        "a": 1.0,
        "b": 0.0,
    }

    result = engine.measure(
        ascii_image_path,
        shaft_box,
        float("nan"),
        dummy_calibration,
        engine_output_dir
    )

    measured_pixel = float(
        result["measured_pixel"]
    )

    std_pixel = float(
        result["std_pixel"]
    )

    valid_points = int(
        result["valid_point_count"]
    )

    # Diagnostic conversion only
    diagnostic_mm = (
        CAL_A * measured_pixel
        + CAL_B
    )

    diagnostic_in_spec = (
        SPEC_LOWER_MM
        <= diagnostic_mm
        <= SPEC_UPPER_MM
    )

    # Do not present this as a validated production OK/NG.
    diagnostic_result = (
        "IN_SPEC_DIAGNOSTIC"
        if diagnostic_in_spec
        else "OUT_OF_SPEC_DIAGNOSTIC"
    )

    reference_mm = (
        float(args.reference_mm)
        if args.reference_mm is not None
        else None
    )

    bias_mm = None
    abs_error_mm = None
    abs_error_um = None

    if reference_mm is not None:
        bias_mm = (
            diagnostic_mm
            - reference_mm
        )

        abs_error_mm = abs(
            bias_mm
        )

        abs_error_um = (
            abs_error_mm
            * 1000.0
        )

    # --------------------------------------------------------
    # Copy V3 engine outputs
    # --------------------------------------------------------
    final_engine_output = (
        output_dir / "engine_output"
    )

    copy_engine_outputs(
        engine_output_dir,
        final_engine_output
    )

    # --------------------------------------------------------
    # Result payload
    # --------------------------------------------------------
    summary = {
        "project_stage": "End-to-End Prototype + Pilot Validation",
        "calibration_status": CALIBRATION_STATUS,

        "image": str(image_path),
        "engine": str(engine_path),

        "image_size": {
            "width": int(image.shape[1]),
            "height": int(image.shape[0]),
        },

        "shaft_roi": list(
            shaft_box
        ),

        "measurement": {
            "measured_pixel": measured_pixel,
            "std_pixel": std_pixel,
            "valid_point_count": valid_points,
        },

        "diagnostic_calibration": {
            "equation": (
                "mm = "
                f"{CAL_A:.12f} * pixel + "
                f"{CAL_B:.12f}"
            ),
            "mm_per_pixel": CAL_A,
            "um_per_pixel": CAL_A * 1000.0,
            "r2": CAL_R2,
            "monotonic": CAL_MONOTONIC,
            "note": (
                "Diagnostic conversion only. "
                "Calibration linearity is not validated."
            ),
        },

        "diagnostic_result": {
            "converted_mm": diagnostic_mm,
            "spec_lower_mm": SPEC_LOWER_MM,
            "spec_upper_mm": SPEC_UPPER_MM,
            "status": diagnostic_result,
        },

        "reference_check": {
            "reference_mm": reference_mm,
            "bias_mm": bias_mm,
            "absolute_error_mm": abs_error_mm,
            "absolute_error_um": abs_error_um,
        },

        "warning": (
            "This result must not be used as final production "
            "metrology or authoritative OK/NG judgment."
        ),
    }

    json_path = (
        output_dir
        / "measurement_result.json"
    )

    json_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    txt_path = (
        output_dir
        / "measurement_result.txt"
    )

    with txt_path.open(
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "Shaft OD End-to-End V3\n"
        )
        f.write(
            "========================================\n"
        )

        f.write(
            "Project stage : "
            "End-to-End Prototype + Pilot Validation\n"
        )

        f.write(
            f"Calibration status : {CALIBRATION_STATUS}\n"
        )

        f.write(
            f"Image : {image_path}\n"
        )

        f.write(
            f"Engine : {engine_path}\n"
        )

        f.write(
            f"SHAFT ROI : {shaft_box}\n"
        )

        f.write(
            "\n[PIXEL MEASUREMENT]\n"
        )

        f.write(
            f"Measured pixel : {measured_pixel:.6f}\n"
        )

        f.write(
            f"STD(pixel) : {std_pixel:.6f}\n"
        )

        f.write(
            f"Valid points : {valid_points}\n"
        )

        f.write(
            "\n[DIAGNOSTIC PIXEL -> MM]\n"
        )

        f.write(
            "Equation : "
            f"mm = {CAL_A:.12f} * pixel "
            f"+ {CAL_B:.12f}\n"
        )

        f.write(
            f"mm/pixel : {CAL_A:.12f}\n"
        )

        f.write(
            f"um/pixel : {CAL_A * 1000.0:.6f}\n"
        )

        f.write(
            f"R2 : {CAL_R2:.8f}\n"
        )

        f.write(
            f"Monotonic : {CAL_MONOTONIC}\n"
        )

        f.write(
            f"Converted diameter(mm) : {diagnostic_mm:.6f}\n"
        )

        f.write(
            "Specification(mm) : "
            f"{SPEC_LOWER_MM:.3f} ~ "
            f"{SPEC_UPPER_MM:.3f}\n"
        )

        f.write(
            f"Diagnostic result : {diagnostic_result}\n"
        )

        if reference_mm is not None:
            f.write(
                "\n[REFERENCE CHECK]\n"
            )

            f.write(
                f"Reference(mm) : {reference_mm:.6f}\n"
            )

            f.write(
                f"Bias(mm) : {bias_mm:+.6f}\n"
            )

            f.write(
                f"Absolute error(mm) : {abs_error_mm:.6f}\n"
            )

            f.write(
                f"Absolute error(um) : {abs_error_um:.3f}\n"
            )

        f.write(
            "\n[WARNING]\n"
        )

        f.write(
            "Current calibration is diagnostic only.\n"
        )

        f.write(
            "Do not use this result as final production "
            "metrology or authoritative OK/NG judgment.\n"
        )

    # --------------------------------------------------------
    # Console output
    # --------------------------------------------------------
    print()
    print(
        "============================================================"
    )
    print(
        "Shaft OD End-to-End V3"
    )
    print(
        "Prototype + Pilot Validation"
    )
    print(
        "============================================================"
    )

    print(
        "Image :",
        image_path
    )

    print(
        "Engine :",
        engine_path
    )

    print(
        "SHAFT ROI :",
        shaft_box
    )

    print()
    print(
        "========== PIXEL MEASUREMENT =========="
    )

    print(
        "Measured pixel :",
        measured_pixel
    )

    print(
        "STD(pixel) :",
        std_pixel
    )

    print(
        "Valid points :",
        valid_points
    )

    print()
    print(
        "========== DIAGNOSTIC CALIBRATION =========="
    )

    print(
        "Equation : "
        f"mm = {CAL_A:.12f} * pixel "
        f"+ {CAL_B:.12f}"
    )

    print(
        "1 pixel =",
        f"{CAL_A * 1000.0:.6f}",
        "um"
    )

    print(
        "R2 :",
        CAL_R2
    )

    print(
        "Monotonic :",
        CAL_MONOTONIC
    )

    print(
        "Converted diameter(mm) :",
        diagnostic_mm
    )

    print(
        "Diagnostic result :",
        diagnostic_result
    )

    if reference_mm is not None:
        print()
        print(
            "========== REFERENCE CHECK =========="
        )

        print(
            "Reference(mm) :",
            reference_mm
        )

        print(
            "Bias(mm) :",
            bias_mm
        )

        print(
            "Absolute error(um) :",
            abs_error_um
        )

    print()
    print(
        "Calibration status :",
        CALIBRATION_STATUS
    )

    print(
        "WARNING: diagnostic conversion only; "
        "not validated for production OK/NG."
    )

    print()
    print(
        "Result TXT :",
        txt_path
    )

    print(
        "Result JSON:",
        json_path
    )

    print(
        "Engine output:",
        final_engine_output
    )

    print(
        "============================================================"
    )


if __name__ == "__main__":
    main()
