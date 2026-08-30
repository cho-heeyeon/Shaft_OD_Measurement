# Pixel → mm Calibration

## 1. 목적

OpenCV 영상처리에서 계산되는 샤프트 외경은 Pixel 단위이다.

그러나 실제 제조공정에서 샤프트 외경은 mm 단위로 관리하므로,
영상에서 측정한 Pixel 값을 실제 길이(mm)로 변환하는
Calibration 과정이 필요하다.

본 단계의 목적은 다음 변환 구조를 구현하는 것이다.

Pixel 외경 측정
→ Calibration
→ 실제 외경(mm)


---

## 2. Calibration이 필요한 이유

영상에서 측정된 Pixel 수 자체는 실제 길이를 의미하지 않는다.

Pixel과 실제 길이의 관계는 다음과 같은 촬영조건의 영향을 받을 수 있다.

- 카메라 해상도
- 렌즈
- 카메라와 제품 사이의 거리
- 촬영 배율
- 영상 크기

따라서 실제 크기를 알고 있는 기준값과
영상에서 측정한 Pixel 값을 대응시켜
Pixel → mm 변환 기준을 설정해야 한다.


---

## 3. Calibration 기본 개념

본 단계에서는 실제 계측기로 측정한 외경과
영상에서 측정한 대표 Pixel 외경을 이용하여
mm/pixel 변환계수를 계산하였다.

계산식은 다음과 같다.

`mm_per_pixel = actual_mm / median_pixel`

여기서

- `actual_mm` : 실제 계측기로 측정한 외경(mm)
- `median_pixel` : 영상에서 측정한 대표 외경(pixel)
- `mm_per_pixel` : 1 Pixel에 해당하는 실제 길이(mm/pixel)

이후 Pixel 외경에 변환계수를 적용하여
mm 단위 외경으로 변환하였다.

`measured_mm = median_pixel × mm_per_pixel`


---

## 4. Day016 Calibration 구현

Day016에서는 ROI 중앙 영역의 여러 위치에서
샤프트 상단과 하단 Edge를 검출하고 외경을 측정하였다.

측정 과정은 다음과 같다.

1. ROI 이미지 입력
2. Gray 변환
3. Gaussian Blur
4. Canny Edge 검출
5. 중앙 측정영역 설정
6. 가로 방향 7개 위치 선정
7. 각 위치의 상단/하단 Edge 검출
8. 각 위치의 Pixel 외경 계산
9. 7개 측정값의 Median을 대표 Pixel 외경으로 사용
10. 실제 계측기 외경 입력
11. mm/pixel 변환계수 계산
12. Pixel → mm 변환


---

## 5. Calibration 결과

Day016 기록에서 확인된 Calibration 값은 다음과 같다.

| 항목 | 값 |
|---|---:|
| 대표 Pixel 외경 | 459 px |
| 실제 계측기 기준값 | 20.020 mm |
| 변환계수 | 0.0436166 mm/pixel |
| 변환 결과 | 20.020 mm |

변환계수는 다음 관계로 계산하였다.

`20.020 mm / 459 px ≈ 0.0436166 mm/pixel`

이를 통해 영상에서 측정한 Pixel 외경을
실제 mm 단위로 변환하는 기본 Calibration 구조를 구현하였다.


---

## 6. 결과 이미지

결과 이미지에서는 7개 위치에서 측정한
상단 및 하단 Edge와 외경 측정 구간을 표시하였다.

- 빨간 점 : 상단 Edge
- 파란 점 : 하단 Edge
- 초록선 : 상단 Edge와 하단 Edge 사이의 외경 측정 구간
- 상단 문자 : Calibration을 통해 변환된 외경(mm)

![Calibration 결과](./calibration_result.jpg)


---

## 7. Calibration의 의미

Calibration을 적용하기 전까지 외경 측정결과는
Pixel 단위이므로 실제 도면 규격과 직접 비교할 수 없다.

Calibration을 적용함으로써 다음 구조가 가능해졌다.

영상 측정
→ Pixel 외경
→ mm 외경
→ 도면 규격과 비교

즉,

- OpenCV : Pixel 단위 외경 측정
- Calibration : Pixel을 mm로 변환

하는 역할로 구분할 수 있다.


---

## 8. 검증 한계

본 단계의 Calibration은 하나의 기준값을 이용한
단일 기준점 Calibration이다.

또한 실제 계측값을 이용하여 변환계수를 계산한 뒤,
동일한 대표 Pixel값에 해당 계수를 다시 적용하므로
변환 결과가 기준값과 일치하는 것은 계산 구조상 자연스럽다.

따라서

`20.020 mm → Calibration → 20.020 mm`

라는 결과를 측정시스템이
20.020 mm를 독립적으로 정확하게 측정했다는
성능 검증 결과로 해석해서는 안 된다.

또한 이 결과만으로 측정시스템이
±0.010 mm 수준의 정확도를 확보했다고 판단할 수 없다.


---

## 9. 향후 Calibration 검증

실제 생산환경에서 정밀 측정시스템으로 사용하기 위해서는
다음과 같은 추가 검증이 필요하다.

1. 서로 다른 외경을 가진 복수 기준물 확보
2. 기준물의 실제 외경 측정
3. 동일 촬영조건에서 Pixel 외경 측정
4. Pixel ↔ mm 대응 데이터 구축
5. 복수 기준점을 이용한 Calibration 모델 산출
6. Calibration에 사용하지 않은 독립 샘플 측정
7. 기준값과 Vision 측정값 비교
8. 측정오차 분석
9. 반복 측정 안정성 평가


---

## 10. 전체 시스템에서의 역할

Calibration은 전체 측정 시스템에서 다음 위치에 해당한다.

이미지 입력
→ YOLO ROI 탐지
→ OpenCV Edge 검출
→ Multi-point 측정
→ Median 안정화
→ Gradient / Sub-pixel
→ Line Fitting
→ Pixel 외경
→ Calibration
→ mm 외경
→ 규격 비교
→ OK / NG

즉,

YOLO는 **어디를 측정할 것인가**

OpenCV는 **Pixel로 얼마인가**

Calibration은 **실제 mm로 얼마인가**

를 담당한다.


---

## 11. 결론

본 단계에서는 실제 계측값과 영상의 Pixel 외경을 이용하여
Pixel → mm 변환계수를 계산하고,
영상 측정결과를 실제 mm 단위로 변환하는
Calibration 구조를 구현하였다.

다만 현재 Calibration은 단일 기준값을 이용한
개발단계 Calibration이므로
최종 측정 정확도 검증으로 해석하지 않는다.

향후 복수 기준물과 독립적인 검증 데이터를 이용하여
Calibration 정확도와 측정시스템 성능을
별도로 검증할 필요가 있다.# Pixel → mm Calibration

## 1. 목적

OpenCV 영상처리에서 계산되는 샤프트 외경은 Pixel 단위이다.

그러나 실제 제조공정에서 샤프트 외경은 mm 단위로 관리하므로,
영상에서 측정한 Pixel 값을 실제 길이(mm)로 변환하는
Calibration 과정이 필요하다.

본 단계의 목적은 다음 변환 구조를 구현하는 것이다.

Pixel 외경 측정
→ Calibration
→ 실제 외경(mm)


---

## 2. Calibration이 필요한 이유

영상에서 측정된 Pixel 수 자체는 실제 길이를 의미하지 않는다.

Pixel과 실제 길이의 관계는 다음과 같은 촬영조건의 영향을 받을 수 있다.

- 카메라 해상도
- 렌즈
- 카메라와 제품 사이의 거리
- 촬영 배율
- 영상 크기

따라서 실제 크기를 알고 있는 기준값과
영상에서 측정한 Pixel 값을 대응시켜
Pixel → mm 변환 기준을 설정해야 한다.


---

## 3. Calibration 기본 개념

본 단계에서는 실제 계측기로 측정한 외경과
영상에서 측정한 대표 Pixel 외경을 이용하여
mm/pixel 변환계수를 계산하였다.

계산식은 다음과 같다.

`mm_per_pixel = actual_mm / median_pixel`

여기서

- `actual_mm` : 실제 계측기로 측정한 외경(mm)
- `median_pixel` : 영상에서 측정한 대표 외경(pixel)
- `mm_per_pixel` : 1 Pixel에 해당하는 실제 길이(mm/pixel)

이후 Pixel 외경에 변환계수를 적용하여
mm 단위 외경으로 변환하였다.

`measured_mm = median_pixel × mm_per_pixel`


---

## 4. Day016 Calibration 구현

Day016에서는 ROI 중앙 영역의 여러 위치에서
샤프트 상단과 하단 Edge를 검출하고 외경을 측정하였다.

측정 과정은 다음과 같다.

1. ROI 이미지 입력
2. Gray 변환
3. Gaussian Blur
4. Canny Edge 검출
5. 중앙 측정영역 설정
6. 가로 방향 7개 위치 선정
7. 각 위치의 상단/하단 Edge 검출
8. 각 위치의 Pixel 외경 계산
9. 7개 측정값의 Median을 대표 Pixel 외경으로 사용
10. 실제 계측기 외경 입력
11. mm/pixel 변환계수 계산
12. Pixel → mm 변환


---

## 5. Calibration 결과

Day016 기록에서 확인된 Calibration 값은 다음과 같다.

| 항목 | 값 |
|---|---:|
| 대표 Pixel 외경 | 459 px |
| 실제 계측기 기준값 | 20.020 mm |
| 변환계수 | 0.0436166 mm/pixel |
| 변환 결과 | 20.020 mm |

변환계수는 다음 관계로 계산하였다.

`20.020 mm / 459 px ≈ 0.0436166 mm/pixel`

이를 통해 영상에서 측정한 Pixel 외경을
실제 mm 단위로 변환하는 기본 Calibration 구조를 구현하였다.


---

## 6. 결과 이미지

결과 이미지에서는 7개 위치에서 측정한
상단 및 하단 Edge와 외경 측정 구간을 표시하였다.

- 빨간 점 : 상단 Edge
- 파란 점 : 하단 Edge
- 초록선 : 상단 Edge와 하단 Edge 사이의 외경 측정 구간
- 상단 문자 : Calibration을 통해 변환된 외경(mm)

![Calibration 결과](./calibration_result.jpg)


---

## 7. Calibration의 의미

Calibration을 적용하기 전까지 외경 측정결과는
Pixel 단위이므로 실제 도면 규격과 직접 비교할 수 없다.

Calibration을 적용함으로써 다음 구조가 가능해졌다.

영상 측정
→ Pixel 외경
→ mm 외경
→ 도면 규격과 비교

즉,

- OpenCV : Pixel 단위 외경 측정
- Calibration : Pixel을 mm로 변환

하는 역할로 구분할 수 있다.


---

## 8. 검증 한계

본 단계의 Calibration은 하나의 기준값을 이용한
단일 기준점 Calibration이다.

또한 실제 계측값을 이용하여 변환계수를 계산한 뒤,
동일한 대표 Pixel값에 해당 계수를 다시 적용하므로
변환 결과가 기준값과 일치하는 것은 계산 구조상 자연스럽다.

따라서

`20.020 mm → Calibration → 20.020 mm`

라는 결과를 측정시스템이
20.020 mm를 독립적으로 정확하게 측정했다는
성능 검증 결과로 해석해서는 안 된다.

또한 이 결과만으로 측정시스템이
±0.010 mm 수준의 정확도를 확보했다고 판단할 수 없다.


---

## 9. 향후 Calibration 검증

실제 생산환경에서 정밀 측정시스템으로 사용하기 위해서는
다음과 같은 추가 검증이 필요하다.

1. 서로 다른 외경을 가진 복수 기준물 확보
2. 기준물의 실제 외경 측정
3. 동일 촬영조건에서 Pixel 외경 측정
4. Pixel ↔ mm 대응 데이터 구축
5. 복수 기준점을 이용한 Calibration 모델 산출
6. Calibration에 사용하지 않은 독립 샘플 측정
7. 기준값과 Vision 측정값 비교
8. 측정오차 분석
9. 반복 측정 안정성 평가


---

## 10. 전체 시스템에서의 역할

Calibration은 전체 측정 시스템에서 다음 위치에 해당한다.

이미지 입력
→ YOLO ROI 탐지
→ OpenCV Edge 검출
→ Multi-point 측정
→ Median 안정화
→ Gradient / Sub-pixel
→ Line Fitting
→ Pixel 외경
→ Calibration
→ mm 외경
→ 규격 비교
→ OK / NG

즉,

YOLO는 **어디를 측정할 것인가**

OpenCV는 **Pixel로 얼마인가**

Calibration은 **실제 mm로 얼마인가**

를 담당한다.


---

## 11. 결론

본 단계에서는 실제 계측값과 영상의 Pixel 외경을 이용하여
Pixel → mm 변환계수를 계산하고,
영상 측정결과를 실제 mm 단위로 변환하는
Calibration 구조를 구현하였다.

다만 현재 Calibration은 단일 기준값을 이용한
개발단계 Calibration이므로
최종 측정 정확도 검증으로 해석하지 않는다.

향후 복수 기준물과 독립적인 검증 데이터를 이용하여
Calibration 정확도와 측정시스템 성능을
별도로 검증할 필요가 있다.