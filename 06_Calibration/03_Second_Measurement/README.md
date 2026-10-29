
# 2차 측정 Calibration

## 1. 목적

1차 측정에서는 기본 Pixel → mm 변환 가능성과 촬영조건의 영향을 확인하였다.

2차 측정에서는 단순한 단일 기준점 Calibration을 넘어, **복수 시편을 이용하여 Calibration과 Validation을 분리하고 실제 측정 성능을 검증하는 구조**를 구축하는 것을 목표로 하였다.

전체 구조는 다음과 같다.

```text
Calibration 시편
    ↓
Pixel ↔ 실제 외경 관계 산출
    ↓
Calibration 모델
    ↓
Validation 시편
    ↓
Vision 측정값과 실제 기준값 비교
```

---

## 2. 측정 구조

2차 측정에서는 OpenCV 기반 Edge 측정을 보다 정밀화하였다.

주요 처리 흐름은 다음과 같다.

```text
이미지 입력
    ↓
ROI 설정
    ↓
상·하 Edge 검출
    ↓
Multi-point 측정
    ↓
Median
    ↓
MAD 기반 이상치 확인
    ↓
Sub-pixel
    ↓
Line fitting
    ↓
대표 Pixel 외경
    ↓
Calibration
    ↓
mm 외경
```

단일 지점의 Edge 값에 의존하지 않고 여러 위치에서 측정한 값을 이용하여 반복성과 안정성을 높이는 방향으로 발전하였다.

---

## 3. Calibration과 Validation 분리

2차 측정에서는 Calibration에 사용한 시편과 검증에 사용하는 시편을 분리하였다.

목적은 Calibration에 사용한 동일 데이터에서 다시 성능을 평가하는 문제를 피하고, Calibration 모델이 새로운 시편에서도 적용 가능한지 확인하는 것이었다.

구조는 다음과 같다.

```text
Calibration Data
    ↓
Pixel → mm 관계 산출
    ↓
Calibration 식

Independent Validation Data
    ↓
Vision 측정
    ↓
실측값과 비교
```

이를 통해 Calibration 식의 계산과 실제 성능 검증을 별도의 단계로 관리하였다.

---

## 4. V2 정밀측정 적용

2차 측정에서는 V2 계열의 정밀 Edge 측정 방식을 적용하였다.

주요 개선사항은 다음과 같다.

- 여러 위치에서 외경 측정
- Median 기반 대표값 산출
- MAD 기반 이상값 확인
- Gradient 기반 상·하 Edge 검출
- Sub-pixel 적용
- Line fitting 적용
- ROI 내부에서 실제 외곽 Edge를 찾는 방향으로 개선

이 단계의 목표는 단순한 Canny Edge보다 정밀하고 반복 가능한 Pixel 외경을 얻는 것이었다.

---

## 5. 정량 결과

초기 6개 시편을 이용한 V2 Calibration에서는 Pixel과 실제 외경 사이의 선형관계를 산출하였다.

당시 V2 전용 Calibration 식은 다음과 같이 계산되었다.

```text
mm = 0.00768241927417 × pixel + 11.1258745302
```

Calibration 데이터에서는 비교적 높은 선형성이 나타났다.

```text
R² ≈ 0.9869
```

그러나 Validation 데이터 전체에 적용했을 때는 다음과 같은 결과가 나타났다.

| 항목 | 결과 |
|---|---:|
| Bias | 약 -0.0382 mm |
| MAE | 약 0.05446 mm |
| 최대오차 | 약 0.14417 mm |
| OK 판정 | 11 / 42 |

따라서 Calibration 데이터 내부의 선형성만으로는 실제 측정 성능을 보장할 수 없음을 확인하였다.

---

## 6. 확인된 주요 문제

### 6.1 Pixel 순서성 문제

일부 시편에서는 실제 외경이 증가해도 Pixel 외경이 기대한 방향으로 변화하지 않았다.

즉, 실제 외경과 Pixel값의 순서가 일관되지 않는 문제가 나타났다.

이는 단순한 Calibration 식의 문제가 아니라, 영상에서 선택되는 Edge 자체가 불안정할 가능성을 의미하였다.

---

### 6.2 내부 Edge 및 반사 영향

표면 반사나 명암 변화에 의해 실제 외곽선보다 내부의 강한 Edge가 선택되는 사례가 확인되었다.

이 경우 측정 Pixel값 자체가 실제 외경을 나타내지 않으므로 Calibration 식을 적용하더라도 정확한 mm 값을 얻기 어렵다.

---

### 6.3 YOLO Bounding Box 의존성

초기 V2 측정에서는 YOLO가 검출한 Bounding Box의 높이와 위치가 OpenCV 정밀측정 결과에 영향을 줄 가능성이 확인되었다.

특히 특정 Gate 범위에 의존할 경우 Bounding Box 변화가 ROI 및 Edge 선택에 영향을 줄 수 있었다.

따라서 이후 단계에서는:

```text
YOLO = 측정 위치 탐색
OpenCV = 정밀 외경 측정
```

으로 역할을 분리하고, YOLO Bounding Box의 크기 자체를 정밀 치수 판단에 사용하지 않는 방향으로 개선하였다.

---

### 6.4 시편 위치 및 촬영배율

시편의 높이, 카메라와의 거리, 촬영배율 변화도 Pixel값 변화의 원인 후보로 확인되었다.

일반 렌즈와 스마트폰 환경에서는 Z 방향 위치 변화가 영상 배율 변화로 이어질 수 있기 때문에, Calibration 식의 안정성을 확보하려면 촬영조건을 더 엄격하게 고정할 필요가 있었다.

---

## 7. 2차 측정의 해석

2차 측정에서는 복수 시편을 이용하여 Calibration 모델을 만들고 Validation 데이터에 적용하는 구조까지 구현하였다.

그러나 Validation 결과에서 오차가 크게 나타났고, 일부 시편에서는 Pixel 순서성 문제와 Edge 오선택이 확인되었다.

따라서 이 단계에서의 핵심 결론은 다음과 같다.

> Calibration 수식의 선형성이 높더라도, 측정 Pixel값 자체가 물리적으로 안정하지 않으면 실제 측정 정확도는 확보할 수 없다.

즉, Calibration 모델보다 먼저 다음 조건을 해결해야 한다고 판단하였다.

- 실제 외곽 Edge의 안정적인 선택
- ROI 위치의 일관성
- 촬영거리 및 배율 고정
- 시편 높이와 위치 고정
- 반복 촬영 Pixel 안정성 확보

---

## 8. 다음 단계로의 개선 방향

2차 측정 결과를 바탕으로 3차 측정에서는 Calibration 식 자체보다 **촬영조건과 Edge 검출 안정성 문제를 우선적으로 해결하는 방향**으로 전환하였다.

주요 개선 방향은 다음과 같다.

1. 촬영거리 고정
2. V-block 사용
3. 백라이트 적용
4. 차광 적용
5. 스마트폰 1.0× 고정
6. 카메라와 샤프트 중심 높이 정렬
7. 동일 물리적 측정부 기준 ROI 적용
8. YOLO Bounding Box 의존성 축소
9. Reflection 대응 Edge 알고리즘 적용
10. 반복 촬영을 통한 Pixel 안정성 재확인

---

## 9. 결론

2차 측정에서는 단일 기준점 Calibration에서 발전하여, 복수 시편을 이용한 Calibration과 Independent Validation 구조를 구현하였다.

또한 Multi-point, Median, MAD, Sub-pixel 및 Line fitting 등 정밀 Edge 측정 알고리즘을 적용하였다.

하지만 Validation 결과에서는 오차가 크게 나타났고, 일부 시편에서 Pixel 순서성 및 Edge 오선택 문제가 확인되었다.

따라서 2차 측정의 핵심 성과는 최종 Calibration 식을 확정한 것이 아니라,

> **Calibration 성능을 제한하는 주요 원인이 수식 자체보다 촬영조건, ROI 및 Edge 선택 안정성에 있음을 확인한 것**

으로 정리한다.

이 결과를 바탕으로 3차 측정에서는 촬영조건을 고정하고 실제 측정부를 다시 정의하여 Calibration 문제를 재검토하였다.
