import streamlit as st
import requests


# ============================================================
# 1. 기본 설정
# ============================================================

st.set_page_config(
    page_title="Shaft OD Measurement",
    page_icon="📏",
    layout="centered"
)


API_URL = "http://127.0.0.1:8000/measure"


# ============================================================
# 2. 화면 제목
# ============================================================

st.title("Shaft OD Measurement System")

st.write(
    "샤프트 이미지를 업로드하면 "
    "AI Vision 측정 시스템이 외경을 측정하고 "
    "OK / NG를 판정합니다."
)


# ============================================================
# 3. 이미지 업로드
# ============================================================

uploaded_file = st.file_uploader(
    "측정할 샤프트 이미지를 선택하세요.",
    type=["jpg", "jpeg", "png"]
)


if uploaded_file is not None:

    st.image(
        uploaded_file,
        caption="측정 이미지"
    )

    # ========================================================
    # 4. 측정 실행
    # ========================================================

    if st.button("외경 측정"):

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type
            )
        }

        try:

            response = requests.post(
                API_URL,
                files=files,
                timeout=120
            )

            if response.status_code == 200:

                data = response.json()

                st.success("측정 완료")

                st.write(
                    "파일명:",
                    data["filename"]
                )

                st.subheader("측정 결과")

                st.code(
                    data["measurement_result"]
                )

            else:

                st.error(
                    f"측정 실패: HTTP {response.status_code}"
                )

                st.write(
                    response.text
                )

        except requests.exceptions.ConnectionError:

            st.error(
                "FastAPI 서버에 연결할 수 없습니다."
            )

        except Exception as e:

            st.error(
                f"오류 발생: {e}"
            )