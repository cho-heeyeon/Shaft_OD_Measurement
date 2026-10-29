# Pixel → mm Calibration

## 1. 목적

OpenCV 영상처리에서 계산되는 샤프트 외경은 기본적으로 Pixel 단위이다.

그러나 실제 제조공정에서는 샤프트 외경을 mm 단위로 관리하므로, 영상에서 측정한 Pixel 외경을 실제 길이(mm)로 변환하는 Calibration 과정이 필요하다.

본 프로젝트에서는 Calibration을 한 번에 확정하지 않고, 측정 알고리즘과 촬영조건을 개선하면서 단계적으로 검증하였다.

전체 흐름은 다음과 같다.

```text
기본 Calibration 구현
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

# 3. 기본 Calibration 구현

## 3.1 목적

초기 개발 단계에서는 Pixel 외경을 mm 단위로 변환하는 가장 기본적인 Calibration 기능을 구현하였다.

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

기본 Calibration에서는 다음 순서로 측정하였다.

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

## 3.3 기본 Calibration 결과

초기 개발 단계에서 기록된 값은 다음과 같다.

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

이를 통해 Pixel → mm 변환 기능 자체를 구현하였다.

다만 이 결과는 **단일 기준점으로 계산한 초기 개발단계 Calibration**이다.

동일 기준값으로 변환계수를 계산한 뒤 다시 동일 Pixel값에 적용한 것이므로, 20.020 mm가 다시 계산되는 것은 구조상 자연스럽다.

따라서 이 결과를 독립적인 측정 정확도 검증 결과로 해석하지 않는다.

---

# 4. 1차 측정 — 실제 촬영환경 적용

기본 Calibration 구현 이후 실제 샤프트 영상에 Calibration 구조를 적용하면서 Pixel 외경과 실제 외경의 대응 가능성을 검토하였다.

이 단계에서는 단순히 하나의 이미지에서 값을 변환하는 것이 아니라, 실제 촬영환경에서 반복적으로 사용할 수 있는지 확인하는 방향으로 확장하였다.

### 주요 확인사항

- 촬영거리 변화에 따른 영상 배율 변화
- 시편 위치 및 높이에 따른 Pixel 변화
- ROI 위치 변화
- 표면 반사에 의한 내부 Edge 선택 가능성
- 실제 외곽선이 아닌 잘못된 Edge 선택
- 기준 측정 위치와 영상 측정 위치의 불일치 가능성

이를 통해 단순한 mm/pixel 계수만으로는 정밀 측정 안정성을 확보하기 어렵다는 점을 확인하였다.

---

# 5. 2차 측정 — Calibration과 Validation 분리

2차 측정에서는 Calibration에 사용한 시편과 Calibration에 사용하지 않은 시편을 구분하여 검증하는 방향으로 발전하였다.

목표 구조는 다음과 같다.

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

### 알고리즘 개선

- Multi-point 측정
- 31-point 측정 구조
- Median
- MAD
- Gradient 기반 Edge 검출
- Sub-pixel
- Line fitting

복수 시편을 적용하면서 일부 데이터에서는 실제 외경 변화와 Pixel 변화의 관계가 예상과 다르게 나타났다.

주요 원인 후보는 다음과 같았다.

- 내부 반사 Edge 선택
- YOLO Bounding Box 위치 변화
- 촬영 배율 변화
- 시편 높이 및 깊이 변화
- 기준 계측 위치와 영상 측정 위치 차이

따라서 Calibration 수식 자체보다 **Pixel 측정값의 물리적 안정성 확보가 먼저 필요하다**고 판단하였다.

---

# 6. 3차 측정 — 촬영조건 및 Edge 안정성 재검증

3차 측정에서는 Calibration 문제의 원인을 보다 명확하게 분리하기 위해 촬영조건과 측정영역을 재정비하였다.

### 주요 개선사항

- 스마트폰 1.0× 고정
- V-block 사용
- 백라이트 적용
- 차광 적용
- 카메라와 샤프트 중심 높이 정렬
- 광축 90° 유지
- 촬영거리 고정
- 동일 ROI 적용
- 반복 촬영 수행

또한 YOLO와 정밀 치수 측정의 역할을 다음과 같이 구분하였다.

```text
YOLO = 측정 위치 탐색
OpenCV = 실제 Edge 및 Pixel 외경 측정
```

---

## 6.1 최신 측정 ROI

3차 촬영 분석에서는 실제 측정부를 다시 확인하고 다음 ROI를 적용하였다.

```text
ROI = [8008, 3329, 8280, 4276]
```

ROI의 가로 방향 폭은 272 pixel이며 실제 측정부의 축 방향 길이 10.2 mm에 해당한다.

중앙 5 mm 영역은 샤프트 중심을 기준으로:

```text
좌측 2 mm + 우측 3 mm
```

범위로 설정하였다.

단, `272 px = 10.2 mm` 관계는 **축 방향 ROI 위치 정의용**이며 외경 방향 Pixel → mm Calibration 계수를 의미하지 않는다.

---

## 6.2 V3 Reflection 대응

3차 측정에서는 최신 측정엔진:

```text
measurement_engine_EDGE_V3_REFLECTION.py
```

을 이용하여 반사 및 내부 Edge 오선택 문제를 줄이는 방향으로 개선하였다.

주요 기능은 다음과 같다.

- 상·하 Edge 검출
- 31-point 측정
- Median
- MAD
- Gradient
- Sub-pixel
- Line fitting
- Reflection 대응

Calibration 계산보다 먼저 **실제 외곽 Edge가 반복적으로 안정되게 선택되는지**를 확인하는 방향으로 검증하였다.

---

# 7. 3차 Calibration 재검토

새 ROI와 안정된 Edge 결과를 기준으로 Calibration 후보 데이터를 다시 검토하였다.

일부 안정 데이터에서는 실제 외경 기준값과 Pixel값의 순서성이 다시 나타났다.

| 시편 | 실제 기준값(mm) | 대표 Pixel |
|---|---:|---:|
| NO6 | 20.011 | 약 750.040 |
| NO2 | 20.020 | 약 749.688 |
| NO3 | 20.028 | 약 748.608 |

다만 실제 외경이 증가하면서 측정 Pixel은 감소하는 관계가 나타났다.

수학적으로 Calibration 모델을 계산할 수는 있으나, 일반적인 외경 실루엣 측정에서 기대되는 관계와 다른 부분이 있어 물리적 원인의 추가 확인이 필요하다.

또한 기준 외경의 전체 범위가 약 17 μm로 매우 좁아 작은 Pixel 변동도 Calibration 식에 큰 영향을 줄 수 있다.

따라서 해당 결과를 **최종 Calibration 식으로 확정하지 않았다.**

---

# 8. 반복 측정과 Calibration 안정성

3차 측정에서는 동일 시편을 반복 촬영하여 Pixel 측정 반복성을 함께 확인하였다.

일부 시편에서는 안정적인 결과가 나타났으나 다음 문제가 여전히 확인되었다.

- 촬영 간 Pixel 이동
- Edge 오선택
- 재장착에 따른 위치 변화
- 반사 조건 변화
- 이상 측정값 발생

따라서 Calibration 모델을 확정하기 전에 반복 Pixel 측정의 안정성이 우선 확보되어야 한다.

---

# 9. Pin Gauge 검토

촬영 Scale의 변화를 확인하기 위한 보조 기준으로 Pin Gauge 사용도 검토하였다.

```text
Known Pin Diameter
        ↓
Pin Pixel 측정
        ↓
Scale 변화 확인
```

현재 스마트폰 기반 촬영에서는 Pin을 이용한 직접 보정 후 반복 CV가 오히려 증가하는 결과가 나타났다.

따라서 현재 단계에서 Pin Gauge는 직접적인 치수 보정보다는 **촬영 Scale과 촬영환경 변화 진단용**으로 활용하는 것이 적절하다고 판단하였다.

---

# 10. 표면거칠기 검토

3차 측정에서는 표면거칠기 Ra, Rq, Rz와 Edge 측정 안정성의 관계도 탐색하였다.

Rq 증가와 Edge MAD 증가 사이에 일부 양의 경향이 관찰되었으나, 현재 데이터 수가 제한되어 있고 통계적으로 유의한 관계가 확인된 것은 아니다.

또한 촬영 간 Pixel 변화와 Edge 오선택이 동시에 존재하므로 표면거칠기를 Calibration 오차의 직접 원인으로 확정하지 않는다.

따라서 현재 표면거칠기 분석은 **탐색적 분석**으로 관리한다.

---

# 11. 현재 Calibration 판단

현재까지의 프로젝트 상태는 다음과 같이 정리한다.

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
- OK / NG 판정 구조

### 파일럿 검증 수행

- 반복 촬영
- Calibration / Validation 분리
- 촬영거리 비교
- 재장착 시험
- Pin Gauge 비교
- 표면거칠기 비교
- ROI 및 Edge 재검토

### 아직 확정하지 않은 부분

- 최종 Pixel → mm Calibration 식
- ±0.010 mm 공차 수준의 독립 정확도 검증
- 촬영 위치 변화에 대한 안정성
- Edge 오선택 제거
- 표면거칠기의 정량 영향
- 측정 불확도

따라서 현재 프로젝트 단계는 다음과 같이 정의한다.

> **Calibration 기능 구현 및 파일럿 검증 수행, 최종 정밀 Calibration은 추가 검증 필요**

---

# 12. 현재 Calibration / Independent Validation 방향

최종 Calibration 및 Validation은 다음 절차로 진행하는 것을 목표로 한다.

1. 촬영 광학조건 고정
2. 동일 물리적 측정부 유지
3. Edge 품질 Gate 적용
4. 반복 Pixel 안정성 확인
5. 추적 가능한 복수 기준물 확보
6. 기준물 실제 외경 측정
7. Pixel ↔ mm 대응 데이터 구축
8. 복수 기준점 Calibration 모델 산출
9. Calibration에 사용하지 않은 독립 시편 확보
10. Independent Validation
11. Bias 평가
12. MAE 평가
13. 최대오차 평가
14. 반복성 평가
15. 측정 불확도 검토

---

# 13. 향후 광학계 개선

현재 스마트폰 기반 시스템은 알고리즘 PoC 및 파일럿 검증에는 활용할 수 있으나, 미크론 단위의 정밀 Calibration을 위해서는 광학 조건을 추가로 안정화할 필요가 있다.

향후 검토 대상은 다음과 같다.

- 산업용 Global Shutter 카메라
- Telecentric Lens
- Telecentric 또는 Collimated Backlight
- 고정 지그
- 차광 구조
- 추적 가능한 기준물
- 동일 높이 및 동일 광축 유지

---

# 14. 전체 시스템에서의 역할

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

본 프로젝트의 Calibration은 **기본 Pixel → mm 변환 기능 구현**에서 시작하여 1차·2차·3차 측정을 통해 반복성, ROI, 촬영배율, 반사 및 Edge 선택 문제를 단계적으로 검토하였다.

초기에는 Pixel을 mm로 변환하는 기능 구현에 초점을 두었으나, 후속 실험을 통해 정밀측정에서는 Calibration 수식 자체보다 **촬영조건과 Edge 검출 안정성 확보가 선행되어야 한다**는 점을 확인하였다.

3차 측정에서는 동일 측정부를 기준으로 ROI를 재정의하고 V3 Reflection 대응 알고리즘을 적용하여 Calibration 관계를 다시 검토하였다.

일부 안정 데이터에서 기준 외경과 Pixel값의 순서성이 나타났지만, 기준값 범위가 좁고 Pixel 변동 및 Edge 선택 영향이 남아 있기 때문에 최종 Calibration 식으로 확정하지 않았다.

따라서 현재 단계의 핵심 성과는 다음과 같다.

> **Pixel → mm Calibration 기능 구현, Calibration / Independent Validation 구조 확립, 정밀측정 성능을 제한하는 촬영조건 및 Edge 안정성 요인 규명**

향후 산업용 광학계와 추적 가능한 복수 기준물을 이용하여 Calibration 및 Independent Validation을 수행하고 최종 측정 정확도와 측정 불확도를 검증할 예정이다.
