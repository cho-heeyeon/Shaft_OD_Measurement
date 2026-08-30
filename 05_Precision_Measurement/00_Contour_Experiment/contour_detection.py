import cv2
from pathlib import Path


def main():
    # 이미지 경로 설정
    image_path = Path("Day010/sample.jpg")

    # 이미지 읽기
    image = cv2.imread(str(image_path))

    # 이미지 읽기 실패 확인
    if image is None:
        print("이미지를 읽을 수 없습니다.")
        return

    # 원본 이미지 복사
    result = image.copy()

    # 흑백 이미지로 변환
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 노이즈 감소
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 경계선 검출
    edges = cv2.Canny(blurred, 50, 150)

    # Contour 검출
    contours, hierarchy = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    print("찾은 Contour 개수 :", len(contours))

    # Contour가 없을 경우 종료
    if len(contours) == 0:
        print("Contour를 찾지 못했습니다.")
        return

    # 가장 큰 Contour 선택
    largest_contour = max(contours, key=cv2.contourArea)

    # 가장 큰 Contour의 면적 계산
    largest_area = cv2.contourArea(largest_contour)

    print("가장 큰 Contour 면적 :", largest_area)

    # 가장 큰 Contour만 초록색으로 그리기
    cv2.drawContours(
        result,
        [largest_contour],
        -1,
        (0, 255, 0),
        3
    )

    # 결과 이미지 저장
    output_path = Path("Day010/largest_contour.jpg")
    cv2.imwrite(str(output_path), result)

    print("결과 이미지 저장 완료 :", output_path)


if __name__ == "__main__":
    main()