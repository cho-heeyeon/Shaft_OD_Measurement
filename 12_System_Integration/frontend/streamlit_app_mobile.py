import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
from PIL import Image

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="Shaft OD 현장 자동측정",
    page_icon="📏",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
CALIBRATION_FILE = BASE_DIR / "calibration_config.json"

# 기존 End-to-End V1 기준값
DEFAULT_CALIBRATION = {
    "reference_mm": 20.0210,
    "reference_pixel": 464.0600,
    "spec_lower": 20.0100,
    "spec_upper": 20.0300,
    "updated_at": "End-to-End V1 default",
}

st.markdown(
    """
<style>
.block-container {
    max-width: 1150px;
    padding-top: 1.4rem;
    padding-bottom: 2rem;
}
.main-title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: .2rem;
}
.sub-title {
    font-size: 1rem;
    opacity: .75;
    margin-bottom: 1.2rem;
}
.card {
    padding: 18px 20px;
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 14px;
    margin-bottom: 10px;
}
.ok {
    padding:18px;
    border-radius:14px;
    font-size:2rem;
    font-weight:800;
    text-align:center;
    background:rgba(0,180,90,.12);
    border:1px solid rgba(0,180,90,.35);
}
.ng {
    padding:18px;
    border-radius:14px;
    font-size:2rem;
    font-weight:800;
    text-align:center;
    background:rgba(220,60,60,.12);
    border:1px solid rgba(220,60,60,.35);
}
.cal-box {
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(80,140,255,.35);
    background: rgba(80,140,255,.08);
    margin-bottom: 14px;
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 공통 함수
# =========================================================
def load_calibration():
    if CALIBRATION_FILE.exists():
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            required = {"reference_mm", "reference_pixel", "spec_lower", "spec_upper"}
            if required.issubset(data.keys()):
                return data
        except Exception:
            pass

    return DEFAULT_CALIBRATION.copy()


def save_calibration(data):
    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_measurement_text(text):
    data = {}
    for line in text.splitlines():
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
    """
    FastAPI /measure 결과에서 '측정 Pixel'만 추출한다.
    mm 환산은 아래의 저장된 Calibration 값을 사용해 Streamlit에서 다시 계산한다.
    """
    result_text = payload.get("result_text") or payload.get("measurement_result") or ""
    parsed = parse_measurement_text(result_text)

    measured_pixel = payload.get(
        "measured_pixel",
        as_float(parsed.get("Measured pixel"))
    )

    confidence = payload.get(
        "confidence",
        as_float(parsed.get("YOLO confidence"))
    )

    return measured_pixel, confidence, result_text


def pixel_to_mm(measured_pixel, calibration):
    ref_pixel = float(calibration["reference_pixel"])
    ref_mm = float(calibration["reference_mm"])

    if ref_pixel <= 0:
        raise ValueError("Calibration Pixel은 0보다 커야 합니다.")

    mm_per_pixel = ref_mm / ref_pixel
    measured_mm = measured_pixel * mm_per_pixel
    return measured_mm, mm_per_pixel


def render_measurement_result(
    measured_pixel,
    confidence,
    measured_mm,
    mm_per_pixel,
    calibration,
    result_text=""
):
    spec_lower = float(calibration["spec_lower"])
    spec_upper = float(calibration["spec_upper"])

    result = "OK" if spec_lower <= measured_mm <= spec_upper else "NG"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("측정 외경", f"{measured_mm:.4f} mm")
    c2.metric("측정 Pixel", f"{measured_pixel:.4f} px")
    c3.metric(
        "1 Pixel 환산값",
        f"{mm_per_pixel:.6f} mm/px"
    )
    c4.metric(
        "YOLO Confidence",
        f"{confidence:.3f}" if confidence is not None else "-"
    )

    st.caption(
        f"현재 Calibration: "
        f"{calibration['reference_mm']:.4f} mm = "
        f"{calibration['reference_pixel']:.4f} px"
    )
    st.caption(
        f"판정 규격: {spec_lower:.3f} ~ {spec_upper:.3f} mm"
    )

    if result == "OK":
        st.markdown('<div class="ok">✅ OK</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ng">❌ NG</div>', unsafe_allow_html=True)

    with st.expander("상세 결과 보기"):
        st.write(f"Measured Pixel : {measured_pixel:.6f}")
        st.write(f"mm / Pixel : {mm_per_pixel:.9f}")
        st.write(f"Measured mm : {measured_mm:.6f}")
        st.write(f"Specification : {spec_lower:.4f} ~ {spec_upper:.4f} mm")
        st.write(f"Result : {result}")

        if result_text:
            st.divider()
            st.caption("기존 End-to-End V1 원본 응답")
            st.code(result_text, language="text")


# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.header("⚙️ 현장 설정")

    api_url = st.text_input(
        "FastAPI 측정 주소",
        value="http://127.0.0.1:8000/measure"
    )

    input_mode = st.radio(
        "입력 방식",
        ["모바일 카메라", "이미지 업로드"]
    )

    st.divider()
    st.caption("권장 설치 조건")
    st.write("📱 스마트폰 위치 고정")
    st.write("🧰 샤프트 고정 지그")
    st.write("💡 A4 LED 백라이트")
    st.write("📐 거리·각도·줌 고정")
    st.write("📷 동일 해상도 사용")


# =========================================================
# 제목 / 현재 Calibration 표시
# =========================================================
st.markdown(
    '<div class="main-title">Shaft OD 현장 자동측정</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">'
    '① Calibration → ② 자동 측정 | '
    '모바일 + 고정 지그 + 백라이트 + YOLO/OpenCV End-to-End V1'
    '</div>',
    unsafe_allow_html=True
)

calibration = load_calibration()

st.markdown(
    f"""
<div class="cal-box">
<b>현재 적용 Calibration</b><br>
기준 실측값 : {calibration['reference_mm']:.4f} mm<br>
기준 Pixel : {calibration['reference_pixel']:.4f} px<br>
1 Pixel : {calibration['reference_mm'] / calibration['reference_pixel']:.6f} mm/px<br>
규격 : {calibration['spec_lower']:.3f} ~ {calibration['spec_upper']:.3f} mm<br>
저장 시각 : {calibration.get('updated_at', '-')}
</div>
""",
    unsafe_allow_html=True
)


# =========================================================
# ① Calibration / ② 자동 측정
# =========================================================
tab_cal, tab_measure = st.tabs(
    ["① Calibration", "② 자동 측정"]
)


# =========================================================
# TAB 1 : Calibration
# =========================================================
with tab_cal:
    st.subheader("① Calibration")

    st.info(
        "카메라 거리·각도·줌·해상도·지그·백라이트 조건을 먼저 고정한 뒤 "
        "기준 샤프트를 촬영하세요."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        reference_mm = st.number_input(
            "기준 샤프트 실측값 (mm)",
            min_value=0.001,
            value=float(calibration["reference_mm"]),
            step=0.001,
            format="%.4f"
        )

    with c2:
        spec_lower = st.number_input(
            "규격 하한 (mm)",
            value=float(calibration["spec_lower"]),
            step=0.001,
            format="%.4f"
        )

    with c3:
        spec_upper = st.number_input(
            "규격 상한 (mm)",
            value=float(calibration["spec_upper"]),
            step=0.001,
            format="%.4f"
        )

    calibration_image = None

    if input_mode == "모바일 카메라":
        calibration_image = st.camera_input(
            "기준 샤프트를 놓고 Calibration 촬영",
            key="calibration_camera"
        )
    else:
        calibration_image = st.file_uploader(
            "기준 샤프트 이미지 선택",
            type=["jpg", "jpeg", "png"],
            key="calibration_upload"
        )

    if calibration_image is not None:
        image_bytes = calibration_image.getvalue()
        st.image(
            Image.open(calibration_image),
            caption="Calibration 입력 이미지",
            use_container_width=True
        )

        if st.button(
            "💾 Calibration 측정 및 저장",
            type="primary",
            use_container_width=True
        ):
            if spec_lower >= spec_upper:
                st.error("규격 하한은 규격 상한보다 작아야 합니다.")
            else:
                filename = (
                    getattr(calibration_image, "name", None)
                    or f"calibration_{datetime.now():%Y%m%d_%H%M%S}.jpg"
                )

                with st.spinner(
                    "기준 샤프트 Pixel 측정 중..."
                ):
                    try:
                        payload = call_measure_api(
                            api_url,
                            image_bytes,
                            filename
                        )

                        measured_pixel, confidence, result_text = (
                            extract_pixel_result(payload)
                        )

                        if measured_pixel is None:
                            st.error(
                                "FastAPI 응답에서 Measured pixel 값을 찾지 못했습니다."
                            )
                        elif measured_pixel <= 0:
                            st.error(
                                "Calibration Pixel이 0 이하입니다. 촬영 조건을 확인하세요."
                            )
                        else:
                            new_calibration = {
                                "reference_mm": float(reference_mm),
                                "reference_pixel": float(measured_pixel),
                                "spec_lower": float(spec_lower),
                                "spec_upper": float(spec_upper),
                                "updated_at": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                            }

                            save_calibration(new_calibration)

                            mm_per_pixel = (
                                reference_mm / measured_pixel
                            )

                            st.success(
                                "✅ 새로운 Calibration이 저장되었습니다."
                            )

                            a, b, c = st.columns(3)
                            a.metric(
                                "기준 실측값",
                                f"{reference_mm:.4f} mm"
                            )
                            b.metric(
                                "새 기준 Pixel",
                                f"{measured_pixel:.4f} px"
                            )
                            c.metric(
                                "새 1 Pixel",
                                f"{mm_per_pixel:.6f} mm/px"
                            )

                            st.warning(
                                "이제 위쪽의 '② 자동 측정' 탭에서 "
                                "새 기준값으로 측정할 수 있습니다."
                            )

                            st.rerun()

                    except requests.exceptions.ConnectionError:
                        st.error(
                            "FastAPI 서버에 연결할 수 없습니다."
                        )
                    except Exception as e:
                        st.error(f"Calibration 오류: {e}")

    st.divider()

    if st.button(
        "↩ 기존 End-to-End V1 기준값으로 초기화"
    ):
        save_calibration(DEFAULT_CALIBRATION.copy())
        st.success("기존 V1 Calibration으로 초기화했습니다.")
        st.rerun()


# =========================================================
# TAB 2 : 자동 측정
# =========================================================
with tab_measure:
    st.subheader("② 자동 측정")

    current_calibration = load_calibration()

    st.caption(
        f"적용 기준: "
        f"{current_calibration['reference_mm']:.4f} mm = "
        f"{current_calibration['reference_pixel']:.4f} px"
    )

    st.warning(
        "Calibration 이후에는 카메라 거리·각도·줌·해상도를 바꾸지 마세요. "
        "조건을 변경했다면 ① Calibration을 다시 실행하세요."
    )

    measurement_image = None

    if input_mode == "모바일 카메라":
        measurement_image = st.camera_input(
            "측정할 샤프트를 놓고 촬영",
            key="measurement_camera"
        )
    else:
        measurement_image = st.file_uploader(
            "측정할 샤프트 이미지 선택",
            type=["jpg", "jpeg", "png"],
            key="measurement_upload"
        )

    if measurement_image is None:
        st.info(
            "샤프트를 촬영하면 촬영 직후 자동 측정합니다."
        )
    else:
        image_bytes = measurement_image.getvalue()
        image_hash = hashlib.sha256(
            image_bytes
        ).hexdigest()

        st.image(
            Image.open(measurement_image),
            caption="자동 측정 입력 이미지",
            use_container_width=True
        )

        already_done = (
            st.session_state.get("last_measure_image_hash")
            == image_hash
        )
        cached_result = st.session_state.get(
            "last_measure_result"
        )

        if already_done and cached_result is not None:
            render_measurement_result(**cached_result)

        else:
            filename = (
                getattr(measurement_image, "name", None)
                or f"shaft_{datetime.now():%Y%m%d_%H%M%S}.jpg"
            )

            with st.spinner(
                "YOLO ROI → OpenCV Pixel 측정 → "
                "새 Calibration 적용 → OK/NG 판정 중..."
            ):
                try:
                    payload = call_measure_api(
                        api_url,
                        image_bytes,
                        filename
                    )

                    measured_pixel, confidence, result_text = (
                        extract_pixel_result(payload)
                    )

                    if measured_pixel is None:
                        st.error(
                            "FastAPI 응답에서 Measured pixel 값을 찾지 못했습니다."
                        )
                    else:
                        measured_mm, mm_per_pixel = pixel_to_mm(
                            measured_pixel,
                            current_calibration
                        )

                        result_data = {
                            "measured_pixel": measured_pixel,
                            "confidence": confidence,
                            "measured_mm": measured_mm,
                            "mm_per_pixel": mm_per_pixel,
                            "calibration": current_calibration,
                            "result_text": result_text,
                        }

                        st.session_state[
                            "last_measure_image_hash"
                        ] = image_hash

                        st.session_state[
                            "last_measure_result"
                        ] = result_data

                        st.success("자동 측정 완료")
                        render_measurement_result(**result_data)

                except requests.exceptions.ConnectionError:
                    st.error(
                        "FastAPI 서버에 연결할 수 없습니다."
                    )
                except Exception as e:
                    st.error(f"자동 측정 오류: {e}")


st.divider()
st.caption(
    "현재 버전은 1점 Calibration 방식입니다. "
    "기준 샤프트 1개의 실측값과 촬영된 Pixel 값을 저장해 환산합니다. "
    "독립적인 정밀도 검증은 별도로 수행해야 합니다."
)
