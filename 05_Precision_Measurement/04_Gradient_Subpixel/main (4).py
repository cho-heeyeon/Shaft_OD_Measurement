import cv2
import numpy as np
from pathlib import Path


# ---------------------------------
# 1. 이미지 읽기
# ---------------------------------

image_path = Path("Day017-2/test_roi.jpg")

image = cv2.imread(str(image_path))

if image is None:
    raise FileNotFoundError("검증 ROI 이미지를 찾을 수 없습니다.")


# ---------------------------------
# 2. GRAY / Blur
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


# ---------------------------------
# 3. 세로 방향 Gradient
# ---------------------------------

gradient_y = cv2.Sobel(
    blur,
    cv2.CV_64F,
    0,
    1,
    ksize=3
)

gradient_abs = np.abs(
    gradient_y
)


# ---------------------------------
# 4. 이미지 크기
# ---------------------------------

height, width = gray.shape

center_y = height // 2


# ---------------------------------
# 5. 측정 위치
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
# 6. Sub-pixel 보간 함수
# ---------------------------------

def subpixel_peak(profile, index):

    # 양 끝에서는 보간 불가
    if index <= 0 or index >= len(profile) - 1:
        return float(index)

    y1 = profile[index - 1]
    y2 = profile[index]
    y3 = profile[index + 1]

    denominator = (
        y1
        - 2 * y2
        + y3
    )

    # 0 나누기 방지
    if denominator == 0:
        return float(index)

    offset = 0.5 * (
        y1 - y3
    ) / denominator

    return index + offset


# ---------------------------------
# 7. 여러 위치에서 Sub-pixel 측정
# ---------------------------------

diameters_sub = []

top_sub_values = []
bottom_sub_values = []

result = image.copy()


print()
print("x | top_sub | bottom_sub | diameter_sub")
print("---------------------------------------------")


for x in x_positions:

    # x 주변 5pixel 평균 사용
    x1 = max(0, x - 2)
    x2 = min(width, x + 3)

    strip = gradient_abs[:, x1:x2]

    profile = np.mean(
        strip,
        axis=1
    )


    # ---------------------------------
    # 상단 Edge
    # ---------------------------------

    top_profile = profile[:center_y]

    top_index = np.argmax(
        top_profile
    )

    y_top_sub = subpixel_peak(
        top_profile,
        top_index
    )


    # ---------------------------------
    # 하단 Edge
    # ---------------------------------

    bottom_profile = profile[center_y:]

    bottom_index_local = np.argmax(
        bottom_profile
    )

    bottom_index = (
        center_y
        + bottom_index_local
    )

    y_bottom_sub = subpixel_peak(
        profile,
        bottom_index
    )


    # ---------------------------------
    # 외경 계산
    # ---------------------------------

    diameter_sub = (
        y_bottom_sub
        - y_top_sub
    )

    top_sub_values.append(
        y_top_sub
    )

    bottom_sub_values.append(
        y_bottom_sub
    )

    diameters_sub.append(
        diameter_sub
    )


    print(
        x,
        "|",
        round(y_top_sub, 3),
        "|",
        round(y_bottom_sub, 3),
        "|",
        round(diameter_sub, 3)
    )


    # ---------------------------------
    # 표시
    # ---------------------------------

    y_top_draw = int(
        round(y_top_sub)
    )

    y_bottom_draw = int(
        round(y_bottom_sub)
    )

    cv2.circle(
        result,
        (x, y_top_draw),
        5,
        (0, 0, 255),
        -1
    )

    cv2.circle(
        result,
        (x, y_bottom_draw),
        5,
        (255, 0, 0),
        -1
    )

    cv2.line(
        result,
        (x, y_top_draw),
        (x, y_bottom_draw),
        (0, 255, 0),
        2
    )


# ---------------------------------
# 8. 대표값 계산
# ---------------------------------

mean_sub = np.mean(
    diameters_sub
)

median_sub = np.median(
    diameters_sub
)

std_sub = np.std(
    diameters_sub
)


print()
print("========== Sub-pixel 결과 ==========")

print(
    "외경 평균(sub-pixel) :",
    mean_sub
)

print(
    "외경 중앙값(sub-pixel) :",
    median_sub
)

print(
    "외경 표준편차(sub-pixel) :",
    std_sub
)


# ---------------------------------
# 9. mm 변환
# ---------------------------------

MM_PER_PIXEL = 0.0436166

measured_mm = (
    median_sub
    * MM_PER_PIXEL
)


print()
print(
    "영상 측정 외경(mm) :",
    measured_mm
)


# ---------------------------------
# 10. 실제 계측값 입력
# ---------------------------------

actual_mm = float(
    input(
        "실제 계측기 외경(mm)을 입력하세요 : "
    )
)


# ---------------------------------
# 11. 오차 계산
# ---------------------------------

error_mm = (
    measured_mm
    - actual_mm
)

error_um = (
    error_mm
    * 1000
)

abs_error_um = abs(
    error_um
)


print()
print(
    "영상 측정값(mm) :",
    measured_mm
)

print(
    "실제 계측값(mm) :",
    actual_mm
)

print(
    "오차(mm) :",
    error_mm
)

print(
    "오차(μm) :",
    error_um
)

print(
    "절대오차(μm) :",
    abs_error_um
)


# ---------------------------------
# 12. Day018과 비교
# ---------------------------------

DAY018_ERROR_UM = 130.8498

improvement = (
    DAY018_ERROR_UM
    - abs_error_um
)


print()
print(
    "Day018 절대오차(μm) :",
    DAY018_ERROR_UM
)

print(
    "Day019 절대오차(μm) :",
    abs_error_um
)

print(
    "오차 개선량(μm) :",
    improvement
)


# ---------------------------------
# 13. 결과 표시
# ---------------------------------

text1 = f"SubPixel: {median_sub:.3f} px"
text2 = f"Vision: {measured_mm:.3f} mm"
text3 = f"Error: {error_um:.1f} um"

cv2.putText(
    result,
    text1,
    (10, 30),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.6,
    (0, 255, 0),
    2
)

cv2.putText(
    result,
    text2,
    (10, 60),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.6,
    (0, 255, 0),
    2
)

cv2.putText(
    result,
    text3,
    (10, 90),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.6,
    (0, 255, 0),
    2
)


# ---------------------------------
# 14. 저장
# ---------------------------------

output_dir = Path("Day019")

output_dir.mkdir(exist_ok=True)

cv2.imwrite(
    str(
        output_dir
        / "subpixel_result.jpg"
    ),
    result
)

print()
print(
    "저장 완료 : Day019/subpixel_result.jpg"
)