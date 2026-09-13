import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Shaft OD 현장 검증 V2",
    page_icon="📏",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = PROJECT_DIR / "measurement_data"
CAL_DIR = DATA_DIR / "calibration"
VAL_DIR = DATA_DIR / "validation"
MEAS_DIR = DATA_DIR / "measurement"
RESULT_DIR = DATA_DIR / "results"

for folder in [CAL_DIR, VAL_DIR, MEAS_DIR, RESULT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

CALIBRATION_FILE = BASE_DIR / "calibration_config_multi_point.json"
VALIDATION_FILE = BASE_DIR / "validation_status.json"
CAL_CSV = RESULT_DIR / "calibration_records.csv"
VAL_CSV = RESULT_DIR / "validation_records.csv"
MEAS_CSV = RESULT_DIR / "measurement_records.csv"

DEFAULT_SPEC_LOWER = 20.0100
DEFAULT_SPEC_UPPER = 20.0300
DEFAULT_REPEAT = 10

st.markdown(
    """
<style>
.block-container {max-width: 1200px; padding-top: 1.2rem; padding-bottom: 2rem;}
.main-title {font-size: 2rem; font-weight: 800; margin-bottom: .2rem;}
.sub-title {font-size: 1rem; opacity: .78; margin-bottom: 1rem;}
.box {padding: 14px 16px; border: 1px solid rgba(128,128,128,.28); border-radius: 12px; margin-bottom: 12px;}
.ok {padding: 18px; border-radius: 14px; font-size: 2rem; font-weight: 800; text-align: center;
     background: rgba(0,180,90,.12); border: 1px solid rgba(0,180,90,.35);}
.ng {padding: 18px; border-radius: 14px; font-size: 2rem; font-weight: 800; text-align: center;
     background: rgba(220,60,60,.12); border: 1px solid rgba(220,60,60,.35);}
</style>
""",
    unsafe_allow_html=True,
)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_id(text):
    text = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", str(text).strip())
    return text or "sample"


def parse_measurement_text(text):
    data = {}
    for line in str(text).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data


def as_float(value, default=None):
    if value is None:
        return default
    m = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(m.group()) if m else default


def call_measure_api(api_url, image_bytes, filename):
    files = {"file": (filename, image_bytes, "image/jpeg")}
    response = requests.post(api_url, files=files, timeout=120)
    response.raise_for_status()
    return response.json()


def extract_pixel_result(payload):
    result_text = payload.get("result_text") or payload.get("measurement_result") or ""
    parsed = parse_measurement_text(result_text)
    measured_pixel = payload.get("measured_pixel", as_float(parsed.get("Measured pixel")))
    confidence = payload.get("confidence", as_float(parsed.get("YOLO confidence")))
    return measured_pixel, confidence, result_text


def save_image(image_bytes, folder, prefix, sample_id, repeat_no):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{safe_id(sample_id)}_{repeat_no:02d}_{timestamp}.jpg"
    path = folder / filename
    path.write_bytes(image_bytes)
    return path


def append_csv(path, row, fieldnames):
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def read_csv_safe(path):
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def delete_sample_records(csv_path, sample_id):
    """선택 시편의 CSV 기록과 연결된 촬영 이미지만 삭제한다."""
    df = read_csv_safe(csv_path)
    if df.empty or "sample_id" not in df.columns:
        return 0, 0

    mask = df["sample_id"].astype(str) == str(sample_id)
    target = df[mask].copy()
    remain = df[~mask].copy()

    deleted_images = 0
    if "image_path" in target.columns:
        for raw_path in target["image_path"].dropna().astype(str):
            try:
                image_path = Path(raw_path)
                if image_path.exists() and image_path.is_file():
                    image_path.unlink()
                    deleted_images += 1
            except Exception:
                # 이미지 삭제 실패가 CSV 초기화 전체를 막지 않도록 한다.
                pass

    deleted_records = int(len(target))
    if remain.empty:
        if csv_path.exists():
            csv_path.unlink()
    else:
        remain.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return deleted_records, deleted_images


def clear_all_records(csv_path, image_folder=None):
    """CSV 전체와 해당 단계의 저장 이미지를 초기화한다."""
    deleted_records = 0
    df = read_csv_safe(csv_path)
    if not df.empty:
        deleted_records = int(len(df))

    if csv_path.exists():
        csv_path.unlink()

    deleted_images = 0
    if image_folder is not None and image_folder.exists():
        for image_path in image_folder.glob("*.jpg"):
            try:
                image_path.unlink()
                deleted_images += 1
            except Exception:
                pass

    return deleted_records, deleted_images


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path, default=None):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_calibration():
    data = load_json(CALIBRATION_FILE)
    if not data:
        return None
    required = {"calibration_type", "a", "b", "spec_lower", "spec_upper", "reference_points"}
    return data if required.issubset(data.keys()) else None


def pixel_to_mm(pixel, calibration):
    return float(calibration["a"]) * float(pixel) + float(calibration["b"])


def get_validation_status():
    return load_json(VALIDATION_FILE, {"approved": False}) or {"approved": False}


def reset_validation_status(reason="Calibration updated"):
    save_json(
        VALIDATION_FILE,
        {"approved": False, "updated_at": now_text(), "reason": reason},
    )


def get_input_image(label, key, input_mode):
    if input_mode == "모바일 카메라":
        return st.camera_input(label, key=key)
    return st.file_uploader(label, type=["jpg", "jpeg", "png"], key=key)


def image_hash(image_bytes):
    return hashlib.sha256(image_bytes).hexdigest()


def calibration_summary(df, sample_specs):
    rows = []
    for sample_id, actual_mm in sample_specs.items():
        part = df[df["sample_id"].astype(str) == str(sample_id)] if not df.empty else pd.DataFrame()
        pixels = pd.to_numeric(part.get("measured_pixel", pd.Series(dtype=float)), errors="coerce").dropna()
        rows.append(
            {
                "sample_id": sample_id,
                "actual_mm": float(actual_mm),
                "count": int(len(pixels)),
                "median_pixel": float(pixels.median()) if len(pixels) else np.nan,
                "mean_pixel": float(pixels.mean()) if len(pixels) else np.nan,
                "std_pixel": float(pixels.std(ddof=1)) if len(pixels) > 1 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def fit_calibration(summary_df, spec_lower, spec_upper, repeat_target):
    x = summary_df["median_pixel"].astype(float).to_numpy()
    y = summary_df["actual_mm"].astype(float).to_numpy()

    a, b = np.polyfit(x, y, 1)
    pred = a * x + b
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    ordered = np.sort(x)
    separations = np.diff(ordered)
    min_separation = float(np.min(np.abs(separations))) if len(separations) else 0.0
    max_std = float(summary_df["std_pixel"].max()) if len(summary_df) else 0.0
    separation_ratio = (min_separation / max_std) if max_std > 0 else None

    return {
        "calibration_type": "linear_multi_point",
        "a": float(a),
        "b": float(b),
        "r2_reference_fit": float(r2),
        "spec_lower": float(spec_lower),
        "spec_upper": float(spec_upper),
        "repeat_target": int(repeat_target),
        "reference_points": summary_df.to_dict(orient="records"),
        "min_reference_pixel_separation": min_separation,
        "max_reference_repeat_std_pixel": max_std,
        "separation_to_std_ratio": separation_ratio,
        "updated_at": now_text(),
        "note": "PoC multi-point calibration. Independent validation required before measurement use.",
    }


def validation_metrics(df):
    if df.empty:
        return None
    work = df.copy()
    work["error_mm"] = pd.to_numeric(work["error_mm"], errors="coerce")
    work["abs_error_mm"] = pd.to_numeric(work["abs_error_mm"], errors="coerce")
    work = work.dropna(subset=["error_mm", "abs_error_mm"])
    if work.empty:
        return None
    return {
        "n": int(len(work)),
        "mae_mm": float(work["abs_error_mm"].mean()),
        "max_abs_error_mm": float(work["abs_error_mm"].max()),
        "bias_mm": float(work["error_mm"].mean()),
        "std_error_mm": float(work["error_mm"].std(ddof=1)) if len(work) > 1 else 0.0,
    }


with st.sidebar:
    st.header("⚙️ 현장 설정")
    api_url = st.text_input("FastAPI 측정 주소", value="http://127.0.0.1:8000/measure")
    input_mode = st.radio("입력 방식", ["모바일 카메라", "이미지 업로드"])
    repeat_target = st.number_input(
        "Calibration / Validation 반복 횟수",
        min_value=2,
        max_value=30,
        value=DEFAULT_REPEAT,
        step=1,
    )
    st.divider()
    st.caption("촬영 조건 고정")
    st.write("📱 스마트폰 위치·거리·각도·줌 고정")
    st.write("🧰 동일 지그 / 동일 측정부")
    st.write("💡 동일 백라이트 조건")
    st.write("📷 동일 해상도")
    st.warning("촬영 기하조건이 바뀌면 Calibration을 다시 수행하세요.")


st.markdown('<div class="main-title">Shaft OD 현장 검증 V2</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">① 3점 반복 Calibration → ② 독립 Validation → ③ Measurement</div>',
    unsafe_allow_html=True,
)

calibration = load_calibration()
validation_status = get_validation_status()

s1, s2, s3 = st.columns(3)
s1.metric("Calibration", "완료" if calibration else "미완료")
s2.metric("Validation 승인", "완료" if validation_status.get("approved") else "미완료")
s3.metric("측정식", "mm = a×pixel + b" if calibration else "-")

if calibration:
    st.markdown(
        f"""
<div class="box">
<b>현재 Calibration 식</b><br>
mm = {calibration['a']:.10f} × pixel + {calibration['b']:.10f}<br>
참조점 fit R² = {calibration.get('r2_reference_fit', float('nan')):.6f}<br>
규격 = {calibration['spec_lower']:.4f} ~ {calibration['spec_upper']:.4f} mm<br>
저장 시각 = {calibration.get('updated_at', '-')}
</div>
""",
        unsafe_allow_html=True,
    )


tab_cal, tab_val, tab_meas, tab_data = st.tabs(
    ["① 3점 반복 Calibration", "② 독립 Validation", "③ Measurement", "④ 저장 데이터"]
)


with tab_cal:
    st.subheader("① 3점 반복 Calibration")
    st.info(
        "기준 샤프트 A/B/C의 신뢰 가능한 실측 mm를 입력하고 각 샤프트를 반복 촬영합니다. "
        "기존 YOLO/OpenCV 측정 엔진이 각 사진에서 대표 Pixel을 반환합니다."
    )

    spec1, spec2 = st.columns(2)
    spec_lower = spec1.number_input("규격 하한 (mm)", value=DEFAULT_SPEC_LOWER, step=0.001, format="%.4f")
    spec_upper = spec2.number_input("규격 상한 (mm)", value=DEFAULT_SPEC_UPPER, step=0.001, format="%.4f")

    a_col, b_col, c_col = st.columns(3)
    actual_a = a_col.number_input("A 기준 실측값 (mm)", value=20.0110, step=0.001, format="%.4f")
    actual_b = b_col.number_input("B 기준 실측값 (mm)", value=20.0200, step=0.001, format="%.4f")
    actual_c = c_col.number_input("C 기준 실측값 (mm)", value=20.0290, step=0.001, format="%.4f")
    sample_specs = {"A": actual_a, "B": actual_b, "C": actual_c}

    selected_cal_id = st.selectbox("지금 촬영할 Calibration 샤프트", ["A", "B", "C"])
    cal_df = read_csv_safe(CAL_CSV)
    current_count = 0
    if not cal_df.empty and "sample_id" in cal_df.columns:
        current_count = int((cal_df["sample_id"].astype(str) == selected_cal_id).sum())
    st.caption(f"{selected_cal_id} 현재 저장 횟수: {current_count} / 목표 {int(repeat_target)}회")

    cal_image = get_input_image(
        f"Calibration 샤프트 {selected_cal_id} 촬영/선택",
        key=f"cal_image_{selected_cal_id}",
        input_mode=input_mode,
    )

    if cal_image is not None:
        cal_bytes = cal_image.getvalue()
        st.image(Image.open(cal_image), caption=f"Calibration {selected_cal_id}", use_container_width=True)
        this_hash = image_hash(cal_bytes)
        duplicate_key = f"last_cal_hash_{selected_cal_id}"

        if st.button(f"➕ {selected_cal_id} 반복 측정 1회 저장", type="primary", use_container_width=True):
            if spec_lower >= spec_upper:
                st.error("규격 하한은 규격 상한보다 작아야 합니다.")
            elif st.session_state.get(duplicate_key) == this_hash:
                st.warning("같은 이미지는 이미 저장했습니다. 새로 촬영/선택하세요.")
            else:
                try:
                    with st.spinner("YOLO/OpenCV 대표 Pixel 측정 중..."):
                        repeat_no = current_count + 1
                        payload = call_measure_api(api_url, cal_bytes, f"CAL_{selected_cal_id}_{repeat_no:02d}.jpg")
                        measured_pixel, confidence, _ = extract_pixel_result(payload)
                        if measured_pixel is None or float(measured_pixel) <= 0:
                            raise ValueError("Measured pixel을 얻지 못했습니다.")

                        saved_path = save_image(cal_bytes, CAL_DIR, "CAL", selected_cal_id, repeat_no)
                        row = {
                            "timestamp": now_text(),
                            "sample_id": selected_cal_id,
                            "repeat_no": repeat_no,
                            "actual_mm": float(sample_specs[selected_cal_id]),
                            "measured_pixel": float(measured_pixel),
                            "confidence": confidence if confidence is not None else "",
                            "image_path": str(saved_path),
                        }
                        append_csv(
                            CAL_CSV,
                            row,
                            ["timestamp", "sample_id", "repeat_no", "actual_mm", "measured_pixel", "confidence", "image_path"],
                        )
                        st.session_state[duplicate_key] = this_hash
                        st.success(f"{selected_cal_id} {repeat_no}회 저장 완료: {float(measured_pixel):.4f} px")
                        st.rerun()
                except requests.exceptions.ConnectionError:
                    st.error("FastAPI 서버에 연결할 수 없습니다.")
                except Exception as e:
                    st.error(f"Calibration 측정 오류: {e}")

    cal_df = read_csv_safe(CAL_CSV)
    summary = calibration_summary(cal_df, sample_specs)
    st.markdown("#### 반복 측정 현황")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    enough = bool((summary["count"] >= int(repeat_target)).all())
    if enough:
        st.success("A/B/C가 모두 목표 반복 횟수에 도달했습니다.")
        if st.button("📐 3점 선형 Calibration 식 산출 및 저장", type="primary", use_container_width=True):
            try:
                new_cal = fit_calibration(summary, spec_lower, spec_upper, repeat_target)
                save_json(CALIBRATION_FILE, new_cal)
                # 새 Calibration 식을 만들면 이전 Validation 데이터는 새 식의 검증으로 사용할 수 없다.
                clear_all_records(VAL_CSV, VAL_DIR)
                reset_validation_status("New calibration created; independent validation required")
                st.success("Calibration 식을 저장했습니다. 이전 Validation 기록은 초기화되었으며, 다음은 ② 독립 Validation입니다.")
                st.code(
                    f"mm = {new_cal['a']:.10f} × pixel + {new_cal['b']:.10f}\n"
                    f"Reference fit R² = {new_cal['r2_reference_fit']:.6f}",
                    language="text",
                )
                ratio = new_cal.get("separation_to_std_ratio")
                if ratio is not None:
                    st.write(f"기준시편 최소 Pixel 간격 / 최대 반복 SD = {ratio:.2f}")
                    if ratio < 3:
                        st.warning(
                            "기준시편 간 Pixel 분리가 반복 흔들림에 비해 작습니다. "
                            "3배 기준은 공식 합격기준이 아닌 PoC 확인용 경고입니다."
                        )
                st.rerun()
            except Exception as e:
                st.error(f"Calibration 식 산출 오류: {e}")
    else:
        st.warning("A/B/C 각각 목표 반복 횟수까지 저장해야 Calibration 식을 산출합니다.")

    st.divider()
    with st.expander("Calibration 재촬영 / 초기화"):
        st.info(
            "A/B/C 중 한 시편의 반복 촬영이 실패했으면 해당 시편만 지우고 다시 촬영할 수 있습니다. "
            "선택 시편을 지우면 기존 Calibration 식과 Validation 승인은 무효화됩니다."
        )

        reset_cal_id = st.selectbox(
            "재촬영할 Calibration 시편",
            ["A", "B", "C"],
            key="reset_cal_sample_id",
        )
        confirm_sample_reset = st.checkbox(
            f"{reset_cal_id} 기록과 촬영 이미지를 삭제하고 재촬영하겠습니다.",
            key="confirm_cal_sample_reset",
        )
        if st.button(
            f"🗑️ {reset_cal_id}만 초기화 → 재촬영",
            disabled=not confirm_sample_reset,
            use_container_width=True,
        ):
            deleted_records, deleted_images = delete_sample_records(CAL_CSV, reset_cal_id)
            if CALIBRATION_FILE.exists():
                CALIBRATION_FILE.unlink()

            # Calibration이 바뀌면 이전 Validation 결과는 더 이상 유효하지 않다.
            clear_all_records(VAL_CSV, VAL_DIR)
            reset_validation_status(f"Calibration sample {reset_cal_id} reset; validation must be repeated")
            st.session_state.pop(f"last_cal_hash_{reset_cal_id}", None)

            st.success(
                f"{reset_cal_id} 초기화 완료: 기록 {deleted_records}건, 이미지 {deleted_images}개 삭제. "
                "이제 같은 시편을 처음부터 다시 촬영하세요."
            )
            st.rerun()

        st.divider()
        st.warning(
            "아래 전체 초기화는 A/B/C Calibration을 모두 처음부터 다시 할 때만 사용하세요. "
            "연결된 Validation 기록/승인도 함께 초기화됩니다."
        )
        confirm_all_cal_reset = st.checkbox(
            "Calibration A/B/C 전체 기록과 촬영 이미지를 모두 삭제하겠습니다.",
            key="confirm_all_cal_reset",
        )
        if st.button(
            "🗑️ Calibration 전체 초기화",
            disabled=not confirm_all_cal_reset,
            use_container_width=True,
        ):
            deleted_records, deleted_images = clear_all_records(CAL_CSV, CAL_DIR)
            if CALIBRATION_FILE.exists():
                CALIBRATION_FILE.unlink()
            clear_all_records(VAL_CSV, VAL_DIR)
            reset_validation_status("Calibration reset; validation must be repeated")
            for sid in ["A", "B", "C"]:
                st.session_state.pop(f"last_cal_hash_{sid}", None)
            st.success(
                f"Calibration 전체 초기화 완료: 기록 {deleted_records}건, 이미지 {deleted_images}개 삭제."
            )
            st.rerun()


with tab_val:
    st.subheader("② 독립 Validation")
    calibration = load_calibration()
    if not calibration:
        st.warning("먼저 ① Calibration을 완료하세요.")
    else:
        st.info(
            "Calibration에 사용하지 않은 D/E/F 샤프트를 사용합니다. "
            "저장된 mm = a×pixel+b를 적용한 비전 측정값과 기준 계측값을 비교합니다."
        )

        d_col, e_col, f_col = st.columns(3)
        actual_d = d_col.number_input("D 검증 기준값 (mm)", value=20.0140, step=0.001, format="%.4f")
        actual_e = e_col.number_input("E 검증 기준값 (mm)", value=20.0220, step=0.001, format="%.4f")
        actual_f = f_col.number_input("F 검증 기준값 (mm)", value=20.0270, step=0.001, format="%.4f")
        val_specs = {"D": actual_d, "E": actual_e, "F": actual_f}

        selected_val_id = st.selectbox("지금 촬영할 Validation 샤프트", ["D", "E", "F"])
        val_df = read_csv_safe(VAL_CSV)
        current_val_count = 0
        if not val_df.empty and "sample_id" in val_df.columns:
            current_val_count = int((val_df["sample_id"].astype(str) == selected_val_id).sum())
        st.caption(f"{selected_val_id} 현재 저장 횟수: {current_val_count} / 목표 {int(repeat_target)}회")

        val_image = get_input_image(
            f"Validation 샤프트 {selected_val_id} 촬영/선택",
            key=f"val_image_{selected_val_id}",
            input_mode=input_mode,
        )

        if val_image is not None:
            val_bytes = val_image.getvalue()
            st.image(Image.open(val_image), caption=f"Validation {selected_val_id}", use_container_width=True)
            this_hash = image_hash(val_bytes)
            duplicate_key = f"last_val_hash_{selected_val_id}"

            if st.button(f"➕ {selected_val_id} 검증 측정 1회 저장", type="primary", use_container_width=True):
                if st.session_state.get(duplicate_key) == this_hash:
                    st.warning("같은 이미지는 이미 저장했습니다. 새로 촬영/선택하세요.")
                else:
                    try:
                        with st.spinner("독립 검증 측정 중..."):
                            repeat_no = current_val_count + 1
                            payload = call_measure_api(api_url, val_bytes, f"VAL_{selected_val_id}_{repeat_no:02d}.jpg")
                            measured_pixel, confidence, _ = extract_pixel_result(payload)
                            if measured_pixel is None or float(measured_pixel) <= 0:
                                raise ValueError("Measured pixel을 얻지 못했습니다.")

                            measured_mm = pixel_to_mm(measured_pixel, calibration)
                            actual_mm = float(val_specs[selected_val_id])
                            error_mm = measured_mm - actual_mm
                            abs_error_mm = abs(error_mm)
                            saved_path = save_image(val_bytes, VAL_DIR, "VAL", selected_val_id, repeat_no)

                            row = {
                                "timestamp": now_text(),
                                "sample_id": selected_val_id,
                                "repeat_no": repeat_no,
                                "actual_mm": actual_mm,
                                "measured_pixel": float(measured_pixel),
                                "measured_mm": float(measured_mm),
                                "error_mm": float(error_mm),
                                "abs_error_mm": float(abs_error_mm),
                                "confidence": confidence if confidence is not None else "",
                                "image_path": str(saved_path),
                            }
                            append_csv(
                                VAL_CSV,
                                row,
                                ["timestamp", "sample_id", "repeat_no", "actual_mm", "measured_pixel", "measured_mm", "error_mm", "abs_error_mm", "confidence", "image_path"],
                            )
                            st.session_state[duplicate_key] = this_hash
                            st.success(
                                f"{selected_val_id} {repeat_no}회 저장 완료 | "
                                f"비전 {measured_mm:.4f} mm | 오차 {error_mm:+.4f} mm"
                            )
                            st.rerun()
                    except requests.exceptions.ConnectionError:
                        st.error("FastAPI 서버에 연결할 수 없습니다.")
                    except Exception as e:
                        st.error(f"Validation 오류: {e}")

        val_df = read_csv_safe(VAL_CSV)
        if not val_df.empty:
            st.markdown("#### Validation 저장 결과")
            st.dataframe(val_df.tail(50), use_container_width=True, hide_index=True)
            metrics = validation_metrics(val_df)
            if metrics:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Validation N", metrics["n"])
                m2.metric("MAE", f"{metrics['mae_mm']:.6f} mm")
                m3.metric("Max |Error|", f"{metrics['max_abs_error_mm']:.6f} mm")
                m4.metric("Bias", f"{metrics['bias_mm']:+.6f} mm")

            counts = val_df.groupby(val_df["sample_id"].astype(str)).size().to_dict()
            val_enough = all(int(counts.get(s, 0)) >= int(repeat_target) for s in ["D", "E", "F"])
            if val_enough:
                st.success("D/E/F가 모두 목표 반복 횟수에 도달했습니다.")
                st.warning(
                    "아래 승인은 자동 정확도 인증이 아닙니다. MAE·최대오차·반복성 및 기준계측기 조건을 "
                    "사용자가 검토한 뒤 승인합니다."
                )
                if st.button("✅ Validation 검토 완료 → Measurement 사용 승인", type="primary", use_container_width=True):
                    save_json(
                        VALIDATION_FILE,
                        {
                            "approved": True,
                            "approved_at": now_text(),
                            "calibration_updated_at": calibration.get("updated_at"),
                            "metrics": metrics,
                            "note": "User-reviewed PoC validation approval; not a metrology certification.",
                        },
                    )
                    st.success("Measurement 사용 승인을 저장했습니다.")
                    st.rerun()
            else:
                st.info("D/E/F 각각 목표 반복 횟수까지 측정하면 최종 Validation 지표를 확인할 수 있습니다.")
        else:
            st.info("아직 Validation 데이터가 없습니다.")

        st.divider()
        with st.expander("Validation 재촬영 / 초기화"):
            st.info(
                "D/E/F 중 한 시편의 검증 촬영이 실패했으면 해당 시편만 지우고 다시 촬영할 수 있습니다. "
                "선택 시편을 지우면 Measurement 사용 승인은 자동 해제됩니다."
            )

            reset_val_id = st.selectbox(
                "재촬영할 Validation 시편",
                ["D", "E", "F"],
                key="reset_val_sample_id",
            )
            confirm_val_sample_reset = st.checkbox(
                f"{reset_val_id} 기록과 촬영 이미지를 삭제하고 재검증하겠습니다.",
                key="confirm_val_sample_reset",
            )
            if st.button(
                f"🗑️ {reset_val_id}만 초기화 → 재촬영",
                disabled=not confirm_val_sample_reset,
                use_container_width=True,
            ):
                deleted_records, deleted_images = delete_sample_records(VAL_CSV, reset_val_id)
                reset_validation_status(f"Validation sample {reset_val_id} reset")
                st.session_state.pop(f"last_val_hash_{reset_val_id}", None)
                st.success(
                    f"{reset_val_id} 초기화 완료: 기록 {deleted_records}건, 이미지 {deleted_images}개 삭제. "
                    "이제 같은 시편을 처음부터 다시 촬영하세요."
                )
                st.rerun()

            st.divider()
            confirm_all_val_reset = st.checkbox(
                "Validation D/E/F 전체 기록과 촬영 이미지를 모두 삭제하겠습니다.",
                key="confirm_all_val_reset",
            )
            if st.button(
                "🗑️ Validation 전체 초기화",
                disabled=not confirm_all_val_reset,
                use_container_width=True,
            ):
                deleted_records, deleted_images = clear_all_records(VAL_CSV, VAL_DIR)
                reset_validation_status("Validation reset")
                for sid in ["D", "E", "F"]:
                    st.session_state.pop(f"last_val_hash_{sid}", None)
                st.success(
                    f"Validation 전체 초기화 완료: 기록 {deleted_records}건, 이미지 {deleted_images}개 삭제."
                )
                st.rerun()


with tab_meas:
    st.subheader("③ Measurement")
    calibration = load_calibration()
    validation_status = get_validation_status()

    if not calibration:
        st.warning("먼저 ① Calibration을 완료하세요.")
    elif not validation_status.get("approved"):
        st.warning("② 독립 Validation 결과를 검토하고 Measurement 사용 승인을 완료하세요.")
    else:
        st.success("검토 승인된 Calibration 식을 Measurement에 적용합니다.")
        selected_meas_id = st.selectbox("측정 시편 ID", ["G", "H", "I", "J", "기타"])
        if selected_meas_id == "기타":
            selected_meas_id = st.text_input("시편 ID 직접 입력", value="M01")

        meas_image = get_input_image(
            "측정할 샤프트 촬영/선택",
            key="measurement_image_v2",
            input_mode=input_mode,
        )

        if meas_image is not None:
            meas_bytes = meas_image.getvalue()
            st.image(Image.open(meas_image), caption=f"Measurement {selected_meas_id}", use_container_width=True)
            this_hash = image_hash(meas_bytes)

            if st.session_state.get("last_measure_hash_v2") == this_hash:
                cached = st.session_state.get("last_measure_result_v2")
                if cached:
                    st.metric("측정 외경", f"{cached['measured_mm']:.4f} mm")
                    st.markdown(
                        '<div class="ok">✅ OK</div>' if cached["result"] == "OK" else '<div class="ng">❌ NG</div>',
                        unsafe_allow_html=True,
                    )
            else:
                try:
                    with st.spinner("YOLO/OpenCV Pixel → 검증된 Calibration → mm → OK/NG..."):
                        payload = call_measure_api(api_url, meas_bytes, f"MEAS_{safe_id(selected_meas_id)}.jpg")
                        measured_pixel, confidence, _ = extract_pixel_result(payload)
                        if measured_pixel is None or float(measured_pixel) <= 0:
                            raise ValueError("Measured pixel을 얻지 못했습니다.")

                        measured_mm = pixel_to_mm(measured_pixel, calibration)
                        spec_lower = float(calibration["spec_lower"])
                        spec_upper = float(calibration["spec_upper"])
                        result = "OK" if spec_lower <= measured_mm <= spec_upper else "NG"

                        meas_df = read_csv_safe(MEAS_CSV)
                        repeat_no = 1
                        if not meas_df.empty and "sample_id" in meas_df.columns:
                            repeat_no = int((meas_df["sample_id"].astype(str) == str(selected_meas_id)).sum()) + 1
                        saved_path = save_image(meas_bytes, MEAS_DIR, "MEAS", selected_meas_id, repeat_no)

                        row = {
                            "timestamp": now_text(),
                            "sample_id": selected_meas_id,
                            "repeat_no": repeat_no,
                            "measured_pixel": float(measured_pixel),
                            "measured_mm": float(measured_mm),
                            "spec_lower": spec_lower,
                            "spec_upper": spec_upper,
                            "result": result,
                            "confidence": confidence if confidence is not None else "",
                            "calibration_a": float(calibration["a"]),
                            "calibration_b": float(calibration["b"]),
                            "image_path": str(saved_path),
                        }
                        append_csv(
                            MEAS_CSV,
                            row,
                            ["timestamp", "sample_id", "repeat_no", "measured_pixel", "measured_mm", "spec_lower", "spec_upper", "result", "confidence", "calibration_a", "calibration_b", "image_path"],
                        )

                        st.session_state["last_measure_hash_v2"] = this_hash
                        st.session_state["last_measure_result_v2"] = {
                            "measured_mm": measured_mm,
                            "result": result,
                        }

                        m1, m2, m3 = st.columns(3)
                        m1.metric("대표 Pixel", f"{float(measured_pixel):.4f} px")
                        m2.metric("측정 외경", f"{measured_mm:.4f} mm")
                        m3.metric("YOLO Confidence", f"{confidence:.3f}" if confidence is not None else "-")
                        st.caption(f"적용식: mm = {calibration['a']:.10f} × pixel + {calibration['b']:.10f}")
                        st.caption(f"규격: {spec_lower:.4f} ~ {spec_upper:.4f} mm")
                        st.markdown(
                            '<div class="ok">✅ OK</div>' if result == "OK" else '<div class="ng">❌ NG</div>',
                            unsafe_allow_html=True,
                        )
                except requests.exceptions.ConnectionError:
                    st.error("FastAPI 서버에 연결할 수 없습니다.")
                except Exception as e:
                    st.error(f"Measurement 오류: {e}")


with tab_data:
    st.subheader("④ 저장 데이터 확인")
    st.caption(f"저장 폴더: {DATA_DIR}")

    for title, path in [
        ("Calibration records", CAL_CSV),
        ("Validation records", VAL_CSV),
        ("Measurement records", MEAS_CSV),
    ]:
        st.markdown(f"#### {title}")
        df = read_csv_safe(path)
        if df.empty:
            st.info("저장 데이터 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                f"⬇ {title} CSV 다운로드",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=path.name,
                mime="text/csv",
                key=f"download_{path.name}",
            )

    calibration = load_calibration()
    if calibration:
        st.markdown("#### Calibration JSON")
        st.json(calibration)

    st.markdown("#### 폴더 구조")
    st.code(
        """12_System_Integration/
└─ measurement_data/
   ├─ calibration/   # A/B/C 반복 촬영 이미지
   ├─ validation/    # D/E/F 반복 촬영 이미지
   ├─ measurement/   # G/H/I/J 실제 측정 이미지
   └─ results/
      ├─ calibration_records.csv
      ├─ validation_records.csv
      └─ measurement_records.csv
""",
        language="text",
    )

st.divider()
st.caption(
    "PoC 현장 검증용입니다. Calibration 시편과 Validation 시편은 분리해야 하며, "
    "Validation 합격기준은 제품 공차와 별도로 계측시스템 목적에 맞게 정해야 합니다."
)
