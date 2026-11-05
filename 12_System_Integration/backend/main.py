"""FastAPI adapter for Shaft OD V3 Reflection Edge.

Modes: calibration (raw pixel), validation (active calibration), measurement
(active calibration + validation approval). The frontend and backend must run
from the SAME 12_System_Integration project directory / shared filesystem.
"""
from __future__ import annotations

from datetime import datetime
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "database"))
from database import init_db, save_measurement  # noqa: E402

ENGINE = BASE_DIR / "measurement" / "measurement_engine_EDGE_V3_REFLECTION.py"
BASE_CALIBRATION = BASE_DIR / "measurement" / "calibration_config_abc.json"
ACTIVE_CALIBRATION = BASE_DIR / "frontend" / "calibration_config_multi_point.json"
VALIDATION_STATUS = BASE_DIR / "frontend" / "validation_status.json"
MODEL = BASE_DIR / "measurement" / "models" / "best.pt"
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
OUTPUT_ROOT = BASE_DIR / "measurement" / "output_v3"
SPEC_LOWER, SPEC_UPPER = 20.010, 20.030
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
MAX_IMAGE_BYTES = 100 * 1024 * 1024

app = FastAPI(title="Shaft OD Measurement API", version="2.0-v3")


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=f"설정 파일을 읽을 수 없습니다: {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=409, detail=f"설정 파일 구조 오류: {path.name}")
    return data


def _calibration(path: Path, require_full: bool) -> dict:
    data = _load_json(path)
    required = {"a", "b"}
    if require_full:
        required |= {"calibration_type", "spec_lower", "spec_upper", "reference_points", "updated_at"}
    if not required.issubset(data):
        raise HTTPException(status_code=409, detail=f"Calibration 항목 부족: {path.name}")
    try:
        a, b = float(data["a"]), float(data["b"])
        lo = float(data.get("spec_lower", SPEC_LOWER))
        hi = float(data.get("spec_upper", SPEC_UPPER))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=409, detail="Calibration 계수/규격 형식 오류") from exc
    if not all(math.isfinite(v) for v in (a, b, lo, hi)) or a <= 0 or lo >= hi:
        raise HTTPException(status_code=409, detail="Calibration 값이 유효하지 않습니다")
    if require_full and (not isinstance(data["reference_points"], list) or not data["reference_points"]):
        raise HTTPException(status_code=409, detail="Calibration 기준점 정보 없음")
    return data


def _validated(cal: dict):
    status = _load_json(VALIDATION_STATUS)
    if status.get("approved") is not True or status.get("calibration_updated_at") != cal.get("updated_at"):
        raise HTTPException(status_code=409, detail="현재 Calibration에 대한 Independent Validation 승인이 필요합니다")


def _number(data: dict, key: str) -> float:
    try:
        val = float(data[key])
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"V3 결과 값 오류: {key}") from exc
    if not math.isfinite(val):
        raise HTTPException(status_code=422, detail=f"V3 결과가 유효한 숫자가 아닙니다: {key}")
    return val


def _confidence(value):
    try:
        val = float(value)
        return val if math.isfinite(val) else None
    except (ValueError, TypeError):
        return None


@app.on_event("startup")
def startup():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "shaft_od_measurement", "engine": "V3_REFLECTION"}


@app.post("/measure")
async def measure(file: UploadFile = File(...), phase: str = Form("measurement"),
                  expected_calibration_updated_at: str = Form("")):
    if phase not in {"calibration", "validation", "measurement"}:
        raise HTTPException(status_code=400, detail="phase는 calibration/validation/measurement 중 하나여야 합니다")
    original_name = Path((file.filename or "").replace("\\", "/")).name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="지원하지 않는 이미지 확장자입니다")
    calibration_path = BASE_CALIBRATION if phase == "calibration" else ACTIVE_CALIBRATION
    if not ENGINE.is_file() or not calibration_path.is_file():
        raise HTTPException(status_code=409, detail="V3 엔진 또는 해당 단계의 Calibration 파일이 없습니다")
    cal = _calibration(calibration_path, require_full=(phase != "calibration"))
    if phase != "calibration" and expected_calibration_updated_at != cal.get("updated_at"):
        raise HTTPException(status_code=409, detail="요청 시점의 Calibration 버전과 서버 버전이 다릅니다")
    if phase == "measurement":
        _validated(cal)
    roi_box = os.environ.get("SHAFT_MEASUREMENT_BOX", "").strip()
    if not roi_box and not MODEL.is_file():
        raise HTTPException(status_code=409, detail="YOLO best.pt가 없습니다. 모델을 설치하거나 진단용 SHAFT_MEASUREMENT_BOX를 지정하세요")

    request_id = uuid4().hex
    image_path = UPLOAD_DIR / f"{request_id}{suffix}"
    output_dir = OUTPUT_ROOT / request_id
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        image_bytes = await file.read(MAX_IMAGE_BYTES + 1)
        if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="이미지가 비어 있거나 100MB를 초과합니다")
        image_path.write_bytes(image_bytes)
        cmd = [sys.executable, str(ENGINE), str(image_path),
               "--calibration", str(calibration_path), "--output-dir", str(output_dir)]
        if roi_box:
            cmd += ["--box", roi_box]
        else:
            cmd += ["--model", str(MODEL)]
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR))
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="V3 측정 제한시간 초과") from exc
        if process.returncode != 0:
            raise HTTPException(status_code=422, detail=f"V3 측정 실패(REJECT): {(process.stderr or process.stdout)[-1200:]}")
        try:
            data = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="V3 JSON 결과를 읽을 수 없습니다") from exc
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="V3 JSON 형식 오류")
        pixel = _number(data, "measured_pixel")
        std_pixel = _number(data, "std_pixel")
        valid_count = int(_number(data, "valid_point_count"))
        confidence = _confidence(data.get("confidence"))
        if pixel <= 0 or valid_count < 8 or valid_count > 31 or std_pixel < 0:
            raise HTTPException(status_code=422, detail="Edge 품질 불충분: REJECT")
        measured_mm = float(cal["a"]) * pixel + float(cal["b"])
        engine_mm = _number(data, "measured_mm_existing_calibration")
        if abs(engine_mm - measured_mm) > 1e-7:
            raise HTTPException(status_code=409, detail="엔진과 Backend의 Calibration 계산이 일치하지 않습니다")
        lower = float(cal.get("spec_lower", SPEC_LOWER))
        upper = float(cal.get("spec_upper", SPEC_UPPER))
        result = "OK" if lower <= measured_mm <= upper else "NG"

        # The frontend owns calibration/validation/measurement CSVs. Persist only
        # validated production-style measurements in the legacy SQLite table.
        if phase == "measurement":
            try:
                save_measurement(
                    measured_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    filename=original_name, confidence=confidence, measured_pixel=pixel,
                    measured_mm=measured_mm, spec_lower=lower, spec_upper=upper, result=result,
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"SQLite 저장 실패: {exc}") from exc

        result_text = (f"YOLO confidence: {confidence if confidence is not None else 'N/A'}\n"
                       f"Measured pixel: {pixel:.9f}\nMeasured mm: {measured_mm:.9f}\n"
                       f"Specification: {lower:.4f} ~ {upper:.4f} mm\nResult: {result}\n"
                       f"Engine: V3_REFLECTION\nValid edge points: {valid_count}\n")
        return {
            "status": "success", "phase": phase, "request_id": request_id,
            "filename": original_name, "engine": "V3_REFLECTION",
            "measured_pixel": pixel, "measured_mm": measured_mm,
            "confidence": confidence, "std_pixel": std_pixel,
            "valid_point_count": valid_count, "spec_lower": lower, "spec_upper": upper,
            "result": result, "calibration_a": float(cal["a"]),
            "calibration_b": float(cal["b"]),
            "calibration_updated_at": cal.get("updated_at"),
            "measurement_result": result_text, "result_text": result_text,
        }
    finally:
        await file.close()
