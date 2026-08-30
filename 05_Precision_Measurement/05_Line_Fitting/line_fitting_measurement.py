from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


# ============================================================
# 1. 경로 설정
# ============================================================

BASE_DIR = Path("Day025")

IMAGE_PATH = BASE_DIR / "sample_07.jpg"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Day023에서 학습한 YOLO 모델
MODEL_PATH = Path(
    "runs/detect/Day023/runs/"
    "measurement_roi_aug-2/weights/best.pt"
)


# ============================================================
# 2. YOLO ROI 검출
# ============================================================

model = YOLO(str(MODEL_PATH))

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

        confidence = float(box.conf[0])

        if confidence > best_conf:

            best_conf = confidence
            best_box = box


if best_box is None:

    print("YOLO ROI 검출 실패")
    raise SystemExit


# ============================================================
# 3. YOLO 신뢰도 검사
# ============================================================

print()
print("========== YOLO ROI ==========")
print("confidence :", best_conf)


if best_conf < 0.70:

    print("ROI 신뢰도 부족")
    print("측정을 중단합니다.")

    raise SystemExit


# ============================================================
# 4. 원본 이미지
# ============================================================

image = cv2.imread(str(IMAGE_PATH))

if image is None:

    print("이미지를 읽을 수 없습니다.")
    raise SystemExit


image_h, image_w = image.shape[:2]


x1, y1, x2, y2 = (
    best_box.xyxy[0]
    .cpu()
    .numpy()
    .astype(int)
)


# 이미지 범위 보호
x1 = max(0, x1)
y1 = max(0, y1)

x2 = min(image_w, x2)
y2 = min(image_h, y2)


print("x1 :", x1)
print("y1 :", y1)
print("x2 :", x2)
print("y2 :", y2)


## ==========================================
# Day026
# 상단 / 하단 외곽선 Line Fitting
# ==========================================

# ROI를 위아래로 확장
box_h = y2 - y1

expand_y = int(box_h * 0.8)

ey1 = max(0, y1 - expand_y)
ey2 = min(image.shape[0], y2 + expand_y)

roi = image[ey1:ey2, x1:x2].copy()

gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

# 약한 Gaussian Blur
gray = cv2.GaussianBlur(
    gray,
    (5, 5),
    0
)

# ------------------------------------------
# 여러 x 위치에서 외곽 Edge 탐색
# ------------------------------------------

roi_h, roi_w = gray.shape

x_positions = np.linspace(
    int(roi_w * 0.20),
    int(roi_w * 0.80),
    15
).astype(int)

top_points = []
bottom_points = []

for x in x_positions:

    profile = gray[:, x].astype(np.float32)

    # y 방향 밝기 변화
    gradient = np.abs(
        np.gradient(profile)
    )

    center_y = roi_h // 2

    # 상단 검색 영역
    top_region = gradient[
        int(roi_h * 0.10):
        center_y
    ]

    # 하단 검색 영역
    bottom_region = gradient[
        center_y:
        int(roi_h * 0.90)
    ]

    if len(top_region) == 0 or len(bottom_region) == 0:
        continue

    top_y = (
        np.argmax(top_region)
        + int(roi_h * 0.10)
    )

    bottom_y = (
        np.argmax(bottom_region)
        + center_y
    )

    # 너무 비정상적인 측정은 제외
    diameter = bottom_y - top_y

    if diameter > roi_h * 0.20:

        top_points.append(
            [x, top_y]
        )

        bottom_points.append(
            [x, bottom_y]
        )


top_points = np.array(
    top_points,
    dtype=np.float32
)

bottom_points = np.array(
    bottom_points,
    dtype=np.float32
)


# ==========================================
# Line Fitting
# ==========================================

if (
    len(top_points) >= 5
    and
    len(bottom_points) >= 5
):

    # y = ax + b
    top_a, top_b = np.polyfit(
        top_points[:, 0],
        top_points[:, 1],
        1
    )

    bottom_a, bottom_b = np.polyfit(
        bottom_points[:, 0],
        bottom_points[:, 1],
        1
    )

    print()
    print(
        "========== Day026 Line Fitting =========="
    )

    print(
        "상단 기울기 :",
        top_a
    )

    print(
        "하단 기울기 :",
        bottom_a
    )


    # --------------------------------------
    # 여러 위치에서 두 직선 사이 거리
    # --------------------------------------

    diameters = []

    for x in x_positions:

        top_y_fit = (
            top_a * x
            + top_b
        )

        bottom_y_fit = (
            bottom_a * x
            + bottom_b
        )

        diameter = (
            bottom_y_fit
            - top_y_fit
        )

        diameters.append(
            diameter
        )


    diameters = np.array(
        diameters
    )

    print()
    print(
        "Line fitting 측정값 :",
        np.round(
            diameters,
            2
        )
    )

    print(
        "평균(pixel) :",
        np.mean(diameters)
    )

    print(
        "중앙값(pixel) :",
        np.median(diameters)
    )

    print(
        "표준편차(pixel) :",
        np.std(diameters)
    )


    # ======================================
    # 결과 시각화
    # ======================================

    result_roi = roi.copy()

    # 실제 검출점 표시
    for x, y in top_points.astype(int):

        cv2.circle(
            result_roi,
            (x, y),
            4,
            (0, 0, 255),
            -1
        )


    for x, y in bottom_points.astype(int):

        cv2.circle(
            result_roi,
            (x, y),
            4,
            (255, 0, 0),
            -1
        )


    # fitted line 표시
    x_start = 0
    x_end = roi_w - 1

    top_start = int(
        top_a * x_start
        + top_b
    )

    top_end = int(
        top_a * x_end
        + top_b
    )

    bottom_start = int(
        bottom_a * x_start
        + bottom_b
    )

    bottom_end = int(
        bottom_a * x_end
        + bottom_b
    )


    cv2.line(
        result_roi,
        (x_start, top_start),
        (x_end, top_end),
        (0, 255, 0),
        2
    )

    cv2.line(
        result_roi,
        (x_start, bottom_start),
        (x_end, bottom_end),
        (0, 255, 0),
        2
    )


    # 중앙 측정선
    center_x = roi_w // 2

    center_top = int(
        top_a * center_x
        + top_b
    )

    center_bottom = int(
        bottom_a * center_x
        + bottom_b
    )

    cv2.line(
        result_roi,
        (center_x, center_top),
        (center_x, center_bottom),
        (0, 255, 255),
        2
    )


    # --------------------------------------
    # 저장
    # --------------------------------------

    output_dir = Path(
        "Day026/output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_dir
        / "line_fitting_measurement.jpg"
    )

    cv2.imwrite(
        str(output_path),
        result_roi
    )

    print()
    print(
        "결과 저장 :",
        output_path
    )

else:

    print(
        "Line fitting에 필요한 Edge 점이 부족합니다."
    )