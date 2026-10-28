
import cv2
from pathlib import Path


# ---------------------------------
# 1. 경로 설정
# ---------------------------------

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

base_dir = ROOT / "02_Data" / "04_YOLO_Dataset"

image_dir = base_dir / "images"
label_dir = base_dir / "labels"

label_dir.mkdir(exist_ok=True)


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
# 3. 마우스 상태 변수
# ---------------------------------

drawing = False

start_point = None
end_point = None


# ---------------------------------
# 4. 마우스 콜백 함수
# ---------------------------------

def mouse_callback(event, x, y, flags, param):

    global drawing
    global start_point
    global end_point

    # 왼쪽 버튼 누름
    if event == cv2.EVENT_LBUTTONDOWN:

        drawing = True

        start_point = (x, y)
        end_point = (x, y)


    # 마우스 이동
    elif event == cv2.EVENT_MOUSEMOVE:

        if drawing:

            end_point = (x, y)


    # 왼쪽 버튼 놓음
    elif event == cv2.EVENT_LBUTTONUP:

        drawing = False

        end_point = (x, y)


# ---------------------------------
# 5. 이미지별 라벨링
# ---------------------------------

for filename in sample_files:

    image_path = image_dir / filename

    image = cv2.imread(str(image_path))

    if image is None:

        print(
            "이미지를 찾을 수 없습니다 :",
            image_path
        )

        continue


    original_height, original_width = image.shape[:2]


    # ---------------------------------
    # 화면 표시용 축소
    # ---------------------------------

    scale = 0.4

    display = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale
    )


    window_name = f"Label ROI - {filename}"


    cv2.namedWindow(window_name)

    cv2.setMouseCallback(
        window_name,
        mouse_callback
    )


    start_point = None
    end_point = None


    print()
    print("==============================")
    print("현재 이미지 :", filename)
    print("==============================")

    print(
        "마우스로 측정 ROI를 드래그하세요."
    )

    print(
        "완료 : ENTER 또는 SPACE"
    )

    print(
        "다시 선택 : R"
    )

    print(
        "취소 : ESC"
    )


    # ---------------------------------
    # ROI 선택 반복
    # ---------------------------------

    while True:

        temp = display.copy()


        # 선택 박스 표시
        if (
            start_point is not None
            and end_point is not None
        ):

            cv2.rectangle(
                temp,
                start_point,
                end_point,
                (0, 0, 255),
                2
            )


        cv2.imshow(
            window_name,
            temp
        )


        key = (
            cv2.waitKey(20)
            & 0xFF
        )


        # Enter 또는 Space
        if key == 13 or key == 32:

            if (
                start_point is not None
                and end_point is not None
            ):

                break


        # R = 다시 선택
        elif key == ord("r"):

            start_point = None
            end_point = None


        # ESC
        elif key == 27:

            start_point = None
            end_point = None

            break


    cv2.destroyWindow(
        window_name
    )


    # ---------------------------------
    # 선택 안 한 경우
    # ---------------------------------

    if (
        start_point is None
        or end_point is None
    ):

        print(
            "라벨 선택 취소 :",
            filename
        )

        continue


    # ---------------------------------
    # 6. 좌표 정리
    # ---------------------------------

    x1 = min(
        start_point[0],
        end_point[0]
    )

    y1 = min(
        start_point[1],
        end_point[1]
    )

    x2 = max(
        start_point[0],
        end_point[0]
    )

    y2 = max(
        start_point[1],
        end_point[1]
    )


    # 원본 이미지 좌표로 복원
    x1 = int(x1 / scale)
    y1 = int(y1 / scale)

    x2 = int(x2 / scale)
    y2 = int(y2 / scale)


    # ---------------------------------
    # 7. Bounding Box 크기
    # ---------------------------------

    box_width = x2 - x1
    box_height = y2 - y1


    center_x = (
        x1 + box_width / 2
    )

    center_y = (
        y1 + box_height / 2
    )


    # ---------------------------------
    # 8. YOLO 정규화
    # ---------------------------------

    x_center_norm = (
        center_x / original_width
    )

    y_center_norm = (
        center_y / original_height
    )

    width_norm = (
        box_width / original_width
    )

    height_norm = (
        box_height / original_height
    )


    # ---------------------------------
    # 9. YOLO Label 저장
    # ---------------------------------

    class_id = 0

    label_path = (
        label_dir
        / f"{Path(filename).stem}.txt"
    )


    with open(
        label_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{class_id} "
            f"{x_center_norm:.6f} "
            f"{y_center_norm:.6f} "
            f"{width_norm:.6f} "
            f"{height_norm:.6f}\n"
        )


    print()
    print(
        "YOLO Label 저장 :",
        label_path
    )

    print(
        "class_id :",
        class_id
    )

    print(
        "x_center :",
        round(x_center_norm, 6)
    )

    print(
        "y_center :",
        round(y_center_norm, 6)
    )

    print(
        "width :",
        round(width_norm, 6)
    )

    print(
        "height :",
        round(height_norm, 6)
    )


print()
print("==============================")
print("모든 YOLO 라벨링 완료")
print("==============================")
