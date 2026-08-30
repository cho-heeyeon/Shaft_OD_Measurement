import cv2
import numpy as np
from pathlib import Path


# 1. Day013 ROI 이미지 읽기
image_path = Path("Day013/shaft_roi.jpg")

image = cv2.imread(str(image_path))

if image is None:
    raise FileNotFoundError("ROI 이미지를 찾을 수 없습니다.")


# 2. GRAY 변환
gray = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2GRAY
)


# 3. Blur
blur = cv2.GaussianBlur(
    gray,
    (5, 5),
    0
)


# 4. Edge 검출
edge = cv2.Canny(
    blur,
    50,
    150
)


# 5. 이미지 크기
height, width = edge.shape

center_y = height // 2


# 6. 중앙 측정 영역 설정
x_start = int(width * 0.25)
x_end = int(width * 0.75)

sample_count = 7

x_positions = np.linspace(
    x_start,
    x_end,
    sample_count,
    dtype=int
)


# 7. 외경 측정
diameters = []

result = image.copy()


for x in x_positions:

    x1 = max(0, x - 2)
    x2 = min(width, x + 3)

    strip = edge[:, x1:x2]

    row_scores = np.sum(
        strip > 0,
        axis=1
    )


    # 상단 Edge
    top_scores = row_scores[:center_y]

    y_top = np.argmax(top_scores)


    # 하단 Edge
    y_bottom = None

    for y in range(center_y, height):

        if row_scores[y] >= 2:

            y_bottom = y


    if y_bottom is None:
        continue


    diameter_pixel = y_bottom - y_top

    diameters.append(
        diameter_pixel
    )


    # 결과 표시
    cv2.circle(
        result,
        (x, y_top),
        5,
        (0, 0, 255),
        -1
    )

    cv2.circle(
        result,
        (x, y_bottom),
        5,
        (255, 0, 0),
        -1
    )

    cv2.line(
        result,
        (x, y_top),
        (x, y_bottom),
        (0, 255, 0),
        2
    )


# 8. 대표 Pixel 외경
median_pixel = np.median(diameters)

print("측정값(pixel) :", diameters)
print("대표 외경(pixel) :", median_pixel)


# 9. 실제 계측기 외경 입력
actual_mm = float(
    input("실제 계측기 외경(mm)을 입력하세요 : ")
)


# 10. 캘리브레이션
mm_per_pixel = actual_mm / median_pixel

print()
print("실제 외경(mm) :", actual_mm)
print("대표 외경(pixel) :", median_pixel)
print("1 pixel당 실제 길이 :", mm_per_pixel, "mm/pixel")


# 11. Pixel → mm 변환
measured_mm = median_pixel * mm_per_pixel

print("영상 측정 외경(mm) :", measured_mm)


# 12. 이미지에 측정값 표시
text = f"Diameter: {measured_mm:.3f} mm"

cv2.putText(
    result,
    text,
    (20, 40),
    cv2.FONT_HERSHEY_SIMPLEX,
    1.0,
    (0, 255, 0),
    2
)


# 13. 저장
output_dir = Path("Day016")

output_dir.mkdir(exist_ok=True)

cv2.imwrite(
    str(output_dir / "calibration_result.jpg"),
    result
)

cv2.imwrite(
    str(output_dir / "edge.jpg"),
    edge
)

print()
print("저장 완료 : Day016/calibration_result.jpg")