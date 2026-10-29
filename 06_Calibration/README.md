# Pixel → mm Calibration

## 1. 목적

OpenCV 영상처리에서 계산되는 샤프트 외경은 기본적으로 Pixel 단위이다.

그러나 실제 제조공정에서는 샤프트 외경을 mm 단위로 관리하므로, 영상에서 측정한 Pixel 외경을 실제 길이(mm)로 변환하는 Calibration 과정이 필요하다.

본 프로젝트에서는 Calibration을 한 번에 확정하지 않고, 측정 알고리즘과 촬영조건을 개선하면서 단계적으로 검증하였다.

전체 흐름은 다음과 같다.

```text
Day016 기본 Calibration 구현
        ↓
1차 측정
        ↓
2차 측정
        ↓
3차 측정
        ↓
현재 Calibration / Independent Validation 검증
```

---

## 2. Calibration이 필요한 이유

영상에서 측정된 Pixel 수 자체는 실제 길이를 의미하지 않는다.

Pixel과 실제 길이의 관계는 다음 조건의 영향을 받을 수 있다.

- 카메라 해상도
- 렌즈 특성
- 카메라와 제품 사이의 거리
- 촬영 배율
- 제품의 높이와 위치
- ROI 위치
- 영상 Scale
- 조명과 반사
- Edge 검출 위치

따라서 실제 크기를 알고 있는 기준값과 영상에서 측정한 Pixel 값을 대응시켜 Pixel → mm 변환 기준을 설정해야 한다.

---

# 3. Day016 — 기본 Calibration 구현

## 3.1 목적

Day016에서는 Pixel 외경을 mm 단위로 변환하는 가장 기본적인 Calibration 기능을 구현하였다.

실제 계측기로 측정한 하나의 기준 외경과 영상에서 측정한 대표 Pixel 값을 이용하여 mm/pixel 변환계수를 계산하였다.

기본 계산식은 다음과 같다.

```text
mm_per_pixel = actual_mm / median_pixel
```

이후:

```text
measured_mm = median_pixel × mm_per_pixel
```

을 적용하여 Pixel 외경을 mm 단위로 변환하였다.

---

## 3.2 측정 방법

Day016에서는 다음 순서로 측정하였다.

1. ROI 이미지 입력
2. Gray 변환
3. Gaussian Blur
4. Canny Edge 검출
5. 중앙 측정영역 설정
6. 가로 방향 7개 위치 선정
7. 각 위치의 상단 / 하단 Edge 검출
8. 각 위치의 Pixel 외경 계산
9. 7개 측정값의 Median 계산
10. 실제 계측기 기준값 입력
11. mm/pixel 변환계수 계산
12. Pixel → mm 변환

---

## 3.3 Day016 결과

당시 기록된 값은 다음과 같다.

| 항목 | 값 |
|---|---:|
| 대표 Pixel 외경 | 459 px |
| 실제 계측기 기준값 | 20.020 mm |
| 변환계수 | 0.0436166 mm/pixel |
| 변환 결과 | 20.020 mm |

계산식:

```text
20.020 mm / 459 px ≈ 0.0436166 mm/pixel
```

이를 통해 Pixel → mm 변환 기능 자체는 구현하였다.

다만 이 결과는 **단일 기준점으로 계산한 초기 개발단계 Calibration**이다.

동일 기준값으로 변환계수를 계산한 뒤 다시 동일 Pixel값에 적용한 것이므로, 20.020 mm가 다시 계산되는 것은 구조상 자연스럽다.

따라서 이 결과를 독립적인 측정 정확도 검증 결과로 해석하지 않는다.

---

# 4. 1차 측정 — Pixel → mm 적용 가능성 검토

Day016 기본 구현 이후 실제 샤프트 영상에 Calibration 구조를 적용하면서 Pixel 외경과 실제 외경의 대응 가능성을 검토하였다.

이 단계에서는 단순히 하나의 이미지에서 값을 변환하는 것이 아니라, 실제 촬영환경에서 반복적으로 사용할 수 있는지 확인하는 방향으로 확장하였다.

## 4.1 확인된 문제

1차 측정에서는 다음과 같은 문제가 확인되었다.

- 촬영거리 변화에 따른 영상 배율 변화
- 시편 위치 및 높이에 따른 Pixel 변화
- ROI 위치 변화
- 표면 반사에 의한 내부 Edge 선택 가능성
- 실제 외곽선이 아닌 잘못된 Edge 선택
- 기준 측정 위치와 영상 측정 위치 불일치 가능성

즉, 단순한 mm/pixel 계수만으로는 정밀 측정 안정성을 확보하기 어렵다는 점을 확인하였다.

---

# 5. 2차 측정 — Calibration과 Validation 분리

2차 측정에서는 Calibration에 사용한 시편과 Calibration에 사용하지 않은 시편을 구분하여 검증하는 방향으로 발전하였다.

목표는 단순 변환계수 계산이 아니라 다음 구조를 만드는 것이었다.

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

## 5.1 알고리즘 개선

이 단계에서는 초기 Edge 측정 방식에서 다음과 같은 정밀화가 이루어졌다.

- Multi-point 측정
- 31-point 측정 구조
- Median
- MAD
- Gradient 기반 Edge 검출
- Sub-pixel
- Line fitting

이를 통해 한 지점의 Edge 값에 의존하지 않고 여러 측정점의 대표값을 이용하도록 개선하였다.

---

## 5.2 확인된 문제

복수 시편에 Calibration을 적용한 결과 일부 데이터에서는 실제 외경 변화와 Pixel 변화의 관계가 예상과 다르게 나타났다.

주요 문제는 다음과 같았다.

- 기준 외경 증가와 Pixel 증가 방향이 일관되지 않는 경우
- 내부 반사 Edge 선택
- YOLO Bounding Box 위치 변화의 영향
- 촬영 배율 변화
- 시편의 깊이 및 높이 변화
- 실제 계측 위치와 영상 ROI 위치 차이

따라서 Calibration 수식 자체보다 **Pixel 측정값이 물리적으로 안정적인가**를 먼저 확인해야 한다고 판단하였다.

---

# 6. 3차 측정 — 촬영조건 및 Edge 안정성 중심 재검증

3차 측정에서는 Calibration 문제의 원인을 보다 명확하게 분리하기 위해 촬영조건과 측정영역을 재정비하였다.

## 6.1 촬영조건 개선

주요 촬영조건은 다음과 같이 관리하였다.

- 스마트폰 1.0× 고정
- V-block 사용
- 백라이트 사용
- 차광 적용
- 카메라와 샤프트 중심 높이 정렬
- 광축 90° 유지
- 촬영거리 고정
- 동일 ROI 적용
- 반복 촬영 수행

10월 8일 촬영에서는 400 mm 조건이 사용되었으며, 이후 촬영조건 비교를 통해 300 mm 조건의 안정성도 별도로 확인하였다.

---

## 6.2 YOLO와 정밀측정의 역할 분리

기존 YOLO 모델은 사용자가 지정한 `measurement_roi` 위치를 탐지하도록 학습하였다.

그러나 신규 촬영조건에서는 일부 이미지에서 ROI 검출 실패가 발생하였다.

따라서 정밀측정 검증 단계에서는 YOLO를 치수값 산출에 직접 사용하지 않고,

```text
YOLO = 측정 위치 탐색
OpenCV = 실제 Edge 측정
```

으로 역할을 분리하였다.

Calibration 원인분석 단계에서는 실제 측정부를 확인한 고정 ROI를 사용하여 Edge 측정 문제와 YOLO 위치 문제를 분리하였다.

---

## 6.3 최신 측정 ROI

3차 촬영 분석에서는 실제 측정부를 다시 확인하고 다음 ROI를 사용하였다.

```text
ROI = [8008, 3329, 8280, 4276]
```

ROI의 가로 방향 폭은 272 pixel이며 실제 측정부의 축 방향 길이 10.2 mm에 해당한다.

중앙 5 mm 영역은 샤프트 중심을 기준으로:

```text
좌측 2 mm + 우측 3 mm
```

범위로 설정하였다.

중요한 점은 이 272 pixel / 10.2 mm 관계는 **샤프트 축 방향 ROI 범위 정의용**이며, 외경 방향 Pixel → mm Calibration 계수로 사용하지 않는다는 것이다.

---

## 6.4 V3 Reflection 대응

3차 측정에서는 최신 측정엔진인:

```text
measurement_engine_EDGE_V3_REFLECTION.py
```

을 기준으로 Reflection 영향을 줄이는 방향으로 측정 알고리즘을 개선하였다.

주요 기능은 다음과 같다.

- 상·하 Edge 검출
- 31-point 측정
- Median
- MAD
- Gradient
- Sub-pixel
- Line fitting
- Reflection 대응
- 이상 Edge 억제

이 단계에서는 **실제 외곽 Edge가 안정적으로 검출되는지**를 Calibration보다 우선적으로 확인하였다.

---

# 7. 3차 Calibration 재검토

새 ROI와 안정된 Edge 결과를 기준으로 Calibration 후보 데이터를 다시 검토하였다.

일부 안정 데이터에서는 실제 외경 기준값과 Pixel값의 순서성이 다시 회복되는 결과가 확인되었다.

예를 들어 Calibration 후보 데이터에서는 다음과 같은 관계를 확인하였다.

| 시편 | 실제 기준값(mm) | 대표 Pixel |
|---|---:|---:|
| NO6 | 20.011 | 약 750.040 |
| NO2 | 20.020 | 약 749.688 |
| NO3 | 20.028 | 약 748.608 |

실제 외경이 증가하면서 측정 Pixel은 감소하는 관계가 나타났다.

이 관계는 수학적으로 Calibration 모델을 계산할 수 있으나, 일반적인 실루엣 외경 측정에서 기대되는 방향과 다르게 나타나는 부분이 있어 물리적 원인에 대한 추가 검증이 필요하다.

또한 세 기준값의 전체 범위가 약 17 μm 수준으로 매우 좁기 때문에 작은 Pixel 변동이 Calibration 식에 큰 영향을 줄 수 있다.

따라서 해당 결과는 **Calibration 후보 관계**로만 관리하고 최종 Calibration 식으로 확정하지 않았다.

---

# 8. 반복 촬영과 Calibration 안정성

3차 촬영에서는 동일 시편을 반복 촬영하여 Pixel 측정의 반복성을 함께 확인하였다.

일부 시편은 안정적인 CV를 보였으나, 일부 시편에서는 다음 문제가 확인되었다.

- 촬영 간 Pixel 이동
- Edge 오선택
- 재장착에 따른 위치 변화
- 반사 조건 변화
- 이상 측정값 발생

따라서 Calibration 정확도를 평가하기 전에 반복 측정에서 Pixel값이 안정적으로 유지되는지 확인하는 과정이 필요하다.

---

# 9. Pin Gauge 검토

촬영 시스템의 Scale 변화를 확인하기 위해 Pin Gauge를 함께 사용하는 방법도 검토하였다.

기본 개념은:

```text
Known Pin Diameter
        ↓
Pin Pixel 측정
        ↓
Scale 확인
```

이다.

그러나 현재 스마트폰 기반 조건에서는 Pin을 이용한 직접 보정값 적용 후 반복 CV가 오히려 증가하는 결과가 나타났다.

따라서 현재 단계에서 Pin Gauge는:

**직접적인 외경 보정용 기준물이라기보다 촬영 Scale 및 촬영환경 변화 진단용**

으로 사용하는 것이 더 적절하다고 판단하였다.

---

# 10. 표면거칠기와 Calibration

3차 측정에서는 Ra, Rq, Rz와 Edge 측정 안정성의 관계도 함께 검토하였다.

Rq가 증가할수록 Edge MAD가 증가하는 경향은 일부 데이터에서 관찰되었으나, 현재 데이터 수가 제한되어 있고 통계적 유의성이 확보되지 않았다.

또한 반복 촬영에서 발생하는 Pixel 이동과 Edge 오선택 영향이 존재하기 때문에 표면거칠기를 Calibration 오차의 직접 원인으로 단정하지 않는다.

따라서 표면거칠기 분석은 현재 **탐색적 분석**으로 관리한다.

---

# 11. Calibration의 현재 판단

현재까지의 결과를 종합하면 다음과 같다.

### 구현 완료

- Pixel 외경 측정
- Pixel → mm 변환 기능
- Multi-point 측정
- Median / MAD
- Gradient
- Sub-pixel
- Line fitting
- Reflection 대응
- Calibration 기능
- OK / NG 판정 기능

### 파일럿 검증 수행

- 반복 촬영
- Calibration / Validation 분리
- 촬영거리 비교
- 재장착 시험
- Pin Gauge 비교
- 표면거칠기 비교
- ROI 및 Edge 재검토

### 아직 확정되지 않은 부분

- 최종 Pixel → mm Calibration 식
- ±0.010 mm 공차 수준의 독립 정확도 검증
- 촬영 위치 변화에 대한 완전한 안정성
- Edge 오선택 제거
- 표면거칠기의 정량 영향
- 측정 불확도

따라서 현재 프로젝트 단계는:

> **Calibration 기능 구현 및 파일럿 검증 완료, 최종 정밀 Calibration은 추가 검증 필요**

로 정의한다.

---

# 12. 현재 Calibration / Independent Validation 방향

최종 Calibration은 다음 절차로 진행하는 것이 목표이다.

1. 촬영 광학조건 고정
2. 동일 물리적 측정부 유지
3. Edge 품질 Gate 적용
4. 반복 Pixel 안정성 확인
5. 추적 가능한 복수 기준물 확보
6. 기준물의 실제 외경 측정
7. Pixel ↔ mm 대응 데이터 구축
8. 복수 기준점 Calibration 모델 산출
9. Calibration에 사용하지 않은 독립 시편 확보
10. Independent Validation 수행
11. Bias 계산
12. MAE 계산
13. 최대오차 계산
14. 반복성 평가
15. 측정 불확도 검토

---

# 13. 향후 광학계 개선

현재 스마트폰 기반 시스템은 알고리즘 PoC 및 파일럿 검증에는 사용할 수 있으나, 미크론 단위 정밀 Calibration을 위해서는 광학 조건의 안정화가 필요하다.

향후 검토 대상은 다음과 같다.

- 산업용 Global Shutter 카메라
- Telecentric Lens
- Telecentric 또는 Collimated Backlight
- 고정 지그
- 차광 구조
- 추적 가능한 기준물
- 동일 높이 및 동일 광축 유지

이를 통해 촬영 배율, Perspective, Z 방향 위치 변화 및 Edge 불안정 영향을 최소화하는 것이 목표이다.

---

# 14. 전체 시스템에서의 Calibration 역할

전체 시스템의 처리 흐름은 다음과 같다.

```text
이미지 입력
    ↓
YOLO Measurement ROI 탐지
    ↓
OpenCV Edge 검출
    ↓
31-point 측정
    ↓
Median / MAD
    ↓
Gradient / Sub-pixel
    ↓
Line Fitting
    ↓
Reflection 대응
    ↓
Pixel 외경
    ↓
Calibration
    ↓
mm 외경
    ↓
Independent Validation
    ↓
규격 비교
    ↓
OK / NG
```

각 기능의 역할은 다음과 같다.

- **YOLO** : 어디를 측정할 것인가
- **OpenCV** : Pixel 기준 외경이 얼마인가
- **Calibration** : Pixel을 실제 mm로 어떻게 변환할 것인가
- **Validation** : 변환된 측정값이 실제 기준값과 얼마나 일치하는가

---

# 15. 결론

본 프로젝트의 Calibration은 Day016의 단일 기준점 변환 구현에서 시작하여, 1차·2차·3차 측정을 통해 반복성, ROI, 촬영배율, 반사, Edge 선택 및 검증 구조를 단계적으로 개선하였다.

초기에는 하나의 Pixel 값을 mm로 변환하는 기능 구현이 중심이었으나, 후속 실험을 통해 정밀측정에서는 Calibration 식 자체보다 **촬영조건과 Edge 검출의 안정성이 선행되어야 한다**는 점을 확인하였다.

3차 측정에서는 동일 측정부를 기준으로 ROI를 재정의하고 V3 Reflection 대응 알고리즘을 적용하여 Calibration 관계를 다시 검토하였다.

일부 안정 데이터에서는 기준 외경과 Pixel값의 순서성이 회복되었으나, 기준값 범위가 좁고 Pixel 변동 및 Edge 선택 영향이 남아 있어 최종 Calibration 식으로 확정하지 않았다.

따라서 현재 단계의 핵심 성과는 다음과 같다.

> **Pixel → mm Calibration 기능 구현, Calibration / Independent Validation 구조 확립, 그리고 정밀측정 성능을 제한하는 촬영조건 및 Edge 안정성 요인 규명**

향후 산업용 광학계와 추적 가능한 복수 기준물을 이용하여 Calibration 및 Independent Validation을 수행하고, 최종 측정 정확도와 측정 불확도를 검증할 예정이다.
개발단계 Calibration이므로
최종 측정 정확도 검증으로 해석하지 않는다.

향후 복수 기준물과 독립적인 검증 데이터를 이용하여
Calibration 정확도와 측정시스템 성능을
별도로 검증할 필요가 있다.
