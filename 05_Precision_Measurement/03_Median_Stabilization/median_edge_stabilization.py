import cv2
import numpy as np
from pathlib import Path


# ---------------------------------
# 1. 새 검증 ROI 이미지
# ---------------------------------

image_path = Path("Day017-2/test_roi.jpg")

image = cv2.imread(str(image_path))

if image is None:
    raise FileNotFoundError("검증 ROI 이미지를 찾을 수 없습니다.")


# ---------------------------------
# 2. GRAY / Blur / Edge
# ---------------------------------

gray = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2GRAY
)

blur = cv2.GaussianBlur(
    gray,
    (5, 5),
    0
)

edge = cv2.Canny(
    blur,
    50,
    150
)


# ---------------------------------
# 3. 이미지 크기
# ---------------------------------

height, width = edge.shape

center_y = height // 2


# ---------------------------------
# 4. 중앙 측정 영역
# ---------------------------------

x_start = int(width * 0.25)
x_end = int(width * 0.75)

sample_count = 7

x_positions = np.linspace(
    x_start,
    x_end,
    sample_count,
    dtype=int
)


# ---------------------------------
# 5. 1차 상단 Edge 후보 수집
# ---------------------------------

top_candidates = []

bottom_values = []

for x in x_positions:

    x1 = max(0, x - 2)
    x2 = min(width, x + 3)

    strip = edge[:, x1:x2]

    row_scores = np.sum(
        strip > 0,
        axis=1
    )

    # 상단 Edge 후보
    top_scores = row_scores[:center_y]

    y_top = np.argmax(
        top_scores
    )

    top_candidates.append(
        y_top
    )

    # 하단 Edge
    y_bottom = None

    for y in range(center_y, height):

        if row_scores[y] >= 2:
            y_bottom = y

    bottom_values.append(
        y_bottom
    )


print("상단 Edge 후보 :", top_candidates)

print("하단 Edge 후보 :", bottom_values)


# ---------------------------------
# 6. 상단 Edge 중앙값 계산
# ---------------------------------

stable_top = int(
    np.median(top_candidates)
)

print()
print("안정화 상단 Edge :", stable_top)


# ---------------------------------
# 7. 안정화된 상단 Edge로 외경 재계산
# ---------------------------------

diameters = []

result = image.copy()


print()
print("x | top_raw | top_stable | bottom | diameter")
print("------------------------------------------------")


for i, x in enumerate(x_positions):

    y_top_raw = top_candidates[i]

    y_top = stable_top

    y_bottom = bottom_values[i]

    if y_bottom is None:
        continue


    diameter = (
        y_bottom
        - y_top
    )

    diameters.append(
        diameter
    )


    print(
        x,
        "|",
        y_top_raw,
        "|",
        y_top,
        "|",
        y_bottom,
        "|",
        diameter
    )


    # 원래 상단 Edge 후보
    cv2.circle(
        result,
        (x, y_top_raw),
        4,
        (0, 255, 255),
        -1
    )


    # 안정화 상단 Edge
    cv2.circle(
        result,
        (x, y_top),
        5,
        (0, 0, 255),
        -1
    )


    # 하단 Edge
    cv2.circle(
        result,
        (x, y_bottom),
        5,
        (255, 0, 0),
        -1
    )


    # 외경 측정선
    cv2.line(
        result,
        (x, y_top),
        (x, y_bottom),
        (0, 255, 0),
        2
    )


# ---------------------------------
# 8. 통계 계산
# ---------------------------------

mean_diameter = np.mean(
    diameters
)

median_diameter = np.median(
    diameters
)

std_diameter = np.std(
    diameters
)

top_std_before = np.std(
    top_candidates
)

top_std_after = np.std(
    [stable_top] * len(top_candidates)
)


print()
print("========== 안정화 결과 ==========")

print(
    "상단 Edge 표준편차 BEFORE :",
    top_std_before
)

print(
    "상단 Edge 표준편차 AFTER :",
    top_std_after
)

print(
    "외경 평균(pixel) :",
    mean_diameter
)

print(
    "외경 중앙값(pixel) :",
    median_diameter
)

print(
    "외경 표준편차(pixel) :",
    std_diameter
)


# ---------------------------------
# 9. Day016 기준과 비교
# ---------------------------------

BASE_PIXEL = 459

pixel_difference = (
    median_diameter
    - BASE_PIXEL
)

MM_PER_PIXEL = 0.0436166

difference_um = (
    pixel_difference
    * MM_PER_PIXEL
    * 1000
)


print()
print("Day016 기준 :", BASE_PIXEL)
print("Day018 대표값 :", median_diameter)
print("차이(pixel) :", pixel_difference)
print("차이(μm) :", difference_um)


# ---------------------------------
# 10. 저장
# ---------------------------------

output_dir = Path("Day018")

output_dir.mkdir(exist_ok=True)

cv2.imwrite(
    str(output_dir / "edge.jpg"),
    edge
)

cv2.imwrite(
    str(output_dir / "stable_top_edge_result.jpg"),
    result
)

print()
print(
    "저장 완료 : Day018/stable_top_edge_result.jpg"
)