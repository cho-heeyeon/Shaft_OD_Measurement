import hashlib
import re
from datetime import datetime

import requests
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Shaft OD 현장 자동측정", page_icon="📏", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 1.4rem; padding-bottom: 2rem;}
.main-title {font-size: 2rem; font-weight: 800; margin-bottom: .2rem;}
.sub-title {font-size: 1rem; opacity: .75; margin-bottom: 1.2rem;}
.card {padding: 18px 20px; border: 1px solid rgba(128,128,128,.25); border-radius: 14px; margin-bottom: 10px;}
.ok {padding:18px;border-radius:14px;font-size:2rem;font-weight:800;text-align:center;background:rgba(0,180,90,.12);border:1px solid rgba(0,180,90,.35);}
.ng {padding:18px;border-radius:14px;font-size:2rem;font-weight:800;text-align:center;background:rgba(220,60,60,.12);border:1px solid rgba(220,60,60,.35);}
</style>
""", unsafe_allow_html=True)

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
    r = requests.post(api_url, files=files, timeout=120)
    r.raise_for_status()
    return r.json()

def render_result(payload):
    result_text = payload.get("result_text") or payload.get("measurement_result") or ""
    parsed = parse_measurement_text(result_text)
    measured_mm = payload.get("measured_mm", as_float(parsed.get("Measured mm")))
    measured_pixel = payload.get("measured_pixel", as_float(parsed.get("Measured pixel")))
    confidence = payload.get("confidence", as_float(parsed.get("YOLO confidence")))
    result = payload.get("result", parsed.get("Result", "-"))

    spec_lower = payload.get("spec_lower")
    spec_upper = payload.get("spec_upper")
    if spec_lower is None or spec_upper is None:
        vals = re.findall(r"\d+(?:\.\d+)?", parsed.get("Specification", ""))
        if len(vals) >= 2:
            spec_lower, spec_upper = float(vals[0]), float(vals[1])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("측정 외경", f"{measured_mm:.4f} mm" if measured_mm is not None else "-")
    c2.metric("측정 Pixel", f"{measured_pixel:.4f} px" if measured_pixel is not None else "-")
    c3.metric("YOLO Confidence", f"{confidence:.3f}" if confidence is not None else "-")
    c4.metric("규격", f"{spec_lower:.3f} ~ {spec_upper:.3f} mm" if spec_lower is not None else "-")

    if str(result).upper() == "OK":
        st.markdown('<div class="ok">✅ OK</div>', unsafe_allow_html=True)
    elif str(result).upper() == "NG":
        st.markdown('<div class="ng">❌ NG</div>', unsafe_allow_html=True)
    else:
        st.info(f"판정: {result}")

    with st.expander("상세 측정 결과 보기"):
        st.code(result_text if result_text else str(payload), language="text")

with st.sidebar:
    st.header("⚙️ 현장 설정")
    api_url = st.text_input("FastAPI 측정 주소", value="http://127.0.0.1:8000/measure")
    mode = st.radio("입력 방식", ["모바일 카메라", "이미지 업로드"])
    auto_measure = st.toggle("촬영 후 자동 측정", value=True)
    st.divider()
    st.caption("권장 설치")
    st.write("📱 모바일/스마트폰 고정")
    st.write("🧰 샤프트 고정 지그")
    st.write("💡 A4 LED 라이트박스")
    st.write("📐 카메라 거리·각도 고정")

st.markdown('<div class="main-title">Shaft OD 현장 자동측정</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">모바일 삼각대 + 고정 지그 + A4 백라이트 + YOLO/OpenCV End-to-End V1</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="card"><b>측정 순서</b><br>① 샤프트 장착<br>② 백라이트 ON<br>③ 모바일 촬영<br>④ 자동 측정</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="card"><b>촬영 조건</b><br>카메라 위치 고정<br>줌 배율 고정<br>조명 밝기 고정<br>동일 해상도</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="card"><b>측정 로직</b><br>ROI: YOLO<br>외경: OpenCV<br>변환: Calibration<br>판정: 20.010~20.030 mm</div>', unsafe_allow_html=True)

st.divider()
left, right = st.columns([1.05, 1])

captured = None
filename = None

with left:
    st.subheader("1. 현장 이미지 입력")
    if mode == "모바일 카메라":
        captured = st.camera_input("샤프트를 중앙에 놓고 촬영하세요")
        if captured is not None:
            filename = f"shaft_{datetime.now():%Y%m%d_%H%M%S}.jpg"
    else:
        captured = st.file_uploader("샤프트 이미지 선택", type=["jpg", "jpeg", "png"])
        if captured is not None:
            filename = captured.name

    if captured is not None:
        image_bytes = captured.getvalue()
        st.image(Image.open(captured), caption="측정 입력 이미지", use_container_width=True)

with right:
    st.subheader("2. 자동측정 결과")
    if captured is None:
        st.info("왼쪽에서 샤프트를 촬영하거나 이미지를 선택하세요.")
    else:
        image_bytes = captured.getvalue()
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        run_measurement = auto_measure
        if not auto_measure:
            run_measurement = st.button("📏 측정 실행", type="primary", use_container_width=True)

        already_done = st.session_state.get("last_image_hash") == image_hash
        cached_payload = st.session_state.get("last_payload")

        if run_measurement and auto_measure and already_done and cached_payload is not None:
            render_result(cached_payload)
        elif run_measurement:
            with st.spinner("YOLO ROI 탐지 → OpenCV 측정 → 판정 중..."):
                try:
                    payload = call_measure_api(api_url, image_bytes, filename or "shaft.jpg")
                    st.session_state["last_image_hash"] = image_hash
                    st.session_state["last_payload"] = payload
                    st.success("측정 완료")
                    render_result(payload)
                except requests.exceptions.ConnectionError:
                    st.error("FastAPI 서버에 연결할 수 없습니다.")
                    st.code("python -m uvicorn 12_System_Integration.backend.main:app --host 0.0.0.0 --port 8000")
                except Exception as e:
                    st.error(f"측정 오류: {e}")

st.divider()
st.caption("모바일 브라우저 보안상 카메라 셔터 자체는 사용자가 한 번 눌러야 할 수 있습니다. '촬영 후 자동 측정'은 촬영 직후 End-to-End 측정을 자동 실행하는 기능입니다.")
