
# Current Calibration / Independent Validation

## 1. 목적

본 문서는 기본 Calibration, 1차 측정, 2차 측정, 3차 측정을 거친 이후 현재 샤프트 외경 자동측정 시스템의 Calibration 및 Independent Validation 상태를 정리하기 위한 것이다.

현재 프로젝트의 핵심 목표는 단순히 Pixel → mm 변환식을 만드는 것이 아니라,

> 동일한 촬영조건과 동일한 물리적 측정부에서 반복 가능하고 독립적으로 검증 가능한 정밀 측정구조를 확보하는 것

이다.

---

## 2. 현재 단계

현재 프로젝트는 다음 단계에 있다.

```text
기본 Calibration 구현
        ↓
1차 측정
실제 촬영환경 적용
        ↓
2차 측정
Calibration / Validation 분리
        ↓
3차 측정
촬영조건 + ROI + Edge 안정성 재검토
        ↓
현재
Calibration 후보 관계 검토 완료
Independent Validation 추가 필요
```

현재 상태는 다음과 같이 정의한다.

> **Calibration 기능 구현 및 파일럿 검증 수행 완료, 최종 정밀 Calibration과 Independent Validation은 추가 검증 필요**

---

## 3. 현재까지 구현된 기능

현재 시스템에는 다음 기능이 구현되어 있다.

### ROI 탐색

- YOLO 기반 `measurement_roi` 탐지
- 실제 외경 측정부 위치 자동 탐색

### 정밀 Edge 측정

- 상·하 Edge 검출
- Multi-point 측정
- 31-point 측정
- Median
- MAD
- Gradient 기반 Edge
- Sub-pixel
- Line fitting
- Reflection 대응

### Calibration

- Pixel → mm 변환 구조
- 복수 기준값 기반 Calibration 검토
- Calibration과 Validation 데이터 분리 구조

### 판정

- mm 단위 외경 산출
- 규격 비교
- OK / NG 판정 구조

---

## 4. 현재 Calibration 판단

3차 측정에서는 실제 측정부 기준 ROI를 다시 정의하고 V3 Reflection 측정엔진을 이용하여 Calibration 후보 데이터를 재검토하였다.

일부 안정 데이터에서는 기준 외경과 Pixel값의 순서성이 이전보다 개선되었다.

대표적인 Calibration 후보 데이터는 다음과 같다.

| 시편 | 실제 기준값(mm) | 대표 Pixel |
|---|---:|---:|
| NO6 | 20.011 | 약 750.040 |
| NO2 | 20.020 | 약 749.688 |
| NO3 | 20.028 | 약 748.608 |

다만 다음 이유로 최종 Calibration 식으로 확정하지 않았다.

- 기준 외경 범위가 약 17 μm로 매우 좁음
- 촬영 간 Pixel 변동 존재
- Edge 오선택 가능성 존재
- 실제 외경 증가와 Pixel 변화 방향에 대한 추가 물리 검증 필요
- Calibration 데이터 수가 제한적임

따라서 현재 Calibration 결과는 **후보 관계**로 관리한다.

---

## 5. Independent Validation의 의미

Calibration에 사용한 동일 시편으로 다시 정확도를 평가하면 실제 성능을 과대평가할 수 있다.

따라서 최종 성능 검증에서는 Calibration에 사용하지 않은 별도의 시편을 이용해야 한다.

구조는 다음과 같다.

```text
Calibration Sample
        ↓
Pixel ↔ mm 관계 산출
        ↓
Calibration Model
        ↓
Independent Validation Sample
        ↓
Vision 측정
        ↓
실제 기준값과 비교
```

Independent Validation에서는 최소한 다음 지표를 확인한다.

- Bias
- MAE
- 최대오차
- 반복 STD
- CV
- OK / NG 판정 일치율

---

## 6. 현재 남아 있는 주요 리스크

### 6.1 촬영 Scale 변화

스마트폰과 일반 렌즈 환경에서는 제품의 높이 및 카메라와의 거리 변화에 따라 Pixel Scale이 변할 수 있다.

따라서 촬영거리와 제품 위치를 엄격하게 고정할 필요가 있다.

---

### 6.2 Edge 오선택

표면 반사나 내부 명암 경계가 실제 외곽선보다 강하게 나타날 경우 잘못된 Edge를 선택할 수 있다.

이 문제는 최종 Calibration 정확도에 직접적인 영향을 줄 수 있다.

---

### 6.3 기준값 범위 부족

현재 Calibration 후보 기준값 범위는 매우 좁다.

좁은 범위에서는 작은 Pixel 오차도 Calibration 기울기에 큰 영향을 줄 수 있다.

따라서 보다 넓은 외경 범위의 기준물 확보가 필요하다.

---

### 6.4 반복 측정 안정성

일부 시편에서는 반복 촬영 시 Pixel값 이동과 이상값이 확인되었다.

따라서 Calibration 모델 확정 전에 반복성 확보가 선행되어야 한다.

---

### 6.5 표면거칠기 영향

표면거칠기와 Edge MAD 사이에 일부 경향은 관찰되었으나 현재 데이터만으로 직접적인 인과관계를 확정할 수 없다.

현재는 탐색적 분석 결과로 관리한다.

---

## 7. Pin Gauge 활용 방향

Pin Gauge는 촬영 Scale 변화를 확인하기 위한 보조 기준으로 검토하였다.

현재 데이터에서는 Pin을 이용한 직접 보정 후 반복 CV가 오히려 증가하는 사례가 나타났다.

따라서 현재 단계에서는 Pin Gauge를:

> 외경값 직접 보정보다 촬영 Scale 및 촬영환경 변화 진단용 기준

으로 활용하는 것이 적절하다고 판단한다.

향후에는 샤프트 목표 외경에 가까운 복수 기준물을 사용하여 Calibration 선형성을 확인할 필요가 있다.

---

## 8. 현재 측정시스템의 해석 범위

현재 시스템은 다음 수준으로 해석한다.

### 가능한 표현

- YOLO와 OpenCV를 이용한 End-to-End 측정 구조 구현
- Pixel → mm Calibration 기능 구현
- 반복 촬영 기반 파일럿 검증 수행
- Calibration / Validation 분리 구조 구축
- ROI, 촬영배율, 반사, Edge 오선택 등의 핵심 제한요인 확인

### 현재 사용하지 않는 표현

- ±0.010 mm 정밀도 확보 완료
- 양산 측정시스템 검증 완료
- 미크론 단위 측정 정확도 확보
- 최종 Calibration 완료

현재 결과는 **PoC 및 파일럿 검증 단계**로 판단한다.

---

## 9. 최종 Calibration Gate

다음 조건을 만족한 이후 최종 Calibration 모델을 확정한다.

### Gate 1. 촬영조건 고정

- 카메라 위치 고정
- 촬영거리 고정
- 제품 높이 고정
- 광축 90° 유지
- 조명조건 고정
- 차광 적용

### Gate 2. Edge 안정성

- 실제 외곽 Edge 반복 검출
- 내부 반사 Edge 억제
- 이상 Edge 자동 거부
- 반복 Pixel 안정성 확보

### Gate 3. 기준물

- 추적 가능한 실제 기준값 확보
- 복수 외경 기준물 확보
- 목표 외경 주변의 충분한 Calibration 범위 확보

### Gate 4. Calibration

- Pixel ↔ mm 선형성 검토
- Calibration 모델 산출
- Calibration Residual 평가

### Gate 5. Independent Validation

- Calibration 미사용 시편 적용
- Bias 평가
- MAE 평가
- 최대오차 평가
- 반복성 평가
- OK / NG 판정 성능 평가

---

## 10. 향후 산업용 광학계 검증

현재 스마트폰 기반 시스템은 알고리즘 개발과 파일럿 검증에는 활용할 수 있으나, 미크론 단위 정밀 측정을 위해서는 광학계 안정화가 필요하다.

향후 검토 대상은 다음과 같다.

- 산업용 Global Shutter Camera
- Telecentric Lens
- Telecentric 또는 Collimated Backlight
- 고정 지그
- 무광 차광 구조
- 추적 가능한 기준물
- 동일 높이 및 동일 광축 유지

이 구조를 통해 Perspective, Z 위치 변화, Scale 변화 및 Edge 불안정 영향을 줄이는 것이 목표이다.

---

## 11. 최종 검증 절차

최종 Calibration 및 Independent Validation은 다음 절차로 수행한다.

```text
광학조건 고정
    ↓
기준물 확보
    ↓
반복 Pixel 안정성 확인
    ↓
복수 기준점 Calibration
    ↓
Calibration 모델 산출
    ↓
Independent Validation Sample 측정
    ↓
Bias / MAE / Max Error 평가
    ↓
반복성 평가
    ↓
측정 불확도 검토
    ↓
최종 OK / NG 성능 검증
```

---

## 12. 현재 결론

현재까지의 측정을 통해 Pixel → mm Calibration 기능과 Calibration / Independent Validation 구조는 구현하였다.

또한 1차~3차 측정을 통해 정밀 측정성능을 제한하는 주요 요인이 단순한 Calibration 식 자체보다 다음 조건에 있다는 점을 확인하였다.

- 촬영조건 안정성
- ROI 일관성
- 실제 외곽 Edge 선택
- 반복 Pixel 안정성
- 충분한 Calibration 기준값 범위

따라서 현재 단계에서는 최종 Calibration 식을 성급하게 확정하지 않고, 측정 Pixel의 물리적 안정성과 독립 Validation 조건을 먼저 확보하는 것을 우선한다.

현재 프로젝트 상태는 다음과 같이 정리한다.

> **End-to-End 측정 기능 구현 + Calibration 파일럿 검증 수행 + 정밀측정 제한요인 규명**

향후 산업용 광학계와 복수 기준물을 적용한 Calibration 및 Independent Validation을 통해 최종 측정 정확도와 측정 불확도를 검증할 예정이다.
