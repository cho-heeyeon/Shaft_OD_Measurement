
import cv2
from pathlib import Path


# ---------------------------------
# 1. 경로 설정
# ---------------------------------

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

base_dir = ROOT / "02_Data" / "04_YOLO_Dataset"

image_dir = base_dir / "images" / "train"
label_dir = base_dir / "labels" / "train"

verify_dir = base_dir / "verified"
verify_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------
# 2. 이미지 목록
# ---------------------------------

sample_files = [
    "sample_03.jpg",
    "sample_04.jpg",
    "sample_06.jpg",
    "sample_07.jpg",
    "sample_N01.jpg",
    "sample_N02.jpg",
]


# ---------------------------------
# 3. 이미지별 라벨 검증
# ---------------------------------

for filename in sample_files:

    image_path = image_dir / filename

    label_path = (
        label_dir
        / f"{Path(filename).stem}.txt"
    )

    image = cv2.imread(str(image_path))

    if image is None:
        print("이미지를 찾을 수 없습니다 :", image_path)
        continue

    if not label_path.exists():
        print("라벨 파일이 없습니다 :", label_path)
        continue

    height, width = image.shape[:2]

    result = image.copy()


    # ---------------------------------
    # 4. YOLO 라벨 읽기
    # ---------------------------------

    with open(
        label_path,
        "r",
        encoding="utf-8"
    ) as f:

        lines = f.readlines()


    for line in lines:

        parts = line.strip().split()

        if len(parts) != 5:
            continue

        class_id = int(parts[0])

        x_center_norm = float(parts[1])
        y_center_norm = float(parts[2])
        width_norm = float(parts[3])
        height_norm = float(parts[4])


        # ---------------------------------
        # 5. 정규화 좌표 → pixel 좌표
        # ---------------------------------

        box_width = width_norm * width
        box_height = height_norm * height

        center_x = x_center_norm * width
        center_y = y_center_norm * height


        x1 = int(
            center_x
            - box_width / 2
        )

        y1 = int(
            center_y
            - box_height / 2
        )

        x2 = int(
            center_x
            + box_width / 2
        )

        y2 = int(
            center_y
            + box_height / 2
        )


        # ---------------------------------
        # 6. Bounding Box 표시
        # ---------------------------------

        cv2.rectangle(
            result,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            5
        )


        # 클래스 이름 표시
        text = "measurement_roi"

        cv2.putText(
            result,
            text,
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            3
        )


    # ---------------------------------
    # 7. 결과 저장
    # ---------------------------------

    output_path = (
        verify_dir
        / f"{Path(filename).stem}_verified.jpg"
    )

    cv2.imwrite(
        str(output_path),
        result
    )

    print(
        "검증 이미지 저장 :",
        output_path
    )


print()
print("==============================")
print("YOLO 라벨 검증 완료")
print("==============================")
