import cv2
import numpy as np

from pathlib import Path
from ultralytics import YOLO


# ============================================================
# Day027
# YOLO + OpenCV + Sub-pixel + Calibration + OK/NG
#
# 최종 V1
# ============================================================


# ============================================================
# 1. 경로
# ============================================================

BASE_DIR = Path("Day027")

IMAGE_PATH = (
    BASE_DIR
    / "images"
    / "sample_07.jpg"
)

OUTPUT_DIR = (
    BASE_DIR
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


MODEL_PATH = Path(
    "runs/detect/Day023/runs/"
    "measurement_roi_aug-2/weights/best.pt"
)


# ============================================================
# 2. Calibration 기준
#
# 중요:
# 현재 최종 측정 알고리즘으로 sample_07을 측정한
# 대표 pixel 값을 사용합니다.
#
# 실측 계측기 값:
# 20.021 mm
#
# 현재 알고리즘 측정 pixel:
# 약 464.06 pixel
# ============================================================

CALIBRATION_PIXEL = 464.06

CALIBRATION_MM = 20.021


# ============================================================
# 3. 제품 검사 규격
# ============================================================

SPEC_LOWER = 20.010
SPEC_UPPER = 20.030

SPEC_CENTER = (
    SPEC_LOWER
    + SPEC_UPPER
) / 2.0


# ============================================================
# 4. Pixel → mm 변환계수
# ============================================================

MM_PER_PIXEL = (
    CALIBRATION_MM
    / CALIBRATION_PIXEL
)


print()
print(
    "=========================================="
)

print(
    "Day027 Shaft Measurement System V1"
)

print(
    "=========================================="
)

print()

print(
    "Calibration pixel :",
    CALIBRATION_PIXEL
)

print(
    "Calibration mm :",
    CALIBRATION_MM
)

print(
    "mm / pixel :",
    MM_PER_PIXEL
)

print(
    "제품 규격 :",
    f"{SPEC_LOWER:.3f}",
    "~",
    f"{SPEC_UPPER:.3f}",
    "mm"
)


# ============================================================
# 5. YOLO 모델 로드
# ============================================================

model = YOLO(
    str(MODEL_PATH)
)


# ============================================================
# 6. YOLO 측정 ROI 검출
# ============================================================

results = model.predict(
    source=str(IMAGE_PATH),
    conf=0.25,
    imgsz=640,
    verbose=False
)


best_box = None
best_conf = 0.0


for result in results:

    if result.boxes is None:
        continue


    for box in result.boxes:

        confidence = float(
            box.conf[0]
        )


        if confidence > best_conf:

            best_conf = confidence
            best_box = box


if best_box is None:

    raise RuntimeError(
        "YOLO ROI 검출 실패"
    )


print()
print(
    "========== YOLO ROI =========="
)

print(
    "Confidence :",
    best_conf
)


# ============================================================
# 7. 원본 이미지
# ============================================================

image = cv2.imread(
    str(IMAGE_PATH)
)


if image is None:

    raise FileNotFoundError(
        f"이미지를 찾을 수 없습니다: {IMAGE_PATH}"
    )


image_h, image_w = (
    image.shape[:2]
)


# ============================================================
# 8. YOLO Bounding Box
# ============================================================

x1, y1, x2, y2 = (
    best_box.xyxy[0]
    .cpu()
    .numpy()
    .astype(int)
)


x1 = max(
    0,
    x1
)

y1 = max(
    0,
    y1
)

x2 = min(
    image_w,
    x2
)

y2 = min(
    image_h,
    y2
)


print(
    "x1 :", x1
)

print(
    "y1 :", y1
)

print(
    "x2 :", x2
)

print(
    "y2 :", y2
)


# ============================================================
# 9. 측정 ROI 확장
# ============================================================

box_h = (
    y2 - y1
)


vertical_margin = int(
    box_h
    * 0.40
)


measure_y1 = max(
    0,
    y1 - vertical_margin
)


measure_y2 = min(
    image_h,
    y2 + vertical_margin
)


roi = image[
    measure_y1:measure_y2,
    x1:x2
].copy()


if roi.size == 0:

    raise RuntimeError(
        "측정 ROI 생성 실패"
    )


# ============================================================
# 10. ROI 저장
# ============================================================

cv2.imwrite(
    str(
        OUTPUT_DIR
        / "measurement_crop.jpg"
    ),
    roi
)


# ============================================================
# 11. OpenCV 전처리
# ============================================================

gray = cv2.cvtColor(
    roi,
    cv2.COLOR_BGR2GRAY
)


blur = cv2.GaussianBlur(
    gray,
    (5, 5),
    0
)


roi_h, roi_w = (
    blur.shape
)


# ============================================================
# 12. Sub-pixel Edge 보간
#
# Gradient peak 주변 3점을 이용해
# 정수 pixel보다 세밀한 위치 계산
# ============================================================

def subpixel_edge(
    abs_gradient,
    index
):

    if index <= 0:

        return float(
            index
        )


    if index >= (
        len(abs_gradient) - 1
    ):

        return float(
            index
        )


    g1 = float(
        abs_gradient[
            index - 1
        ]
    )


    g2 = float(
        abs_gradient[
            index
        ]
    )


    g3 = float(
        abs_gradient[
            index + 1
        ]
    )


    denominator = (
        g1
        - 2.0 * g2
        + g3
    )


    if abs(
        denominator
    ) < 1e-12:

        return float(
            index
        )


    offset = (
        0.5
        * (g1 - g3)
        / denominator
    )


    offset = np.clip(
        offset,
        -1.0,
        1.0
    )


    return (
        float(index)
        + float(offset)
    )


# ============================================================
# 13. 실제 외곽 Edge 검출
#
# 사용 조건:
#
# 1. 상단/하단 Gradient 방향 반대
# 2. 충분한 Gradient 강도
# 3. 내부 Edge 제외
# 4. 가능한 후보 중 바깥쪽 우선
# ============================================================

def find_outer_edge(
    gray_image,
    x
):

    # --------------------------------------------------------
    # 한 column만 사용하지 않고
    # 주변 5 pixel 평균
    # --------------------------------------------------------

    strip_x1 = max(
        0,
        x - 2
    )


    strip_x2 = min(
        gray_image.shape[1],
        x + 3
    )


    profile = np.mean(
        gray_image[
            :,
            strip_x1:strip_x2
        ],
        axis=1
    ).astype(
        np.float32
    )


    # --------------------------------------------------------
    # Gradient
    # --------------------------------------------------------

    gradient = np.gradient(
        profile
    )


    abs_gradient = np.abs(
        gradient
    )


    h = len(
        profile
    )


    # --------------------------------------------------------
    # 상단 / 하단 검색영역
    # --------------------------------------------------------

    upper_end = int(
        h
        * 0.46
    )


    lower_start = int(
        h
        * 0.54
    )


    upper_abs = (
        abs_gradient[
            :upper_end
        ]
    )


    lower_abs = (
        abs_gradient[
            lower_start:
        ]
    )


    if len(upper_abs) == 0:

        return None


    if len(lower_abs) == 0:

        return None


    # --------------------------------------------------------
    # 강한 Gradient 후보
    # --------------------------------------------------------

    upper_threshold = np.percentile(
        upper_abs,
        82
    )


    lower_threshold = np.percentile(
        lower_abs,
        82
    )


    upper_candidates = np.where(
        upper_abs
        >= upper_threshold
    )[0]


    lower_candidates = (
        np.where(
            lower_abs
            >= lower_threshold
        )[0]
        + lower_start
    )


    candidate_pairs = []


    # --------------------------------------------------------
    # 상단 / 하단 후보 조합
    # --------------------------------------------------------

    for top_idx in upper_candidates:

        top_gradient = float(
            gradient[
                top_idx
            ]
        )


        for bottom_idx in lower_candidates:

            bottom_gradient = float(
                gradient[
                    bottom_idx
                ]
            )


            # ------------------------------------------------
            # 실제 상·하단 외곽은
            # Gradient 방향이 반대
            # ------------------------------------------------

            if (
                top_gradient
                * bottom_gradient
                >= 0
            ):

                continue


            diameter_integer = (
                bottom_idx
                - top_idx
            )


            # ------------------------------------------------
            # 지나치게 작은 내부 Edge 제거
            # ------------------------------------------------

            if diameter_integer < (
                h * 0.25
            ):

                continue


            # ------------------------------------------------
            # 지나치게 큰 배경 Edge 제거
            # ------------------------------------------------

            if diameter_integer > (
                h * 0.60
            ):

                continue


            strength = (
                abs(
                    top_gradient
                )
                +
                abs(
                    bottom_gradient
                )
            )


            candidate_pairs.append(
                (
                    int(
                        top_idx
                    ),
                    int(
                        bottom_idx
                    ),
                    float(
                        diameter_integer
                    ),
                    float(
                        strength
                    )
                )
            )


    if len(
        candidate_pairs
    ) == 0:

        return None


    # --------------------------------------------------------
    # 너무 약한 후보 제거
    # --------------------------------------------------------

    strengths = np.array(
        [
            pair[3]
            for pair
            in candidate_pairs
        ]
    )


    maximum_strength = float(
        np.max(
            strengths
        )
    )


    strength_limit = (
        maximum_strength
        * 0.55
    )


    strong_pairs = [
        pair

        for pair
        in candidate_pairs

        if pair[3]
        >= strength_limit
    ]


    if len(
        strong_pairs
    ) == 0:

        strong_pairs = (
            candidate_pairs
        )


    # --------------------------------------------------------
    # 충분히 강한 후보 중
    # 가장 바깥쪽 Pair 선택
    # --------------------------------------------------------

    best_pair = max(
        strong_pairs,
        key=lambda pair:
            pair[2]
    )


    top_idx = int(
        best_pair[0]
    )


    bottom_idx = int(
        best_pair[1]
    )


    # --------------------------------------------------------
    # Sub-pixel 보정
    # --------------------------------------------------------

    top_sub = subpixel_edge(
        abs_gradient,
        top_idx
    )


    bottom_sub = subpixel_edge(
        abs_gradient,
        bottom_idx
    )


    diameter_sub = (
        bottom_sub
        - top_sub
    )


    return (
        top_sub,
        bottom_sub,
        diameter_sub
    )


# ============================================================
# 14. 여러 X 위치에서 외경 측정
#
# 단일 측정선에 의존하지 않고
# 31개 위치에서 측정
# ============================================================

x_positions = np.linspace(
    int(
        roi_w
        * 0.18
    ),
    int(
        roi_w
        * 0.82
    ),
    31
).astype(
    int
)


top_points = []

bottom_points = []

diameters = []


for x in x_positions:

    edge_result = find_outer_edge(
        blur,
        x
    )


    if edge_result is None:

        continue


    (
        top_y,
        bottom_y,
        diameter
    ) = edge_result


    top_points.append(
        [
            x,
            top_y
        ]
    )


    bottom_points.append(
        [
            x,
            bottom_y
        ]
    )


    diameters.append(
        diameter
    )


# ============================================================
# 15. NumPy 변환
# ============================================================

diameters = np.array(
    diameters,
    dtype=np.float64
)


top_points = np.array(
    top_points,
    dtype=np.float64
)


bottom_points = np.array(
    bottom_points,
    dtype=np.float64
)


if len(
    diameters
) < 10:

    raise RuntimeError(
        "측정 가능한 Edge 점이 부족합니다."
    )


# ============================================================
# 16. Raw 측정 통계
# ============================================================

print()
print(
    "========== Raw Pixel 측정 =========="
)


print(
    "측정값 :",
    np.round(
        diameters,
        3
    )
)


print(
    "Raw Median :",
    np.median(
        diameters
    )
)


print(
    "Raw STD :",
    np.std(
        diameters
    )
)


# ============================================================
# 17. MAD 기반 Outlier 제거
# ============================================================

raw_median = float(
    np.median(
        diameters
    )
)


deviation = np.abs(
    diameters
    - raw_median
)


mad = float(
    np.median(
        deviation
    )
)


if mad > 0:

    robust_sigma = (
        1.4826
        * mad
    )


    outlier_threshold = (
        3.0
        * robust_sigma
    )


    valid_mask = (
        deviation
        <= outlier_threshold
    )


else:

    valid_mask = np.ones(
        len(
            diameters
        ),
        dtype=bool
    )


valid_diameters = (
    diameters[
        valid_mask
    ]
)


valid_top = (
    top_points[
        valid_mask
    ]
)


valid_bottom = (
    bottom_points[
        valid_mask
    ]
)


if len(
    valid_diameters
) < 8:

    raise RuntimeError(
        "Outlier 제거 후 유효 측정점 부족"
    )


# ============================================================
# 18. 최종 Pixel 측정
# ============================================================

measured_pixel = float(
    np.median(
        valid_diameters
    )
)


mean_pixel = float(
    np.mean(
        valid_diameters
    )
)


std_pixel = float(
    np.std(
        valid_diameters
    )
)


print()
print(
    "========== 최종 Pixel 측정 =========="
)


print(
    "전체 측정 수 :",
    len(
        diameters
    )
)


print(
    "유효 측정 수 :",
    len(
        valid_diameters
    )
)


print(
    "Median(pixel) :",
    measured_pixel
)


print(
    "Mean(pixel) :",
    mean_pixel
)


print(
    "STD(pixel) :",
    std_pixel
)


# ============================================================
# 19. Pixel → mm
# ============================================================

measured_mm = (
    measured_pixel
    * MM_PER_PIXEL
)


error_mm = (
    measured_mm
    - CALIBRATION_MM
)


absolute_error_mm = abs(
    error_mm
)


print()
print(
    "========== Calibration / mm =========="
)


print(
    "Calibration pixel :",
    CALIBRATION_PIXEL
)


print(
    "Calibration mm :",
    CALIBRATION_MM
)


print(
    "Vision pixel :",
    measured_pixel
)


print(
    "Vision 측정 외경(mm) :",
    measured_mm
)


print(
    "실측 기준값(mm) :",
    CALIBRATION_MM
)


print(
    "실측 대비 오차(mm) :",
    error_mm
)


print(
    "절대 오차(mm) :",
    absolute_error_mm
)


# ============================================================
# 20. 제품 OK / NG 판정
# ============================================================

if (
    SPEC_LOWER
    <= measured_mm
    <= SPEC_UPPER
):

    judgement = "OK"

else:

    judgement = "NG"


print()
print(
    "========== 최종 판정 =========="
)


print(
    "제품 규격 :",
    f"{SPEC_LOWER:.3f}",
    "~",
    f"{SPEC_UPPER:.3f}",
    "mm"
)


print(
    "규격 중심값 :",
    f"{SPEC_CENTER:.3f}",
    "mm"
)


print(
    "실측 기준값 :",
    f"{CALIBRATION_MM:.3f}",
    "mm"
)


print(
    "Vision 측정값 :",
    f"{measured_mm:.4f}",
    "mm"
)


print(
    "실측 대비 오차 :",
    f"{error_mm:+.4f}",
    "mm"
)


print(
    "판정 :",
    judgement
)


# ============================================================
# 21. 측정 결과 이미지
# ============================================================

measurement_image = roi.copy()


for (
    top_point,
    bottom_point
) in zip(
    valid_top,
    valid_bottom
):

    x = int(
        round(
            top_point[0]
        )
    )


    top_y = int(
        round(
            top_point[1]
        )
    )


    bottom_y = int(
        round(
            bottom_point[1]
        )
    )


    # --------------------------------------------------------
    # 측정선
    # --------------------------------------------------------

    cv2.line(
        measurement_image,
        (
            x,
            top_y
        ),
        (
            x,
            bottom_y
        ),
        (0, 255, 0),
        1
    )


    # 상단 Edge
    cv2.circle(
        measurement_image,
        (
            x,
            top_y
        ),
        2,
        (0, 0, 255),
        -1
    )


    # 하단 Edge
    cv2.circle(
        measurement_image,
        (
            x,
            bottom_y
        ),
        2,
        (255, 0, 0),
        -1
    )


# ============================================================
# 22. 결과 텍스트
# ============================================================

cv2.putText(
    measurement_image,
    f"YOLO : {best_conf:.3f}",
    (5, 22),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.48,
    (0, 255, 255),
    1
)


cv2.putText(
    measurement_image,
    f"Pixel : {measured_pixel:.3f}",
    (5, 44),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.48,
    (0, 255, 255),
    1
)


cv2.putText(
    measurement_image,
    (
        f"Diameter : "
        f"{measured_mm:.4f} mm"
    ),
    (5, 66),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.48,
    (0, 255, 255),
    1
)


cv2.putText(
    measurement_image,
    (
        f"Spec : "
        f"{SPEC_LOWER:.3f} ~ "
        f"{SPEC_UPPER:.3f}"
    ),
    (5, 88),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.44,
    (0, 255, 255),
    1
)


cv2.putText(
    measurement_image,
    (
        f"Error : "
        f"{error_mm:+.4f} mm"
    ),
    (5, 110),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.44,
    (0, 255, 255),
    1
)


# ============================================================
# 23. OK / NG 색상
# ============================================================

if judgement == "OK":

    judgement_color = (
        0,
        255,
        0
    )

else:

    judgement_color = (
        0,
        0,
        255
    )


cv2.putText(
    measurement_image,
    f"RESULT : {judgement}",
    (5, 138),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.75,
    judgement_color,
    2
)


# ============================================================
# 24. 최종 측정 이미지 저장
# ============================================================

measurement_result_path = (
    OUTPUT_DIR
    / "shaft_measurement_final.jpg"
)


cv2.imwrite(
    str(
        measurement_result_path
    ),
    measurement_image
)


# ============================================================
# 25. 전체 이미지에 ROI 표시
# ============================================================

overview = image.copy()


# YOLO 검출 ROI
cv2.rectangle(
    overview,
    (
        x1,
        y1
    ),
    (
        x2,
        y2
    ),
    (0, 0, 255),
    3
)


# 측정 확장 ROI
cv2.rectangle(
    overview,
    (
        x1,
        measure_y1
    ),
    (
        x2,
        measure_y2
    ),
    (0, 255, 0),
    2
)


cv2.putText(
    overview,
    (
        f"ROI conf "
        f"{best_conf:.3f}"
    ),
    (
        x1,
        max(
            25,
            y1 - 12
        )
    ),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.65,
    (0, 0, 255),
    2
)


overview_path = (
    OUTPUT_DIR
    / "measurement_roi_final.jpg"
)


cv2.imwrite(
    str(
        overview_path
    ),
    overview
)


# ============================================================
# 26. 최종 결과 Summary TXT 저장
# ============================================================

summary_path = (
    OUTPUT_DIR
    / "measurement_result.txt"
)


with open(
    summary_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "Day027 Shaft Measurement System V1\n"
    )

    f.write(
        "====================================\n"
    )

    f.write(
        f"YOLO confidence : "
        f"{best_conf:.6f}\n"
    )

    f.write(
        f"Calibration pixel : "
        f"{CALIBRATION_PIXEL:.4f}\n"
    )

    f.write(
        f"Calibration mm : "
        f"{CALIBRATION_MM:.4f}\n"
    )

    f.write(
        f"Measured pixel : "
        f"{measured_pixel:.4f}\n"
    )

    f.write(
        f"Measured mm : "
        f"{measured_mm:.4f}\n"
    )

    f.write(
        f"STD pixel : "
        f"{std_pixel:.4f}\n"
    )

    f.write(
        f"Error mm : "
        f"{error_mm:+.4f}\n"
    )

    f.write(
        f"Specification : "
        f"{SPEC_LOWER:.3f} ~ "
        f"{SPEC_UPPER:.3f} mm\n"
    )

    f.write(
        f"Result : "
        f"{judgement}\n"
    )


# ============================================================
# 27. 완료
# ============================================================

print()
print(
    "========== 결과 파일 =========="
)

print(
    "ROI :",
    overview_path
)

print(
    "측정 이미지 :",
    measurement_result_path
)

print(
    "결과 TXT :",
    summary_path
)


print()
print(
    "=========================================="
)

print(
    "Day027 최종 V1 완료"
)

print(
    "=========================================="
)