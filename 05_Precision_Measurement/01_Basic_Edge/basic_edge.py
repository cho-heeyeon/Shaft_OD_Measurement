import cv2
import numpy as np
from pathlib import Path


# 1. ROI 이미지 읽기
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


# 5. Edge 이미지 저장
output_path = Path("Day014/edge.jpg")

cv2.imwrite(
    str(output_path),
    edge
)

print("Edge 저장 완료 :", output_path)

# 각 y 위치에 Edge pixel이 몇 개 있는지 계산
row_scores = np.sum(edge > 0, axis=1)

height = edge.shape[0]

center_y = height // 2

print("ROI 높이 :", height)
print("ROI 중심 y :", center_y)

top_scores = row_scores[:center_y]

y_top = np.argmax(top_scores)

print("위쪽 Edge :", y_top)

bottom_scores = row_scores[center_y:]

y_bottom = center_y + np.argmax(bottom_scores)

print("아래쪽 Edge :", y_bottom)

diameter_pixel = y_bottom - y_top

print("샤프트 외경(pixel) :", diameter_pixel)

result = image.copy()

width = image.shape[1]

# 위쪽 Edge
cv2.line(
    result,
    (0, y_top),
    (width, y_top),
    (0, 0, 255),
    2
)

# 아래쪽 Edge
cv2.line(
    result,
    (0, y_bottom),
    (width, y_bottom),
    (255, 0, 0),
    2
)

# 결과 저장
result_path = Path("Day014/diameter_result.jpg")

cv2.imwrite(
    str(result_path),
    result
)

print("측정 결과 저장 :", result_path)